# Saga C ABI Profile 2 — 2027 Preview

Status: normative preview for Saga implementation 0.19.0.

## 1. Scope

C ABI Profile 2 extends the scalar FFI profile with C-compatible aggregate layout,
by-value aggregate calls/returns, function callbacks and explicit raw-pointer
ownership. The profile is only available inside `unsafe` and shall fail closed
when the platform backend is not available.

The language semantics are platform-neutral; actual structure size/alignment and
calling convention are those of the selected platform C ABI. A conforming backend
shall disclose its target ABI and shall not silently substitute a different ABI.

## 2. Type descriptors

Portable scalar descriptors are:

`i8 u8 i16 u16 i32 u32 i64 u64 f32 f64 bool ptr void`

An aggregate descriptor is `struct{field:type,...}`. Aggregates may contain
supported scalars, pointers, nested supported aggregates, and fixed-size array
fields written `array[N:type]`. Layout uses the platform C ABI field alignment,
array element stride, and tail padding. A field descriptor is not a Saga object layout;
it is an explicit foreign layout.

## 3. Ownership

`ffi.alloc` and aggregate return values are **owned** pointers. Exactly one live
owner is responsible for release through `ffi.free` or resource cleanup.
`ffi.ptr_add`, pointer fields and callback code pointers are **borrowed**.

A conforming implementation shall reject:

- freeing a borrowed pointer;
- freeing an owner more than once;
- dereferencing an owner after release;
- dereferencing a derived pointer after its owner is released;
- using a callback code pointer after the callback is closed;
- an out-of-bounds access when the pointer carries a known extent.

Unknown-length pointers obtained from C are allowed only in `unsafe`; bounds then
remain a caller proof obligation.

## 4. Aggregate operations

`ffi.layout(["name:type", ...])` creates a foreign layout description.
`ffi.struct_alloc(layout)` returns zero-initialized owned storage.
`ffi.struct_get` and `ffi.struct_set` operate by declared field offset and type.

`ffi.call(library, symbol, return_type, argument_types, arguments)` shall use the
target C calling convention. Aggregate descriptors can be passed and returned by
value. Pointer arguments pass C addresses, not Saga object identities.

## 5. Callbacks

`ffi.callback(callable, return_type, argument_types)` creates a native C-callable
trampoline. Callback arguments are converted at the boundary and the Saga
callable is invoked through its normal runtime contract. `ffi.callback_ptr`
returns a borrowed pointer whose lifetime is tied to the callback object.
`ffi.callback_close` invalidates the trampoline before releasing it.

A callback shall not outlive the Saga interpreter/runtime context that owns it.
Cross-thread callback entry is an implementation profile feature and must be
explicitly disclosed; it is not implied by C ABI Profile 2.

## 6. Reference implementation qualification

Saga Native 0.19.0 contains a libffi-backed Linux x86-64 reference backend.
Unsupported hosts report the FFI as unavailable rather than emulating a possibly
incompatible calling convention. The normative profile does not require libffi;
other implementations may use platform assembly, LLVM, compiler builtins or a
vendor ABI layer if observable C ABI behavior is equivalent.
