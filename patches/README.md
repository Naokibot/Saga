# Saga focused patch sets

## Saga 0.45.0 — Language Synthesis

Saga 0.45.0 was reviewed from the frozen Saga 0.44.0 4 kHz hosted-control source tree. The repository carries the release documentation and the focused implementation change set; the full historical monorepo source remains distributed separately as the reviewed source ZIP.

The 0.44→0.45 patch is stored as five numbered UTF-8 text parts because this connected GitHub writer operates on text files. Concatenate the parts in numeric order before applying them:

```bash
cat patches/saga-0.44.0-to-0.45.0-language-synthesis.patch.part-* > saga-0.44.0-to-0.45.0-language-synthesis.patch
cd saga-lang-0.44.0-4khz-control
patch -p1 < ../saga-0.44.0-to-0.45.0-language-synthesis.patch
```

Frozen reviewed Saga 0.45 source tree SHA-256:

`cb06d5ac6e6ff7532c37499e3d38b51753a573d9110a42b5fcfabfba4729e804`

Full reviewed source ZIP SHA-256:

`bcb6fb350d20befea983dabf4458381e95b21d71bdc3361ccf518bb14c22f97b`

Canonical local focused patch SHA-256:

`73d60309157fab0cf212d115444cad972f2b01e4415b6538a1c5350b55dc08ff`

The patch promotes common `async` / `await`, `taskgroup`, `defer`, `using`, resource `move`, Python/Go async module ABI parity, and common Go/Python task-pool operations while retaining the 0.44 machine/drone/control profiles.

As with earlier focused patch sets, the repository snapshot is review-oriented and should not be treated as a byte-for-byte mirror of the separately distributed full source ZIP.

## Historical Saga 0.40 change set

Saga 0.40.0 was reviewed from the frozen Saga 0.39 drone release. Its focused implementation change set is stored here as five numbered review segments covering the drone-policy/offboard changes.

Frozen reviewed Saga 0.40 source tree SHA-256:

`674c31e67af1e11d67a639ee86bf6e9987bbe100c5bd2436c3e1717f462dc1f7`

Full reviewed source ZIP SHA-256:

`15a52e463f2f6bf4342a40fbf3415b6d6dfc8d95e57c588b35c693e91b52048e`

Canonical local focused patch SHA-256:

`7e6743bee1ead27c92f52f618de6e1534c6c7d8e2592b71786ead257059a6d41`
