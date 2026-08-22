# Saga Compatibility and Change Procedure

## Versioning

Saga uses `MAJOR.MINOR.PATCH`.

- **PATCH:** diagnostics, performance or security corrections that do not intentionally change accepted conforming programs.
- **MINOR:** additive syntax, APIs or opt-in behavior. Deprecations may begin.
- **MAJOR:** removal, incompatible grammar changes or changed observable semantics.

Before 1.0, minor versions may refine provisional hosted modules, but the normative core still follows the removal procedure below.

## Removal procedure

1. Publish a Saga RFC describing motivation, alternatives, migration and security impact.
2. Add a deprecation diagnostic for at least two minor releases.
3. Provide an automated migration where practical.
4. Obtain test results from the Python and Go implementations.
5. Update the conformance suite before acceptance.
6. Remove only in a new major version unless a documented security emergency requires otherwise.

## Automated compatibility gate

`tools/api_snapshot.py` records keywords, built-ins, standard-module functions and the grammar hash. `tools/compatibility_check.py` rejects removed public names within the same major release. Grammar changes always require human semantic review even when no API name is removed.

## Specification corrections

An editorial corrigendum cannot change program output, accepted syntax or required diagnostics. A semantic defect report shall identify affected clauses and include a conformance test.
