//go:build !sagaffi || !linux || !amd64 || !cgo

package main

import "fmt"

type ffiRawArg struct {
	I64 int64
	U64 uint64
	F64 float64
	Ptr uintptr
}
type ffiRawResult = ffiRawArg

func ffiProfile2Available() bool    { return false }
func ffiPointerSize() int           { return 8 }
func ffiAlloc(int) uintptr          { return 0 }
func ffiFree(uintptr)               {}
func ffiZero(uintptr, int)          {}
func ffiCopy(uintptr, uintptr, int) {}
func ffiLoadI8(uintptr) int8        { return 0 }
func ffiLoadU8(uintptr) uint8       { return 0 }
func ffiLoadI16(uintptr) int16      { return 0 }
func ffiLoadU16(uintptr) uint16     { return 0 }
func ffiLoadI32(uintptr) int32      { return 0 }
func ffiLoadU32(uintptr) uint32     { return 0 }
func ffiLoadI64(uintptr) int64      { return 0 }
func ffiLoadU64(uintptr) uint64     { return 0 }
func ffiLoadF32(uintptr) float32    { return 0 }
func ffiLoadF64(uintptr) float64    { return 0 }
func ffiLoadPtr(uintptr) uintptr    { return 0 }
func ffiStoreI8(uintptr, int8)      {}
func ffiStoreU8(uintptr, uint8)     {}
func ffiStoreI16(uintptr, int16)    {}
func ffiStoreU16(uintptr, uint16)   {}
func ffiStoreI32(uintptr, int32)    {}
func ffiStoreU32(uintptr, uint32)   {}
func ffiStoreI64(uintptr, int64)    {}
func ffiStoreU64(uintptr, uint64)   {}
func ffiStoreF32(uintptr, float32)  {}
func ffiStoreF64(uintptr, float64)  {}
func ffiStorePtr(uintptr, uintptr)  {}
func ffiCallABI(string, string, string, []string, []Value) (ffiRawResult, error) {
	return ffiRawResult{}, fmt.Errorf("C ABI Profile 2 is unavailable; build with cgo and -tags sagaffi on linux/amd64")
}
func ffiMakeCallback(uint64, string, []string) (uintptr, uintptr, error) {
	return 0, 0, fmt.Errorf("C ABI callbacks unavailable")
}
func ffiCloseCallback(uintptr) {}
