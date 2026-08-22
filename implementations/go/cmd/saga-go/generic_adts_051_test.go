package main

import (
	"testing"
)

func TestGenericADT051InferenceAndMatch(t *testing.T) {
	src := `enum Maybe[T] { None, Some(T) }
let value = Maybe.Some(42)
match value {
case Maybe.Some(item) { let checked: int = item; print(checked) }
case Maybe.None { print(0) }
}`
	out, err := runSagaForTest(t, src)
	if err != nil {
		t.Fatal(err)
	}
	if out != "42" {
		t.Fatalf("output=%q", out)
	}
}

func TestGenericADT051ContextCompletesTypeParameters(t *testing.T) {
	src := `enum Either[L, R] { Left(L), Right(R) }
let value: Either[int, text] = Either.Left(7)
match value {
case Either.Left(item) { let checked: int = item; print(checked) }
case Either.Right(message) { let checked: text = message; print(checked) }
}`
	out, err := runSagaForTest(t, src)
	if err != nil {
		t.Fatal(err)
	}
	if out != "7" {
		t.Fatalf("output=%q", out)
	}
}

func TestGenericADT051PayloadCaseFallsThroughToNullaryVariant(t *testing.T) {
	src := `enum Maybe[T] { None, Some(T) }
let value: Maybe[int] = Maybe.None
match value {
case Maybe.Some(item) { print(item) }
case Maybe.None { print("empty") }
}`
	out, err := runSagaForTest(t, src)
	if err != nil {
		t.Fatal(err)
	}
	if out != "empty" {
		t.Fatalf("output=%q", out)
	}
}

func TestGenericADT051NullaryVariantNeedsContext(t *testing.T) {
	_, err := runSagaForTest(t, `enum Maybe[T] { None, Some(T) }
let value = Maybe.None`)
	sagaErr, ok := err.(*SagaError)
	if !ok || sagaErr.ID != "SAGA-T113" {
		t.Fatalf("expected SagaError ID SAGA-T113, got %#v", err)
	}
}
