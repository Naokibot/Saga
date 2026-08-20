# Saga 0.50.0 canonical Production GA patch

This directory stores the exact reviewed Git patch from Saga 0.49.0 Production & Industrial to **Saga 0.50.0 Production GA — Control Language & Toolchain**.

The compressed patch is split into six chunks because the connected GitHub writer is optimized for bounded text/binary objects. Concatenate them in numeric order; the result is byte-for-byte the reviewed `.xz` file.

```sh
cat saga-0.49.0-to-0.50.0-production-ga.patch.xz.part-00 \
    saga-0.49.0-to-0.50.0-production-ga.patch.xz.part-01 \
    saga-0.49.0-to-0.50.0-production-ga.patch.xz.part-02 \
    saga-0.49.0-to-0.50.0-production-ga.patch.xz.part-03 \
    saga-0.49.0-to-0.50.0-production-ga.patch.xz.part-04 \
    saga-0.49.0-to-0.50.0-production-ga.patch.xz.part-05 \
  > saga-0.49.0-to-0.50.0-production-ga.patch.xz

sha256sum saga-0.49.0-to-0.50.0-production-ga.patch.xz
xz -dc saga-0.49.0-to-0.50.0-production-ga.patch.xz \
  > saga-0.49.0-to-0.50.0-production-ga.patch
sha256sum saga-0.49.0-to-0.50.0-production-ga.patch
```

Expected SHA-256:

- compressed `.xz`: `7ac568fb419396e47cc5582fafb37838ced613a886871e449043d947980923b9`
- canonical Git patch: `24e60b4a2f5da9bdadc4e191ef6845ed471d2431a3e6dde5d933a4b5edf4e85c`

Chunk SHA-256 values:

- part-00: `84b4d29f0f68fb61c8f8dbca278a0a86ddb8126064900760468e9a44c7dd2d0d`
- part-01: `f4a074ec249755f71d7e4b44227f47f1bc868948413312401454cab40c97c1b5`
- part-02: `a8d3854dec7e20d24280e40b1473f36ac01b8e58f6b8d27157ec79709c47833b`
- part-03: `da9b7db6c80d84dc10283061533c2e5f79dadc9c9fbf6842d50c667030232df7`
- part-04: `bb73f09ba900b5b483ffd643600ade8f3dfcc2b04766ffadbaf45b1c1179c660`
- part-05: `cfd5598a786897275fcc08375fb52bd9793e45dccc5293065376da0ab2e8c73e`

Apply from the exact Saga 0.49.0 Production & Industrial source baseline with `git apply` or inspect with `git apply --check` first. The patch contains the complete reviewed 0.49→0.50 change set; release evidence is also stored alongside it for human review.
