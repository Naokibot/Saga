# Native FFI — C ABI Profile 2

Saga 0.19.0 extends the optional `sagaffi` profile beyond scalar calls.

```saga
edition 2027
use ffi

unsafe {
    let pair = ffi.layout(["x:i32", "y:f64"])
    let p = ffi.struct_alloc(pair)
    ffi.struct_set(pair, p, "x", 21)
    ffi.struct_set(pair, p, "y", 1.5f64)

    # By-value C aggregate call/return.
    let out = ffi.call("./libprobe.so", "pair_twice",
        "struct{x:i32,y:f64}",
        ["struct{x:i32,y:f64}"], [p])

    fn plus10(x:int) -> int = x + 10
    let cb = ffi.callback(plus10, "i64", ["i64"])
    let fnptr = ffi.callback_ptr(cb)

    # Explicit lifetimes.
    ffi.callback_close(cb)
    ffi.free(out)
    ffi.free(p)
}
```

Owned allocations, borrowed derived pointers and callback code pointers carry
separate lifetime state. A child pointer becomes invalid when its owning parent
is released. Borrowed pointers cannot be freed. Double-free is rejected.

The 0.19 reference implementation validates Profile 2 on Linux x86-64 through
libffi. Other hosts fail closed unless a matching ABI backend is built.
