# Saga Module System 2027

A module source starts with `module Identifier`. `use "relative.saga" as alias` imports it under one namespace. Only `public` top-level declarations cross the boundary; default `internal` declarations do not. Qualified class types use `alias.Type`.

Source modules execute in an isolated module environment and expose explicit exported values. A legacy file with no `module` declaration continues to use 1.0 textual/source-unit inclusion semantics. Cyclic source dependencies remain invalid.

## Qualified exported type identity

A public declaration that refers to another public type in the same source module is observed from an importer using the imported namespace. For example, if `models.IntSource` implements module-local public interface `Source`, an importer observes the relation as `models.IntSource implements models.Source`. The same qualification applies recursively to exported field types, method signatures, generic function signatures, generic constraints and associated-type bindings. Implementations shall not leak the child module's unqualified type identity across the module boundary.
