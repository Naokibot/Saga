# Saga Language Specification 1.0 — independent review guide

## Review set

- `SAGA_LANGUAGE_SPECIFICATION_1.0_FINAL_CANDIDATE.md`
- `spec/saga-1.0.ebnf`
- `spec/SAGA_SELF_HOSTING_PROFILE_1.0_FINAL_CANDIDATE.md`
- `spec/SAGA_NATIVE_DISTRIBUTION_PROFILE_1.0_FINAL_CANDIDATE.md`
- `docs/design/STABILITY_CONTRACT_1.0_FINAL_CANDIDATE.md`
- current conformance corpora and both implementations

Start with:

```sh
python tools/spec_review_lint.py
python tools/reviewer_preflight.py --quick
```

## What must be reviewed

Check normative terminology, grammar/semantics consistency, types and conversions, errors/exceptions, ownership/resource behavior, concurrency/memory behavior, modules/generics/OOP, implementation-defined behavior, compatibility promises, diagnostic/non-normative boundaries, and whether the conformance corpus actually distinguishes required behavior.

## Exact-bytes approval

The project does not self-promote the candidate to Final. The independent reviewer signs `review/spec/spec-review-attestation-template.json` after filling the reviewer identity/date and using the exact hashes printed by:

```sh
python tools/spec_review_lint.py
python - <<'PY'
import hashlib
from pathlib import Path
from tools.verify_spec_review_attestation import proposed_final_bytes
print('candidate_sha256', hashlib.sha256(Path('SAGA_LANGUAGE_SPECIFICATION_1.0_FINAL_CANDIDATE.md').read_bytes()).hexdigest())
print('grammar_sha256', hashlib.sha256(Path('spec/saga-1.0.ebnf').read_bytes()).hexdigest())
print('proposed_final_sha256', hashlib.sha256(proposed_final_bytes()).hexdigest())
PY
```

Sign the canonical JSON `payload` with an independently controlled Ed25519 key and place the base64 signature in `signature_ed25519_base64`. Deliver the public key separately from the reviewed archive where practical.

Verify and promote only after approval:

```sh
python tools/verify_spec_review_attestation.py review-attestation.json reviewer-public-key.hex
python tools/promote_spec_final.py review-attestation.json reviewer-public-key.hex
```

Any unresolved normative issue means `decision` must not be `APPROVE` and the candidate remains non-Final.
