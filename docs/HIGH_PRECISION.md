# High precision numbers

Saga has three exact numeric families:

- `int`: arbitrary-precision integer subject only to available host resources;
- `rational`: exact integer ratio;
- `decimal`: base-10 decimal using a caller-selected precision.

The default Decimal precision is 50 digits. `--precision N` or `precision(N)` may select any positive precision supported by the host decimal provider. Saga 0.9 defines no language-level maximum precision.

Examples:

```saga
precision(20000)
let third = decimal(1 / 3)
print(third)
```

`0.1 + 0.2 == 0.3` is true because decimal literals are base-10 exact values rather than binary floating-point approximations.
