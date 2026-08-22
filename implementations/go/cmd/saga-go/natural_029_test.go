package main

import (
	"errors"
	"testing"
)

func TestNatural029DifferentialCorpus(t *testing.T) {
	tests := []struct {
		name string
		src  string
		want string
	}{
		{"natural binding", `name = "Saga"
print(name)`, "Saga"},
		{"implicit map closure", `values = [1, 2, 3]
print(values.map { it * 2 })`, "[2, 4, 6]"},
		{"explicit fold closure", `values = [1, 2, 3]
print(values.fold(0) { total, n -> total + n })`, "6"},
		{"legacy pipeline callbacks", `values = [1, 2, 3]
print(values |> filter { it > 1 } |> transform { it * 2 })`, "[4, 6]"},
		{"first class closure", `greet = { print("Hello") }
greet()`, "Hello"},
		{"closure return boundary", `values = [1, 2, 3]
print(values.map { if it > 1 { return it * 10 } return it })`, "[1, 20, 30]"},
		{"natural pipeline names", `values = [3, 1, 2, 2]
print(values |> map { it * 2 } |> distinct |> sorted |> take(2))`, "[2, 4]"},
		{"legacy reduce pipeline order", `fn add(a: int, b: int) -> int { return a + b }
values = [1, 2, 3]
print(values |> reduce(add, 0))`, "6"},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got, err := runSagaForTest(t, tc.src)
			if err != nil {
				t.Fatal(err)
			}
			if got != tc.want {
				t.Fatalf("got %q want %q", got, tc.want)
			}
		})
	}
}

func TestNatural029DuplicateClosureParametersAreRejected(t *testing.T) {
	src := `let f: fn[int,int,int] = { x, x -> x }`
	toks, err := lex(src, "<test>")
	if err != nil {
		t.Fatal(err)
	}
	_, err = parse(toks)
	if err == nil {
		t.Fatal("duplicate closure parameters were accepted")
	}
	var se *SagaError
	if !errors.As(err, &se) || se.ID != "SAGA-P001" {
		t.Fatalf("expected SAGA-P001, got %v", err)
	}
}

func TestNatural029ControlHeaderDoesNotStealBodyAsClosure(t *testing.T) {
	src := `
fn ready() -> bool { return true }
if ready() { print("ok") }
`
	got, err := runSagaForTest(t, src)
	if err != nil {
		t.Fatal(err)
	}
	if got != "ok" {
		t.Fatalf("got %q", got)
	}
}

func TestNatural029AssignmentResolvesTargetBeforeRHS(t *testing.T) {
	src := `
class Box(var value:int) {}
let box = Box(0)
fn target() -> Box { print("target") return box }
fn rhs() -> int { print("rhs") return 7 }
target().value = rhs()
print(box.value)
`
	got, err := runSagaForTest(t, src)
	if err != nil {
		t.Fatal(err)
	}
	if got != "target\nrhs\n7" {
		t.Fatalf("assignment evaluation order changed: %q", got)
	}
}

func TestNatural029BareArguments(t *testing.T) {
	src := `
print "Hello"
fn add(a: int, b: int) -> int { return a + b }
print add(2, 3)
`
	got, err := runSagaForTest(t, src)
	if err != nil {
		t.Fatal(err)
	}
	if got != "Hello\n5" {
		t.Fatalf("bare-argument call mismatch: %q", got)
	}
}

func TestNatural029BareArgumentCanTakeTrailingClosure(t *testing.T) {
	src := `
fn panel(title: text, body: fn[unit]) -> unit {
    print(title)
    body()
}
panel "Todo" { print("inside") }
`
	got, err := runSagaForTest(t, src)
	if err != nil {
		t.Fatal(err)
	}
	if got != "Todo\ninside" {
		t.Fatalf("bare-argument trailing closure mismatch: %q", got)
	}
}

func TestNatural029BareArgumentsDoNotStealSubtraction(t *testing.T) {
	src := `
let n = 3
print(n - 1)
`
	got, err := runSagaForTest(t, src)
	if err != nil {
		t.Fatal(err)
	}
	if got != "2" {
		t.Fatalf("subtraction was reinterpreted as a bare call: %q", got)
	}
}
