# Modules in Saga 0.30

Saga 0.30 adds namespaced modules without making small programs heavier.

## Start with one file

```saga
name = "Saga"
print "Hello", name
```

Nothing changes until the program needs a boundary.

## Add a module when the boundary matters

`models.saga`:

```saga
module models

public class User(let name: text) {
    fn greet() -> text = "Hello " + self.name
}

public fn twice(value: int) -> int = value * 2

internal fn implementationDetail() -> int = 99
```

`main.saga`:

```saga
use "models.saga" as m

user = m.User("Aki")
print user.greet()
print m.twice(21)
```

`m.implementationDetail()` is rejected: `internal` is a real module boundary, not a naming convention.

## Why qualified names stay qualified

If two modules both define `User`, Saga does not guess that they are interchangeable:

```saga
use "customer.saga" as customer
use "staff.saga" as staff

let c: customer.User = customer.User("Aki")
```

`customer.User` and `staff.User` are distinct nominal types.

This makes refactors and large codebases more predictable than flattening every imported name into one global scope.

## Inheritance across a module boundary

```saga
use "models.saga" as m

class Admin(let level: int) extends m.User {
    fn label() -> text = self.name + ":" + text(self.level)
}
```

The checker and runtime use the same qualified class identity. A fresh `.smi.json` also reconstructs the inherited constructor shape, so separate checking and source checking agree.

## Separate frontend compilation

Compile a public interface:

```bash
saga module compile models.saga
```

This creates `models.smi.json`.

Verify it:

```bash
saga module verify models.smi.json --source models.saga
```

The interface stores the public ABI and the ABI hashes of namespaced dependencies. It contains no executable source body.

If only a dependency implementation changes, an importer whose dependency ABI is unchanged stays fresh. If a dependency signature changes, the importer becomes stale.

That gives Saga an incremental type-checking boundary without pretending that 0.30 already has a full native object linker.

## Public API rule in 0.30

A public API may expose its own public types, built-in types and its type variables. It may not accidentally expose an internal type or an imported alias type:

```saga
module facade
use "database.saga" as db

// rejected in 0.30
public fn raw() -> db.Row = db.Row(...)
```

A later explicit re-export design can add this deliberately. 0.30 chooses the simpler rule because the ABI should not depend on a local import alias.

## Project layout

Both common implementations recognize `saga.toml` as the project-root boundary:

```text
my-app/
  saga.toml
  src/
    main.saga
  shared/
    models.saga
```

`src/main.saga` can use `../shared/models.saga` because both files remain inside the same project.

## Compatibility

Old module-less source units keep working as flattened includes. This makes migration incremental: add `module` only when a real namespace boundary is useful.

For the normative contract, see `spec/SAGA_MODULE_CORE_0.30.md`.
