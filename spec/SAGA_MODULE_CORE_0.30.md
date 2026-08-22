# Saga Natural Module Core 0.30 — Reference Semantics

Status: **Preview**  
Language version: **0.30**  
Interface schema: **`saga.module-interface.v1`**  
Grammar overlay: **`spec/saga-0.30-module.ebnf`**

Natural Module Core 0.30 extends Natural Core with a common namespaced module and separate-interface model implemented by both the Python reference implementation and the independent Go implementation.

The design goal is simple: a small program may still be a single file, while a larger program gains explicit namespace, visibility and ABI boundaries without changing to another language dialect.

## 1. Module declaration

A namespaced source unit begins with exactly one leading module declaration:

```saga
module models
```

`module` must be the first semantic declaration in that source unit and may appear only once. 0.30 module names are single identifiers. Hierarchical dotted module names are not part of this profile.

A source file without a `module` declaration retains the pre-0.30 legacy source-unit behavior and may be flattened by `use` for compatibility.

## 2. Visibility

Top-level declarations are **internal by default**.

```saga
module models

public class User(let name: text) {}
public fn find(id: int) -> option[User] = none()
internal fn normalize(value: text) -> text = value.trim()
let cacheSize = 128  // internal
```

The official vocabulary is `public` and `internal`. Top-level `private` is accepted only as a compatibility spelling for `internal`.

Only public top-level variables, functions, classes and interfaces form the common module ABI. Internal members remain usable inside their defining module but are not visible through an imported namespace.

## 3. Import and namespace binding

A namespaced source module is imported with `use`:

```saga
use "models.saga" as m

let user: m.User = m.User("Aki")
print(m.find(7))
```

If `as` is omitted, the declared module name is the namespace binding:

```saga
use "models.saga"
print(models.find(7))
```

A module has one canonical binding within a compilation graph. Importing the same canonical source through two different aliases is rejected with `SAGA-P109`.

Wildcard namespace flattening is intentionally absent from Natural Module Core 0.30.

## 4. Namespace isolation

A namespaced module is checked and executed in an isolated module environment. Its dependencies belong to that module's lexical namespace and do not leak into its importer.

Qualified nominal types keep namespace identity:

```saga
use "a.saga" as a
use "b.saga" as b

// a.User and b.User are different nominal types even if their declarations match.
```

The runtime preserves the same identity rule for class instances, inheritance checks and dynamic contract checks.

## 5. Qualified inheritance

A local class may extend a public imported class:

```saga
use "models.saga" as m

class LocalUser(let id: int) extends m.User {
    fn label() -> text = self.name + ":" + text(self.id)
}
```

Constructor shape includes inherited fields in the same order as source checking, including when the imported class was reconstructed only from a fresh module interface.

## 6. Public API boundary

A public API must be independently understandable from its own module interface.

Therefore Natural Module Core 0.30 rejects a public declaration that exposes:

- a module-internal nominal type;
- a nominal type imported from another module alias.

Example rejected in 0.30:

```saga
module facade
use "dep.saga" as d

public fn make() -> d.User = d.User("x")
```

The same rule applies to public bases, implemented interfaces, fields, function parameters/results and method signatures.

Explicit public re-export is intentionally deferred to a later profile. This keeps the 0.30 ABI independent of an importer's local alias spelling.

## 7. Legacy source-unit compatibility

A module-less dependency keeps the historical flattened form:

```saga
// helper.saga — no module declaration
fn add(a: int, b: int) -> int = a + b
```

```saga
use "helper.saga"
print(add(2, 3))
```

A module-less legacy source unit may not be imported with `as alias`, because it has no namespace identity to bind.

## 8. Project root and source graph

When a `saga.toml` is present in the entry file's ancestor chain, its directory is the project root for both common implementations. Otherwise the entry source directory is the root.

Relative source imports may move between subdirectories while remaining inside that project root:

```text
project/
  saga.toml
  src/main.saga
  shared/models.saga
```

`src/main.saga` may use `../shared/models.saga`. A source import that escapes the project/package boundary, forms a cycle, or crosses a rejected user-controlled symbolic-link path fails closed.

## 9. Saga Module Interface (`.smi.json`)

Separate frontend compilation emits a deterministic Saga Module Interface:

```bash
saga module compile models.saga
saga module verify models.smi.json --source models.saga
```

The common interface contains:

- schema and language version;
- module name;
- source SHA-256;
- deterministic public exports;
- dependency module names and dependency ABI hashes;
- public ABI SHA-256;
- build SHA-256.

No executable implementation body is stored in the interface.

### 9.1 ABI hash

`abi_sha256` is computed from the schema, module identity and canonical public export surface. Implementation-only body changes therefore do not change ABI.

Declaration ordering that is not semantically ABI-significant is canonicalized. Public method and implemented-interface lists are sorted. Field declaration order is retained because positional constructor shape depends on it.

### 9.2 Build hash

`build_sha256` binds:

- source hash;
- own ABI hash;
- dependency ABI records.

A loader verifies both ABI and build hashes before trusting an interface.

### 9.3 Dependency invalidation

An importer interface records the ABI hash of every namespaced dependency used while it was compiled.

If a dependency implementation changes without changing its public ABI, rebuilding the dependency interface does not invalidate the importer interface.

If the dependency public ABI changes, the importer interface is stale and must be recompiled.

### 9.4 Fresh interface use

When a sibling `.smi.json` is fresh and valid, the checker may reconstruct the imported public type surface from the interface rather than re-typechecking that dependency body.

If the interface is missing, damaged, stale, has a bad hash, has an unsupported language/schema version, or has a stale dependency ABI, the implementation must not silently trust it. Source checking is the correctness fallback where source is available.

### 9.5 Output safety

Interface output must end in `.smi.json`. User-controlled symbolic-link outputs are rejected. Writes are atomic (`temp + fsync + replace` or the platform-equivalent atomic file helper) so a partially written interface is not considered a successful build.

## 10. Common ABI type surface

The common 0.30 interface supports the shared Natural Core type surface implemented by both Python and Go. Canonical type text includes nominal types, generic types, type variables and function types.

Declarations that have no representation shared by the Python and Go common implementations are not silently emitted as a common SMI public API. A public declaration using such a feature must stay outside the common ABI profile until a shared representation exists.

Saga 0.45 promotes async functions into that shared representation without changing the SMI schema: a public `async fn` declared with result `T` is serialized with effective public result `future[T]`. Other implementation-preview-only declaration forms remain outside the common ABI until separately promoted.

## 11. Separate compilation claim boundary

Natural Module Core 0.30 provides **frontend/interface separate compilation**:

- an implementation can independently compile a module public surface;
- importers can type-check against a fresh SMI without re-typechecking the dependency body;
- ABI-stable implementation changes do not force importer re-typechecking;
- ABI changes deterministically invalidate dependants.

This is not yet a claim of fully independent native object-file compilation and linker-level incremental code generation. The Python and Go runtimes still execute the source implementation body when running a program. Native object modules, linker artifacts and package-distributed precompiled implementations are later milestones.

## 12. Conformance requirements

A Natural Module Core 0.30 implementation must agree on at least:

1. leading/unique module declaration rules;
2. default-internal and explicit-public visibility;
3. namespace isolation and qualified member lookup;
4. qualified nominal identity;
5. imported-base inheritance and constructor shape;
6. canonical alias rejection;
7. hidden/internal diagnostics;
8. public-surface leak rejection;
9. project-root import containment;
10. SMI public export serialization;
11. ABI/build hash verification;
12. dependency ABI freshness semantics;
13. stale-interface fallback behavior.

Project conformance evidence compares the Python and Go implementations on these behaviors. Passing the corpus is executable evidence for this declared profile, not a mathematical proof of equivalence on every possible program.
