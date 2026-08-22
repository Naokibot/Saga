//go:build !sagaruntime

package main

import (
	"fmt"
	"os"
	"strconv"
	"strings"
)

type pyEmitter struct {
	b      strings.Builder
	indent int
}

func (p *pyEmitter) line(s string) { p.b.WriteString(strings.Repeat("    ", p.indent) + s + "\n") }
func pyName(n string) string {
	switch n {
	case "text":
		return "str"
	case "none":
		return "saga_none"
	case "any":
		return "saga_any"
	}
	return n
}
func (p *pyEmitter) expr(e Expr) (string, error) {
	switch x := e.(type) {
	case *Literal:
		switch v := x.Value.(type) {
		case nil:
			return "None", nil
		case bool:
			if v {
				return "True", nil
			}
			return "False", nil
		case string:
			return strconv.Quote(v), nil
		case Number:
			if v.Kind == "int" {
				return v.R.Num().String(), nil
			}
			if v.Kind == "decimal" {
				return "Decimal(" + strconv.Quote(v.String()) + ")", nil
			}
			return "Fraction(" + v.R.Num().String() + "," + v.R.Denom().String() + ")", nil
		}
	case *Variable:
		return pyName(x.Name), nil
	case *ListExpr:
		parts := []string{}
		for _, q := range x.Items {
			z, e := p.expr(q)
			if e != nil {
				return "", e
			}
			parts = append(parts, z)
		}
		return "[" + strings.Join(parts, ", ") + "]", nil
	case *InterpolatedString:
		parts := []string{}
		for j, t := range x.Texts {
			if t != "" {
				parts = append(parts, strconv.Quote(t))
			}
			if j < len(x.Exprs) {
				z, e := p.expr(x.Exprs[j])
				if e != nil {
					return "", e
				}
				parts = append(parts, "str("+z+")")
			}
		}
		if len(parts) == 0 {
			return `""`, nil
		}
		return "(" + strings.Join(parts, " + ") + ")", nil
	case *Unary:
		r, e := p.expr(x.Right)
		if e != nil {
			return "", e
		}
		op := map[Kind]string{MINUS: "-", BANG: "not ", NOT: "not "}[x.Op.Kind]
		return "(" + op + r + ")", nil
	case *Binary:
		l, e := p.expr(x.Left)
		if e != nil {
			return "", e
		}
		r, e := p.expr(x.Right)
		if e != nil {
			return "", e
		}
		if x.Op.Kind == SLASH {
			return "_saga_div(" + l + "," + r + ")", nil
		}
		if x.Op.Kind == PERCENT {
			return "_saga_rem(" + l + "," + r + ")", nil
		}
		op := map[Kind]string{PLUS: "+", MINUS: "-", STAR: "*", POWER: "**", EQEQ: "==", BANGEQ: "!=", LESS: "<", LESSEQ: "<=", GREATER: ">", GREATEREQ: ">=", AND: "and", OR: "or"}[x.Op.Kind]
		if op == "" {
			return "", fmt.Errorf("unsupported Python operator")
		}
		return "(" + l + " " + op + " " + r + ")", nil
	case *RangeExpr:
		a, e := p.expr(x.Start)
		if e != nil {
			return "", e
		}
		b, e := p.expr(x.End)
		if e != nil {
			return "", e
		}
		return "_saga_range(" + a + "," + b + ")", nil
	case *Call:
		c, e := p.expr(x.Callee)
		if e != nil {
			return "", e
		}
		aa := []string{}
		for _, q := range x.Args {
			z, e := p.expr(q)
			if e != nil {
				return "", e
			}
			aa = append(aa, z)
		}
		return c + "(" + strings.Join(aa, ", ") + ")", nil
	case *Member:
		t, e := p.expr(x.Target)
		if e != nil {
			return "", e
		}
		return t + "." + x.Name, nil
	case *Index:
		t, e := p.expr(x.Target)
		if e != nil {
			return "", e
		}
		q, e := p.expr(x.Index)
		if e != nil {
			return "", e
		}
		return t + "[" + q + "]", nil
	}
	return "", fmt.Errorf("unsupported Python expression %T", e)
}
func (p *pyEmitter) block(b *Block) error {
	if b == nil || len(b.Stmts) == 0 {
		p.line("pass")
		return nil
	}
	for _, s := range b.Stmts {
		if e := p.stmt(s); e != nil {
			return e
		}
	}
	return nil
}
func (p *pyEmitter) stmt(s Stmt) error {
	switch x := s.(type) {
	case *UseStmt:
		p.line("# Saga use " + x.Module)
		return nil
	case *VarDecl:
		v, e := p.expr(x.Init)
		if e != nil {
			return e
		}
		p.line(pyName(x.Name) + " = " + v)
	case *Assign:
		v, e := p.expr(x.Value)
		if e != nil {
			return e
		}
		t, e := p.expr(x.Target)
		if e != nil {
			return e
		}
		p.line(t + " = " + v)
	case *ExprStmt:
		v, e := p.expr(x.Expr)
		if e != nil {
			return e
		}
		p.line(v)
	case *Block:
		return p.block(x)
	case *IfStmt:
		c, e := p.expr(x.Cond)
		if e != nil {
			return e
		}
		p.line("if " + c + ":")
		p.indent++
		p.block(x.Then)
		p.indent--
		if x.Else != nil {
			p.line("else:")
			p.indent++
			p.stmt(x.Else)
			p.indent--
		}
	case *WhileStmt:
		c, e := p.expr(x.Cond)
		if e != nil {
			return e
		}
		p.line("while " + c + ":")
		p.indent++
		p.block(x.Body)
		p.indent--
	case *ForStmt:
		q, e := p.expr(x.Iterable)
		if e != nil {
			return e
		}
		p.line("for " + x.Name + " in " + q + ":")
		p.indent++
		p.block(x.Body)
		p.indent--
	case *BreakStmt:
		p.line("break")
	case *ContinueStmt:
		p.line("continue")
	case *ReturnStmt:
		if x.Value == nil {
			p.line("return")
		} else {
			v, e := p.expr(x.Value)
			if e != nil {
				return e
			}
			p.line("return " + v)
		}
	case *ThrowStmt:
		v, e := p.expr(x.Value)
		if e != nil {
			return e
		}
		p.line("raise SagaThrown(" + v + ")")
	case *TryStmt:
		p.line("try:")
		p.indent++
		p.block(x.Try)
		p.indent--
		if x.Catch != nil {
			p.line("except Exception as " + x.CatchName + ":")
			p.indent++
			p.block(x.Catch)
			p.indent--
		}
		if x.Finally != nil {
			p.line("finally:")
			p.indent++
			p.block(x.Finally)
			p.indent--
		}
	case *FnDecl:
		params := []string{}
		for _, q := range x.Params {
			params = append(params, q.Name)
		}
		p.line("def " + x.Name + "(" + strings.Join(params, ", ") + "):")
		p.indent++
		if x.ExprBody != nil {
			v, e := p.expr(x.ExprBody)
			if e != nil {
				return e
			}
			p.line("return " + v)
		} else {
			p.block(x.Body)
		}
		p.indent--
	case *ClassDecl:
		if x.Interface {
			p.line("class " + x.Name + ":")
			p.indent++
			p.line("pass")
			p.indent--
			return nil
		}
		base := "object"
		if x.Base != nil {
			base = x.Base.Name
		}
		decor := ""
		if x.Record {
			decor = "@dataclass\n"
		}
		if decor != "" {
			p.line(strings.TrimSpace(decor))
		}
		p.line("class " + x.Name + "(" + base + "):")
		p.indent++
		if len(x.Fields) > 0 {
			params := []string{}
			for _, f := range x.Fields {
				params = append(params, f.Name)
			}
			p.line("def __init__(self, " + strings.Join(params, ", ") + "):")
			p.indent++
			for _, f := range x.Fields {
				p.line("self." + f.Name + " = " + f.Name)
			}
			p.indent--
		}
		if len(x.Methods) == 0 && len(x.Fields) == 0 {
			p.line("pass")
		}
		for _, m := range x.Methods {
			params := []string{"self"}
			for _, q := range m.Params {
				params = append(params, q.Name)
			}
			p.line("def " + m.Name + "(" + strings.Join(params, ", ") + "):")
			p.indent++
			if m.ExprBody != nil {
				v, e := p.expr(m.ExprBody)
				if e != nil {
					return e
				}
				p.line("return " + v)
			} else {
				p.block(m.Body)
			}
			p.indent--
		}
		p.indent--
	case *EnumDecl:
		p.line("class " + x.Name + "(Enum):")
		p.indent++
		for j, v := range x.Variants {
			if len(v.Payload) > 0 {
				return fmt.Errorf("payload enum is not supported by legacy Python transpiler")
			}
			p.line(v.Name + " = " + strconv.Itoa(j+1))
		}
		p.indent--
	case *MatchStmt:
		v, e := p.expr(x.Value)
		if e != nil {
			return e
		}
		tmp := "_saga_match_value"
		p.line(tmp + " = " + v)
		for j, c := range x.Cases {
			q, e := p.expr(c.Pattern)
			if e != nil {
				return e
			}
			if j == 0 {
				p.line("if " + tmp + " == " + q + ":")
			} else {
				p.line("elif " + tmp + " == " + q + ":")
			}
			p.indent++
			p.block(c.Body)
			p.indent--
		}
		if x.Default != nil {
			p.line("else:")
			p.indent++
			p.block(x.Default)
			p.indent--
		}
	case *TestDecl:
		p.line("def test_" + sanitizePyName(x.Name) + "():")
		p.indent++
		p.block(x.Body)
		p.indent--
	default:
		return fmt.Errorf("unsupported Python statement %T", s)
	}
	return nil
}
func sanitizePyName(s string) string {
	var b strings.Builder
	for _, r := range s {
		if (r >= 'a' && r <= 'z') || (r >= 'A' && r <= 'Z') || (r >= '0' && r <= '9') || r == '_' {
			b.WriteRune(r)
		} else {
			b.WriteByte('_')
		}
	}
	if b.Len() == 0 {
		return "case"
	}
	return b.String()
}
func transpilePython(path string) (string, error) {
	stmts, e := loadProgram(path)
	if e != nil {
		return "", e
	}
	c := NewChecker()
	if e = c.Check(stmts); e != nil {
		return "", e
	}
	p := &pyEmitter{}
	p.line("# Generated by Saga Native " + sagaGoVersion + "; optional interoperability target")
	p.line("from decimal import Decimal")
	p.line("from fractions import Fraction")
	p.line("from dataclasses import dataclass")
	p.line("from enum import Enum")
	p.line("class SagaThrown(Exception): pass")
	p.line("def _saga_div(a,b): return Fraction(a,b) if isinstance(a,int) and isinstance(b,int) else a/b")
	p.line("def _saga_rem(a,b):")
	p.indent++
	p.line("if b == 0: raise ZeroDivisionError('Saga remainder by zero')")
	p.line("q = abs(a) // abs(b)")
	p.line("if (a < 0) != (b < 0): q = -q")
	p.line("return a - q * b")
	p.indent--
	p.line("def _saga_range(a,b): return range(a,b+1) if a<=b else range(a,b-1,-1)")
	p.line("def text(v): return str(v)")
	p.line("def some(v): return ('some',v)")
	p.line("def saga_none(): return ('none',None)")
	p.line("def ok(v): return ('ok',v)")
	p.line("def err(v): return ('err',v)")
	for _, s := range stmts {
		if e = p.stmt(s); e != nil {
			return "", e
		}
	}
	return p.b.String(), nil
}
func runTranspilePython(args []string) int {
	if len(args) < 1 {
		fmt.Fprintln(os.Stderr, "source file required")
		return 64
	}
	out := ""
	for j := 1; j < len(args); j++ {
		if (args[j] == "-o" || args[j] == "--output") && j+1 < len(args) {
			out = args[j+1]
			j++
		} else {
			fmt.Fprintln(os.Stderr, "unknown transpile option:", args[j])
			return 64
		}
	}
	src, e := transpilePython(args[0])
	if e != nil {
		return printDiagnostic(e)
	}
	if out == "" {
		fmt.Print(src)
	} else if e = os.WriteFile(out, []byte(src), 0644); e != nil {
		fmt.Fprintln(os.Stderr, e)
		return 74
	}
	return 0
}
