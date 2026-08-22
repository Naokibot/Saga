# External validation gates for Saga 0.17

Machine-readable status is `validation/external-gates-0.17.0.json`.

A gate is `PASS` only when it was actually executed in the required environment. `READY_UNEXECUTED` means source/harness preparation is complete but the required target host is unavailable. `BLOCKED` is never treated as a pass.

External evidence still required includes Windows/macOS target-host Desktop execution, real physical controller/GPU evidence, organizationally independent implementation governance, an independent laboratory certificate, and a live public Internet package registry. Hosted CI may provide target-OS execution evidence but shall not be labeled physical hardware unless the operator explicitly establishes that fact.
