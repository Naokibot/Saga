# Native Aggregates and GC in Saga 0.34

Saga 0.34 moves the direct native backend beyond scalar/value-only programs. The same `--profile codegen` path can now lower tagged unions, collections, and plain objects into real native module objects without routing supported operations through the Go Standard Runtime.

## Tagged unions

```saga
enum Result {
    Ok(int),
    Err(text)
}

fn describe(value: Result) {
    match value {
        case Result.Ok(number) { print(number) }
        case Result.Err(message) { print(message) }
    }
}
```

Payload values are part of the enum's native ABI. The compiler also emits payload information into `.smi.json` and `.nabi.json`, so changing `Ok(int)` to `Ok(text)` is an ABI change and invalidates importers.

A tagged union may contain a managed object/collection payload in 0.34. The GC scans that payload when the tagged value is rooted or stored inside another managed object.

## Collections

Direct native code supports `list`, `map`, and `set` as Saga-managed references. They can contain scalars, text, tagged values, and managed object references where the element ABI is supported.

```saga
let boxes: list[Box] = [Box(1), Box(2)]
print(boxes[1].value)
```

## Plain classes

```saga
class Box(var value: int) {
    fn add(delta: int) -> int {
        self.value = self.value + delta
        return self.value
    }
}

let box = Box(5)
print(box.add(3))
```

Constructors and methods are native symbols. Objects have nominal identity and mutable field slots. Inheritance, interfaces, and virtual dispatch remain fail-closed in this preview.

## Saga allocator and collector

The runtime now owns allocation policy for managed native values. Small/medium blocks are recycled through size-class free lists; the collector is a single-threaded stop-the-world mark/sweep implementation.

This is deliberately a correctness-first collector. It gives Saga a real object graph and root model needed for later generational/concurrent collectors without pretending that 0.34 is already a production low-pause GC.

Compiler-generated roots are lexical. Nested block roots are unwound before leaving scope, including `break`, `continue`, and `return` paths.

## What to use 0.34 for

0.34 is useful for validating direct-native application logic involving structured data and object graphs. It is not yet the profile for latency-sensitive concurrent servers or class hierarchies that depend on virtual dispatch.
