package main

import "testing"

func TestFFIRuntimeDefenseInDepthRequiresUnsafe(t *testing.T) {
	it := NewInterpreter(NewChecker(), func(string) {})
	_, err := it.callFFI("profile", nil, Token{Lex: "ffi.profile"})
	se, ok := err.(*SagaError)
	if !ok || se.ID != "SAGA-R188" {
		t.Fatalf("runtime must reject FFI outside unsafe with SAGA-R188: %T %v", err, err)
	}
}
