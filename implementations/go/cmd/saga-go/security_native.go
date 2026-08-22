package main

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/hmac"
	"crypto/rand"
	"crypto/sha256"
	"crypto/sha512"
	"crypto/subtle"
	"crypto/tls"
	"crypto/x509"
	"encoding/hex"
	"encoding/json"
	"encoding/pem"
	"fmt"
	"io"
	"net"
	"os"
	"strconv"
	"strings"
	"time"
)

const (
	sagaPasswordIterations = 210000
	sagaPasswordSaltBytes  = 16
	sagaPasswordKeyBytes   = 32
)

func pbkdf2SHA256(password, salt []byte, iterations, keyLen int) []byte {
	if iterations <= 0 || keyLen <= 0 {
		return nil
	}
	hLen := sha256.Size
	blocks := (keyLen + hLen - 1) / hLen
	out := make([]byte, 0, blocks*hLen)
	var counter [4]byte
	for block := 1; block <= blocks; block++ {
		counter[0] = byte(block >> 24)
		counter[1] = byte(block >> 16)
		counter[2] = byte(block >> 8)
		counter[3] = byte(block)
		mac := hmac.New(sha256.New, password)
		_, _ = mac.Write(salt)
		_, _ = mac.Write(counter[:])
		u := mac.Sum(nil)
		t := append([]byte(nil), u...)
		for j := 1; j < iterations; j++ {
			mac = hmac.New(sha256.New, password)
			_, _ = mac.Write(u)
			u = mac.Sum(nil)
			for k := range t {
				t[k] ^= u[k]
			}
		}
		out = append(out, t...)
	}
	return out[:keyLen]
}

func sagaPasswordHash(password string) (string, error) {
	salt := make([]byte, sagaPasswordSaltBytes)
	if _, err := rand.Read(salt); err != nil {
		return "", err
	}
	derived := pbkdf2SHA256([]byte(password), salt, sagaPasswordIterations, sagaPasswordKeyBytes)
	return fmt.Sprintf("pbkdf2-sha256$%d$%s$%s", sagaPasswordIterations, hex.EncodeToString(salt), hex.EncodeToString(derived)), nil
}

func sagaPasswordVerify(password, encoded string) bool {
	parts := strings.Split(encoded, "$")
	if len(parts) != 4 || parts[0] != "pbkdf2-sha256" {
		return false
	}
	iterations, err := strconv.Atoi(parts[1])
	if err != nil || iterations < 10000 || iterations > 1000000 {
		return false
	}
	salt, err := hex.DecodeString(parts[2])
	if err != nil || len(salt) < 8 || len(salt) > 64 {
		return false
	}
	expected, err := hex.DecodeString(parts[3])
	if err != nil || len(expected) < 16 || len(expected) > 64 {
		return false
	}
	actual := pbkdf2SHA256([]byte(password), salt, iterations, len(expected))
	return subtle.ConstantTimeCompare(actual, expected) == 1
}

func sagaAESGCMEncrypt(keyHex, plaintext, aad string) (string, error) {
	key, err := hex.DecodeString(keyHex)
	if err != nil {
		return "", fmt.Errorf("key_hex must be hexadecimal")
	}
	if len(key) != 16 && len(key) != 24 && len(key) != 32 {
		return "", fmt.Errorf("AES key must be 16, 24, or 32 bytes")
	}
	block, err := aes.NewCipher(key)
	if err != nil {
		return "", err
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return "", err
	}
	nonce := make([]byte, gcm.NonceSize())
	if _, err := rand.Read(nonce); err != nil {
		return "", err
	}
	sealed := gcm.Seal(nil, nonce, []byte(plaintext), []byte(aad))
	payload := append(nonce, sealed...)
	return hex.EncodeToString(payload), nil
}

func sagaAESGCMDecrypt(keyHex, payloadHex, aad string) (string, error) {
	key, err := hex.DecodeString(keyHex)
	if err != nil {
		return "", fmt.Errorf("key_hex must be hexadecimal")
	}
	if len(key) != 16 && len(key) != 24 && len(key) != 32 {
		return "", fmt.Errorf("AES key must be 16, 24, or 32 bytes")
	}
	payload, err := hex.DecodeString(payloadHex)
	if err != nil {
		return "", fmt.Errorf("ciphertext_hex must be hexadecimal")
	}
	block, err := aes.NewCipher(key)
	if err != nil {
		return "", err
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return "", err
	}
	if len(payload) < gcm.NonceSize()+gcm.Overhead() {
		return "", fmt.Errorf("AES-GCM payload is too short")
	}
	plain, err := gcm.Open(nil, payload[:gcm.NonceSize()], payload[gcm.NonceSize():], []byte(aad))
	if err != nil {
		return "", fmt.Errorf("authentication failed")
	}
	if !validUTF8String(string(plain)) {
		return "", fmt.Errorf("decrypted plaintext is not valid UTF-8")
	}
	return string(plain), nil
}

func certificateInfo(cert *x509.Certificate) map[string]any {
	return map[string]any{
		"subject":            cert.Subject.String(),
		"issuer":             cert.Issuer.String(),
		"serial":             cert.SerialNumber.String(),
		"not_before_unix_ms": cert.NotBefore.UnixMilli(),
		"not_after_unix_ms":  cert.NotAfter.UnixMilli(),
		"dns_names":          cert.DNSNames,
		"ip_addresses": func() []string {
			out := make([]string, len(cert.IPAddresses))
			for i, ip := range cert.IPAddresses {
				out[i] = ip.String()
			}
			return out
		}(),
		"signature_algorithm":  cert.SignatureAlgorithm.String(),
		"public_key_algorithm": cert.PublicKeyAlgorithm.String(),
		"is_ca":                cert.IsCA,
	}
}

func sagaTLSProbe(host string, port int, serverName, caPEM string, timeoutMS int) (string, error) {
	if host == "" {
		return "", fmt.Errorf("host required")
	}
	if port < 1 || port > 65535 {
		return "", fmt.Errorf("port must be 1..65535")
	}
	if timeoutMS < 1 || timeoutMS > 60000 {
		return "", fmt.Errorf("timeout_ms must be 1..60000")
	}
	if serverName == "" {
		serverName = host
	}
	roots, err := x509.SystemCertPool()
	if err != nil || roots == nil {
		roots = x509.NewCertPool()
	}
	if strings.TrimSpace(caPEM) != "" && !roots.AppendCertsFromPEM([]byte(caPEM)) {
		return "", fmt.Errorf("ca_pem contains no parseable certificate")
	}
	dialer := &net.Dialer{Timeout: time.Duration(timeoutMS) * time.Millisecond}
	cfg := &tls.Config{ServerName: serverName, RootCAs: roots, MinVersion: tls.VersionTLS12}
	conn, err := tls.DialWithDialer(dialer, "tcp", net.JoinHostPort(host, strconv.Itoa(port)), cfg)
	if err != nil {
		return "", err
	}
	defer conn.Close()
	state := conn.ConnectionState()
	if len(state.PeerCertificates) == 0 {
		return "", fmt.Errorf("peer sent no certificate")
	}
	info := map[string]any{
		"tls_version":          tlsVersionName(state.Version),
		"cipher_suite":         tls.CipherSuiteName(state.CipherSuite),
		"server_name":          serverName,
		"negotiated_protocol":  state.NegotiatedProtocol,
		"verified_chain_count": len(state.VerifiedChains),
		"certificate":          certificateInfo(state.PeerCertificates[0]),
	}
	b, err := json.Marshal(info)
	if err != nil {
		return "", err
	}
	return string(b), nil
}

func tlsVersionName(v uint16) string {
	switch v {
	case tls.VersionTLS13:
		return "TLS1.3"
	case tls.VersionTLS12:
		return "TLS1.2"
	case tls.VersionTLS11:
		return "TLS1.1"
	case tls.VersionTLS10:
		return "TLS1.0"
	default:
		return fmt.Sprintf("0x%04x", v)
	}
}

func sagaCertificateInfo(pemText string) (string, error) {
	block, _ := pem.Decode([]byte(pemText))
	if block == nil || block.Type != "CERTIFICATE" {
		return "", fmt.Errorf("PEM certificate required")
	}
	cert, err := x509.ParseCertificate(block.Bytes)
	if err != nil {
		return "", err
	}
	b, err := json.Marshal(certificateInfo(cert))
	if err != nil {
		return "", err
	}
	return string(b), nil
}

func (i *Interpreter) callSecurityModule(module, name string, args []Value, t Token) (Value, bool, error) {
	bad := func(msg string) (Value, bool, error) { return nil, true, i.rerr(t, "SAGA-R150", msg) }
	result := func(v string, err error) (Value, bool, error) {
		if err != nil {
			return ResultValue{OK: false, Value: err.Error()}, true, nil
		}
		return ResultValue{OK: true, Value: v}, true, nil
	}
	if module == "crypto" {
		switch name {
		case "sha512":
			if len(args) != 1 {
				return bad("crypto.sha512(text)")
			}
			s, ok := args[0].(string)
			if !ok {
				return bad("text required")
			}
			h := sha512.Sum512([]byte(s))
			return hex.EncodeToString(h[:]), true, nil
		case "hmac_sha256":
			if len(args) != 2 {
				return bad("crypto.hmac_sha256(key,text)")
			}
			key, kok := args[0].(string)
			text, tok := args[1].(string)
			if !kok || !tok {
				return bad("key and text required")
			}
			mac := hmac.New(sha256.New, []byte(key))
			_, _ = mac.Write([]byte(text))
			return hex.EncodeToString(mac.Sum(nil)), true, nil
		case "random_hex":
			if len(args) != 1 {
				return bad("crypto.random_hex(bytes)")
			}
			n, e := numberToInt(args[0])
			if e != nil || n < 1 || n > 4096 {
				return bad("bytes must be 1..4096")
			}
			b := make([]byte, n)
			if _, e = rand.Read(b); e != nil {
				return nil, true, i.rerr(t, "SAGA-R160", e.Error())
			}
			return hex.EncodeToString(b), true, nil
		case "constant_equal":
			if len(args) != 2 {
				return bad("crypto.constant_equal(a,b)")
			}
			a, aok := args[0].(string)
			b, bok := args[1].(string)
			if !aok || !bok {
				return bad("text arguments required")
			}
			if len(a) != len(b) {
				return false, true, nil
			}
			return subtle.ConstantTimeCompare([]byte(a), []byte(b)) == 1, true, nil
		case "password_hash":
			if len(args) != 1 {
				return bad("crypto.password_hash(password)")
			}
			p, ok := args[0].(string)
			if !ok {
				return bad("password must be text")
			}
			v, e := sagaPasswordHash(p)
			if e != nil {
				return nil, true, i.rerr(t, "SAGA-R160", e.Error())
			}
			return v, true, nil
		case "password_verify":
			if len(args) != 2 {
				return bad("crypto.password_verify(password,encoded)")
			}
			p, pok := args[0].(string)
			enc, eok := args[1].(string)
			if !pok || !eok {
				return bad("text arguments required")
			}
			return sagaPasswordVerify(p, enc), true, nil
		case "aes_gcm_encrypt":
			if len(args) != 3 {
				return bad("crypto.aes_gcm_encrypt(key_hex,plaintext,aad)")
			}
			k, kok := args[0].(string)
			p, pok := args[1].(string)
			aad, aok := args[2].(string)
			if !kok || !pok || !aok {
				return bad("text arguments required")
			}
			return result(sagaAESGCMEncrypt(k, p, aad))
		case "aes_gcm_decrypt":
			if len(args) != 3 {
				return bad("crypto.aes_gcm_decrypt(key_hex,ciphertext_hex,aad)")
			}
			k, kok := args[0].(string)
			p, pok := args[1].(string)
			aad, aok := args[2].(string)
			if !kok || !pok || !aok {
				return bad("text arguments required")
			}
			return result(sagaAESGCMDecrypt(k, p, aad))
		}
	}
	if module == "security" {
		switch name {
		case "sha512", "hmac_sha256", "random_hex", "constant_equal", "password_hash", "password_verify":
			return i.callSecurityModule("crypto", name, args, t)
		case "file_sha256":
			if len(args) != 1 {
				return bad("security.file_sha256(path)")
			}
			p, ok := args[0].(string)
			if !ok || p == "" {
				return bad("path must be text")
			}
			f, e := os.Open(p)
			if e != nil {
				return ResultValue{OK: false, Value: e.Error()}, true, nil
			}
			defer f.Close()
			h := sha256.New()
			if _, e = io.Copy(h, f); e != nil {
				return ResultValue{OK: false, Value: e.Error()}, true, nil
			}
			return ResultValue{OK: true, Value: hex.EncodeToString(h.Sum(nil))}, true, nil
		case "ip_valid":
			if len(args) != 1 {
				return bad("security.ip_valid(ip)")
			}
			s, ok := args[0].(string)
			if !ok {
				return bad("ip must be text")
			}
			return net.ParseIP(s) != nil, true, nil
		case "cidr_contains":
			if len(args) != 2 {
				return bad("security.cidr_contains(cidr,ip)")
			}
			cidr, cok := args[0].(string)
			ipText, iok := args[1].(string)
			if !cok || !iok {
				return bad("cidr and ip must be text")
			}
			ip := net.ParseIP(ipText)
			if ip == nil {
				return ResultValue{OK: false, Value: "invalid IP address"}, true, nil
			}
			_, network, e := net.ParseCIDR(cidr)
			if e != nil {
				return ResultValue{OK: false, Value: e.Error()}, true, nil
			}
			return ResultValue{OK: true, Value: network.Contains(ip)}, true, nil
		case "certificate_info":
			if len(args) != 1 {
				return bad("security.certificate_info(pem)")
			}
			p, ok := args[0].(string)
			if !ok {
				return bad("PEM must be text")
			}
			return result(sagaCertificateInfo(p))
		case "tls_probe":
			if len(args) != 5 {
				return bad("security.tls_probe(host,port,server_name,ca_pem,timeout_ms)")
			}
			host, hok := args[0].(string)
			port, e1 := numberToInt(args[1])
			sn, sok := args[2].(string)
			ca, cok := args[3].(string)
			tm, e2 := numberToInt(args[4])
			if !hok || e1 != nil || !sok || !cok || e2 != nil {
				return bad("host text, port int, server_name text, ca_pem text, timeout_ms int required")
			}
			return result(sagaTLSProbe(host, port, sn, ca, tm))
		}
		return nil, true, i.rerr(t, "SAGA-R123", "unknown security member: "+name)
	}
	return nil, false, nil
}
