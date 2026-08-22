# Saga 0.8.0 validation report

Date: 2026-08-07

## Environment used here

- Debian GNU/Linux 13 container/host environment
- x86-64 Linux
- CPython 3.13
- Go toolchain available in the build environment

## Results

| Validation | Result |
|---|---|
| Python automated test suite | 101 / 101 pass |
| Self-conformance suite | pass |
| Portable Core candidate suite | 13 / 13 pass |
| Python/Go differential suite | 13 / 13 agree/pass |
| Go tests with race detector | pass |
| Go `vet` | pass |
| Random parser inputs | 20,000 cases, 0 unexpected host exceptions |
| Generated expression executions | 5,000 cases, 0 unexpected host exceptions |
| Source above former 8 MiB ceiling | 9 MiB compile pass |
| Nesting above former 512 ceiling | 3,000 parentheses compile pass |
| Precision above former 10,000 ceiling | precision 20,000 pass |
| Function arity above former 64 ceiling | 80 parameters/arguments pass |
| Exponent above former 1,000,000 ceiling | exponent 1,000,001 pass |
| Thread pool above former 256 ceiling | 257-worker pool creation/shutdown pass |
| `task.cpu_map` | pass |
| `task.cpu_filter` | pass |
| `task.cpu_reduce` | pass, result 204 in full sample |
| CPU process identity test | multiple worker PIDs observed on multi-CPU host |
| Linux x86-64 native installer check | pass |
| Linux x86-64 native installation | pass |
| Installed Saga version | Saga 0.8.0 |
| Installed runtime CPU-parallel sample | pass |
| Linux x86-64 uninstall | pass |
| Linux ARM64 installer format | ELF AArch64 generated |
| Windows x86-64 installer format | PE32+ x86-64 generated |
| Windows ARM64 installer format | PE32+ ARM64 generated |

CPU parallel sample output:

```text
[1, 4, 9, 16, 25, 36, 49, 64]
[4, 16, 36, 64]
204
```

Former-limit smoke evidence:

```text
SOURCE_OVER_OLD_8M_LIMIT_OK 9437184
NESTING_OVER_OLD_512_LIMIT_OK 3000
PRECISION_20000_OK 1
ARITY_80_OK 2
EXPONENT_OVER_OLD_1000000_LIMIT_OK true
```

## Not claimed as validated

- Windows installer execution on a physical/virtual Windows system
- Linux ARM64 installer execution on an ARM64 machine
- macOS
- Android/iOS
- third-party penetration testing
- independent ISO/IEC conformance laboratory testing
- extremely large jobs up to physical memory/process exhaustion

The absence of a Saga-defined fixed ceiling must not be interpreted as a guarantee that arbitrary resource consumption succeeds on finite hardware.
