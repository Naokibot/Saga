# New Work Item Proposal — Draft Input

**Proposed title:** Information technology — Programming languages — Saga  
**Proposed deliverable:** International Standard or, if maturity is judged insufficient, Technical Specification  
**Proposed committee:** ISO/IEC JTC 1/SC 22  
**Project leader:** To be nominated through the proposing National Body or eligible liaison organization

## Scope

Standardize a beginner-first, statically checked programming language with exact decimal and rational arithmetic, immutable-by-default bindings, capability-gated hosted effects, structured diagnostics, and portable core semantics.

## Purpose and justification

Programming education often begins with concise dynamic languages, while production systems frequently require stronger static checking, predictable numerical behavior, and explicit security boundaries. Saga proposes a small language core intended to reduce the transition cost between introductory programming and application development.

The proposal should be supported by evidence beyond the reference implementation, including independent implementations or prototype back ends, education trials, production pilots, accessibility studies, international stakeholder interviews, and interoperability requirements.

## Existing work and differentiation

The proposal shall be reviewed against existing SC 22 language standards and language-vulnerability work. Saga should not claim that individual features are novel. The potential standardization value is the defined combination and its conformance profile:

- concise syntax and inference;
- exact base-10 and rational arithmetic by default;
- immutable-by-default local state;
- non-null core;
- capability-scoped external effects;
- beginner-oriented normative diagnostics requirements.

## Initial working draft

`DRAFT_STANDARD.md` and `spec/saga-0.7.ebnf` form the initial outline. They require editorial conversion to the ISO/IEC drafting rules and review by standards professionals.

## Stakeholders to recruit

- programming-language implementers;
- educators and learners;
- application and enterprise developers;
- numerical-computing specialists;
- cybersecurity and language-vulnerability experts;
- accessibility and internationalization specialists;
- tool vendors and package maintainers;
- National Bodies from at least the minimum number required by the applicable proposal ballot.

## Proposed work plan

1. Preliminary study and stakeholder validation.
2. Freeze Saga Core 1.0 semantics.
3. Maintain the Python and Go implementations, broaden their common conformance profile, and obtain independent implementation review.
4. Expand the conformance suite and resolve all unspecified behavior.
5. Submit an NP with a nominated Project Leader and working draft.
6. Address committee comments through WD, CD, enquiry, approval, and publication stages.

## Patent and licensing statement

The proposer should document known patent claims, trademark ownership of the name Saga, reference implementation licensing, and a royalty-free specification policy before submission.

## Market evidence still required

- named organizations willing to implement or deploy;
- named universities or schools willing to evaluate;
- measured learning outcomes;
- portability results on Windows, macOS, Linux, mobile, and embedded targets;
- long-term maintenance and governance commitments;
- localization evidence beyond Japanese and English.
