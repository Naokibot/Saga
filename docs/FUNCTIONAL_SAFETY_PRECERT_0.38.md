# Functional-safety pre-certification boundary — Saga 0.38

Saga's internal safety harness references IEC 61508:2010, ISO 13849-1:2023 and the IEC 62061:2021 amendment line. It verifies software safety-state semantics, explicit reset behavior, stop-callback failure propagation and modeled E-stop, soft-limit, following-error, communication-loss, encoder-stuck and watchdog faults.

This is **not certification**. A SIL or PL claim requires a machine-specific risk assessment, target allocation, component reliability/diagnostic data, safety architecture, physical safety-function validation, lifecycle/configuration evidence and independent assessment. The 0.38 report therefore emits `NOT_CERTIFIED`, with SIL/PL targets left unassigned rather than inventing them.
