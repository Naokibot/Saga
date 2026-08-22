# Saga Isolated-Task and CPU-Parallel Memory Model 0.8

## 1. Scope

This model covers `task.spawn`, `task.submit`, `task.parallel_map`, futures, `task.cpu_map`, `task.cpu_filter`, `task.cpu_reduce`, and output events.

## 2. Isolated tasks

The main execution and each isolated task are separate agents. Saga bindings and object fields are locations only within one agent. No mutable Saga location is shared between isolated task agents.

## 3. Send values

The following are Send when contained values are also Send: unit, bool, int, decimal, rational, text, bytes, date/time values, immutable lists/maps/sets, ranges, errors, and structurally copied Saga class instances. Futures and native resources such as DB connections, sockets, GUI objects, pools, images, plugins, Spark sessions and GPIO handles are not Send.

Task creation snapshots Send arguments and Send globals. Mutations in one task are not visible in another.

## 4. CPU process workers

CPU workers are separate operating-system processes in the Python reference implementation. They use a stricter **Process-Send** profile: scalar/value types, option, immutable collections, ranges, date/time, bytes and errors may cross the boundary; object identity, native resources, futures and local closures may not.

A CPU worker reconstructs top-level Saga declarations from the already checked program. It inherits no filesystem, network, database, UI, process, plugin, environment or cloud capability. Worker output is not merged into caller output; returned Process-Send values are the communication channel.

## 5. Ordering

- Argument evaluation happens-before scheduling.
- Successful task completion happens-before `await` returns.
- `task.all` returns after all supplied futures complete.
- A Saga 0.45 `taskgroup` lexical exit happens after all Saga async futures registered to that group reach a terminal state.
- `task.shutdown(pool)` returns after submitted threaded tasks complete.
- One caller-side `print`/`console.write` is an atomic output event.
- Ordering among independent task or process workers is unspecified.
- `cpu_map` and `cpu_filter` return results in input order.
- `cpu_reduce` uses tree reduction; an associative reducer is required for worker-count-independent results.

## 6. Data races

Standard Saga values cannot create a shared-memory data race through isolated task APIs. CPU-process APIs do not share Saga memory at all. Foreign plugins and host extensions are outside this guarantee.

## 7. Resource model

Saga 0.8 defines no fixed worker-count ceiling. Worker count `0` requests automatic selection. Positive counts are passed to the host execution provider; the provider may reject a count it cannot support because of operating-system or runtime resources.


## 8. Saga 0.45 resource transfer

`move name` consumes a checked move-only resource binding. A consumed binding cannot be read again until an explicitly mutable binding is assigned a new resource value. This ownership marker applies to the Saga binding; it is not a general alias/borrow proof for arbitrary foreign code.

`using name = resource { ... }` establishes deterministic resource cleanup at lexical exit. Ordinary Saga values remain garbage-collected/managed, so these rules do not turn the general Saga value model into manual memory management.
