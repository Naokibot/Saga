# Saga 0.29 — 50 Before / After Examples

Status legend: **Implemented** means the Python reference frontend/runtime in this tree accepts the new form. **Design target** means the spelling is part of the redesign direction but is not claimed as 0.29 executable parity yet.

1. **Local binding — Implemented**  
   Before: `let name = "Saga"`  
   After: `name = "Saga"`
2. **Intentional mutation — Implemented**  
   Before: `var count = 0`  
   After: `var count = 0` (kept because mutation is important information)
3. **Map — Implemented**  
   Before: `transform(double, values)`  
   After: `values.map(double)`
4. **Map with inline callback — Implemented**  
   Before: `fn double(x: int) -> int = x * 2; transform(double, values)`  
   After: `values.map { it * 2 }`
5. **Filter — Implemented**  
   Before: `filter(active, users)`  
   After: `users.filter(active)`
6. **Filter inline — Implemented**  
   Before: `filter(is_positive, values)`  
   After: `values.filter { it > 0 }`
7. **Fold — Implemented**  
   Before: `reduce(add, values, 0)`  
   After: `values.fold(0) { total, value -> total + value }`
8. **Any — Implemented**  
   Before: `any(is_ready, jobs)`  
   After: `jobs.any { it.ready }`
9. **All — Implemented**  
   Before: `all(valid, items)`  
   After: `items.all { it.valid }`
10. **None — Implemented**  
    Before: `not any(blocked, users)`  
    After: `users.none { it.blocked }`
11. **Sort — Implemented**  
    Before: `sort(values)`  
    After: `values.sorted()`
12. **Sort by key — Implemented**  
    Before: named comparator/key helper around sort  
    After: `users.sortedBy { it.score }`
13. **Unique — Implemented**  
    Before: `unique(values)`  
    After: `values.distinct()`
14. **Take — Implemented**  
    Before: `slice(values, 0, 10)`  
    After: `values.take(10)`
15. **Skip — Implemented**  
    Before: manual slice from N  
    After: `values.skip(10)`
16. **Zip — Implemented**  
    Before: manual index loop  
    After: `names.zip(scores)`
17. **Flatten — Implemented**  
    Before: nested loops plus append  
    After: `groups.flatten()`
18. **Flat map — Implemented**  
    Before: map then flatten  
    After: `rows.flatMap { it.cells }`
19. **Chunk — Implemented**  
    Before: manual range/slice loop  
    After: `bytes.chunk(1024)`
20. **Sliding window — Implemented**  
    Before: manual neighboring-index loop  
    After: `samples.window(3)`
21. **Group identical values — Implemented**  
    Before: manual map accumulation  
    After: `values.group()`
22. **Group by key — Implemented**  
    Before: manual map accumulation by property  
    After: `users.groupBy { it.team }`
23. **Sum — Implemented**  
    Before: `sum(values)`  
    After: `values.sum()`
24. **Contains — Implemented**  
    Before: `contains(values, target)`  
    After: `values.contains(target)`
25. **Chaining — Implemented**  
    Before: `sort(unique(transform(double, filter(active, values))))`  
    After: `values.filter(active).map(double).distinct().sorted()`
26. **Pipeline — Implemented**  
    Before: nested functional calls  
    After: `values |> filter { it > 0 } |> map { it * 2 }`
27. **Repeat block — Implemented**  
    Before: `for n in 1..3 { print("Hi") }`  
    After: `repeat(3) { print("Hi") }`
28. **Text trim — Implemented**  
    Before: `trim(name)`  
    After: `name.trim()`
29. **Text case — Implemented**  
    Before: `upper(name)`  
    After: `name.upper()`
30. **Text split — Implemented**  
    Before: `split(line, ",")`  
    After: `line.split(",")`
31. **Text prefix — Implemented**  
    Before: `starts_with(path, "/api")`  
    After: `path.startsWith("/api")`
32. **Map keys — Implemented**  
    Before: `map_keys(index)`  
    After: `index.keys()`
33. **Map lookup — Implemented**  
    Before: `map_get(index, key, fallback)`  
    After: `index.get(key, fallback)`
34. **Optional map lookup — Implemented**  
    Before: sentinel fallback convention  
    After: `index.get(key)` returns `option[value]`
35. **Set to list — Implemented**  
    Before: manual iteration  
    After: `items.toList()`
36. **Library DSL call — Implemented**  
    Before: `panel("Todo", body)`  
    After: `panel "Todo" { ... }`
37. **Simple output — Implemented**  
    Before: `print("Hello")`  
    After: `print "Hello"`
38. **Two-parameter closure — Implemented**  
    Before: separately declared callback  
    After: `{ total, value -> total + value }`
39. **Contextual callback type — Implemented**  
    Before: repeat parameter type annotations inside local callback  
    After: `values.filter { it > 0 }` with `it` inferred from the list
40. **Migration preview — Implemented**  
    Before: hand-edit every old HOF call  
    After: `saga migrate .` previews provably safe rewrites
41. **Migration write — Implemented**  
    Before: unchecked textual replacement  
    After: `saga migrate . --write` parses the result before replacement
42. **Immutable concise binding — Implemented**  
    Before: short syntax would imply mutable state in many scripting languages  
    After: `x = 1` is immutable; write `var x = 1` to mutate
43. **Result propagation — Design target**  
    Before: `if is_err(r) { return r } ...`  
    After: `value = read()?`
44. **Structured timeout — Design target**  
    Before: timer/task cancellation boilerplate  
    After: `timeout 5.seconds { fetch() }`
45. **Resource scope — Design target**  
    Before: explicit close in every path  
    After: `using file.open(path) { file -> ... }`
46. **Retry policy — Design target**  
    Before: loop/catch/sleep boilerplate  
    After: `retry 3, backoff: exponential { request() }`
47. **GUI builder — Design target library**  
    Before: host-widget construction ceremony  
    After: `window "Todo" { column { button "Save" { save() } } }`
48. **HTTP route DSL — Design target library**  
    Before: explicit router object/handler registration  
    After: `route GET, "/users" { request -> ... }`
49. **Declarative parallel collection — Design target**  
    Before: pool/future orchestration  
    After: `images.parallel().map { resize(it) }`
50. **Capability intent — Design target refinement**  
    Before: scattered host permission setup  
    After: a visible capability declaration at the boundary, with ordinary internal code remaining uncluttered.
