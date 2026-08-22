# Saga standardization readiness — Language Edition 1.0 RC1

This document describes engineering preparation for possible international standardization. It does not claim ISO, IEC, JTC 1, Ecma, INCITS, JISC, or another standards body's approval.

## Engineering baseline included in the project

- normative English language specification and EBNF;
- stable Unicode and locale-independent lexical rules;
- machine-stable diagnostics independent of translated prose;
- independent Native and Python Standard Core implementations;
- cross-implementation conformance tests;
- fixed-point Saga-sourced compiler proof;
- reproducible package and compatibility snapshots;
- explicit optional profiles rather than implementation-specific behavior in Standard Core;
- normative Saga Game Profile RC1 with backend-independent semantics;
- evidence-backed Native `saga standards` registry with SHA-256 evidence storage and a hash-chained event log.

## External gates the source tree cannot self-certify

The readiness registry intentionally requires evidence for the following before it can report a submission-ready evidence set:

1. an eligible standards proposer with evidence;
2. a Project Leader who has explicitly consented;
3. a base document or outline and market-relevance evidence before proposal submission;
4. the applicable committee context, so NP participation thresholds can be evaluated;
5. after an NP ballot, at least a two-thirds majority of P-members voting and active participation commitments from at least four P-members when the committee has 16 or fewer P-members, otherwise at least five (subject to the current Directives and any committee-specific increase/exception);
6. for the project's engineering-maturity gate, a multinational expert team, multi-country adoption, a genuinely independent second implementation and an independent conformance laboratory;
7. an intact tamper-evident registry chain.

These are project readiness gates, not a substitute for the formal rules of a standards organization. Actual proposal eligibility and ballot procedures are governed by the organization receiving the submission.

## Native evidence workflow

```bash
saga standards --root .saga-standards init
saga standards --root .saga-standards record set-proposer ...
saga standards --root .saga-standards record nominate-leader ...
saga standards --root .saga-standards record set-base-document ...
saga standards --root .saga-standards record set-committee ...
saga standards --root .saga-standards record record-np-ballot ...
saga standards --root .saga-standards status --json
saga standards --root .saga-standards verify --json
```

Every material claim stores a copy of its evidence under a SHA-256 content address. Registry events include the previous event digest, producing a tamper-evident chain that `verify` recomputes.

## Standardization design rules for Saga

- Standard Core semantics must not name Python, Go, SDL, OpenGL, a vendor cloud, or a particular operating system.
- Hosted profiles must declare optionality and exact failure behavior.
- Unsupported constructs fail explicitly instead of changing meaning by backend.
- Machine diagnostics, conformance vectors and compatibility manifests are versioned independently from translated prose.
- No release may call itself an International Standard solely because its own test suite passes.
