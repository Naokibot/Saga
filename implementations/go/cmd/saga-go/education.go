package main

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

type diagnosticLesson struct {
	Title   string
	Why     string
	Fix     string
	Example string
}

var diagnosticLessons = map[string]diagnosticLesson{
	"SAGA-T101": {"Immutable value changed", "Values declared with let are stable by default. This prevents accidental state changes.", "Use var only when the value really needs to change.", "var count = 0\ncount = count + 1"},
	"SAGA-T102": {"Unknown name", "The name is not visible in the current lexical scope.", "Check the spelling or declare the value before using it.", "let score = 90\nprint(score)"},
	"SAGA-T103": {"Type mismatch", "Saga does not silently coerce unrelated types.", "Make the types agree or convert explicitly.", "let age: int = int(\"15\")"},
	"SAGA-T104": {"Condition must be bool", "Saga avoids truthy/falsy rules so conditions remain predictable.", "Write an explicit comparison.", "if count > 0 { print(\"ready\") }"},
	"SAGA-T105": {"Function argument mismatch", "The call does not match the function contract.", "Check argument count and types at the call site.", "fn add(a:int,b:int)->int = a+b\nprint(add(2,3))"},
	"SAGA-T107": {"Private member access", "Private state is visible only to its owning class.", "Expose a method when external access is intentional.", "class User(private let secret:text) { fn reveal()->text=self.secret }"},

	"SAGA-T170": {"Exact and floating values do not mix implicitly", "Exact decimal/rational arithmetic and IEEE floating-point arithmetic have different guarantees.", "Convert explicitly with float32/float64 or stay in the exact numeric family.", "let x=float64(1)+1.0f64"},
	"SAGA-T172": {"Generic constraint not satisfied", "The concrete type does not provide every capability required by the where-clause.", "Pass a conforming type or change the generic constraint.", "fn max[T](a:T,b:T)->T where T:Comparable { if a>b{return a}; return b }"},
	"SAGA-T173": {"Associated type cannot be resolved", "An interface requires a type member that the concrete implementation did not bind.", "Add `type Item = ConcreteType` to the implementing class.", "class SourceImpl implements Source { type Item=int; ... }"},
	"SAGA-T178": {"Unsafe boundary required", "FFI and native JIT operations can violate Saga's normal safety guarantees.", "Place the smallest possible foreign/native operation inside `unsafe { ... }`.", `unsafe { print(ffi.call_i64("libc.so.6","labs",[-1])) }`},
	"SAGA-T180": {"Resource already moved", "A move-only resource has exactly one live owner.", "Use the destination binding, or assign a new resource into a mutable source binding before using it again.", "let owned=move handle\nprint(owned)"},
	"SAGA-R181": {"Use after move", "The runtime detected access through an ownership binding that has already transferred its resource.", "Use the new owner or create/reassign a fresh resource.", "let owned=move handle"},
	"SAGA-R101": {"Index out of range", "The requested position is outside the collection.", "Check len(value) or use get(list,index,fallback).", "print(get(values, 10, 0))"},
	"SAGA-R102": {"Division by zero", "Division by zero has no valid numeric result in Saga exact arithmetic.", "Validate the denominator before dividing.", "if divisor != 0 { print(total / divisor) }"},
	"SAGA-R104": {"Tried to unwrap none", "option[T] requires the missing-value case to be handled.", "Use is_some, unwrap_or, or branch before unwrap.", "let name:option[text]=none()\nprint(unwrap_or(name, \"guest\"))"},
}

func explainDiagnostic(id string) int {
	x, ok := diagnosticLessons[strings.ToUpper(id)]
	if !ok {
		fmt.Fprintln(os.Stderr, "No extended lesson for diagnostic:", id)
		return 64
	}
	fmt.Println(id + ": " + x.Title)
	fmt.Println("why: " + x.Why)
	fmt.Println("fix: " + x.Fix)
	fmt.Println("example:")
	fmt.Println(x.Example)
	return 0
}

func printLearningPath() {
	fmt.Println("Saga learning path")
	fmt.Println("1. Foundation: let/var, exact numbers, text, list, if, for, functions")
	fmt.Println("2. Application: option[T], map/set, exceptions, modules, packages, tests")
	fmt.Println("3. Architecture: classes, interfaces, generics, annotations, closures")
	fmt.Println("4. Concurrency: isolated tasks, parallel_map, deterministic value boundaries")
	fmt.Println("5. Toolchain: lock/verify/pack, standalone builds, self-host compiler")
	fmt.Println("Rule: simple programs never need advanced features; advanced programs can opt into them gradually.")
}

func createProject(name, level string) error {
	if name == "" || name == "." || name == ".." {
		return fmt.Errorf("project name required")
	}
	root, err := filepath.Abs(name)
	if err != nil {
		return err
	}
	if _, err = os.Stat(root); err == nil {
		return fmt.Errorf("path already exists: %s", root)
	}
	if err = os.MkdirAll(filepath.Join(root, "tests"), 0755); err != nil {
		return err
	}
	language := "1.0"
	if level == "advanced" {
		language = "2027"
	}
	toml := fmt.Sprintf("[project]\nname = %q\nversion = \"0.1.0\"\nlanguage = %q\nentry = \"main.saga\"\ntest_dir = \"tests\"\n", filepath.Base(root), language)
	if err = os.WriteFile(filepath.Join(root, "saga.toml"), []byte(toml), 0644); err != nil {
		return err
	}
	var main string
	switch level {
	case "advanced":
		main = "interface Named { fn name() -> text }\n\nclass Person(let value:text) implements Named {\n    override fn name() -> text = self.value\n}\n\nfn describe[T](value:T, render:fn[T,text]) -> text {\n    return render(value)\n}\n\nlet person:Named = Person(\"Saga\")\nprint(person.name())\n"
	case "standard":
		main = "fn greet(name:text) -> text {\n    return \"Hello, \" + name\n}\n\nlet users = [\"Aki\", \"Mina\", \"Kai\"]\nfor user in users {\n    print(greet(user))\n}\n"
	default:
		main = "let name = \"Saga\"\nprint(\"Hello,\", name)\n"
	}
	return os.WriteFile(filepath.Join(root, "main.saga"), []byte(main), 0644)
}
