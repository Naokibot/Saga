//go:build sagajit && linux && amd64 && cgo

package main

/*
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

typedef int64_t (*saga_jit_fn0)(void);
typedef int64_t (*saga_jit_fn1)(int64_t);
typedef int64_t (*saga_jit_fn2)(int64_t,int64_t);
typedef int64_t (*saga_jit_fn3)(int64_t,int64_t,int64_t);
typedef int64_t (*saga_jit_fn4)(int64_t,int64_t,int64_t,int64_t);
typedef struct { void *code; size_t size; } saga_jit_block;

static saga_jit_block* saga_jit_alloc(const unsigned char *src, size_t n) {
  long page = sysconf(_SC_PAGESIZE);
  if (page <= 0) return NULL;
  size_t size = (n + (size_t)page - 1) & ~((size_t)page - 1);
  void *p = mmap(NULL, size, PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_ANONYMOUS, -1, 0);
  if (p == MAP_FAILED) return NULL;
  memcpy(p, src, n);
  if (mprotect(p, size, PROT_READ|PROT_EXEC) != 0) { munmap(p,size); return NULL; }
  saga_jit_block *b = (saga_jit_block*)calloc(1,sizeof(saga_jit_block));
  if (!b) { munmap(p,size); return NULL; }
  b->code=p; b->size=size; return b;
}
static int64_t saga_jit_call(saga_jit_block *b, int argc, int64_t *a) {
  switch(argc) {
    case 0: return ((saga_jit_fn0)b->code)();
    case 1: return ((saga_jit_fn1)b->code)(a[0]);
    case 2: return ((saga_jit_fn2)b->code)(a[0],a[1]);
    case 3: return ((saga_jit_fn3)b->code)(a[0],a[1],a[2]);
    case 4: return ((saga_jit_fn4)b->code)(a[0],a[1],a[2],a[3]);
    default: return 0;
  }
}
static void saga_jit_free(saga_jit_block *b) {
  if (!b) return;
  if (b->code && b->size) munmap(b->code,b->size);
  free(b);
}
*/
import "C"
import (
	"fmt"
	"unsafe"
)

func jitAvailable() bool { return true }
func jitAlloc(code []byte) (uintptr, error) {
	if len(code) == 0 {
		return 0, fmt.Errorf("empty JIT program")
	}
	b := C.saga_jit_alloc((*C.uchar)(unsafe.Pointer(&code[0])), C.size_t(len(code)))
	if b == nil {
		return 0, fmt.Errorf("mmap/mprotect JIT allocation failed")
	}
	return uintptr(unsafe.Pointer(b)), nil
}
func jitInvoke(handle uintptr, args []int64) (int64, error) {
	if handle == 0 || len(args) > 4 {
		return 0, fmt.Errorf("invalid JIT handle or arity")
	}
	var p *C.int64_t
	if len(args) > 0 {
		p = (*C.int64_t)(unsafe.Pointer(&args[0]))
	}
	r := C.saga_jit_call((*C.saga_jit_block)(unsafe.Pointer(handle)), C.int(len(args)), p)
	return int64(r), nil
}
func jitRelease(handle uintptr) {
	if handle != 0 {
		C.saga_jit_free((*C.saga_jit_block)(unsafe.Pointer(handle)))
	}
}
