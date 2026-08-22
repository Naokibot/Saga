package main

import (
	"bytes"
	"fmt"
	"math"
	"math/big"
	"sort"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
)

type Value any

type Number struct {
	R    *big.Rat
	Kind string
}

// FloatValue is deliberately separate from Number. Number is exact; FloatValue
// follows IEEE-754 semantics and therefore requires explicit conversions at
// exact/float boundaries.
type FloatValue struct {
	V    float64
	Bits int // 32 or 64
}

func newFloatValue(text string, bits int) (FloatValue, error) {
	text = strings.ReplaceAll(text, "_", "")
	text = strings.TrimSuffix(text, fmt.Sprintf("f%d", bits))
	v, err := strconv.ParseFloat(text, bits)
	if err != nil {
		return FloatValue{}, err
	}
	if bits == 32 {
		v = float64(float32(v))
	}
	return FloatValue{V: v, Bits: bits}, nil
}

func (f FloatValue) String() string {
	if math.IsNaN(f.V) {
		return "NaN"
	}
	if math.IsInf(f.V, 1) {
		return "Infinity"
	}
	if math.IsInf(f.V, -1) {
		return "-Infinity"
	}
	return strconv.FormatFloat(f.V, 'g', -1, f.Bits)
}

func newNumber(text, kind string) (Number, error) {
	text = strings.ReplaceAll(text, "_", "")
	r := new(big.Rat)
	if _, ok := r.SetString(text); !ok {
		return Number{}, fmt.Errorf("invalid number %s", text)
	}
	return Number{R: r, Kind: kind}, nil
}
func numberFromInt64(n int64) Number     { return Number{R: new(big.Rat).SetInt64(n), Kind: "int"} }
func numberFromBigInt(n *big.Int) Number { return Number{R: new(big.Rat).SetInt(n), Kind: "int"} }
func (n Number) clone() Number           { return Number{R: new(big.Rat).Set(n.R), Kind: n.Kind} }
func (n Number) isInt() bool             { return n.R.IsInt() }
func (n Number) Int() (*big.Int, bool) {
	if !n.R.IsInt() {
		return nil, false
	}
	return new(big.Int).Set(n.R.Num()), true
}
func (n Number) String() string {
	switch n.Kind {
	case "decimal":
		places := decimalPlaces(n.R)
		if places < 1 {
			places = 1
		}
		s := n.R.FloatString(places)
		s = strings.TrimRight(strings.TrimRight(s, "0"), ".")
		if s == "" || s == "-0" {
			return "0"
		}
		return s
	default:
		if n.R.IsInt() {
			return n.R.Num().String()
		}
		return n.R.RatString()
	}
}
func decimalPlaces(r *big.Rat) int {
	d := new(big.Int).Abs(new(big.Int).Set(r.Denom()))
	two, five := 0, 0
	z := big.NewInt(0)
	twoI, fiveI := big.NewInt(2), big.NewInt(5)
	tmp := new(big.Int)
	for d.Cmp(big.NewInt(1)) > 0 {
		tmp.Mod(d, twoI)
		if tmp.Cmp(z) != 0 {
			break
		}
		d.Div(d, twoI)
		two++
	}
	for d.Cmp(big.NewInt(1)) > 0 {
		tmp.Mod(d, fiveI)
		if tmp.Cmp(z) != 0 {
			break
		}
		d.Div(d, fiveI)
		five++
	}
	if d.Cmp(big.NewInt(1)) == 0 {
		if two > five {
			return two
		}
		return five
	}
	return 50
}

type OptionValue struct {
	Present bool
	Value   Value
}
type ResultValue struct {
	OK    bool
	Value Value
}
type RangeValue struct{ Start, End *big.Int }
type ErrorValue struct{ Kind, Message string }
type EnumType struct {
	Name     string
	Variants map[string]int
}
type EnumConstructor struct {
	Enum    string
	Variant string
	Arity   int
}
type EnumValue struct {
	Enum    string
	Variant string
	Payload []Value
}

type MapEntry struct{ Key, Value Value }
type MapValue struct{ Entries []MapEntry }
type SetValue struct{ Items []Value }

type Cell struct {
	V       Value
	Mutable bool
	Moved   bool
}
type Env struct {
	Parent *Env
	Values map[string]*Cell
}

func newEnv(parent *Env) *Env { return &Env{Parent: parent, Values: map[string]*Cell{}} }
func (e *Env) define(name string, v Value, mutable bool) {
	e.Values[name] = &Cell{V: v, Mutable: mutable}
}
func (e *Env) getCell(name string) (*Cell, bool) {
	if c, ok := e.Values[name]; ok {
		return c, true
	}
	if e.Parent != nil {
		return e.Parent.getCell(name)
	}
	return nil, false
}
func (e *Env) get(name string) (Value, error) {
	if c, ok := e.getCell(name); ok {
		if c.Moved {
			return nil, &SagaError{Code: "SAGA-R001", ID: "SAGA-R181", Message: "use after move: " + name}
		}
		return c.V, nil
	}
	return nil, &SagaError{Code: "SAGA-R001", ID: "SAGA-R110", Message: "unknown name: " + name}
}
func (e *Env) move(name string) (Value, error) {
	c, ok := e.getCell(name)
	if !ok {
		return nil, &SagaError{Code: "SAGA-R001", ID: "SAGA-R110", Message: "unknown name: " + name}
	}
	if c.Moved {
		return nil, &SagaError{Code: "SAGA-R001", ID: "SAGA-R181", Message: "value already moved: " + name}
	}
	c.Moved = true
	return c.V, nil
}
func (e *Env) set(name string, v Value) error {
	c, ok := e.getCell(name)
	if !ok {
		return &SagaError{Code: "SAGA-R001", ID: "SAGA-R110", Message: "unknown name: " + name}
	}
	if !c.Mutable {
		return &SagaError{Code: "SAGA-R001", ID: "SAGA-R111", Message: "cannot assign to immutable binding: " + name}
	}
	c.V = v
	c.Moved = false
	return nil
}

type Function struct {
	Decl    *FnDecl
	Closure *Env
	Owner   string
}
type NativeFunc struct {
	Name string
	Call func(*Interpreter, []Value) (Value, error)
}
type ClosureValue struct {
	Expr *ClosureExpr
	Env  *Env
}
type ExtensionMethod struct {
	Receiver Value
	Name     string
}
type CoreModule struct{ Name string }
type BoundMethod struct {
	Receiver *Instance
	Function *Function
}
type Class struct {
	Info    *ClassInfo
	Decl    *ClassDecl
	Methods map[string]*Function
}
type Instance struct {
	Class  *Class
	Fields map[string]Value
}

type FutureValue struct {
	done      chan struct{}
	mu        sync.Mutex
	result    taskResult
	cancelled atomic.Bool
}
type taskResult struct {
	value Value
	err   error
}

func newFuture(run func() (Value, error)) *FutureValue {
	f := &FutureValue{done: make(chan struct{})}
	go func() {
		v, e := run()
		f.mu.Lock()
		f.result = taskResult{v, e}
		f.mu.Unlock()
		close(f.done)
	}()
	return f
}
func (f *FutureValue) await() (Value, error) {
	<-f.done
	if f.cancelled.Load() {
		return nil, &SagaError{Code: "SAGA-R001", ID: "SAGA-R182", Message: "task was cancelled"}
	}
	f.mu.Lock()
	defer f.mu.Unlock()
	return f.result.value, f.result.err
}

type ChannelValue struct {
	Ch     chan Value
	closed atomic.Bool
}

type ActorRequest struct {
	Value Value
	Reply *FutureValue
}
type ActorValue struct {
	Inbox  chan actorEnvelope
	closed atomic.Bool
}
type actorEnvelope struct {
	Value Value
	Done  chan taskResult
}

type TaskGroupValue struct {
	mu      sync.Mutex
	Futures []*FutureValue
}

type TaskPoolValue struct {
	sem    chan struct{}
	closed atomic.Bool
	wg     sync.WaitGroup
}

func newTaskPoolValue(workers int) *TaskPoolValue {
	return &TaskPoolValue{sem: make(chan struct{}, workers)}
}

func (p *TaskPoolValue) submit(run func() (Value, error)) (*FutureValue, error) {
	if p.closed.Load() {
		return nil, &SagaError{Code: "SAGA-R001", ID: "SAGA-R188", Message: "task pool is closed"}
	}
	p.wg.Add(1)
	return newFuture(func() (Value, error) {
		defer p.wg.Done()
		p.sem <- struct{}{}
		defer func() { <-p.sem }()
		return run()
	}), nil
}

func (p *TaskPoolValue) close() {
	p.closed.Store(true)
	p.wg.Wait()
}

type SourceModuleValue struct {
	Name    string
	Exports map[string]Value
}

func isHashable(v Value) bool {
	switch x := v.(type) {
	case Number, FloatValue, bool, string, []byte, OptionValue, EnumValue:
		return true
	case *Instance:
		if x == nil || x.Class == nil || !classDerives(x.Class.Info, "Hash") {
			return false
		}
		for _, n := range x.Class.Info.FieldOrder {
			if !isHashable(x.Fields[n]) {
				return false
			}
		}
		return true
	default:
		return false
	}
}
func equalValues(a, b Value, seen map[[2]*Instance]bool) bool {
	switch x := a.(type) {
	case Number:
		y, ok := b.(Number)
		return ok && x.R.Cmp(y.R) == 0
	case FloatValue:
		y, ok := b.(FloatValue)
		return ok && x.Bits == y.Bits && x.V == y.V
	case bool:
		y, ok := b.(bool)
		return ok && x == y
	case string:
		y, ok := b.(string)
		return ok && x == y
	case []byte:
		y, ok := b.([]byte)
		return ok && bytes.Equal(x, y)
	case OptionValue:
		y, ok := b.(OptionValue)
		return ok && x.Present == y.Present && (!x.Present || equalValues(x.Value, y.Value, seen))
	case ResultValue:
		y, ok := b.(ResultValue)
		return ok && x.OK == y.OK && equalValues(x.Value, y.Value, seen)
	case EnumValue:
		y, ok := b.(EnumValue)
		if !ok || x.Enum != y.Enum || x.Variant != y.Variant || len(x.Payload) != len(y.Payload) {
			return false
		}
		for idx := range x.Payload {
			if !equalValues(x.Payload[idx], y.Payload[idx], seen) {
				return false
			}
		}
		return true
	case []Value:
		y, ok := b.([]Value)
		if !ok || len(x) != len(y) {
			return false
		}
		for i := range x {
			if !equalValues(x[i], y[i], seen) {
				return false
			}
		}
		return true
	case MapValue:
		y, ok := b.(MapValue)
		if !ok || len(x.Entries) != len(y.Entries) {
			return false
		}
		for _, e := range x.Entries {
			v, ok := mapLookup(y, e.Key)
			if !ok || !equalValues(e.Value, v, seen) {
				return false
			}
		}
		return true
	case SetValue:
		y, ok := b.(SetValue)
		if !ok || len(x.Items) != len(y.Items) {
			return false
		}
		for _, e := range x.Items {
			if !setHas(y, e) {
				return false
			}
		}
		return true
	case *Instance:
		y, ok := b.(*Instance)
		if !ok {
			return false
		}
		if x == y {
			return true
		}
		if x.Class == nil || y.Class == nil || x.Class.Info == nil || y.Class.Info == nil || x.Class.Info.Name != y.Class.Info.Name {
			return false
		}
		if !(x.Class.Info.Record && y.Class.Info.Record) && !(classDerives(x.Class.Info, "Equal") && classDerives(y.Class.Info, "Equal")) {
			return false
		}
		if seen == nil {
			seen = map[[2]*Instance]bool{}
		}
		pair := [2]*Instance{x, y}
		if seen[pair] {
			return true
		}
		seen[pair] = true
		for _, n := range x.Class.Info.FieldOrder {
			if !equalValues(x.Fields[n], y.Fields[n], seen) {
				return false
			}
		}
		return true
	case nil:
		return b == nil
	default:
		return fmt.Sprintf("%T:%v", a, a) == fmt.Sprintf("%T:%v", b, b)
	}
}
func mapLookup(m MapValue, key Value) (Value, bool) {
	for _, e := range m.Entries {
		if equalValues(e.Key, key, nil) {
			return e.Value, true
		}
	}
	return nil, false
}
func mapPut(m MapValue, key, val Value) MapValue {
	out := MapValue{Entries: append([]MapEntry{}, m.Entries...)}
	for i, e := range out.Entries {
		if equalValues(e.Key, key, nil) {
			out.Entries[i].Value = val
			return out
		}
	}
	out.Entries = append(out.Entries, MapEntry{key, val})
	return out
}
func mapRemove(m MapValue, key Value) MapValue {
	out := MapValue{}
	for _, e := range m.Entries {
		if !equalValues(e.Key, key, nil) {
			out.Entries = append(out.Entries, e)
		}
	}
	return out
}
func setHas(s SetValue, v Value) bool {
	for _, x := range s.Items {
		if equalValues(x, v, nil) {
			return true
		}
	}
	return false
}
func setAddVal(s SetValue, v Value) SetValue {
	if setHas(s, v) {
		return s
	}
	return SetValue{Items: append(append([]Value{}, s.Items...), v)}
}
func setRemoveVal(s SetValue, v Value) SetValue {
	out := SetValue{}
	for _, x := range s.Items {
		if !equalValues(x, v, nil) {
			out.Items = append(out.Items, x)
		}
	}
	return out
}

func formatValue(v Value, private bool) string {
	switch x := v.(type) {
	case nil:
		return "unit"
	case Number:
		return x.String()
	case FloatValue:
		return x.String()
	case bool:
		if x {
			return "true"
		}
		return "false"
	case string:
		return x
	case []byte:
		return fmt.Sprintf("bytes(%d)", len(x))
	case []Value:
		parts := make([]string, len(x))
		for i, v := range x {
			parts[i] = formatValue(v, false)
		}
		return "[" + strings.Join(parts, ", ") + "]"
	case MapValue:
		parts := []string{}
		for _, e := range x.Entries {
			parts = append(parts, formatValue(e.Key, false)+": "+formatValue(e.Value, false))
		}
		return "{" + strings.Join(parts, ", ") + "}"
	case SetValue:
		parts := []string{}
		for _, v := range x.Items {
			parts = append(parts, formatValue(v, false))
		}
		sort.Strings(parts)
		return "set{" + strings.Join(parts, ", ") + "}"
	case OptionValue:
		if !x.Present {
			return "none"
		}
		return "some(" + formatValue(x.Value, false) + ")"
	case ResultValue:
		if x.OK {
			return "ok(" + formatValue(x.Value, false) + ")"
		}
		return "err(" + formatValue(x.Value, false) + ")"
	case EnumType:
		return "<enum " + x.Name + ">"
	case EnumValue:
		if len(x.Payload) == 0 {
			return x.Enum + "." + x.Variant
		}
		parts := []string{}
		for _, v := range x.Payload {
			parts = append(parts, formatValue(v, false))
		}
		return x.Enum + "." + x.Variant + "(" + strings.Join(parts, ", ") + ")"
	case ErrorValue:
		return x.Message
	case *Instance:
		parts := []string{}
		debugDerived := x.Class != nil && classDerives(x.Class.Info, "Debug")
		for _, n := range x.Class.Info.FieldOrder {
			f := x.Class.Info.Fields[n]
			if f.Private && !private && !debugDerived {
				continue
			}
			parts = append(parts, n+"="+formatValue(x.Fields[n], debugDerived))
		}
		return x.Class.Info.Name + "(" + strings.Join(parts, ", ") + ")"
	case *Class:
		return "<class " + x.Info.Name + ">"
	case *Function:
		return "<fn " + x.Decl.Name + ">"
	case *NativeFunc:
		return "<builtin " + x.Name + ">"
	case *FutureValue:
		return "<future>"
	case *ChannelValue:
		return "<channel>"
	case *ActorValue:
		return "<actor>"
	case SourceModuleValue:
		return "<module " + x.Name + ">"
	case CoreModule:
		return "<module " + x.Name + ">"
	case *GameCanvas:
		return fmt.Sprintf("<game-canvas %dx%d>", x.W, x.H)
	default:
		return fmt.Sprint(x)
	}
}
