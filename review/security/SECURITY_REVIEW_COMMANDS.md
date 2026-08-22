# Independent security review — evidence commands

Before review:

```sh
python tools/review_evidence.py --verify release/source-manifest-0.26.2.json
python tools/reviewer_preflight.py
```

Perform the source and dynamic review described by `SECURITY_AUDIT_SCOPE.md`. The final report must be a stable file whose SHA-256 can be attested. Fill `review/security/attestation-template.json` with the exact source-manifest/report hashes, audited scope, methods and open finding counts.

The reviewer signs only the canonical `payload` JSON using an independently controlled Ed25519 key. Deliver the public key out of band where practical.

Project-side verification:

```sh
python tools/verify_external_security_attestation.py \
  security-attestation.json reviewer-public-key.hex \
  --report independent-security-report.pdf \
  --source-manifest release/source-manifest-0.26.2.json
```

GA requires `critical_open=0`, `high_open=0`, `independent=true`, `decision=PASS`, all mandatory scope areas, and both source-review and dynamic-testing methods. Medium/low findings remain visible in the evidence and should include disposition.
