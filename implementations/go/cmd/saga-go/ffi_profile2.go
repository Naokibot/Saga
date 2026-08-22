package main

import (
	"fmt"
	"math"
	"math/big"
	"strconv"
	"strings"
	"sync"
)

// FFIPointer is the explicit C ABI raw-pointer boundary. Ownership is never
// inferred: Owner=true means Saga is responsible for releasing the allocation.
type FFIPointer struct {
	Addr     uintptr
	Size     int
	Owner    bool
	Freed    bool
	Parent   *FFIPointer
	Callback *FFICallback
}

type FFIField struct {
	Name, Desc          string
	Offset, Size, Align int
}
type FFILayout struct {
	Fields      []FFIField
	Size, Align int
}
type FFICallback struct {
	Handle uintptr
	Code   uintptr
	ID     uint64
	Closed bool
}

type ffiCallbackRecord struct {
	interp   *Interpreter
	callable Value
	ret      string
	args     []string
}

var ffiCallbacks = struct {
	sync.RWMutex
	next uint64
	m    map[uint64]ffiCallbackRecord
}{next: 1, m: map[uint64]ffiCallbackRecord{}}

func ffiScalarSizeAlign(desc string) (int, int, bool) {
	switch strings.TrimSpace(desc) {
	case "i8", "u8", "bool":
		return 1, 1, true
	case "i16", "u16":
		return 2, 2, true
	case "i32", "u32", "f32":
		return 4, 4, true
	case "i64", "u64", "f64":
		return 8, 8, true
	case "ptr":
		return ffiPointerSize(), ffiPointerSize(), true
	case "void":
		return 0, 1, true
	}
	return 0, 0, false
}
func parseFFIArrayDesc(desc string) (int, string, error) {
	s := strings.TrimSpace(desc)
	if !strings.HasPrefix(s, "array[") || !strings.HasSuffix(s, "]") {
		return 0, "", fmt.Errorf("expected array[N:type]")
	}
	body := strings.TrimSpace(s[6 : len(s)-1])
	depth, split := 0, -1
	for j, r := range body {
		switch r {
		case '{', '[':
			depth++
		case '}', ']':
			depth--
		case ':':
			if depth == 0 {
				split = j
				goto found
			}
		}
	}
found:
	if split < 1 {
		return 0, "", fmt.Errorf("array descriptor requires array[N:type]")
	}
	n, e := strconv.Atoi(strings.TrimSpace(body[:split]))
	if e != nil || n < 1 || n > 1048576 {
		return 0, "", fmt.Errorf("invalid array length")
	}
	elem := strings.TrimSpace(body[split+1:])
	if elem == "" {
		return 0, "", fmt.Errorf("missing array element type")
	}
	return n, elem, nil
}
func ffiTypeSizeAlign(desc string) (int, int, error) {
	if s, a, ok := ffiScalarSizeAlign(strings.TrimSpace(desc)); ok {
		return s, a, nil
	}
	if strings.HasPrefix(strings.TrimSpace(desc), "struct{") {
		l, e := parseFFIStructDesc(desc)
		if e != nil {
			return 0, 0, e
		}
		return l.Size, l.Align, nil
	}
	if strings.HasPrefix(strings.TrimSpace(desc), "array[") {
		n, elem, e := parseFFIArrayDesc(desc)
		if e != nil {
			return 0, 0, e
		}
		es, ea, e := ffiTypeSizeAlign(elem)
		if e != nil {
			return 0, 0, e
		}
		stride := alignUp(es, ea)
		return stride * n, ea, nil
	}
	return 0, 0, fmt.Errorf("unsupported C ABI type %q", desc)
}
func ffiAggregateDesc(desc string) bool {
	s := strings.TrimSpace(desc)
	return strings.HasPrefix(s, "struct{") || strings.HasPrefix(s, "array[")
}

func alignUp(v, a int) int {
	if a <= 1 {
		return v
	}
	return (v + a - 1) &^ (a - 1)
}

func parseFFIStructDesc(desc string) (*FFILayout, error) {
	s := strings.TrimSpace(desc)
	if !strings.HasPrefix(s, "struct{") || !strings.HasSuffix(s, "}") {
		return nil, fmt.Errorf("expected struct{...} descriptor")
	}
	body := strings.TrimSpace(s[len("struct{") : len(s)-1])
	parts := []string{}
	depth, start := 0, 0
	for j, r := range body {
		switch r {
		case '{':
			depth++
		case '}':
			depth--
		case ',':
			if depth == 0 {
				parts = append(parts, strings.TrimSpace(body[start:j]))
				start = j + 1
			}
		}
	}
	if strings.TrimSpace(body[start:]) != "" {
		parts = append(parts, strings.TrimSpace(body[start:]))
	}
	fields := []FFIField{}
	off, maxA := 0, 1
	for idx, p := range parts {
		name := fmt.Sprintf("f%d", idx)
		typ := p
		if k := strings.Index(p, ":"); k >= 0 {
			name = strings.TrimSpace(p[:k])
			typ = strings.TrimSpace(p[k+1:])
		}
		sz, al, e := ffiTypeSizeAlign(typ)
		if e != nil {
			return nil, e
		}
		off = alignUp(off, al)
		fields = append(fields, FFIField{Name: name, Desc: typ, Offset: off, Size: sz, Align: al})
		off += sz
		if al > maxA {
			maxA = al
		}
	}
	return &FFILayout{Fields: fields, Size: alignUp(off, maxA), Align: maxA}, nil
}
func ffiLayoutFromFields(items []Value) (*FFILayout, error) {
	parts := make([]string, len(items))
	for j, v := range items {
		s, ok := v.(string)
		if !ok {
			return nil, fmt.Errorf("layout fields must be text name:type")
		}
		parts[j] = s
	}
	return parseFFIStructDesc("struct{" + strings.Join(parts, ",") + "}")
}
func (l *FFILayout) field(name string) (FFIField, bool) {
	for _, f := range l.Fields {
		if f.Name == name {
			return f, true
		}
	}
	return FFIField{}, false
}

func ffiNumberInt64(v Value) (int64, error) {
	n, ok := v.(Number)
	if !ok {
		return 0, fmt.Errorf("expected integer")
	}
	x, ok := n.Int()
	if !ok || !x.IsInt64() {
		return 0, fmt.Errorf("integer outside int64")
	}
	return x.Int64(), nil
}
func ffiNumberUint64(v Value) (uint64, error) {
	n, ok := v.(Number)
	if !ok {
		return 0, fmt.Errorf("expected integer")
	}
	x, ok := n.Int()
	if !ok || x.Sign() < 0 || x.BitLen() > 64 {
		return 0, fmt.Errorf("integer outside uint64")
	}
	return x.Uint64(), nil
}
func ffiFloat(v Value, bits int) (float64, error) {
	f, ok := v.(FloatValue)
	if !ok {
		return 0, fmt.Errorf("expected float%d", bits)
	}
	return f.V, nil
}

func ffiPointerLive(p *FFIPointer, dereference bool) bool {
	if p == nil || p.Freed {
		return false
	}
	if dereference && p.Addr == 0 {
		return false
	}
	for q := p.Parent; q != nil; q = q.Parent {
		if q.Freed || q.Addr == 0 {
			return false
		}
	}
	if p.Callback != nil && p.Callback.Closed {
		return false
	}
	return true
}

func ffiReadValue(p *FFIPointer, off int, desc string) (Value, error) {
	if !ffiPointerLive(p, true) {
		return nil, fmt.Errorf("invalid/freed pointer")
	}
	sz, _, ok := ffiScalarSizeAlign(desc)
	if !ok {
		return nil, fmt.Errorf("unsupported scalar %s", desc)
	}
	if off < 0 || (p.Size > 0 && off+sz > p.Size) {
		return nil, fmt.Errorf("pointer read out of bounds")
	}
	a := p.Addr + uintptr(off)
	switch desc {
	case "i8":
		return numberFromInt64(int64(ffiLoadI8(a))), nil
	case "u8", "bool":
		return numberFromInt64(int64(ffiLoadU8(a))), nil
	case "i16":
		return numberFromInt64(int64(ffiLoadI16(a))), nil
	case "u16":
		return numberFromInt64(int64(ffiLoadU16(a))), nil
	case "i32":
		return numberFromInt64(int64(ffiLoadI32(a))), nil
	case "u32":
		return numberFromInt64(int64(ffiLoadU32(a))), nil
	case "i64":
		return numberFromInt64(ffiLoadI64(a)), nil
	case "u64":
		return numberFromBigInt(newBigIntUint64(ffiLoadU64(a))), nil
	case "f32":
		return FloatValue{V: float64(ffiLoadF32(a)), Bits: 32}, nil
	case "f64":
		return FloatValue{V: ffiLoadF64(a), Bits: 64}, nil
	case "ptr":
		q := ffiLoadPtr(a)
		return &FFIPointer{Addr: q, Owner: false}, nil
	}
	return nil, fmt.Errorf("unsupported read type")
}
func ffiWriteValue(p *FFIPointer, off int, desc string, v Value) error {
	if !ffiPointerLive(p, true) {
		return fmt.Errorf("invalid/freed pointer")
	}
	sz, _, ok := ffiScalarSizeAlign(desc)
	if !ok {
		return fmt.Errorf("unsupported scalar %s", desc)
	}
	if off < 0 || (p.Size > 0 && off+sz > p.Size) {
		return fmt.Errorf("pointer write out of bounds")
	}
	a := p.Addr + uintptr(off)
	switch desc {
	case "i8", "i16", "i32", "i64":
		x, e := ffiNumberInt64(v)
		if e != nil {
			return e
		}
		switch desc {
		case "i8":
			ffiStoreI8(a, int8(x))
		case "i16":
			ffiStoreI16(a, int16(x))
		case "i32":
			ffiStoreI32(a, int32(x))
		case "i64":
			ffiStoreI64(a, x)
		}
	case "u8", "bool", "u16", "u32", "u64":
		x, e := ffiNumberUint64(v)
		if e != nil {
			return e
		}
		switch desc {
		case "u8", "bool":
			ffiStoreU8(a, uint8(x))
		case "u16":
			ffiStoreU16(a, uint16(x))
		case "u32":
			ffiStoreU32(a, uint32(x))
		case "u64":
			ffiStoreU64(a, x)
		}
	case "f32":
		x, e := ffiFloat(v, 32)
		if e != nil {
			return e
		}
		ffiStoreF32(a, float32(x))
	case "f64":
		x, e := ffiFloat(v, 64)
		if e != nil {
			return e
		}
		ffiStoreF64(a, x)
	case "ptr":
		q, ok := v.(*FFIPointer)
		if !ok {
			return fmt.Errorf("expected ffi pointer")
		}
		ffiStorePtr(a, q.Addr)
	default:
		return fmt.Errorf("unsupported write type")
	}
	return nil
}

func newBigIntUint64(v uint64) *big.Int { z := new(big.Int); z.SetUint64(v); return z }

func ffiMarshalReturn(desc string, raw ffiRawResult) (Value, error) {
	switch desc {
	case "void":
		return nil, nil
	case "i8", "i16", "i32", "i64":
		return numberFromInt64(raw.I64), nil
	case "u8", "u16", "u32", "u64":
		return numberFromBigInt(newBigIntUint64(raw.U64)), nil
	case "bool":
		return raw.U64 != 0, nil
	case "f32":
		return FloatValue{V: float64(float32(raw.F64)), Bits: 32}, nil
	case "f64":
		return FloatValue{V: raw.F64, Bits: 64}, nil
	case "ptr":
		return &FFIPointer{Addr: raw.Ptr, Owner: false}, nil
	}
	if ffiAggregateDesc(desc) {
		sz, _, e := ffiTypeSizeAlign(desc)
		if e != nil {
			return nil, e
		}
		if raw.Ptr == 0 && sz > 0 {
			return nil, fmt.Errorf("missing struct return storage")
		}
		// ffiCallABI already copied the transient ABI return buffer into a
		// Saga-owned allocation. Adopt it exactly once to avoid a leak.
		return &FFIPointer{Addr: raw.Ptr, Size: sz, Owner: true}, nil
	}
	return nil, fmt.Errorf("unsupported return descriptor %s", desc)
}

func (i *Interpreter) callFFIProfile2(name string, args []Value, t Token) (Value, bool, error) {
	profile2Names := map[string]bool{"profile": true, "ptr_null": true, "alloc": true, "free": true, "ptr_add": true, "ptr_address": true, "borrow": true, "adopt": true, "layout": true, "layout_size": true, "struct_alloc": true, "struct_get": true, "struct_set": true, "load": true, "store": true, "call": true, "callback": true, "callback_ptr": true, "callback_close": true}
	if profile2Names[name] && !ffiProfile2Available() {
		return nil, true, i.rerr(t, "SAGA-R190", "C ABI Profile 2 backend is unavailable on this build/host")
	}
	fail := func(e error) (Value, bool, error) {
		if e == nil {
			return nil, true, nil
		}
		return nil, true, i.rerr(t, "SAGA-R190", e.Error())
	}
	switch name {
	case "profile":
		return "C-ABI-2", true, nil
	case "ptr_null":
		return &FFIPointer{}, true, nil
	case "alloc":
		if len(args) != 1 {
			return fail(fmt.Errorf("ffi.alloc(size)"))
		}
		n, e := ffiNumberInt64(args[0])
		if e != nil || n < 0 {
			return fail(fmt.Errorf("invalid allocation size"))
		}
		a := ffiAlloc(int(n))
		if a == 0 && n > 0 {
			return fail(fmt.Errorf("allocation failed"))
		}
		return &FFIPointer{Addr: a, Size: int(n), Owner: true}, true, nil
	case "free":
		if len(args) != 1 {
			return fail(fmt.Errorf("ffi.free(ptr)"))
		}
		p, ok := args[0].(*FFIPointer)
		if !ok {
			return fail(fmt.Errorf("expected ffi pointer"))
		}
		if e := ffiFreePointer(p); e != nil {
			return fail(e)
		}
		return nil, true, nil
	case "ptr_add":
		if len(args) != 2 {
			return fail(fmt.Errorf("ffi.ptr_add(ptr,offset)"))
		}
		p, ok := args[0].(*FFIPointer)
		if !ok || !ffiPointerLive(p, true) {
			return fail(fmt.Errorf("expected live ffi pointer"))
		}
		n, e := ffiNumberInt64(args[1])
		if e != nil {
			return fail(e)
		}
		if n < 0 || (p.Size > 0 && n > int64(p.Size)) {
			return fail(fmt.Errorf("pointer offset out of bounds"))
		}
		return &FFIPointer{Addr: p.Addr + uintptr(n), Size: maxInt(0, p.Size-int(n)), Owner: false, Parent: p}, true, nil
	case "ptr_address":
		if len(args) != 1 {
			return fail(fmt.Errorf("ffi.ptr_address(ptr)"))
		}
		p, ok := args[0].(*FFIPointer)
		if !ok || !ffiPointerLive(p, false) {
			return fail(fmt.Errorf("expected live ffi pointer"))
		}
		return numberFromBigInt(newBigIntUint64(uint64(p.Addr))), true, nil
	case "borrow":
		if len(args) != 2 {
			return fail(fmt.Errorf("ffi.borrow(ptr,size)"))
		}
		p, ok := args[0].(*FFIPointer)
		n, e := ffiNumberInt64(args[1])
		if !ok || !ffiPointerLive(p, false) || e != nil || n < 0 {
			return fail(fmt.Errorf("invalid borrow arguments"))
		}
		return &FFIPointer{Addr: p.Addr, Size: int(n), Owner: false, Parent: p, Callback: p.Callback}, true, nil
	case "adopt":
		if len(args) != 2 {
			return fail(fmt.Errorf("ffi.adopt(ptr,size)"))
		}
		p, ok := args[0].(*FFIPointer)
		n, e := ffiNumberInt64(args[1])
		if !ok || !ffiPointerLive(p, false) || e != nil || n < 0 {
			return fail(fmt.Errorf("invalid adopt arguments"))
		}
		if p.Owner || p.Parent != nil || p.Callback != nil {
			return fail(fmt.Errorf("only an unowned root C pointer can be adopted"))
		}
		// Ownership transfer invalidates the source handle so two Saga owners cannot exist.
		owned := &FFIPointer{Addr: p.Addr, Size: int(n), Owner: true}
		p.Freed = true
		p.Addr = 0
		return owned, true, nil
	case "layout":
		if len(args) != 1 {
			return fail(fmt.Errorf("ffi.layout(fields)"))
		}
		xs, ok := args[0].([]Value)
		if !ok {
			return fail(fmt.Errorf("fields must be list[text]"))
		}
		l, e := ffiLayoutFromFields(xs)
		if e != nil {
			return fail(e)
		}
		return l, true, nil
	case "layout_size":
		if len(args) != 1 {
			return fail(fmt.Errorf("ffi.layout_size(layout)"))
		}
		l, ok := args[0].(*FFILayout)
		if !ok {
			return fail(fmt.Errorf("expected ffi layout"))
		}
		return numberFromInt64(int64(l.Size)), true, nil
	case "struct_alloc":
		if len(args) != 1 {
			return fail(fmt.Errorf("ffi.struct_alloc(layout)"))
		}
		l, ok := args[0].(*FFILayout)
		if !ok {
			return fail(fmt.Errorf("expected ffi layout"))
		}
		a := ffiAlloc(l.Size)
		if a == 0 && l.Size > 0 {
			return fail(fmt.Errorf("allocation failed"))
		}
		ffiZero(a, l.Size)
		return &FFIPointer{Addr: a, Size: l.Size, Owner: true}, true, nil
	case "struct_get":
		if len(args) != 3 {
			return fail(fmt.Errorf("ffi.struct_get(layout,ptr,field)"))
		}
		l, lok := args[0].(*FFILayout)
		p, pok := args[1].(*FFIPointer)
		f, fok := args[2].(string)
		if !lok || !pok || !fok {
			return fail(fmt.Errorf("invalid struct_get arguments"))
		}
		fd, ok := l.field(f)
		if !ok {
			return fail(fmt.Errorf("unknown struct field %s", f))
		}
		if ffiAggregateDesc(fd.Desc) {
			if !ffiPointerLive(p, true) || (p.Size > 0 && fd.Offset+fd.Size > p.Size) {
				return fail(fmt.Errorf("nested struct field out of bounds"))
			}
			return &FFIPointer{Addr: p.Addr + uintptr(fd.Offset), Size: fd.Size, Owner: false, Parent: p}, true, nil
		}
		v, e := ffiReadValue(p, fd.Offset, fd.Desc)
		if e != nil {
			return fail(e)
		}
		return v, true, nil
	case "struct_set":
		if len(args) != 4 {
			return fail(fmt.Errorf("ffi.struct_set(layout,ptr,field,value)"))
		}
		l, lok := args[0].(*FFILayout)
		p, pok := args[1].(*FFIPointer)
		f, fok := args[2].(string)
		if !lok || !pok || !fok {
			return fail(fmt.Errorf("invalid struct_set arguments"))
		}
		fd, ok := l.field(f)
		if !ok {
			return fail(fmt.Errorf("unknown struct field %s", f))
		}
		if ffiAggregateDesc(fd.Desc) {
			q, ok := args[3].(*FFIPointer)
			if !ok || !ffiPointerLive(q, true) || !ffiPointerLive(p, true) || (q.Size > 0 && q.Size < fd.Size) || (p.Size > 0 && fd.Offset+fd.Size > p.Size) {
				return fail(fmt.Errorf("nested struct_set requires compatible live storage"))
			}
			ffiCopy(p.Addr+uintptr(fd.Offset), q.Addr, fd.Size)
			return nil, true, nil
		}
		if e := ffiWriteValue(p, fd.Offset, fd.Desc, args[3]); e != nil {
			return fail(e)
		}
		return nil, true, nil
	case "load":
		if len(args) != 3 {
			return fail(fmt.Errorf("ffi.load(ptr,offset,type)"))
		}
		p, ok := args[0].(*FFIPointer)
		typ, tok := args[2].(string)
		off, e := ffiNumberInt64(args[1])
		if !ok || !tok || e != nil {
			return fail(fmt.Errorf("invalid load arguments"))
		}
		v, e := ffiReadValue(p, int(off), typ)
		if e != nil {
			return fail(e)
		}
		return v, true, nil
	case "store":
		if len(args) != 4 {
			return fail(fmt.Errorf("ffi.store(ptr,offset,type,value)"))
		}
		p, ok := args[0].(*FFIPointer)
		typ, tok := args[2].(string)
		off, e := ffiNumberInt64(args[1])
		if !ok || !tok || e != nil {
			return fail(fmt.Errorf("invalid store arguments"))
		}
		if e := ffiWriteValue(p, int(off), typ, args[3]); e != nil {
			return fail(e)
		}
		return nil, true, nil
	case "call":
		if len(args) != 5 {
			return fail(fmt.Errorf("ffi.call(library,symbol,return_type,arg_types,args)"))
		}
		lib, lok := args[0].(string)
		sym, sok := args[1].(string)
		ret, rok := args[2].(string)
		typesv, tvok := args[3].([]Value)
		vals, vok := args[4].([]Value)
		if !lok || !sok || !rok || !tvok || !vok {
			return fail(fmt.Errorf("invalid ffi.call arguments"))
		}
		if len(typesv) != len(vals) {
			return fail(fmt.Errorf("argument type/value count mismatch"))
		}
		types := make([]string, len(typesv))
		for j, v := range typesv {
			s, ok := v.(string)
			if !ok {
				return fail(fmt.Errorf("argument type descriptors must be text"))
			}
			types[j] = s
		}
		raw, e := ffiCallABI(lib, sym, ret, types, vals)
		if e != nil {
			return fail(e)
		}
		v, e := ffiMarshalReturn(ret, raw)
		if e != nil {
			return fail(e)
		}
		return v, true, nil
	case "callback":
		if len(args) != 3 {
			return fail(fmt.Errorf("ffi.callback(callable,return_type,arg_types)"))
		}
		ret, rok := args[1].(string)
		tv, ok := args[2].([]Value)
		if !rok || !ok {
			return fail(fmt.Errorf("invalid callback signature"))
		}
		types := make([]string, len(tv))
		for j, v := range tv {
			s, ok := v.(string)
			if !ok {
				return fail(fmt.Errorf("callback arg descriptors must be text"))
			}
			types[j] = s
		}
		ffiCallbacks.Lock()
		id := ffiCallbacks.next
		ffiCallbacks.next++
		ffiCallbacks.m[id] = ffiCallbackRecord{interp: i, callable: args[0], ret: ret, args: types}
		ffiCallbacks.Unlock()
		h, code, e := ffiMakeCallback(id, ret, types)
		if e != nil {
			ffiCallbacks.Lock()
			delete(ffiCallbacks.m, id)
			ffiCallbacks.Unlock()
			return fail(e)
		}
		return &FFICallback{Handle: h, Code: code, ID: id}, true, nil
	case "callback_ptr":
		if len(args) != 1 {
			return fail(fmt.Errorf("ffi.callback_ptr(callback)"))
		}
		cb, ok := args[0].(*FFICallback)
		if !ok || cb.Closed {
			return fail(fmt.Errorf("invalid callback"))
		}
		return &FFIPointer{Addr: cb.Code, Owner: false, Callback: cb}, true, nil
	case "callback_close":
		if len(args) != 1 {
			return fail(fmt.Errorf("ffi.callback_close(callback)"))
		}
		cb, ok := args[0].(*FFICallback)
		if !ok {
			return fail(fmt.Errorf("invalid callback"))
		}
		ffiCloseCallbackValue(cb)
		return nil, true, nil
	}
	return nil, false, nil
}

func ffiFreePointer(p *FFIPointer) error {
	if p == nil {
		return fmt.Errorf("nil pointer")
	}
	if p.Freed {
		return fmt.Errorf("double free")
	}
	if !p.Owner {
		return fmt.Errorf("cannot free borrowed pointer")
	}
	if p.Addr != 0 {
		ffiFree(p.Addr)
	}
	p.Addr = 0
	p.Freed = true
	return nil
}
func ffiCloseCallbackValue(cb *FFICallback) {
	if cb == nil || cb.Closed {
		return
	}
	ffiCloseCallback(cb.Handle)
	ffiCallbacks.Lock()
	delete(ffiCallbacks.m, cb.ID)
	ffiCallbacks.Unlock()
	cb.Closed = true
	cb.Code = 0
	cb.Handle = 0
}

// Called from the platform bridge. It intentionally lives outside the C ABI
// implementation file so callback lifetime and Saga interpreter state remain
// explicit and auditable.
func sagaFFICallbackDispatch(id uint64, raw []ffiRawArg) (ffiRawResult, error) {
	ffiCallbacks.RLock()
	rec, ok := ffiCallbacks.m[id]
	ffiCallbacks.RUnlock()
	if !ok {
		return ffiRawResult{}, fmt.Errorf("callback is closed")
	}
	vals := make([]Value, len(raw))
	for j, r := range raw {
		d := rec.args[j]
		switch {
		case d == "i8" || d == "i16" || d == "i32" || d == "i64":
			vals[j] = numberFromInt64(r.I64)
		case d == "u8" || d == "u16" || d == "u32" || d == "u64":
			vals[j] = numberFromBigInt(newBigIntUint64(r.U64))
		case d == "bool":
			vals[j] = r.U64 != 0
		case d == "f32":
			vals[j] = FloatValue{V: float64(float32(r.F64)), Bits: 32}
		case d == "f64":
			vals[j] = FloatValue{V: r.F64, Bits: 64}
		case d == "ptr":
			vals[j] = &FFIPointer{Addr: r.Ptr, Owner: false}
		case ffiAggregateDesc(d):
			sz, _, e := ffiTypeSizeAlign(d)
			if e != nil {
				return ffiRawResult{}, e
			}
			vals[j] = &FFIPointer{Addr: r.Ptr, Size: sz, Owner: false}
		default:
			return ffiRawResult{}, fmt.Errorf("unsupported callback argument %s", d)
		}
	}
	v, e := rec.interp.invokeDirect(rec.callable, vals, Token{Lex: "ffi-callback"})
	if e != nil {
		return ffiRawResult{}, e
	}
	return ffiEncodeRawResult(rec.ret, v)
}
func ffiEncodeRawResult(desc string, v Value) (ffiRawResult, error) {
	var r ffiRawResult
	switch desc {
	case "void":
		return r, nil
	case "i8", "i16", "i32", "i64":
		x, e := ffiNumberInt64(v)
		r.I64 = x
		r.U64 = uint64(x)
		return r, e
	case "u8", "u16", "u32", "u64":
		x, e := ffiNumberUint64(v)
		r.U64 = x
		r.I64 = int64(x)
		return r, e
	case "bool":
		b, ok := v.(bool)
		if !ok {
			return r, fmt.Errorf("callback bool return required")
		}
		if b {
			r.U64 = 1
		}
		return r, nil
	case "f32", "f64":
		f, ok := v.(FloatValue)
		if !ok {
			return r, fmt.Errorf("callback float return required")
		}
		r.F64 = f.V
		return r, nil
	case "ptr":
		p, ok := v.(*FFIPointer)
		if !ok || !ffiPointerLive(p, false) {
			return r, fmt.Errorf("callback live pointer return required")
		}
		r.Ptr = p.Addr
		return r, nil
	}
	if ffiAggregateDesc(desc) {
		p, ok := v.(*FFIPointer)
		if !ok || !ffiPointerLive(p, true) {
			return r, fmt.Errorf("callback struct return requires live ffi pointer")
		}
		r.Ptr = p.Addr
		return r, nil
	}
	return r, fmt.Errorf("unsupported callback return %s", desc)
}

var _ = math.Float64bits
var _ = strconv.IntSize
