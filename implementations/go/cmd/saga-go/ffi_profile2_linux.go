//go:build sagaffi && linux && amd64 && cgo

package main

/*
#cgo LDFLAGS: -ldl -l:libffi.so.8
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>
#include <stdio.h>

// Minimal libffi 3.x public ABI declarations. These definitions match the
// stable public ffi.h layout used by the validated linux/amd64 reference host.
typedef enum { FFI_OK=0, FFI_BAD_TYPEDEF=1, FFI_BAD_ABI=2, FFI_BAD_ARGTYPE=3 } ffi_status;
typedef enum { FFI_FIRST_ABI=1, FFI_UNIX64=2, FFI_WIN64=3, FFI_EFI64=3, FFI_GNUW64=4, FFI_LAST_ABI, FFI_DEFAULT_ABI=FFI_UNIX64 } ffi_abi;
typedef struct _ffi_type { size_t size; unsigned short alignment; unsigned short type; struct _ffi_type **elements; } ffi_type;
typedef struct { ffi_abi abi; unsigned nargs; ffi_type **arg_types; ffi_type *rtype; unsigned bytes; unsigned flags; } ffi_cif;
typedef struct ffi_closure ffi_closure;
extern ffi_type ffi_type_void, ffi_type_uint8, ffi_type_sint8, ffi_type_uint16, ffi_type_sint16, ffi_type_uint32, ffi_type_sint32, ffi_type_uint64, ffi_type_sint64, ffi_type_float, ffi_type_double, ffi_type_pointer;
extern ffi_status ffi_prep_cif(ffi_cif*, ffi_abi, unsigned, ffi_type*, ffi_type**);
extern void ffi_call(ffi_cif*, void (*)(void), void*, void**);
extern void *ffi_closure_alloc(size_t, void**);
extern void ffi_closure_free(void*);
typedef void (*ffi_closure_fun)(ffi_cif*,void*,void**,void*);
extern ffi_status ffi_prep_closure_loc(ffi_closure*,ffi_cif*,ffi_closure_fun,void*,void*);

#define FFI_TYPE_STRUCT 13

typedef struct SagaTypeNode { ffi_type t; struct SagaTypeNode **children; size_t child_count; } SagaTypeNode;
static void saga_skip_ws(const char **p){while(**p==' '||**p=='\t'||**p=='\n'||**p=='\r')(*p)++;}
static int saga_starts(const char *p,const char *s){return strncmp(p,s,strlen(s))==0;}
static ffi_type* saga_parse_type(const char **pp, SagaTypeNode ***owned, size_t *owned_n){
  const char *p=*pp; saga_skip_ws(&p);
  struct {const char*n; ffi_type*t;} m[]={
   {"void",&ffi_type_void},{"bool",&ffi_type_uint8},{"i8",&ffi_type_sint8},{"u8",&ffi_type_uint8},{"i16",&ffi_type_sint16},{"u16",&ffi_type_uint16},{"i32",&ffi_type_sint32},{"u32",&ffi_type_uint32},{"i64",&ffi_type_sint64},{"u64",&ffi_type_uint64},{"f32",&ffi_type_float},{"f64",&ffi_type_double},{"ptr",&ffi_type_pointer}};
  for(size_t i=0;i<sizeof(m)/sizeof(m[0]);i++){size_t n=strlen(m[i].n);if(strncmp(p,m[i].n,n)==0 && !(p[n]>='a'&&p[n]<='z') && !(p[n]>='0'&&p[n]<='9') && p[n]!='_'){p+=n;*pp=p;return m[i].t;}}
  if(saga_starts(p,"array[")){
    p+=6; char *end=NULL; unsigned long count=strtoul(p,&end,10); if(end==p||count==0||count>1048576||*end!=':')return NULL; p=end+1;
    ffi_type *elem=saga_parse_type(&p,owned,owned_n); if(!elem||*p!=']')return NULL; p++;
    SagaTypeNode *node=(SagaTypeNode*)calloc(1,sizeof(SagaTypeNode)); if(!node)return NULL; node->t.type=FFI_TYPE_STRUCT;
    ffi_type **els=(ffi_type**)calloc((size_t)count+1,sizeof(ffi_type*)); if(!els){free(node);return NULL;}
    for(size_t i=0;i<(size_t)count;i++)els[i]=elem; els[count]=NULL; node->t.elements=els; node->child_count=(size_t)count;
    SagaTypeNode **tmp=(SagaTypeNode**)realloc(*owned,(*owned_n+1)*sizeof(SagaTypeNode*)); if(!tmp){free(els);free(node);return NULL;} *owned=tmp; (*owned)[(*owned_n)++]=node; *pp=p; return &node->t;
  }
  if(saga_starts(p,"struct{")){
    p+=7; SagaTypeNode *node=(SagaTypeNode*)calloc(1,sizeof(SagaTypeNode)); if(!node)return NULL;
    node->t.type=FFI_TYPE_STRUCT; node->t.elements=NULL;
    size_t cap=4,n=0; ffi_type **els=(ffi_type**)calloc(cap+1,sizeof(ffi_type*)); if(!els){free(node);return NULL;}
    for(;;){ saga_skip_ws(&p); if(*p=='}'){p++;break;}
      // optional field-name prefix, recognized by ':' before comma/brace.
      const char *save=p,*q=p;int depth=0,has_colon=0;
      while(*q){if(*q=='{')depth++;else if(*q=='}'){if(depth==0)break;depth--;}else if(*q==':'&&depth==0){has_colon=1;break;}else if(*q==','&&depth==0)break;q++;}
      if(has_colon){p=q+1;} else p=save;
      ffi_type *ft=saga_parse_type(&p,owned,owned_n); if(!ft){free(els);free(node);return NULL;}
      if(n==cap){cap*=2;ffi_type **tmp=(ffi_type**)realloc(els,(cap+1)*sizeof(ffi_type*));if(!tmp){free(els);free(node);return NULL;}els=tmp;}
      els[n++]=ft;els[n]=NULL;saga_skip_ws(&p);if(*p==','){p++;continue;}if(*p=='}'){p++;break;}free(els);free(node);return NULL;
    }
    node->t.elements=els;node->children=NULL;node->child_count=n;
    SagaTypeNode **tmp=(SagaTypeNode**)realloc(*owned,(*owned_n+1)*sizeof(SagaTypeNode*));if(!tmp){free(els);free(node);return NULL;}*owned=tmp;(*owned)[(*owned_n)++]=node;*pp=p;return &node->t;
  }
  return NULL;
}
static void saga_free_types(SagaTypeNode **owned,size_t n){for(size_t i=0;i<n;i++){free(owned[i]->t.elements);free(owned[i]);}free(owned);}
static size_t saga_type_size(const char *desc){SagaTypeNode **owned=NULL;size_t on=0;const char*p=desc;ffi_type*t=saga_parse_type(&p,&owned,&on);if(!t){saga_free_types(owned,on);return 0;} if(t->type==FFI_TYPE_STRUCT){ffi_cif cif;ffi_type*args[1]={t}; if(ffi_prep_cif(&cif,FFI_DEFAULT_ABI,1,&ffi_type_void,args)!=FFI_OK){saga_free_types(owned,on);return 0;}}size_t z=t->size;saga_free_types(owned,on);return z;}
static void* saga_sym2(const char*lib,const char*sym,char*err,size_t errn){dlerror();void*h=dlopen(lib,RTLD_NOW|RTLD_LOCAL);if(!h){snprintf(err,errn,"dlopen: %s",dlerror());return NULL;}dlerror();void*p=dlsym(h,sym);const char*e=dlerror();if(e){snprintf(err,errn,"dlsym: %s",e);return NULL;}return p;}
static int saga_ffi_call2(const char*lib,const char*sym,const char*ret_desc,int argc,const char**arg_desc,void**values,void*ret,char*err,size_t errn){
 void*fn=saga_sym2(lib,sym,err,errn);if(!fn)return 0;SagaTypeNode**owned=NULL;size_t on=0;const char*rp=ret_desc;ffi_type*rt=saga_parse_type(&rp,&owned,&on);if(!rt){snprintf(err,errn,"bad return descriptor");saga_free_types(owned,on);return 0;}ffi_type**ats=(ffi_type**)calloc(argc?argc:1,sizeof(ffi_type*));if(!ats){saga_free_types(owned,on);return 0;}for(int i=0;i<argc;i++){const char*p=arg_desc[i];ats[i]=saga_parse_type(&p,&owned,&on);if(!ats[i]){snprintf(err,errn,"bad argument descriptor %d",i);free(ats);saga_free_types(owned,on);return 0;}}
 ffi_cif cif;ffi_status st=ffi_prep_cif(&cif,FFI_DEFAULT_ABI,(unsigned)argc,rt,ats);if(st!=FFI_OK){snprintf(err,errn,"ffi_prep_cif=%d",(int)st);free(ats);saga_free_types(owned,on);return 0;}ffi_call(&cif,(void(*)(void))fn,ret,values);free(ats);saga_free_types(owned,on);return 1;
}

typedef struct SagaClosureWrap { ffi_cif cif; ffi_type **args; ffi_type *ret; SagaTypeNode **owned; size_t owned_n; ffi_closure *closure; void *code; uintptr_t id; } SagaClosureWrap;
extern void sagaGoFFICallback(uintptr_t id, void *ret, void **args);
static void saga_closure_handler(ffi_cif*cif,void*ret,void**args,void*user){(void)cif;SagaClosureWrap*w=(SagaClosureWrap*)user;sagaGoFFICallback(w->id,ret,args);}
static SagaClosureWrap* saga_callback_make(uintptr_t id,const char*ret_desc,int argc,const char**arg_desc,char*err,size_t errn){SagaClosureWrap*w=(SagaClosureWrap*)calloc(1,sizeof(SagaClosureWrap));if(!w)return NULL;w->id=id;const char*rp=ret_desc;w->ret=saga_parse_type(&rp,&w->owned,&w->owned_n);if(!w->ret){snprintf(err,errn,"bad callback return descriptor");free(w);return NULL;}w->args=(ffi_type**)calloc(argc?argc:1,sizeof(ffi_type*));for(int i=0;i<argc;i++){const char*p=arg_desc[i];w->args[i]=saga_parse_type(&p,&w->owned,&w->owned_n);if(!w->args[i]){snprintf(err,errn,"bad callback arg descriptor");saga_free_types(w->owned,w->owned_n);free(w->args);free(w);return NULL;}}if(ffi_prep_cif(&w->cif,FFI_DEFAULT_ABI,(unsigned)argc,w->ret,w->args)!=FFI_OK){snprintf(err,errn,"ffi_prep_cif callback failed");saga_free_types(w->owned,w->owned_n);free(w->args);free(w);return NULL;}w->closure=(ffi_closure*)ffi_closure_alloc(4096,&w->code);if(!w->closure){snprintf(err,errn,"ffi_closure_alloc failed");saga_free_types(w->owned,w->owned_n);free(w->args);free(w);return NULL;}if(ffi_prep_closure_loc(w->closure,&w->cif,saga_closure_handler,w,w->code)!=FFI_OK){snprintf(err,errn,"ffi_prep_closure_loc failed");ffi_closure_free(w->closure);saga_free_types(w->owned,w->owned_n);free(w->args);free(w);return NULL;}return w;}
static void saga_callback_free(SagaClosureWrap*w){if(!w)return;if(w->closure)ffi_closure_free(w->closure);saga_free_types(w->owned,w->owned_n);free(w->args);free(w);}
static void* saga_callback_code(SagaClosureWrap*w){return w?w->code:NULL;}

static int8_t rd_i8(void*p){return *(int8_t*)p;}static uint8_t rd_u8(void*p){return *(uint8_t*)p;}static int16_t rd_i16(void*p){return *(int16_t*)p;}static uint16_t rd_u16(void*p){return *(uint16_t*)p;}static int32_t rd_i32(void*p){return *(int32_t*)p;}static uint32_t rd_u32(void*p){return *(uint32_t*)p;}static int64_t rd_i64(void*p){return *(int64_t*)p;}static uint64_t rd_u64(void*p){return *(uint64_t*)p;}static float rd_f32(void*p){return *(float*)p;}static double rd_f64(void*p){return *(double*)p;}static void*rd_ptr(void*p){return *(void**)p;}
static void wr_i8(void*p,int8_t v){*(int8_t*)p=v;}static void wr_u8(void*p,uint8_t v){*(uint8_t*)p=v;}static void wr_i16(void*p,int16_t v){*(int16_t*)p=v;}static void wr_u16(void*p,uint16_t v){*(uint16_t*)p=v;}static void wr_i32(void*p,int32_t v){*(int32_t*)p=v;}static void wr_u32(void*p,uint32_t v){*(uint32_t*)p=v;}static void wr_i64(void*p,int64_t v){*(int64_t*)p=v;}static void wr_u64(void*p,uint64_t v){*(uint64_t*)p=v;}static void wr_f32(void*p,float v){*(float*)p=v;}static void wr_f64(void*p,double v){*(double*)p=v;}static void wr_ptr(void*p,void*v){*(void**)p=v;}
static uintptr_t saga_alloc_addr(size_t n){return (uintptr_t)malloc(n);}
static void saga_free_addr(uintptr_t a){free((void*)a);}
static void saga_zero_addr(uintptr_t a,size_t n){if(a&&n)memset((void*)a,0,n);}
static void saga_copy_addr(uintptr_t d,uintptr_t s,size_t n){if(d&&s&&n)memcpy((void*)d,(void*)s,n);}
static int8_t rd_i8_a(uintptr_t a){return rd_i8((void*)a);} static uint8_t rd_u8_a(uintptr_t a){return rd_u8((void*)a);}
static int16_t rd_i16_a(uintptr_t a){return rd_i16((void*)a);} static uint16_t rd_u16_a(uintptr_t a){return rd_u16((void*)a);}
static int32_t rd_i32_a(uintptr_t a){return rd_i32((void*)a);} static uint32_t rd_u32_a(uintptr_t a){return rd_u32((void*)a);}
static int64_t rd_i64_a(uintptr_t a){return rd_i64((void*)a);} static uint64_t rd_u64_a(uintptr_t a){return rd_u64((void*)a);}
static float rd_f32_a(uintptr_t a){return rd_f32((void*)a);} static double rd_f64_a(uintptr_t a){return rd_f64((void*)a);} static uintptr_t rd_ptr_a(uintptr_t a){return (uintptr_t)rd_ptr((void*)a);}
static void wr_i8_a(uintptr_t a,int8_t v){wr_i8((void*)a,v);} static void wr_u8_a(uintptr_t a,uint8_t v){wr_u8((void*)a,v);}
static void wr_i16_a(uintptr_t a,int16_t v){wr_i16((void*)a,v);} static void wr_u16_a(uintptr_t a,uint16_t v){wr_u16((void*)a,v);}
static void wr_i32_a(uintptr_t a,int32_t v){wr_i32((void*)a,v);} static void wr_u32_a(uintptr_t a,uint32_t v){wr_u32((void*)a,v);}
static void wr_i64_a(uintptr_t a,int64_t v){wr_i64((void*)a,v);} static void wr_u64_a(uintptr_t a,uint64_t v){wr_u64((void*)a,v);}
static void wr_f32_a(uintptr_t a,float v){wr_f32((void*)a,v);} static void wr_f64_a(uintptr_t a,double v){wr_f64((void*)a,v);} static void wr_ptr_a(uintptr_t a,uintptr_t v){wr_ptr((void*)a,(void*)v);}
static int saga_ffi_call2_addr(const char*lib,const char*sym,const char*ret_desc,int argc,const char**arg_desc,uintptr_t*addrs,uintptr_t ret,char*err,size_t errn){
 void **vals=(void**)calloc(argc?argc:1,sizeof(void*)); if(!vals){snprintf(err,errn,"allocation failed");return 0;} for(int i=0;i<argc;i++)vals[i]=(void*)addrs[i];
 int ok=saga_ffi_call2(lib,sym,ret_desc,argc,arg_desc,vals,(void*)ret,err,errn); free(vals); return ok;
}
static uintptr_t saga_callback_make_addr(uintptr_t id,const char*ret_desc,int argc,const char**arg_desc,char*err,size_t errn){return (uintptr_t)saga_callback_make(id,ret_desc,argc,arg_desc,err,errn);}
static void saga_callback_free_addr(uintptr_t h){saga_callback_free((SagaClosureWrap*)h);}
static uintptr_t saga_callback_code_addr(uintptr_t h){return (uintptr_t)saga_callback_code((SagaClosureWrap*)h);}
*/
import "C"

import (
	"fmt"
	"unsafe"
)

type ffiRawArg struct {
	I64 int64
	U64 uint64
	F64 float64
	Ptr uintptr
}
type ffiRawResult = ffiRawArg

func ffiProfile2Available() bool { return true }
func ffiPointerSize() int        { return int(unsafe.Sizeof(uintptr(0))) }
func ffiAlloc(n int) uintptr     { return uintptr(C.saga_alloc_addr(C.size_t(n))) }
func ffiFree(p uintptr)          { C.saga_free_addr(C.uintptr_t(p)) }
func ffiZero(p uintptr, n int)   { C.saga_zero_addr(C.uintptr_t(p), C.size_t(n)) }
func ffiCopy(dst, src uintptr, n int) {
	C.saga_copy_addr(C.uintptr_t(dst), C.uintptr_t(src), C.size_t(n))
}
func ffiLoadI8(a uintptr) int8         { return int8(C.rd_i8_a(C.uintptr_t(a))) }
func ffiLoadU8(a uintptr) uint8        { return uint8(C.rd_u8_a(C.uintptr_t(a))) }
func ffiLoadI16(a uintptr) int16       { return int16(C.rd_i16_a(C.uintptr_t(a))) }
func ffiLoadU16(a uintptr) uint16      { return uint16(C.rd_u16_a(C.uintptr_t(a))) }
func ffiLoadI32(a uintptr) int32       { return int32(C.rd_i32_a(C.uintptr_t(a))) }
func ffiLoadU32(a uintptr) uint32      { return uint32(C.rd_u32_a(C.uintptr_t(a))) }
func ffiLoadI64(a uintptr) int64       { return int64(C.rd_i64_a(C.uintptr_t(a))) }
func ffiLoadU64(a uintptr) uint64      { return uint64(C.rd_u64_a(C.uintptr_t(a))) }
func ffiLoadF32(a uintptr) float32     { return float32(C.rd_f32_a(C.uintptr_t(a))) }
func ffiLoadF64(a uintptr) float64     { return float64(C.rd_f64_a(C.uintptr_t(a))) }
func ffiLoadPtr(a uintptr) uintptr     { return uintptr(C.rd_ptr_a(C.uintptr_t(a))) }
func ffiStoreI8(a uintptr, v int8)     { C.wr_i8_a(C.uintptr_t(a), C.int8_t(v)) }
func ffiStoreU8(a uintptr, v uint8)    { C.wr_u8_a(C.uintptr_t(a), C.uint8_t(v)) }
func ffiStoreI16(a uintptr, v int16)   { C.wr_i16_a(C.uintptr_t(a), C.int16_t(v)) }
func ffiStoreU16(a uintptr, v uint16)  { C.wr_u16_a(C.uintptr_t(a), C.uint16_t(v)) }
func ffiStoreI32(a uintptr, v int32)   { C.wr_i32_a(C.uintptr_t(a), C.int32_t(v)) }
func ffiStoreU32(a uintptr, v uint32)  { C.wr_u32_a(C.uintptr_t(a), C.uint32_t(v)) }
func ffiStoreI64(a uintptr, v int64)   { C.wr_i64_a(C.uintptr_t(a), C.int64_t(v)) }
func ffiStoreU64(a uintptr, v uint64)  { C.wr_u64_a(C.uintptr_t(a), C.uint64_t(v)) }
func ffiStoreF32(a uintptr, v float32) { C.wr_f32_a(C.uintptr_t(a), C.float(v)) }
func ffiStoreF64(a uintptr, v float64) { C.wr_f64_a(C.uintptr_t(a), C.double(v)) }
func ffiStorePtr(a uintptr, v uintptr) { C.wr_ptr_a(C.uintptr_t(a), C.uintptr_t(v)) }

type ffiArgStorage struct {
	addr uintptr
	free bool
}

func marshalFFIArg(desc string, v Value) (ffiArgStorage, error) {
	if len(desc) >= 7 && desc[:7] == "struct{" {
		p, ok := v.(*FFIPointer)
		if !ok || !ffiPointerLive(p, true) {
			return ffiArgStorage{}, fmt.Errorf("struct-by-value argument requires live ffi pointer")
		}
		return ffiArgStorage{addr: p.Addr}, nil
	}
	sz, _, ok := ffiScalarSizeAlign(desc)
	if !ok || desc == "void" {
		return ffiArgStorage{}, fmt.Errorf("unsupported argument descriptor %s", desc)
	}
	a := ffiAlloc(maxInt(sz, 8))
	if a == 0 {
		return ffiArgStorage{}, fmt.Errorf("malloc failed")
	}
	s := ffiArgStorage{addr: a, free: true}
	var e error
	switch desc {
	case "ptr":
		q, ok := v.(*FFIPointer)
		if !ok || !ffiPointerLive(q, false) {
			e = fmt.Errorf("ptr argument requires live ffi pointer")
		} else {
			ffiStorePtr(a, q.Addr)
		}
	default:
		e = ffiWriteValue(&FFIPointer{Addr: a, Size: maxInt(sz, 8)}, 0, desc, v)
	}
	if e != nil {
		ffiFree(a)
		return ffiArgStorage{}, e
	}
	return s, nil
}
func ffiCallABI(lib, sym, ret string, types []string, vals []Value) (ffiRawResult, error) {
	cl := C.CString(lib)
	cs := C.CString(sym)
	cr := C.CString(ret)
	defer C.free(unsafe.Pointer(cl))
	defer C.free(unsafe.Pointer(cs))
	defer C.free(unsafe.Pointer(cr))
	argc := len(types)
	cTypes := make([]*C.char, argc)
	stor := make([]ffiArgStorage, argc)
	addrs := make([]C.uintptr_t, argc)
	for j := range types {
		cTypes[j] = C.CString(types[j])
		defer C.free(unsafe.Pointer(cTypes[j]))
		s, e := marshalFFIArg(types[j], vals[j])
		if e != nil {
			return ffiRawResult{}, e
		}
		stor[j] = s
		addrs[j] = C.uintptr_t(s.addr)
		defer func(q ffiArgStorage) {
			if q.free {
				ffiFree(q.addr)
			}
		}(s)
	}
	var typePtr **C.char
	var addrPtr *C.uintptr_t
	if argc > 0 {
		typePtr = (**C.char)(unsafe.Pointer(&cTypes[0]))
		addrPtr = (*C.uintptr_t)(unsafe.Pointer(&addrs[0]))
	}
	retSize := 16
	if l, e := parseFFIStructDesc(ret); e == nil {
		retSize = maxInt(retSize, l.Size)
	}
	rp := ffiAlloc(retSize)
	if rp == 0 {
		return ffiRawResult{}, fmt.Errorf("return allocation failed")
	}
	defer ffiFree(rp)
	ffiZero(rp, retSize)
	errbuf := make([]byte, 512)
	if C.saga_ffi_call2_addr(cl, cs, cr, C.int(argc), typePtr, addrPtr, C.uintptr_t(rp), (*C.char)(unsafe.Pointer(&errbuf[0])), C.size_t(len(errbuf))) == 0 {
		return ffiRawResult{}, fmt.Errorf("%s", cstringBytes(errbuf))
	}
	out := ffiRawResult{}
	switch {
	case ret == "f32":
		out.F64 = float64(ffiLoadF32(rp))
	case ret == "f64":
		out.F64 = ffiLoadF64(rp)
	case ret == "ptr":
		out.Ptr = ffiLoadPtr(rp)
	case len(ret) >= 7 && ret[:7] == "struct{":
		l, _ := parseFFIStructDesc(ret)
		p := ffiAlloc(l.Size)
		ffiCopy(p, rp, l.Size)
		out.Ptr = p
	case ret == "u8" || ret == "bool":
		out.U64 = uint64(ffiLoadU8(rp))
	case ret == "i8":
		out.I64 = int64(ffiLoadI8(rp))
	case ret == "u16":
		out.U64 = uint64(ffiLoadU16(rp))
	case ret == "i16":
		out.I64 = int64(ffiLoadI16(rp))
	case ret == "u32":
		out.U64 = uint64(ffiLoadU32(rp))
	case ret == "i32":
		out.I64 = int64(ffiLoadI32(rp))
	case ret == "u64":
		out.U64 = ffiLoadU64(rp)
	case ret == "i64":
		out.I64 = ffiLoadI64(rp)
	}
	return out, nil
}
func cstringBytes(b []byte) string {
	n := 0
	for n < len(b) && b[n] != 0 {
		n++
	}
	return string(b[:n])
}
func ffiMakeCallback(id uint64, ret string, types []string) (uintptr, uintptr, error) {
	cr := C.CString(ret)
	defer C.free(unsafe.Pointer(cr))
	ct := make([]*C.char, len(types))
	for j := range types {
		ct[j] = C.CString(types[j])
		defer C.free(unsafe.Pointer(ct[j]))
	}
	var pp **C.char
	if len(ct) > 0 {
		pp = (**C.char)(unsafe.Pointer(&ct[0]))
	}
	errbuf := make([]byte, 512)
	h := uintptr(C.saga_callback_make_addr(C.uintptr_t(id), cr, C.int(len(types)), pp, (*C.char)(unsafe.Pointer(&errbuf[0])), C.size_t(len(errbuf))))
	if h == 0 {
		return 0, 0, fmt.Errorf("%s", cstringBytes(errbuf))
	}
	return h, uintptr(C.saga_callback_code_addr(C.uintptr_t(h))), nil
}
func ffiCloseCallback(h uintptr) {
	if h != 0 {
		C.saga_callback_free_addr(C.uintptr_t(h))
	}
}

//export sagaGoFFICallback
func sagaGoFFICallback(id C.uintptr_t, ret unsafe.Pointer, args *unsafe.Pointer) {
	ffiCallbacks.RLock()
	rec, ok := ffiCallbacks.m[uint64(id)]
	ffiCallbacks.RUnlock()
	if !ok {
		return
	}
	raw := make([]ffiRawArg, len(rec.args))
	arr := unsafe.Slice(args, len(rec.args))
	for j, d := range rec.args {
		p := uintptr(arr[j])
		switch {
		case d == "f32":
			raw[j].F64 = float64(ffiLoadF32(p))
		case d == "f64":
			raw[j].F64 = ffiLoadF64(p)
		case d == "ptr":
			raw[j].Ptr = ffiLoadPtr(p)
		case len(d) >= 7 && d[:7] == "struct{":
			raw[j].Ptr = p
		case d == "u8" || d == "bool":
			raw[j].U64 = uint64(ffiLoadU8(p))
		case d == "i8":
			raw[j].I64 = int64(ffiLoadI8(p))
		case d == "u16":
			raw[j].U64 = uint64(ffiLoadU16(p))
		case d == "i16":
			raw[j].I64 = int64(ffiLoadI16(p))
		case d == "u32":
			raw[j].U64 = uint64(ffiLoadU32(p))
		case d == "i32":
			raw[j].I64 = int64(ffiLoadI32(p))
		case d == "u64":
			raw[j].U64 = ffiLoadU64(p)
		case d == "i64":
			raw[j].I64 = ffiLoadI64(p)
		}
	}
	r, e := sagaFFICallbackDispatch(uint64(id), raw)
	if e != nil {
		return
	}
	switch {
	case rec.ret == "f32":
		ffiStoreF32(uintptr(ret), float32(r.F64))
	case rec.ret == "f64":
		ffiStoreF64(uintptr(ret), r.F64)
	case rec.ret == "ptr":
		ffiStorePtr(uintptr(ret), r.Ptr)
	case len(rec.ret) >= 7 && rec.ret[:7] == "struct{":
		l, _ := parseFFIStructDesc(rec.ret)
		ffiCopy(uintptr(ret), r.Ptr, l.Size)
	case rec.ret == "u8" || rec.ret == "bool":
		ffiStoreU8(uintptr(ret), uint8(r.U64))
	case rec.ret == "i8":
		ffiStoreI8(uintptr(ret), int8(r.I64))
	case rec.ret == "u16":
		ffiStoreU16(uintptr(ret), uint16(r.U64))
	case rec.ret == "i16":
		ffiStoreI16(uintptr(ret), int16(r.I64))
	case rec.ret == "u32":
		ffiStoreU32(uintptr(ret), uint32(r.U64))
	case rec.ret == "i32":
		ffiStoreI32(uintptr(ret), int32(r.I64))
	case rec.ret == "u64":
		ffiStoreU64(uintptr(ret), r.U64)
	case rec.ret == "i64":
		ffiStoreI64(uintptr(ret), r.I64)
	}
}
