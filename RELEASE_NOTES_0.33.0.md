# Saga 0.33.0 — Human-Centered Native Value ABI Preview

## Highlights

- Direct Native Value ABI for immutable borrowed UTF-8 `text`.
- Native `option[int|bool|text]` and `result[int|bool|text, int|bool|text]`.
- Postfix `?` lowered to native option/result early return in the supported ABI.
- `enum` + exhaustive `match` on the shared Python/Go language surface.
- `unless` as parser-normalized human-centered control-flow sugar.
- Public enum nominal identity across namespaced modules.
- `.smi.json` public enum exports with matching Python/Go ABI/build hashes.
- Generated C ABI headers expose SagaText/SagaOption/SagaResult representations.
- Native enum/object/closure/collection layout remains fail-closed pending a
  later Native Value ABI revision.

0.33 is a preview, not Saga 1.0 GA. It expands the directly compiled value
surface while preserving the complete Standard Core via existing profiles.
