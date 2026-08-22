# Saga Defensive Cybersecurity Profile 1 — 0.24

Saga 0.24 adds a defensive security surface intended for integrity checks, credential storage primitives, network-policy checks, certificate inspection and verified TLS diagnostics. It is not an exploit or malware framework.

## Saga source APIs

`use security` provides:

- `security.sha512(text) -> text`
- `security.hmac_sha256(key, text) -> text`
- `security.constant_equal(a, b) -> bool`
- `security.random_hex(bytes) -> text`
- `security.password_hash(password) -> text`
- `security.password_verify(password, encoded) -> bool`
- `security.file_sha256(path) -> result[text,text]` on Native
- `security.ip_valid(ip) -> bool`
- `security.cidr_contains(cidr, ip) -> result[bool,text]` on Native
- `security.certificate_info(pem) -> result[text,text]` on Native
- `security.tls_probe(host, port, server_name, ca_pem, timeout_ms) -> result[text,text]` on Native

The existing `crypto` module additionally exposes the new SHA-512/HMAC/random/constant-time/password helpers plus authenticated `aes_gcm_encrypt` and `aes_gcm_decrypt`.

## Security properties

- Password storage uses PBKDF2-HMAC-SHA256 with 210,000 iterations, a fresh 16-byte random salt and a 32-byte derived key. Verification rejects malformed encodings and caps attacker-controlled iteration counts at 1,000,000.
- AES-GCM uses a fresh random nonce. Decryption authenticates both ciphertext and caller-supplied AAD and fails on modification.
- Secret text equality uses a constant-time comparison after equal-length checking.
- File SHA-256 is streamed rather than reading the whole file into memory.
- TLS probing keeps certificate and hostname verification enabled, uses system roots plus an optional supplied CA, and requires TLS 1.2 or newer.
- Random values use the operating system cryptographic random source.

## Example

See `examples/security/defensive_audit.saga`. The example executes as Saga source only and demonstrates SHA-512, HMAC, password hashing/verification, CIDR policy checking and AES-GCM authenticated encryption.

## Boundaries

The profile deliberately does not provide credential theft, persistence, stealth, exploit automation, raw attack packet generation or malware deployment helpers. General network APIs still require the operator to apply normal authorization and policy controls. Internal validation is not a substitute for an independent security audit.
