# Evidence-backed standardization registry

Saga Native includes a local, evidence-backed readiness registry. It is designed to prevent the project from turning aspirations into unsupported standards claims.

Initialize:

```bash
saga standards --root .saga-standards init
```

Record evidence-backed facts:

```bash
saga standards --root .saga-standards record set-proposer --name "..." --type national_body --country JP --evidence evidence.pdf
saga standards --root .saga-standards record nominate-leader --name "..." --email leader@example.org --organization "..." --country JP --consent consent.pdf
saga standards --root .saga-standards record set-base-document --title "Saga Language Specification" --evidence draft.pdf
saga standards --root .saga-standards record set-committee --name "JTC 1/SC ..." --p-members 20 --evidence committee-evidence.pdf
# After the official ballot exists:
saga standards --root .saga-standards record record-np-ballot --approvals 12 --rejections 3 --abstentions 2 --evidence ballot-result.pdf
```

Check and verify:

```bash
saga standards --root .saga-standards status --json
saga standards --root .saga-standards verify --json
```

The proposer type is intentionally restricted to recognized proposal-role categories represented by this project (`national_body`, `committee_secretariat`, `committee`, `category_a_liaison`, `technical_management_board`, `chief_executive_officer`). A generic organization cannot mark itself eligible merely by editing a JSON field.

The registry stores evidence under its SHA-256 digest and appends hash-chained events. It does **not** fabricate Project Leader consent, National Body/P-member commitments, adoption, independent implementation, laboratory independence, market demand, or standards-body acceptance. Those facts must come from real external parties.

See `SAGA_STANDARDIZATION_READINESS_1.0_RC1.md`.

`status` separates three categories: pre-submission evidence, NP acceptance evidence, and project engineering maturity. It uses the current 4/5 active-participation threshold according to the recorded P-member count; the actual ballot and any exception remain authoritative only when issued by the responsible standards body.
