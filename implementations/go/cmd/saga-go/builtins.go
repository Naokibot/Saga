package main

import (
	"fmt"
	"math"
	"math/big"
	"os"
	"runtime"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"
)

func (i *Interpreter) callBuiltin(name string, args []Value) (Value, error) {
	if err := checkRuntimeArity(name, len(args)); err != nil {
		return nil, err
	}
	n := func(v Value) (Number, error) {
		q, ok := v.(Number)
		if !ok {
			return Number{}, fmt.Errorf("number required")
		}
		return q, nil
	}
	intIndex := func(v Value) (int, error) {
		q, e := n(v)
		if e != nil {
			return 0, e
		}
		x, ok := q.Int()
		if !ok || !x.IsInt64() {
			return 0, fmt.Errorf("int required")
		}
		return int(x.Int64()), nil
	}
	switch name {
	case "ok":
		return ResultValue{OK: true, Value: args[0]}, nil
	case "err":
		return ResultValue{OK: false, Value: args[0]}, nil
	case "is_ok":
		q, ok := args[0].(ResultValue)
		return ok && q.OK, nil
	case "is_err":
		q, ok := args[0].(ResultValue)
		return ok && !q.OK, nil
	case "unwrap_ok":
		q, ok := args[0].(ResultValue)
		if !ok {
			return nil, fmt.Errorf("result required")
		}
		if !q.OK {
			return nil, &SagaError{Code: "SAGA-R001", ID: "SAGA-R141", Message: "cannot unwrap err as ok"}
		}
		return q.Value, nil
	case "unwrap_err":
		q, ok := args[0].(ResultValue)
		if !ok {
			return nil, fmt.Errorf("result required")
		}
		if q.OK {
			return nil, &SagaError{Code: "SAGA-R001", ID: "SAGA-R142", Message: "cannot unwrap ok as err"}
		}
		return q.Value, nil
	case "unwrap_result_or":
		q, ok := args[0].(ResultValue)
		if !ok {
			return nil, fmt.Errorf("result required")
		}
		if q.OK {
			return q.Value, nil
		}
		return args[1], nil
	case "some":
		return OptionValue{Present: true, Value: args[0]}, nil
	case "none":
		return OptionValue{}, nil
	case "is_some":
		q, ok := args[0].(OptionValue)
		return ok && q.Present, nil
	case "is_none":
		q, ok := args[0].(OptionValue)
		return ok && !q.Present, nil
	case "unwrap":
		q, ok := args[0].(OptionValue)
		if !ok {
			return nil, fmt.Errorf("option required")
		}
		if !q.Present {
			return nil, &SagaError{Code: "SAGA-R001", ID: "SAGA-R104", Message: "cannot unwrap none"}
		}
		return q.Value, nil
	case "unwrap_or":
		q, ok := args[0].(OptionValue)
		if !ok {
			return nil, fmt.Errorf("option required")
		}
		if q.Present {
			return q.Value, nil
		}
		return args[1], nil
	case "print":
		parts := make([]string, len(args))
		for j, v := range args {
			parts[j] = formatValue(v, false)
		}
		i.emit(strings.Join(parts, " "))
		return nil, nil
	case "len":
		switch q := args[0].(type) {
		case string:
			return numberFromInt64(int64(len([]rune(q)))), nil
		case []byte:
			return numberFromInt64(int64(len(q))), nil
		case []Value:
			return numberFromInt64(int64(len(q))), nil
		case MapValue:
			return numberFromInt64(int64(len(q.Entries))), nil
		case SetValue:
			return numberFromInt64(int64(len(q.Items))), nil
		}
		return nil, fmt.Errorf("len unsupported")
	case "text":
		return formatValue(args[0], false), nil
	case "int", "int8", "int16", "int32", "int64", "uint8", "uint16", "uint32", "uint64":
		var x *big.Int
		switch q := args[0].(type) {
		case Number:
			var ok bool
			x, ok = q.Int()
			if !ok {
				return nil, fmt.Errorf("fractional value cannot convert to %s", name)
			}
		case string:
			x = new(big.Int)
			if _, ok := x.SetString(strings.TrimSpace(q), 10); !ok {
				return nil, fmt.Errorf("invalid %s text", name)
			}
		case FloatValue:
			if math.IsNaN(q.V) || math.IsInf(q.V, 0) {
				return nil, fmt.Errorf("non-finite float cannot convert to %s", name)
			}
			x = big.NewInt(int64(q.V))
		default:
			return nil, fmt.Errorf("%s conversion unsupported", name)
		}
		bits := map[string]int{"int8": 8, "int16": 16, "int32": 32, "int64": 64, "uint8": 8, "uint16": 16, "uint32": 32, "uint64": 64}[name]
		if bits > 0 {
			unsigned := strings.HasPrefix(name, "uint")
			if unsigned {
				if x.Sign() < 0 || x.BitLen() > bits {
					return nil, fmt.Errorf("value out of range for %s", name)
				}
			} else {
				min := new(big.Int).Neg(new(big.Int).Lsh(big.NewInt(1), uint(bits-1)))
				max := new(big.Int).Sub(new(big.Int).Lsh(big.NewInt(1), uint(bits-1)), big.NewInt(1))
				if x.Cmp(min) < 0 || x.Cmp(max) > 0 {
					return nil, fmt.Errorf("value out of range for %s", name)
				}
			}
		}
		q := numberFromBigInt(x)
		q.Kind = name
		return q, nil
	case "decimal":
		if q, ok := args[0].(FloatValue); ok {
			if math.IsNaN(q.V) || math.IsInf(q.V, 0) {
				return nil, fmt.Errorf("non-finite float cannot convert to exact decimal")
			}
			n, e := newNumber(strconv.FormatFloat(q.V, 'g', -1, q.Bits), "decimal")
			if e != nil {
				return nil, e
			}
			return n, nil
		}
		q, e := n(args[0])
		if e != nil {
			return nil, e
		}
		q.Kind = "decimal"
		return q, nil
	case "float32", "float64":
		bits := 64
		if name == "float32" {
			bits = 32
		}
		var f float64
		switch q := args[0].(type) {
		case FloatValue:
			f = q.V
		case Number:
			f, _ = q.R.Float64()
		case string:
			v, e := strconv.ParseFloat(strings.TrimSpace(q), bits)
			if e != nil {
				return nil, fmt.Errorf("invalid float text")
			}
			f = v
		default:
			return nil, fmt.Errorf("float conversion unsupported")
		}
		if bits == 32 {
			f = float64(float32(f))
		}
		return FloatValue{V: f, Bits: bits}, nil
	case "ratio":
		a, e := n(args[0])
		if e != nil {
			return nil, e
		}
		b, e := n(args[1])
		if e != nil {
			return nil, e
		}
		ai, aok := a.Int()
		bi, bok := b.Int()
		if !aok || !bok || bi.Sign() == 0 {
			return nil, fmt.Errorf("ratio requires integer numerator and nonzero denominator")
		}
		return Number{R: new(big.Rat).SetFrac(ai, bi), Kind: "rational"}, nil
	case "abs":
		if f, ok := args[0].(FloatValue); ok {
			f.V = math.Abs(f.V)
			return f, nil
		}
		q, e := n(args[0])
		if e != nil {
			return nil, e
		}
		return Number{R: new(big.Rat).Abs(q.R), Kind: q.Kind}, nil
	case "sqrt":
		if f, ok := args[0].(FloatValue); ok {
			if f.V < 0 {
				return nil, fmt.Errorf("sqrt of negative number")
			}
			f.V = math.Sqrt(f.V)
			if f.Bits == 32 {
				f.V = float64(float32(f.V))
			}
			return f, nil
		}
		q, e := n(args[0])
		if e != nil {
			return nil, e
		}
		if q.R.Sign() < 0 {
			return nil, fmt.Errorf("sqrt of negative number")
		}
		prec := uint(i.Precision*4 + 64)
		bf := new(big.Float).SetPrec(prec).SetRat(q.R)
		root := new(big.Float).SetPrec(prec).Sqrt(bf)
		s := root.Text('f', i.Precision)
		r := new(big.Rat)
		r.SetString(s)
		return Number{R: r, Kind: "decimal"}, nil
	case "round":
		q, e := n(args[0])
		if e != nil {
			return nil, e
		}
		digits, e := intIndex(args[1])
		if e != nil {
			return nil, e
		}
		return roundNumber(q, digits), nil
	case "floor", "ceil":
		q, e := n(args[0])
		if e != nil {
			return nil, e
		}
		num, den := q.R.Num(), q.R.Denom()
		z := new(big.Int).Quo(num, den)
		rem := new(big.Int).Rem(num, den)
		if rem.Sign() != 0 {
			if name == "floor" && num.Sign() < 0 {
				z.Sub(z, big.NewInt(1))
			}
			if name == "ceil" && num.Sign() > 0 {
				z.Add(z, big.NewInt(1))
			}
		}
		return numberFromBigInt(z), nil
	case "min", "max":
		a, _ := n(args[0])
		b, _ := n(args[1])
		cmp := a.R.Cmp(b.R)
		if (name == "min" && cmp <= 0) || (name == "max" && cmp >= 0) {
			return promoteNumber(a, b), nil
		}
		return promoteNumber(b, a), nil
	case "sum", "mean":
		vals, ok := args[0].([]Value)
		if !ok || len(vals) == 0 {
			return nil, fmt.Errorf("non-empty numeric list required")
		}
		total := numberFromInt64(0)
		kind := "int"
		for _, v := range vals {
			q, e := n(v)
			if e != nil {
				return nil, e
			}
			if q.Kind == "decimal" {
				kind = "decimal"
			} else if q.Kind == "rational" && kind == "int" {
				kind = "rational"
			}
			total.R.Add(total.R, q.R)
		}
		total.Kind = kind
		if name == "sum" {
			return total, nil
		}
		den := new(big.Rat).SetInt64(int64(len(vals)))
		total.R.Quo(total.R, den)
		if kind != "decimal" {
			total.Kind = "rational"
		}
		return total, nil
	case "append", "prepend":
		vals := append([]Value{}, args[0].([]Value)...)
		if name == "append" {
			vals = append(vals, args[1])
		} else {
			vals = append([]Value{args[1]}, vals...)
		}
		return vals, nil
	case "repeat":
		cnt, e := intIndex(args[1])
		if e != nil || cnt < 0 {
			return nil, fmt.Errorf("repeat count must be non-negative int")
		}
		out := make([]Value, cnt)
		for j := range out {
			out[j] = cloneValue(args[0])
		}
		return out, nil
	case "set_at":
		vals := append([]Value{}, args[0].([]Value)...)
		idx, e := intIndex(args[1])
		if e != nil || idx < 0 || idx >= len(vals) {
			return nil, &SagaError{Code: "SAGA-R001", ID: "SAGA-R101", Message: "index out of range"}
		}
		vals[idx] = args[2]
		return vals, nil
	case "get":
		vals := args[0].([]Value)
		idx, e := intIndex(args[1])
		if e != nil || idx < 0 || idx >= len(vals) {
			return args[2], nil
		}
		return vals[idx], nil
	case "contains":
		switch q := args[0].(type) {
		case []Value:
			for _, v := range q {
				if equalValues(v, args[1], nil) {
					return true, nil
				}
			}
			return false, nil
		case string:
			s, ok := args[1].(string)
			return ok && strings.Contains(q, s), nil
		case SetValue:
			return setHas(q, args[1]), nil
		case MapValue:
			_, ok := mapLookup(q, args[1])
			return ok, nil
		}
		return false, nil
	case "assert":
		b, ok := args[0].(bool)
		if !ok || !b {
			msg := "assertion failed"
			if len(args) == 2 {
				msg = formatValue(args[1], false)
			}
			return nil, &SagaError{Code: "SAGA-R001", ID: "SAGA-R105", Message: msg}
		}
		return nil, nil
	case "precision":
		d, e := intIndex(args[0])
		if e != nil || d < 1 {
			return nil, fmt.Errorf("precision must be >= 1")
		}
		i.Precision = d
		return nil, nil
	case "slice":
		vals := args[0].([]Value)
		a, _ := intIndex(args[1])
		b, _ := intIndex(args[2])
		if a < 0 {
			a = 0
		}
		if b > len(vals) {
			b = len(vals)
		}
		if a > b {
			a = b
		}
		return append([]Value{}, vals[a:b]...), nil
	case "reverse":
		vals := append([]Value{}, args[0].([]Value)...)
		for a, b := 0, len(vals)-1; a < b; a, b = a+1, b-1 {
			vals[a], vals[b] = vals[b], vals[a]
		}
		return vals, nil
	case "sort":
		return sortValues(args[0].([]Value))
	case "unique":
		out := []Value{}
		for _, v := range args[0].([]Value) {
			found := false
			for _, x := range out {
				if equalValues(v, x, nil) {
					found = true
					break
				}
			}
			if !found {
				out = append(out, v)
			}
		}
		return out, nil
	case "transform":
		vals := args[1].([]Value)
		out := make([]Value, 0, len(vals))
		for _, v := range vals {
			x, e := i.invoke(args[0], []Value{v}, Token{})
			if e != nil {
				return nil, e
			}
			out = append(out, x)
		}
		return out, nil
	case "filter":
		vals := args[1].([]Value)
		out := []Value{}
		for _, v := range vals {
			x, e := i.invoke(args[0], []Value{v}, Token{})
			if e != nil {
				return nil, e
			}
			b, ok := x.(bool)
			if !ok {
				return nil, fmt.Errorf("filter predicate must return bool")
			}
			if b {
				out = append(out, v)
			}
		}
		return out, nil
	case "reduce":
		acc := args[2]
		for _, v := range args[1].([]Value) {
			x, e := i.invoke(args[0], []Value{acc, v}, Token{})
			if e != nil {
				return nil, e
			}
			acc = x
		}
		return acc, nil
	case "find":
		for _, v := range args[1].([]Value) {
			x, e := i.invoke(args[0], []Value{v}, Token{})
			if e != nil {
				return nil, e
			}
			b, ok := x.(bool)
			if !ok {
				return nil, fmt.Errorf("find predicate must return bool")
			}
			if b {
				return v, nil
			}
		}
		return args[2], nil
	case "any", "all":
		for _, v := range args[1].([]Value) {
			x, e := i.invoke(args[0], []Value{v}, Token{})
			if e != nil {
				return nil, e
			}
			b, ok := x.(bool)
			if !ok {
				return nil, fmt.Errorf("predicate must return bool")
			}
			if name == "any" && b {
				return true, nil
			}
			if name == "all" && !b {
				return false, nil
			}
		}
		return name == "all", nil
	case "split":
		return stringsToValues(strings.Split(args[0].(string), args[1].(string))), nil
	case "join":
		vals := args[0].([]Value)
		parts := make([]string, len(vals))
		for j, v := range vals {
			parts[j] = v.(string)
		}
		return strings.Join(parts, args[1].(string)), nil
	case "trim":
		return strings.TrimSpace(args[0].(string)), nil
	case "upper":
		return strings.ToUpper(args[0].(string)), nil
	case "lower":
		return strings.ToLower(args[0].(string)), nil
	case "replace":
		return strings.ReplaceAll(args[0].(string), args[1].(string), args[2].(string)), nil
	case "starts_with":
		return strings.HasPrefix(args[0].(string), args[1].(string)), nil
	case "ends_with":
		return strings.HasSuffix(args[0].(string), args[1].(string)), nil
	case "find_text":
		return numberFromInt64(int64(strings.Index(args[0].(string), args[1].(string)))), nil
	case "substring":
		r := []rune(args[0].(string))
		a, _ := intIndex(args[1])
		b, _ := intIndex(args[2])
		if a < 0 {
			a = 0
		}
		if b > len(r) {
			b = len(r)
		}
		if a > b {
			a = b
		}
		return string(r[a:b]), nil
	case "map_of":
		m := MapValue{}
		for j := 0; j < len(args); j += 2 {
			if !isHashable(args[j]) {
				return nil, fmt.Errorf("map key must be hashable")
			}
			m = mapPut(m, args[j], args[j+1])
		}
		return m, nil
	case "map_get":
		m := args[0].(MapValue)
		if v, ok := mapLookup(m, args[1]); ok {
			return v, nil
		}
		return args[2], nil
	case "map_put":
		m := args[0].(MapValue)
		if !isHashable(args[1]) {
			return nil, fmt.Errorf("map key must be hashable")
		}
		return mapPut(m, args[1], args[2]), nil
	case "map_remove":
		return mapRemove(args[0].(MapValue), args[1]), nil
	case "map_keys":
		m := args[0].(MapValue)
		out := []Value{}
		for _, e := range m.Entries {
			out = append(out, e.Key)
		}
		return out, nil
	case "map_values":
		m := args[0].(MapValue)
		out := []Value{}
		for _, e := range m.Entries {
			out = append(out, e.Value)
		}
		return out, nil
	case "map_contains":
		_, ok := mapLookup(args[0].(MapValue), args[1])
		return ok, nil
	case "set_of":
		s := SetValue{}
		for _, v := range args {
			if !isHashable(v) {
				return nil, fmt.Errorf("set value must be hashable")
			}
			s = setAddVal(s, v)
		}
		return s, nil
	case "set_add":
		if !isHashable(args[1]) {
			return nil, fmt.Errorf("set value must be hashable")
		}
		return setAddVal(args[0].(SetValue), args[1]), nil
	case "set_remove":
		return setRemoveVal(args[0].(SetValue), args[1]), nil
	case "set_contains":
		return setHas(args[0].(SetValue), args[1]), nil
	case "set_union":
		a, b := args[0].(SetValue), args[1].(SetValue)
		out := SetValue{Items: append([]Value{}, a.Items...)}
		for _, v := range b.Items {
			out = setAddVal(out, v)
		}
		return out, nil
	case "set_intersection":
		a, b := args[0].(SetValue), args[1].(SetValue)
		out := SetValue{}
		for _, v := range a.Items {
			if setHas(b, v) {
				out = setAddVal(out, v)
			}
		}
		return out, nil
	}
	return nil, fmt.Errorf("unknown builtin: %s", name)
}

func checkRuntimeArity(name string, n int) error {
	fixed := map[string]int{"len": 1, "text": 1, "int": 1, "int8": 1, "int16": 1, "int32": 1, "int64": 1, "uint8": 1, "uint16": 1, "uint32": 1, "uint64": 1, "decimal": 1, "float32": 1, "float64": 1, "ratio": 2, "abs": 1, "sqrt": 1, "round": 2, "min": 2, "max": 2, "sum": 1, "mean": 1, "append": 2, "prepend": 2, "get": 3, "contains": 2, "precision": 1, "floor": 1, "ceil": 1, "slice": 3, "reverse": 1, "sort": 1, "unique": 1, "transform": 2, "filter": 2, "reduce": 3, "find": 3, "any": 2, "all": 2, "split": 2, "join": 2, "trim": 1, "upper": 1, "lower": 1, "replace": 3, "starts_with": 2, "ends_with": 2, "find_text": 2, "substring": 3, "map_get": 3, "map_put": 3, "map_remove": 2, "map_keys": 1, "map_values": 1, "map_contains": 2, "set_add": 2, "set_remove": 2, "set_contains": 2, "set_union": 2, "set_intersection": 2, "repeat": 2, "set_at": 3, "some": 1, "none": 0, "is_some": 1, "is_none": 1, "unwrap": 1, "unwrap_or": 2, "ok": 1, "err": 1, "is_ok": 1, "is_err": 1, "unwrap_ok": 1, "unwrap_err": 1, "unwrap_result_or": 2}
	if name == "print" || name == "set_of" {
		return nil
	}
	if name == "map_of" {
		if n%2 != 0 {
			return fmt.Errorf("map_of requires key/value pairs")
		}
		return nil
	}
	if name == "assert" {
		if n == 1 || n == 2 {
			return nil
		}
		return fmt.Errorf("assert takes one or two arguments")
	}
	if k, ok := fixed[name]; ok && n != k {
		return fmt.Errorf("%s requires %d arguments", name, k)
	}
	return nil
}
func stringsToValues(x []string) []Value {
	out := make([]Value, len(x))
	for j, v := range x {
		out[j] = v
	}
	return out
}
func promoteNumber(chosen, other Number) Number {
	q := chosen.clone()
	if chosen.Kind == "decimal" || other.Kind == "decimal" {
		q.Kind = "decimal"
	} else if chosen.Kind == "rational" || other.Kind == "rational" {
		q.Kind = "rational"
	}
	return q
}
func roundNumber(q Number, digits int) Number {
	scale := new(big.Int).Exp(big.NewInt(10), big.NewInt(int64(absInt(digits))), nil)
	r := new(big.Rat).Set(q.R)
	if digits >= 0 {
		r.Mul(r, new(big.Rat).SetInt(scale))
	} else {
		r.Quo(r, new(big.Rat).SetInt(scale))
	}
	num, den := r.Num(), r.Denom()
	quo, rem := new(big.Int).QuoRem(num, den, new(big.Int))
	twice := new(big.Int).Abs(new(big.Int).Mul(rem, big.NewInt(2)))
	cmp := twice.Cmp(new(big.Int).Abs(den))
	if cmp > 0 || (cmp == 0 && new(big.Int).Abs(quo).Bit(0) == 1) {
		if num.Sign() >= 0 {
			quo.Add(quo, big.NewInt(1))
		} else {
			quo.Sub(quo, big.NewInt(1))
		}
	}
	out := new(big.Rat).SetInt(quo)
	if digits >= 0 {
		out.Quo(out, new(big.Rat).SetInt(scale))
	} else {
		out.Mul(out, new(big.Rat).SetInt(scale))
	}
	return Number{R: out, Kind: "decimal"}
}
func absInt(x int) int {
	if x < 0 {
		return -x
	}
	return x
}

func (i *Interpreter) callSys(name string, args []Value, t Token) (Value, error) {
	switch name {
	case "args":
		if len(args) != 0 {
			return nil, i.rerr(t, "SAGA-R150", "sys.args takes no arguments")
		}
		out := make([]Value, len(sagaProcessArgs))
		for j, a := range sagaProcessArgs {
			out[j] = a
		}
		return out, nil
	case "version":
		if len(args) != 0 {
			return nil, i.rerr(t, "SAGA-R150", "sys.version takes no arguments")
		}
		return sagaGoVersion, nil
	case "platform":
		if len(args) != 0 {
			return nil, i.rerr(t, "SAGA-R150", "sys.platform takes no arguments")
		}
		return runtime.GOOS, nil
	case "arch":
		if len(args) != 0 {
			return nil, i.rerr(t, "SAGA-R150", "sys.arch takes no arguments")
		}
		return runtime.GOARCH, nil
	case "cpu_count":
		if len(args) != 0 {
			return nil, i.rerr(t, "SAGA-R150", "sys.cpu_count takes no arguments")
		}
		return numberFromInt64(int64(runtime.NumCPU())), nil
	case "page_size":
		if len(args) != 0 {
			return nil, i.rerr(t, "SAGA-R150", "sys.page_size takes no arguments")
		}
		return numberFromInt64(int64(os.Getpagesize())), nil
	}
	return nil, i.rerr(t, "SAGA-R123", "unknown sys member: "+name)
}

func (i *Interpreter) callCompiler(name string, args []Value, t Token) (Value, error) {
	switch name {
	case "version":
		if len(args) != 0 {
			return nil, i.rerr(t, "SAGA-R150", "compiler.version takes no arguments")
		}
		return "Saga self-host compiler API 1", nil
	case "check":
		if !sagaToolchainMode {
			return nil, i.rerr(t, "SAGA-R103", "compiler module is restricted to a verified Saga compiler bundle")
		}
		if len(args) != 1 {
			return nil, i.rerr(t, "SAGA-R150", "compiler.check(path)")
		}
		p, ok := args[0].(string)
		if !ok {
			return nil, i.rerr(t, "SAGA-R150", "compiler.check path must be text")
		}
		stmts, err := loadProgram(p)
		if err != nil {
			return nil, err
		}
		c := NewChecker()
		if err = c.Check(stmts); err != nil {
			return nil, err
		}
		return true, nil
	case "build", "self_build":
		if !sagaToolchainMode {
			return nil, i.rerr(t, "SAGA-R103", "compiler module is restricted to a verified Saga compiler bundle")
		}
		if len(args) != 2 {
			return nil, i.rerr(t, "SAGA-R150", "compiler.build(path, output)")
		}
		p, ok := args[0].(string)
		if !ok {
			return nil, i.rerr(t, "SAGA-R150", "compiler.build path must be text")
		}
		o, ok := args[1].(string)
		if !ok {
			return nil, i.rerr(t, "SAGA-R150", "compiler.build output must be text")
		}
		var out string
		var err error
		if name == "self_build" {
			out, err = buildStandaloneKind(p, o, "compiler")
		} else {
			out, err = buildStandalone(p, o)
		}
		if err != nil {
			return nil, err
		}
		return out, nil
	}
	return nil, i.rerr(t, "SAGA-R123", "unknown compiler member: "+name)
}

func (i *Interpreter) callTask(name string, args []Value, t Token) (Value, error) {
	switch name {
	case "pool":
		if len(args) != 1 {
			return nil, fmt.Errorf("task.pool(workers)")
		}
		workers, err := numberToInt(args[0])
		if err != nil || workers < 1 {
			return nil, fmt.Errorf("worker count must be at least 1")
		}
		return newTaskPoolValue(workers), nil
	case "submit":
		if len(args) < 2 {
			return nil, fmt.Errorf("task.submit(pool, callable, ...args)")
		}
		pool, ok := args[0].(*TaskPoolValue)
		if !ok {
			return nil, fmt.Errorf("task pool required")
		}
		prepared, err := i.prepareIsolatedCall(args[1], append([]Value{}, args[2:]...))
		if err != nil {
			return nil, err
		}
		f, err := pool.submit(prepared.run)
		if err != nil {
			return nil, err
		}
		if len(i.taskGroups) > 0 {
			g := i.taskGroups[len(i.taskGroups)-1]
			g.mu.Lock()
			g.Futures = append(g.Futures, f)
			g.mu.Unlock()
		}
		return f, nil
	case "shutdown":
		if len(args) != 1 {
			return nil, fmt.Errorf("task.shutdown(pool)")
		}
		pool, ok := args[0].(*TaskPoolValue)
		if !ok {
			return nil, fmt.Errorf("task pool required")
		}
		pool.close()
		return nil, nil
	case "spawn":
		if len(args) < 1 {
			return nil, fmt.Errorf("task.spawn requires callable")
		}
		prepared, err := i.prepareIsolatedCall(args[0], append([]Value{}, args[1:]...))
		if err != nil {
			return nil, err
		}
		f := newFuture(prepared.run)
		if len(i.taskGroups) > 0 {
			g := i.taskGroups[len(i.taskGroups)-1]
			g.mu.Lock()
			g.Futures = append(g.Futures, f)
			g.mu.Unlock()
		}
		return f, nil
	case "await":
		if len(args) != 1 {
			return nil, fmt.Errorf("task.await requires future")
		}
		f, ok := args[0].(*FutureValue)
		if !ok {
			return nil, fmt.Errorf("future required")
		}
		return f.await()
	case "all":
		vals, ok := args[0].([]Value)
		if !ok {
			return nil, fmt.Errorf("list[future] required")
		}
		out := []Value{}
		for _, v := range vals {
			f, ok := v.(*FutureValue)
			if !ok {
				return nil, fmt.Errorf("future required")
			}
			x, e := f.await()
			if e != nil {
				return nil, e
			}
			out = append(out, x)
		}
		return out, nil
	case "await_timeout":
		if len(args) != 2 {
			return nil, fmt.Errorf("task.await_timeout(future,milliseconds)")
		}
		f, ok := args[0].(*FutureValue)
		if !ok {
			return nil, fmt.Errorf("future required")
		}
		ms, err := numberToInt(args[1])
		if err != nil || ms < 0 {
			return nil, fmt.Errorf("non-negative timeout required")
		}
		select {
		case <-f.done:
			v, e := f.await()
			if e != nil {
				return ResultValue{OK: false, Value: ErrorValue{Kind: "task", Message: e.Error()}}, nil
			}
			return ResultValue{OK: true, Value: v}, nil
		case <-time.After(time.Duration(ms) * time.Millisecond):
			return ResultValue{OK: false, Value: ErrorValue{Kind: "timeout", Message: "task timeout"}}, nil
		}
	case "cancel":
		if len(args) != 1 {
			return nil, fmt.Errorf("task.cancel(future)")
		}
		f, ok := args[0].(*FutureValue)
		if !ok {
			return nil, fmt.Errorf("future required")
		}
		f.cancelled.Store(true)
		return nil, nil
	case "cancelled":
		if len(args) != 1 {
			return nil, fmt.Errorf("task.cancelled(future)")
		}
		f, ok := args[0].(*FutureValue)
		if !ok {
			return nil, fmt.Errorf("future required")
		}
		return f.cancelled.Load(), nil
	case "channel", "stream":
		if len(args) != 1 {
			return nil, fmt.Errorf("task.%s(capacity)", name)
		}
		cap, err := numberToInt(args[0])
		if err != nil || cap < 0 || cap > 1_000_000 {
			return nil, fmt.Errorf("channel capacity must be 0..1000000")
		}
		return &ChannelValue{Ch: make(chan Value, cap)}, nil
	case "send":
		if len(args) != 2 {
			return nil, fmt.Errorf("task.send(channel,value)")
		}
		ch, ok := args[0].(*ChannelValue)
		if !ok || ch.closed.Load() {
			return nil, fmt.Errorf("open channel required")
		}
		ch.Ch <- snapshotValue(args[1], map[*Instance]*Instance{})
		return nil, nil
	case "recv":
		if len(args) != 1 {
			return nil, fmt.Errorf("task.recv(channel)")
		}
		ch, ok := args[0].(*ChannelValue)
		if !ok {
			return nil, fmt.Errorf("channel required")
		}
		v, open := <-ch.Ch
		if !open {
			return OptionValue{}, nil
		}
		return OptionValue{Present: true, Value: v}, nil
	case "close":
		if len(args) != 1 {
			return nil, fmt.Errorf("task.close(channel)")
		}
		ch, ok := args[0].(*ChannelValue)
		if !ok {
			return nil, fmt.Errorf("channel required")
		}
		if ch.closed.CompareAndSwap(false, true) {
			close(ch.Ch)
		}
		return nil, nil
	case "actor":
		if len(args) != 1 {
			return nil, fmt.Errorf("task.actor(handler)")
		}
		handler := args[0]
		prepared, e := i.prepareIsolatedCall(handler, nil)
		if e != nil {
			return nil, e
		}
		actor := &ActorValue{Inbox: make(chan actorEnvelope, 64)}
		// One persistent isolated invocation owns the handler closure. Messages are
		// processed serially, so actor-local mutable state survives between asks
		// without becoming shared mutable caller state.
		go func() {
			for env := range actor.Inbox {
				if !isSendValue(env.Value, nil) {
					env.Done <- taskResult{nil, fmt.Errorf("actor message is not Send")}
					close(env.Done)
					continue
				}
				prepared.args = []Value{snapshotValue(env.Value, map[*Instance]*Instance{})}
				v, er := prepared.run()
				env.Done <- taskResult{v, er}
				close(env.Done)
			}
		}()
		return actor, nil
	case "ask":
		if len(args) != 2 {
			return nil, fmt.Errorf("task.ask(actor,message)")
		}
		a, ok := args[0].(*ActorValue)
		if !ok || a.closed.Load() {
			return nil, fmt.Errorf("running actor required")
		}
		done := make(chan taskResult, 1)
		a.Inbox <- actorEnvelope{Value: snapshotValue(args[1], map[*Instance]*Instance{}), Done: done}
		f := newFuture(func() (Value, error) { r := <-done; return r.value, r.err })
		if len(i.taskGroups) > 0 {
			g := i.taskGroups[len(i.taskGroups)-1]
			g.mu.Lock()
			g.Futures = append(g.Futures, f)
			g.mu.Unlock()
		}
		return f, nil
	case "stop":
		if len(args) != 1 {
			return nil, fmt.Errorf("task.stop(actor)")
		}
		a, ok := args[0].(*ActorValue)
		if !ok {
			return nil, fmt.Errorf("actor required")
		}
		if a.closed.CompareAndSwap(false, true) {
			close(a.Inbox)
		}
		return nil, nil
	case "parallel_map":
		if len(args) != 3 {
			return nil, fmt.Errorf("parallel_map(function,list,workers)")
		}
		vals, ok := args[1].([]Value)
		if !ok {
			return nil, fmt.Errorf("list required")
		}
		workers := len(vals)
		if q, ok := args[2].(Number); ok {
			if x, ok := q.Int(); ok && x.IsInt64() && x.Int64() > 0 && int(x.Int64()) < workers {
				workers = int(x.Int64())
			}
		}
		if workers < 1 && len(vals) > 0 {
			workers = 1
		}
		out := make([]Value, len(vals))
		errs := make([]error, len(vals))
		prepared := make([]*isolatedInvocation, len(vals))
		for j, v := range vals {
			p, err := i.prepareIsolatedCall(args[0], []Value{v})
			if err != nil {
				return nil, err
			}
			prepared[j] = p
		}
		sem := make(chan struct{}, workers)
		var wg sync.WaitGroup
		for j := range vals {
			wg.Add(1)
			go func(j int) {
				defer wg.Done()
				sem <- struct{}{}
				defer func() { <-sem }()
				out[j], errs[j] = prepared[j].run()
			}(j)
		}
		wg.Wait()
		for _, e := range errs {
			if e != nil {
				return nil, e
			}
		}
		return out, nil
	}
	return nil, i.rerr(t, "SAGA-R123", "unknown task member: "+name)
}

func stableSortSet(s SetValue) SetValue {
	out := append([]Value{}, s.Items...)
	sort.SliceStable(out, func(a, b int) bool { return formatValue(out[a], false) < formatValue(out[b], false) })
	return SetValue{Items: out}
}
