# Independent Conformance Test Handoff

The project supplies a reproducible package, not an independent certification.

An independent laboratory should:

1. obtain the source package through a channel it controls;
2. verify published SHA-256 values;
3. build both implementations without using prebuilt project binaries;
4. run `python conformance/differential.py`;
5. run the full Python unit suite;
6. add negative, fuzzing, Unicode, resource-limit and platform tests of its own;
7. record OS, architecture, toolchain versions and all deviations;
8. sign a report using the laboratory's normal signing process;
9. provide the report through `saga standards add-lab-report`.

The project shall not label a report independent when the testing organization is the proposer, implementation maintainer or a controlled affiliate.
