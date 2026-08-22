# Saga 0.17 third-party conformance lab kit

This kit is deliberately incapable of self-certifying Saga as independently certified. An organization that is independent of the Saga implementation team runs `run_lab.py` on hardware it controls, reviews the raw output, fills its own signature/certificate fields, signs the resulting evidence with its normal accreditation process, and returns the evidence artifact.

Example:
`python run_lab.py --saga /opt/saga/bin/saga --source-root .. --lab-name "Example Independent Lab" --lab-contact "lab@example.test" --output evidence.json`

The project may verify the structure/hash of returned evidence, but only the named lab can make the independent-attestation claim.

## Cryptographic attestation
After reviewing a passing evidence file, the external lab should seal it with a lab-owned Ed25519 key:

`python seal_evidence.py evidence.json --private-key lab-ed25519-private.pem --public-key lab-ed25519-public.pem`

A recipient verifies both structure and signature with `python verify_evidence.py evidence.json`. The Saga project must not create or control the lab private key for an independent certification claim.
