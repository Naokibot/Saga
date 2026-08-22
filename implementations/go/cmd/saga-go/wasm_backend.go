//go:build !sagaruntime

package main

import (
	"bytes"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

type wasmFuncSig struct {
	params int
	result bool
}
type wasmData struct {
	offset int
	text   string
}
type wasmCompiler struct {
	funcs     []*FnDecl
	funcIndex map[string]uint32
	sigs      []wasmFuncSig
	sigIndex  map[wasmFuncSig]uint32
	funcTypes []uint32
	data      []wasmData
	nextData  int
	noHost    bool
}
type wasmFnCompiler struct {
	w      *wasmCompiler
	locals map[string]uint32
	next   uint32
	code   bytes.Buffer
	result bool
}

func uleb(v uint64) []byte {
	b := []byte{}
	for {
		q := byte(v & 0x7f)
		v >>= 7
		if v != 0 {
			q |= 0x80
		}
		b = append(b, q)
		if v == 0 {
			return b
		}
	}
}
func sleb(v int64) []byte {
	b := []byte{}
	more := true
	for more {
		q := byte(v & 0x7f)
		v >>= 7
		sign := q&0x40 != 0
		more = !((v == 0 && !sign) || (v == -1 && sign))
		if more {
			q |= 0x80
		}
		b = append(b, q)
	}
	return b
}
func wasmName(s string) []byte { b := []byte(s); return append(uleb(uint64(len(b))), b...) }
func wasmVec(items ...[]byte) []byte {
	var b bytes.Buffer
	b.Write(uleb(uint64(len(items))))
	for _, x := range items {
		b.Write(x)
	}
	return b.Bytes()
}
func wasmSection(id byte, payload []byte) []byte {
	return append([]byte{id}, append(uleb(uint64(len(payload))), payload...)...)
}
func (w *wasmCompiler) typeID(sig wasmFuncSig) uint32 {
	if x, ok := w.sigIndex[sig]; ok {
		return x
	}
	x := uint32(len(w.sigs))
	w.sigIndex[sig] = x
	w.sigs = append(w.sigs, sig)
	return x
}
func supportedWasmType(t *TypeRef) bool {
	if t == nil {
		return true
	}
	return t.Name == "int" || t.Name == "bool" || t.Name == "unit"
}
func (w *wasmCompiler) intern(s string) (int, int) {
	for _, d := range w.data {
		if d.text == s {
			return d.offset, len([]byte(s))
		}
	}
	off := w.nextData
	w.nextData += len([]byte(s))
	w.data = append(w.data, wasmData{off, s})
	return off, len([]byte(s))
}
func (f *wasmFnCompiler) op(b ...byte)          { f.code.Write(b) }
func (f *wasmFnCompiler) idx(op byte, n uint32) { f.op(op); f.code.Write(uleb(uint64(n))) }
func (f *wasmFnCompiler) iconst(n int64)        { f.op(0x42); f.code.Write(sleb(n)) }
func (f *wasmFnCompiler) alloc(name string) uint32 {
	if x, ok := f.locals[name]; ok {
		return x
	}
	x := f.next
	f.next++
	f.locals[name] = x
	return x
}
func numberI64(n Number) (int64, error) {
	x, ok := n.Int()
	if !ok || !x.IsInt64() {
		return 0, fmt.Errorf("WASM scalar backend requires i64 integer values")
	}
	return x.Int64(), nil
}
func (f *wasmFnCompiler) expr(e Expr) error {
	switch x := e.(type) {
	case *Literal:
		switch v := x.Value.(type) {
		case Number:
			n, er := numberI64(v)
			if er != nil {
				return er
			}
			f.iconst(n)
			return nil
		case bool:
			if v {
				f.iconst(1)
			} else {
				f.iconst(0)
			}
			return nil
		case string:
			return fmt.Errorf("text values are only supported directly inside print in WASM scalar profile")
		}
		return fmt.Errorf("unsupported WASM literal")
	case *Variable:
		n, ok := f.locals[x.Name]
		if !ok {
			return fmt.Errorf("WASM scalar unknown local %s", x.Name)
		}
		f.idx(0x20, n)
		return nil
	case *Unary:
		if x.Op.Kind == MINUS {
			f.iconst(0)
			if e := f.expr(x.Right); e != nil {
				return e
			}
			f.op(0x7d)
			return nil
		}
		if x.Op.Kind == BANG || x.Op.Kind == NOT {
			if e := f.expr(x.Right); e != nil {
				return e
			}
			f.op(0x50, 0xad)
			return nil
		}
		return fmt.Errorf("unsupported WASM unary")
	case *Binary:
		if e := f.expr(x.Left); e != nil {
			return e
		}
		if e := f.expr(x.Right); e != nil {
			return e
		}
		ops := map[Kind]byte{PLUS: 0x7c, MINUS: 0x7d, STAR: 0x7e, SLASH: 0x7f, PERCENT: 0x81, AND: 0x83, OR: 0x84, EQEQ: 0x51, BANGEQ: 0x52, LESS: 0x53, GREATER: 0x55, LESSEQ: 0x57, GREATEREQ: 0x59}
		op, ok := ops[x.Op.Kind]
		if !ok {
			return fmt.Errorf("operator not supported by WASM scalar profile")
		}
		f.op(op)
		if x.Op.Kind == EQEQ || x.Op.Kind == BANGEQ || x.Op.Kind == LESS || x.Op.Kind == GREATER || x.Op.Kind == LESSEQ || x.Op.Kind == GREATEREQ {
			f.op(0xad)
		}
		return nil
	case *Call:
		if v, ok := x.Callee.(*Variable); ok {
			if v.Name == "int" && len(x.Args) == 1 {
				return f.expr(x.Args[0])
			}
			if idx, ok := f.w.funcIndex[v.Name]; ok {
				for _, a := range x.Args {
					if e := f.expr(a); e != nil {
						return e
					}
				}
				f.idx(0x10, idx)
				return nil
			}
		}
		return fmt.Errorf("call not supported by WASM scalar profile")
	}
	return fmt.Errorf("expression %T not supported by WASM scalar profile", e)
}
func (f *wasmFnCompiler) printArg(e Expr) error {
	if l, ok := e.(*Literal); ok {
		if s, ok := l.Value.(string); ok {
			off, n := f.w.intern(s)
			f.op(0x41)
			f.code.Write(sleb(int64(off)))
			f.op(0x41)
			f.code.Write(sleb(int64(n)))
			f.idx(0x10, 1)
			return nil
		}
	}
	if is, ok := e.(*InterpolatedString); ok {
		for j, t := range is.Texts {
			if t != "" {
				off, n := f.w.intern(t)
				f.op(0x41)
				f.code.Write(sleb(int64(off)))
				f.op(0x41)
				f.code.Write(sleb(int64(n)))
				f.idx(0x10, 1)
			}
			if j < len(is.Exprs) {
				if er := f.expr(is.Exprs[j]); er != nil {
					return er
				}
				f.idx(0x10, 0)
			}
		}
		return nil
	}
	if e := f.expr(e); e != nil {
		return e
	}
	f.idx(0x10, 0)
	return nil
}
func (f *wasmFnCompiler) stmt(s Stmt) error {
	switch x := s.(type) {
	case *VarDecl:
		if e := f.expr(x.Init); e != nil {
			return e
		}
		f.idx(0x21, f.alloc(x.Name))
		return nil
	case *Assign:
		v, ok := x.Target.(*Variable)
		if !ok {
			return fmt.Errorf("WASM scalar assignment only supports variables")
		}
		if e := f.expr(x.Value); e != nil {
			return e
		}
		f.idx(0x21, f.alloc(v.Name))
		return nil
	case *ExprStmt:
		if c, ok := x.Expr.(*Call); ok {
			if v, ok := c.Callee.(*Variable); ok && v.Name == "print" {
				if f.w.noHost {
					return fmt.Errorf("embedded WASM profile forbids hosted print")
				}
				for j, a := range c.Args {
					if j > 0 {
						off, n := f.w.intern(" ")
						f.op(0x41)
						f.code.Write(sleb(int64(off)))
						f.op(0x41)
						f.code.Write(sleb(int64(n)))
						f.idx(0x10, 1)
					}
					if e := f.printArg(a); e != nil {
						return e
					}
				}
				off, n := f.w.intern("\n")
				f.op(0x41)
				f.code.Write(sleb(int64(off)))
				f.op(0x41)
				f.code.Write(sleb(int64(n)))
				f.idx(0x10, 1)
				return nil
			}
			if v, ok := c.Callee.(*Variable); ok && v.Name == "assert" && len(c.Args) == 1 {
				if e := f.expr(c.Args[0]); e != nil {
					return e
				}
				f.op(0x50, 0x04, 0x40, 0x00, 0x0b)
				return nil
			}
		}
		if e := f.expr(x.Expr); e != nil {
			return e
		}
		f.op(0x1a)
		return nil
	case *Block:
		for _, q := range x.Stmts {
			if e := f.stmt(q); e != nil {
				return e
			}
		}
		return nil
	case *IfStmt:
		if e := f.expr(x.Cond); e != nil {
			return e
		}
		f.op(0x50, 0x45)
		f.op(0x04, 0x40)
		if e := f.stmt(x.Then); e != nil {
			return e
		}
		if x.Else != nil {
			f.op(0x05)
			if e := f.stmt(x.Else); e != nil {
				return e
			}
		}
		f.op(0x0b)
		return nil
	case *WhileStmt:
		f.op(0x02, 0x40, 0x03, 0x40)
		if e := f.expr(x.Cond); e != nil {
			return e
		}
		f.op(0x50)
		f.idx(0x0d, 1)
		if e := f.stmt(x.Body); e != nil {
			return e
		}
		f.idx(0x0c, 0)
		f.op(0x0b, 0x0b)
		return nil
	case *ForStmt:
		r, ok := x.Iterable.(*RangeExpr)
		if !ok {
			return fmt.Errorf("WASM scalar for requires an integer range")
		}
		iv := f.alloc(x.Name)
		end := f.alloc("$end" + x.Name)
		step := f.alloc("$step" + x.Name)
		if e := f.expr(r.Start); e != nil {
			return e
		}
		f.idx(0x21, iv)
		if e := f.expr(r.End); e != nil {
			return e
		}
		f.idx(0x21, end)
		f.idx(0x20, iv)
		f.idx(0x20, end)
		f.op(0x57)
		f.op(0x04, 0x7e)
		f.iconst(1)
		f.op(0x05)
		f.iconst(-1)
		f.op(0x0b)
		f.idx(0x21, step)
		f.op(0x02, 0x40, 0x03, 0x40)
		f.idx(0x20, step)
		f.iconst(0)
		f.op(0x55)
		f.op(0x04, 0x7e)
		f.idx(0x20, iv)
		f.idx(0x20, end)
		f.op(0x57, 0xad)
		f.op(0x05)
		f.idx(0x20, iv)
		f.idx(0x20, end)
		f.op(0x59, 0xad)
		f.op(0x0b)
		f.op(0x50)
		f.idx(0x0d, 1)
		if e := f.stmt(x.Body); e != nil {
			return e
		}
		f.idx(0x20, iv)
		f.idx(0x20, step)
		f.op(0x7c)
		f.idx(0x21, iv)
		f.idx(0x0c, 0)
		f.op(0x0b, 0x0b)
		return nil
	case *ReturnStmt:
		if x.Value != nil {
			if e := f.expr(x.Value); e != nil {
				return e
			}
		}
		f.op(0x0f)
		return nil
	case *FnDecl, *UseStmt, *ClassDecl, *EnumDecl, *TestDecl:
		return nil
	case *BreakStmt, *ContinueStmt:
		return fmt.Errorf("break/continue are not yet supported in WASM scalar profile")
	}
	return fmt.Errorf("statement %T not supported by WASM scalar profile", s)
}
func (w *wasmCompiler) compileFunc(d *FnDecl) ([]byte, error) {
	f := &wasmFnCompiler{w: w, locals: map[string]uint32{}, result: d.Return != nil && d.Return.Name != "unit"}
	for j, p := range d.Params {
		if p.Type.Name != "int" && p.Type.Name != "bool" {
			return nil, fmt.Errorf("WASM scalar parameter %s must be int/bool", p.Name)
		}
		f.locals[p.Name] = uint32(j)
	}
	f.next = uint32(len(d.Params))
	if d.ExprBody != nil {
		if e := f.expr(d.ExprBody); e != nil {
			return nil, e
		}
		f.op(0x0f)
	} else if d.Body != nil {
		if e := f.stmt(d.Body); e != nil {
			return nil, e
		}
	}
	f.op(0x0b)
	localCount := int(f.next) - len(d.Params)
	var body bytes.Buffer
	if localCount == 0 {
		body.WriteByte(0)
	} else {
		body.WriteByte(1)
		body.Write(uleb(uint64(localCount)))
		body.WriteByte(0x7e)
	}
	body.Write(f.code.Bytes())
	return append(uleb(uint64(body.Len())), body.Bytes()...), nil
}
func (w *wasmCompiler) compileMain(stmts []Stmt) ([]byte, error) {
	f := &wasmFnCompiler{w: w, locals: map[string]uint32{}}
	for _, s := range stmts {
		if _, ok := s.(*FnDecl); ok {
			continue
		}
		if _, ok := s.(*ClassDecl); ok {
			continue
		}
		if _, ok := s.(*EnumDecl); ok {
			continue
		}
		if _, ok := s.(*TestDecl); ok {
			continue
		}
		if e := f.stmt(s); e != nil {
			return nil, e
		}
	}
	f.op(0x0b)
	localCount := int(f.next)
	var body bytes.Buffer
	if localCount == 0 {
		body.WriteByte(0)
	} else {
		body.WriteByte(1)
		body.Write(uleb(uint64(localCount)))
		body.WriteByte(0x7e)
	}
	body.Write(f.code.Bytes())
	return append(uleb(uint64(body.Len())), body.Bytes()...), nil
}
func buildWASM(input, output string) (string, error) {
	stmts, e := loadProgram(input)
	if e != nil {
		return "", e
	}
	c := NewChecker()
	if e = c.Check(stmts); e != nil {
		return "", e
	}
	w := &wasmCompiler{funcIndex: map[string]uint32{}, sigIndex: map[wasmFuncSig]uint32{}, nextData: 1024}
	printI := w.typeID(wasmFuncSig{params: 1})
	printT := w.typeID(wasmFuncSig{params: 2})
	_ = printI
	_ = printT
	for _, s := range stmts {
		if f, ok := s.(*FnDecl); ok {
			if !supportedWasmType(f.Return) {
				return "", fmt.Errorf("WASM scalar supports int/bool/unit return types")
			}
			for _, p := range f.Params {
				if p.Type.Name != "int" && p.Type.Name != "bool" {
					return "", fmt.Errorf("WASM scalar supports int/bool parameters")
				}
			}
			w.funcs = append(w.funcs, f)
		}
	}
	for j, f := range w.funcs {
		w.funcIndex[f.Name] = uint32(2 + j)
		ret := f.Return != nil && f.Return.Name != "unit"
		w.funcTypes = append(w.funcTypes, w.typeID(wasmFuncSig{params: len(f.Params), result: ret}))
	}
	mainType := w.typeID(wasmFuncSig{})
	w.funcTypes = append(w.funcTypes, mainType)
	codes := [][]byte{}
	for _, f := range w.funcs {
		b, e := w.compileFunc(f)
		if e != nil {
			return "", fmt.Errorf("%s: %w", f.Name, e)
		}
		codes = append(codes, b)
	}
	mainBody, e := w.compileMain(stmts)
	if e != nil {
		return "", e
	}
	codes = append(codes, mainBody)
	var mod bytes.Buffer
	mod.Write([]byte{0, 0x61, 0x73, 0x6d, 1, 0, 0, 0})
	types := [][]byte{}
	for _, s := range w.sigs {
		var b bytes.Buffer
		b.WriteByte(0x60)
		b.Write(uleb(uint64(s.params)))
		for j := 0; j < s.params; j++ {
			if s == w.sigs[1] && j < 2 {
				b.WriteByte(0x7f)
			} else {
				b.WriteByte(0x7e)
			}
		}
		if s.result {
			b.Write([]byte{1, 0x7e})
		} else {
			b.WriteByte(0)
		}
		types = append(types, b.Bytes())
	}
	mod.Write(wasmSection(1, wasmVec(types...)))
	imp1 := append(append(wasmName("saga"), wasmName("print_i64")...), 0)
	imp1 = append(imp1, uleb(uint64(printI))...)
	imp2 := append(append(wasmName("saga"), wasmName("print_text")...), 0)
	imp2 = append(imp2, uleb(uint64(printT))...)
	mod.Write(wasmSection(2, wasmVec(imp1, imp2)))
	funcs := make([][]byte, len(w.funcTypes))
	for j, t := range w.funcTypes {
		funcs[j] = uleb(uint64(t))
	}
	mod.Write(wasmSection(3, wasmVec(funcs...)))
	mod.Write(wasmSection(5, []byte{1, 0, 1}))
	memexp := append(wasmName("memory"), 0x02)
	memexp = append(memexp, 0)
	startExp := append(wasmName("_start"), 0x00)
	startExp = append(startExp, uleb(uint64(2+len(w.funcs)))...)
	mod.Write(wasmSection(7, wasmVec(memexp, startExp)))
	var code bytes.Buffer
	code.Write(uleb(uint64(len(codes))))
	for _, b := range codes {
		code.Write(b)
	}
	mod.Write(wasmSection(10, code.Bytes()))
	if len(w.data) > 0 {
		var ds bytes.Buffer
		ds.Write(uleb(uint64(len(w.data))))
		for _, d := range w.data {
			ds.WriteByte(0)
			ds.WriteByte(0x41)
			ds.Write(sleb(int64(d.offset)))
			ds.WriteByte(0x0b)
			bb := []byte(d.text)
			ds.Write(uleb(uint64(len(bb))))
			ds.Write(bb)
		}
		mod.Write(wasmSection(11, ds.Bytes()))
	}
	if output == "" {
		output = strings.TrimSuffix(input, filepath.Ext(input)) + ".wasm"
	}
	if e = os.WriteFile(output, mod.Bytes(), 0644); e != nil {
		return "", e
	}
	return output, nil
}

// buildEmbeddedWASM emits a freestanding WebAssembly library with no imports.
// It is the Edition 2027 Embedded Portable Profile: public scalar functions are
// exported directly and may be called by a firmware/RTOS/host-specific shim.
func buildEmbeddedWASM(input, output string) (string, error) {
	stmts, e := loadProgram(input)
	if e != nil {
		return "", e
	}
	c := NewChecker()
	if e = c.Check(stmts); e != nil {
		return "", e
	}
	w := &wasmCompiler{funcIndex: map[string]uint32{}, sigIndex: map[wasmFuncSig]uint32{}, noHost: true}
	for _, s := range stmts {
		switch q := s.(type) {
		case *FnDecl:
			if q.Async || q.ExternABI != "" {
				return "", fmt.Errorf("embedded WASM does not support async/extern functions")
			}
			if !supportedWasmType(q.Return) {
				return "", fmt.Errorf("embedded WASM supports int/bool/unit return types")
			}
			for _, p := range q.Params {
				if p.Type.Name != "int" && p.Type.Name != "bool" {
					return "", fmt.Errorf("embedded WASM supports int/bool parameters")
				}
			}
			w.funcs = append(w.funcs, q)
		case *EditionDecl, *ModuleDecl:
			// metadata only
		default:
			return "", fmt.Errorf("embedded WASM requires library-style source with function declarations only; got %T", s)
		}
	}
	if len(w.funcs) == 0 {
		return "", fmt.Errorf("embedded WASM requires at least one function")
	}
	for j, f := range w.funcs {
		w.funcIndex[f.Name] = uint32(j)
		ret := f.Return != nil && f.Return.Name != "unit"
		w.funcTypes = append(w.funcTypes, w.typeID(wasmFuncSig{params: len(f.Params), result: ret}))
	}
	codes := make([][]byte, 0, len(w.funcs))
	for _, f := range w.funcs {
		b, e := w.compileFunc(f)
		if e != nil {
			return "", fmt.Errorf("%s: %w", f.Name, e)
		}
		codes = append(codes, b)
	}
	var mod bytes.Buffer
	mod.Write([]byte{0, 0x61, 0x73, 0x6d, 1, 0, 0, 0})
	types := [][]byte{}
	for _, sig := range w.sigs {
		var b bytes.Buffer
		b.WriteByte(0x60)
		b.Write(uleb(uint64(sig.params)))
		for j := 0; j < sig.params; j++ {
			b.WriteByte(0x7e)
		}
		if sig.result {
			b.Write([]byte{1, 0x7e})
		} else {
			b.WriteByte(0)
		}
		types = append(types, b.Bytes())
	}
	mod.Write(wasmSection(1, wasmVec(types...)))
	funcs := make([][]byte, len(w.funcTypes))
	for j, t := range w.funcTypes {
		funcs[j] = uleb(uint64(t))
	}
	mod.Write(wasmSection(3, wasmVec(funcs...)))
	exports := [][]byte{}
	for j, f := range w.funcs {
		if f.Visibility == "public" {
			x := append(wasmName(f.Name), 0x00)
			x = append(x, uleb(uint64(j))...)
			exports = append(exports, x)
		}
	}
	if len(exports) == 0 {
		return "", fmt.Errorf("embedded WASM requires at least one public function export")
	}
	mod.Write(wasmSection(7, wasmVec(exports...)))
	var code bytes.Buffer
	code.Write(uleb(uint64(len(codes))))
	for _, b := range codes {
		code.Write(b)
	}
	mod.Write(wasmSection(10, code.Bytes()))
	if output == "" {
		output = strings.TrimSuffix(input, filepath.Ext(input)) + ".embedded.wasm"
	}
	if e = os.WriteFile(output, mod.Bytes(), 0644); e != nil {
		return "", e
	}
	return output, nil
}
