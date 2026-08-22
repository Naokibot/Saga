//go:build !sagajit || !linux || !amd64 || !cgo

package main

import "fmt"

func jitAvailable() bool { return false }
func jitAlloc(code []byte) (uintptr, error) {
	return 0, fmt.Errorf("native scalar JIT is unavailable; rebuild on linux/amd64 with CGO_ENABLED=1 -tags sagajit")
}
func jitInvoke(handle uintptr, args []int64) (int64, error) {
	return 0, fmt.Errorf("native scalar JIT is unavailable")
}
func jitRelease(handle uintptr) {}
