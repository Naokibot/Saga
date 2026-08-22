# Saga Defensive Cybersecurity Profile 1 — 0.24.1

Saga 0.24.1 retains the defensive security surface introduced in 0.24 and strengthens its cross-implementation contracts and surrounding network/package boundaries. The profile is intended for integrity checking, credential-storage primitives, authenticated encryption, network-policy checks, certificate inspection and verified TLS diagnostics. It is not an exploit or malware framework.

## Saga source APIs

`use security` provides:

- `security.sha512(text) -> text`
- `security.hmac_sha256(key, text) -> text`
- `security.constant_equal(a, b) -> bool`
- `security.random_hex(bytes) -> text`
- `security.password_hash(password) -> text`
- `security.password_verify(password, encoded) -> bool`
- `security.file_sha256(path) -> result[text,text]`
- `security.ip_valid(ip) -> bool`
- `security.cidr_contains(cidr, ip) -> result[bool,text]`
- `security.certificate_info(pem) -> result[text,text]`
- `security.tls_probe(host, port, server_name, ca_pem, timeout_ms) -> result[text,text]`

The `crypto` module also exposes SHA-512/HMAC/random/constant-time/password helpers plus authenticated AES-GCM encrypt/decrypt.

## Security properties

- Password storage uses PBKDF2-HMAC-SHA256 with 210,000 iterations, a fresh 16-byte random salt and a 32-byte derived key. Verification rejects malformed encodings and caps attacker-controlled encoded iteration counts at 1,000,000.
- AES-GCM uses a fresh random nonce and authenticates ciphertext plus caller-supplied AAD; modification is rejected.
- Secret comparison uses constant-time comparison after length checking.
- File SHA-256 is streamed.
- TLS probing verifies certificate chains and hostnames, can add a caller-supplied CA and requires TLS 1.2 or newer.
- Random values use the operating-system cryptographic random source.
- Python and Native implementations now share the same `result[T,E]` contract for fallible security operations.

## 0.24.1 hardening around the profile

- Native/Python `result` value validation and isolated-task snapshot support are regression-tested.
- HTTP and process resource controls are optional administrator policies rather than fixed language-semantic ceilings.
- Registry package downloads/extraction validate package identity, reject traversal/symlinks/duplicates and apply registry-profile wire/archive bounds.
- Universal App JSON payloads reject duplicate object keys.
- HTTP server text/header boundaries reject invalid UTF-8 and CR/LF header injection.

## Validation

The 0.24.1 validator executes known HMAC-SHA256 and PBKDF2-HMAC-SHA256 vectors, AES-GCM roundtrip and tamper rejection, file hashing, IP/CIDR checks, local X.509 parsing and a real localhost TLS handshake using a generated CA/server chain. The full regression additionally exercises DB cross-process conflicts, symlink persistence, registry archive shape, HTTP/process policies and the Saga source type/runtime path.

## Boundaries

The profile deliberately does not provide credential theft, stealth/persistence helpers, exploit automation, raw attack-packet generation or malware deployment. Internal automated review is not an independent penetration test. Hardware/vendor/account-dependent capabilities require qualification in those real external environments.
