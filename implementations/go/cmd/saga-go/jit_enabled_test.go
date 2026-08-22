//go:build sagajit && linux && amd64 && cgo

package main

import "testing"

func TestEdition2027NativeScalarJITExecutesMachineCode(t *testing.T) {
	src := `
use jit
fn formula(a:int,b:int)->int=a*b+a-3
unsafe {
  let compiled=unwrap_ok(jit.compile_i64(formula))
  print(jit.call_i64(compiled,[7,6]))
  jit.close(compiled)
}
`
	got, err := runSagaForTest(t, src)
	if err != nil || got != "46" {
		t.Fatalf("native scalar JIT failed: got=%q err=%v", got, err)
	}
}
