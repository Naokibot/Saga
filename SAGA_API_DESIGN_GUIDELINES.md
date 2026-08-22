# Saga API Design Guidelines 1

Saga optimizes for **time-to-understand**, not minimum character count.

- Public functions and methods use descriptive verb or verb-object names (`read_text`, `write_text`, `contains`, `starts_with`).
- Public types use noun names; generic type parameters may be short when conventional (`T`, `K`, `V`).
- Avoid unexplained abbreviations in public APIs. Established domain terms such as HTTP, JSON, GPU and UTF are acceptable.
- Boolean functions should read as predicates (`is_empty`, `contains`, `can_retry`).
- Paired operations use paired words (`open`/`close`, `encode`/`decode`, `lock`/`unlock`).
- A function that may have no value returns `option[T]`; an expected failure returns `result[T,E]`.
- Lossy numeric conversion is explicit in the name or via an explicit constructor.
- Resource ownership transfer is visible through `move`; APIs should not hide ownership changes behind ordinary getters.
- Unsafe/FFI functionality is segregated from beginner/standard APIs.

The formatter controls syntax layout; libraries should not invent alternate formatting conventions. Stable public names should be changed only through the Saga Evolution and edition compatibility process.
