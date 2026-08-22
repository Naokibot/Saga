# Saga 0.44.0 validation plan and result summary

The release is validated at three levels:

1. **4 kHz scheduler semantics**: 4,000 logical expirations are accumulated over approximately one second and the 250 us period is reported correctly.
2. **4 kHz compute budget**: cached multirotor allocation + compact state-space command + eight-actuator conditioning must have p99 execution below 250 us in the test environment.
3. **Regression**: language core, modules/generics, machine control, fine control, independent Go tests/vet, self-conformance, Python-Go differential and native qualifications are rerun after the final source manifest is fixed.

The authoritative numeric results are written to `validation/control-4khz-0.44.0.json` and other source-bound validation JSON files. Those files are excluded from the source-tree digest so evidence generation does not mutate the reviewed source.

Physical hard-real-time I/O at every 250 us boundary is not claimed by hosted-only evidence.
