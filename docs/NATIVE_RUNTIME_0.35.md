# Native Runtime in Saga 0.35

Saga 0.35 turns the 0.34 managed-aggregate preview into a substantially more complete direct-native object runtime.

## What is new

- **Inheritance and interfaces:** derived objects preserve base layout, interface/abstract contracts are checked, and calls through a base/interface use runtime virtual dispatch.
- **Managed Option/Result:** values such as `option[list[int]]` and `result[Box,text]` can hold GC-managed payloads safely.
- **Owned text:** native string concatenation and generated text can own managed UTF-8 storage instead of relying only on borrowed literals.
- **Native exceptions:** `throw`, `catch`, `finally`, runtime failures and GC roots share one unwind model. `return`, `break` and `continue` execute pending `finally` blocks first.
- **Generational/incremental GC:** young collection, promotion, remembered-set barriers and incremental major marking reduce the need for full-heap synchronous marking. Physical sweeping can run concurrently when C11 threads are available.
- **Generic monomorphization:** local generic functions and classes get concrete native symbols/type ids for each used type tuple. `Box[int]` and `Box[text]` are distinct native aggregate specializations.

## Example

```saga
interface Greeter { fn greet() -> text }

abstract class Person(let name: text) implements Greeter {
    abstract fn role() -> text
    override fn greet() -> text = "Hello " + self.name
}

class Student(let school: text) extends Person {
    override fn role() -> text = "student"
    override fn greet() -> text = "Student " + self.name
}

class Box[T](let value: T) {
    fn get() -> T = self.value
}

let student = Student("Aki", "Saga High")
let greeter: Greeter = student
let box: Box[text] = Box(greeter.greet())
print(box.get())
```

## GC model

0.35 is deliberately described as **generational + incremental marking + concurrent sweep**. It does not claim fully concurrent tracing or production real-time pause bounds. The synchronous `saga_gc_collect()` path remains available for deterministic collection and testing.

## Remaining preview boundaries

Cross-module generic-template specialization, generic inheritance, generic methods and open-world subclass loading remain rejected. Option/Result can carry managed payloads as native values, but recursive Option/Result descriptors are not yet stored directly inside list/map/set/object heap slots.
