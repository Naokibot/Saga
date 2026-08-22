# Saga Language Governance Charter

## 1. Purpose

The Saga Language Project maintains the language specification, conformance suite, reference implementation and independent implementations in an open, reviewable process.

## 2. Roles

- **Project Leader candidate:** coordinates the draft and represents the project after written consent and proposer acceptance.
- **Specification editors:** maintain normative text and resolve editorial issues.
- **Implementation maintainers:** maintain independent implementations and publish conformance results.
- **Conformance maintainers:** maintain tests independently from implementation-specific behavior.
- **Security and internationalization reviewers:** review the capability model, memory model, Unicode profile and diagnostics.
- **Adopters:** provide verifiable use cases and compatibility feedback.

No person is considered appointed merely because a name appears in an example file. The evidence registry requires a consent document.

## 3. Decisions

1. Editorial corrections may be accepted by two editors when they do not change observable behavior.
2. Behavioral changes require a public Saga RFC, two implementation reports, conformance tests and a recorded decision.
3. Security fixes may use an embargoed review, but the final rationale and compatibility impact shall be published.
4. Normative decisions aim for consensus. If consensus is not reached, a two-thirds vote of non-conflicted voting members is required.
5. A person employed by or contracted to an implementation vendor shall disclose that interest.

## 4. Records

Decisions, nominations, adoption claims and test reports shall have stable identifiers and SHA-256 hashes. The `saga standards` registry maintains a hash-chained event log, but it does not replace legal signatures or ISO records.

## 5. Appeals

An appeal shall identify the disputed decision, the affected clause and the requested remedy. A reviewer who did not author the disputed change shall prepare the response.
