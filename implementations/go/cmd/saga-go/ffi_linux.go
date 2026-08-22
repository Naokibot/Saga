//go:build sagaffi && linux && cgo

package main

/*
#cgo LDFLAGS: -ldl
#include <dlfcn.h>
#include <stdint.h>
#include <stdlib.h>

static const char* saga_ffi_error(void){ const char *e=dlerror(); return e?e:"unknown dl error"; }
static void* saga_ffi_symbol(const char* lib,const char* sym){
    dlerror(); void *h=dlopen(lib,RTLD_NOW|RTLD_LOCAL); if(!h)return NULL;
    dlerror(); return dlsym(h,sym);
}
static int64_t saga_i64_0(void* p){ return ((int64_t(*)(void))p)(); }
static int64_t saga_i64_1(void* p,int64_t a){ return ((int64_t(*)(int64_t))p)(a); }
static int64_t saga_i64_2(void* p,int64_t a,int64_t b){ return ((int64_t(*)(int64_t,int64_t))p)(a,b); }
static int64_t saga_i64_3(void* p,int64_t a,int64_t b,int64_t c){ return ((int64_t(*)(int64_t,int64_t,int64_t))p)(a,b,c); }
static int64_t saga_i64_4(void* p,int64_t a,int64_t b,int64_t c,int64_t d){ return ((int64_t(*)(int64_t,int64_t,int64_t,int64_t))p)(a,b,c,d); }
static double saga_f64_0(void* p){ return ((double(*)(void))p)(); }
static double saga_f64_1(void* p,double a){ return ((double(*)(double))p)(a); }
static double saga_f64_2(void* p,double a,double b){ return ((double(*)(double,double))p)(a,b); }
static double saga_f64_3(void* p,double a,double b,double c){ return ((double(*)(double,double,double))p)(a,b,c); }
static double saga_f64_4(void* p,double a,double b,double c,double d){ return ((double(*)(double,double,double,double))p)(a,b,c,d); }
*/
import "C"
import (
	"fmt"
	"unsafe"
)

func ffiAvailable() bool { return true }
func ffiSym(lib, sym string) (unsafe.Pointer, error) {
	clib := C.CString(lib)
	csym := C.CString(sym)
	defer C.free(unsafe.Pointer(clib))
	defer C.free(unsafe.Pointer(csym))
	p := C.saga_ffi_symbol(clib, csym)
	if p == nil {
		return nil, fmt.Errorf("dlsym %s:%s: %s", lib, sym, C.GoString(C.saga_ffi_error()))
	}
	return p, nil
}
func ffiCallI64(lib, sym string, a []int64) (int64, error) {
	p, e := ffiSym(lib, sym)
	if e != nil {
		return 0, e
	}
	switch len(a) {
	case 0:
		return int64(C.saga_i64_0(p)), nil
	case 1:
		return int64(C.saga_i64_1(p, C.int64_t(a[0]))), nil
	case 2:
		return int64(C.saga_i64_2(p, C.int64_t(a[0]), C.int64_t(a[1]))), nil
	case 3:
		return int64(C.saga_i64_3(p, C.int64_t(a[0]), C.int64_t(a[1]), C.int64_t(a[2]))), nil
	case 4:
		return int64(C.saga_i64_4(p, C.int64_t(a[0]), C.int64_t(a[1]), C.int64_t(a[2]), C.int64_t(a[3]))), nil
	default:
		return 0, fmt.Errorf("FFI scalar profile supports at most 4 arguments")
	}
}
func ffiCallF64(lib, sym string, a []float64) (float64, error) {
	p, e := ffiSym(lib, sym)
	if e != nil {
		return 0, e
	}
	switch len(a) {
	case 0:
		return float64(C.saga_f64_0(p)), nil
	case 1:
		return float64(C.saga_f64_1(p, C.double(a[0]))), nil
	case 2:
		return float64(C.saga_f64_2(p, C.double(a[0]), C.double(a[1]))), nil
	case 3:
		return float64(C.saga_f64_3(p, C.double(a[0]), C.double(a[1]), C.double(a[2]))), nil
	case 4:
		return float64(C.saga_f64_4(p, C.double(a[0]), C.double(a[1]), C.double(a[2]), C.double(a[3]))), nil
	default:
		return 0, fmt.Errorf("FFI scalar profile supports at most 4 arguments")
	}
}
