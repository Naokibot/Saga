//go:build !sagaffi || !linux || !cgo

package main

import "fmt"

func ffiAvailable() bool { return false }
func ffiCallI64(_, _ string, _ []int64) (int64, error) {
	return 0, fmt.Errorf("C FFI profile is not available in this Saga Native build")
}
func ffiCallF64(_, _ string, _ []float64) (float64, error) {
	return 0, fmt.Errorf("C FFI profile is not available in this Saga Native build")
}
