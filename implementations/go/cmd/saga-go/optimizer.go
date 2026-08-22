package main

// optimizeProgram performs semantics-preserving optimizations after static
// checking. It deliberately never removes code before type checking, so dead
// branches are still checked and diagnostics stay stable.
func optimizeProgram(stmts []Stmt) []Stmt {
	comptime := map[string]*FnDecl{}
	for _, s := range stmts {
		if f, ok := s.(*FnDecl); ok && f.Comptime && f.ExprBody != nil {
			comptime[f.Name] = f
		}
	}
	for _, s := range stmts {
		foldComptimeStmt(s, comptime)
	}
	out := make([]Stmt, 0, len(stmts))
	for _, s := range stmts {
		out = append(out, optimizeStmt(s))
	}
	return out
}

func foldComptimeStmt(s Stmt, funcs map[string]*FnDecl) {
	switch x := s.(type) {
	case *VarDecl:
		x.Init = foldComptimeExpr(x.Init, funcs)
	case *Assign:
		x.Value = foldComptimeExpr(x.Value, funcs)
	case *ExprStmt:
		x.Expr = foldComptimeExpr(x.Expr, funcs)
	case *ReturnStmt:
		if x.Value != nil {
			x.Value = foldComptimeExpr(x.Value, funcs)
		}
	case *ThrowStmt:
		x.Value = foldComptimeExpr(x.Value, funcs)
	case *Block:
		for _, q := range x.Stmts {
			foldComptimeStmt(q, funcs)
		}
	case *IfStmt:
		x.Cond = foldComptimeExpr(x.Cond, funcs)
		foldComptimeStmt(x.Then, funcs)
		if x.Else != nil {
			foldComptimeStmt(x.Else, funcs)
		}
	case *WhileStmt:
		x.Cond = foldComptimeExpr(x.Cond, funcs)
		foldComptimeStmt(x.Body, funcs)
	case *ForStmt:
		x.Iterable = foldComptimeExpr(x.Iterable, funcs)
		foldComptimeStmt(x.Body, funcs)
	case *FnDecl:
		if x.ExprBody != nil {
			x.ExprBody = foldComptimeExpr(x.ExprBody, funcs)
		}
		if x.Body != nil {
			foldComptimeStmt(x.Body, funcs)
		}
	case *ClassDecl:
		for _, m := range x.Methods {
			foldComptimeStmt(m, funcs)
		}
	case *TryStmt:
		foldComptimeStmt(x.Try, funcs)
		if x.Catch != nil {
			foldComptimeStmt(x.Catch, funcs)
		}
		if x.Finally != nil {
			foldComptimeStmt(x.Finally, funcs)
		}
	case *DeferStmt:
		x.Value = foldComptimeExpr(x.Value, funcs)
	case *UsingStmt:
		x.Init = foldComptimeExpr(x.Init, funcs)
		foldComptimeStmt(x.Body, funcs)
	case *UnsafeStmt:
		foldComptimeStmt(x.Body, funcs)
	case *TaskGroupStmt:
		foldComptimeStmt(x.Body, funcs)
	case *TestDecl:
		foldComptimeStmt(x.Body, funcs)
	}
}

func foldComptimeExpr(e Expr, funcs map[string]*FnDecl) Expr {
	if e == nil {
		return nil
	}
	switch x := e.(type) {
	case *Unary:
		x.Right = foldComptimeExpr(x.Right, funcs)
	case *Binary:
		x.Left = foldComptimeExpr(x.Left, funcs)
		x.Right = foldComptimeExpr(x.Right, funcs)
	case *RangeExpr:
		x.Start = foldComptimeExpr(x.Start, funcs)
		x.End = foldComptimeExpr(x.End, funcs)
	case *ListExpr:
		for j, q := range x.Items {
			x.Items[j] = foldComptimeExpr(q, funcs)
		}
	case *InterpolatedString:
		for j, q := range x.Exprs {
			x.Exprs[j] = foldComptimeExpr(q, funcs)
		}
	case *Index:
		x.Target = foldComptimeExpr(x.Target, funcs)
		x.Index = foldComptimeExpr(x.Index, funcs)
	case *Member:
		x.Target = foldComptimeExpr(x.Target, funcs)
	case *Call:
		x.Callee = foldComptimeExpr(x.Callee, funcs)
		for j, q := range x.Args {
			x.Args[j] = foldComptimeExpr(q, funcs)
		}
		q, ok := x.Callee.(*Variable)
		var f *FnDecl
		if ok {
			f = funcs[q.Name]
		}
		if ok && f != nil && f.ExprBody != nil && len(f.Params) == len(x.Args) {
			all := true
			vals := make([]Value, len(x.Args))
			for j, a := range x.Args {
				l, yes := a.(*Literal)
				if !yes {
					all = false
					break
				}
				vals[j] = cloneValue(l.Value)
			}
			if all {
				it := NewInterpreter(NewChecker(), func(string) {})
				for j, p := range f.Params {
					it.Env.define(p.Name, vals[j], false)
				}
				if v, err := it.eval(f.ExprBody); err == nil {
					return &Literal{Value: cloneValue(v), Tok: x.Tok}
				}
			}
		}
	}
	return e
}

func optimizeStmt(s Stmt) Stmt {
	switch x := s.(type) {
	case *VarDecl:
		x.Init = optimizeExpr(x.Init)
	case *Assign:
		x.Value = optimizeExpr(x.Value)
	case *ExprStmt:
		x.Expr = optimizeExpr(x.Expr)
	case *Block:
		for j, q := range x.Stmts {
			x.Stmts[j] = optimizeStmt(q)
		}
	case *IfStmt:
		x.Cond = optimizeExpr(x.Cond)
		x.Then = optimizeStmt(x.Then).(*Block)
		if x.Else != nil {
			x.Else = optimizeStmt(x.Else)
		}
		if l, ok := x.Cond.(*Literal); ok {
			if b, ok := l.Value.(bool); ok {
				if b {
					return x.Then
				}
				if x.Else != nil {
					return x.Else
				}
				return &Block{Stmts: []Stmt{}}
			}
		}
	case *WhileStmt:
		x.Cond = optimizeExpr(x.Cond)
		x.Body = optimizeStmt(x.Body).(*Block)
		if l, ok := x.Cond.(*Literal); ok {
			if b, ok := l.Value.(bool); ok && !b {
				return &Block{Stmts: []Stmt{}}
			}
		}
	case *ForStmt:
		x.Iterable = optimizeExpr(x.Iterable)
		x.Body = optimizeStmt(x.Body).(*Block)
	case *ReturnStmt:
		if x.Value != nil {
			x.Value = optimizeExpr(x.Value)
		}
	case *ThrowStmt:
		x.Value = optimizeExpr(x.Value)
	case *TryStmt:
		x.Try = optimizeStmt(x.Try).(*Block)
		if x.Catch != nil {
			x.Catch = optimizeStmt(x.Catch).(*Block)
		}
		if x.Finally != nil {
			x.Finally = optimizeStmt(x.Finally).(*Block)
		}
	case *FnDecl:
		if x.ExprBody != nil {
			x.ExprBody = optimizeExpr(x.ExprBody)
		}
		if x.Body != nil {
			x.Body = optimizeStmt(x.Body).(*Block)
		}
	case *ClassDecl:
		for _, m := range x.Methods {
			optimizeStmt(m)
		}
	case *MatchStmt:
		x.Value = optimizeExpr(x.Value)
		for j := range x.Cases {
			x.Cases[j].Pattern = optimizeExpr(x.Cases[j].Pattern)
			x.Cases[j].Body = optimizeStmt(x.Cases[j].Body).(*Block)
		}
		if x.Default != nil {
			x.Default = optimizeStmt(x.Default).(*Block)
		}
	case *TestDecl:
		x.Body = optimizeStmt(x.Body).(*Block)
	}
	return s
}
func optimizeExpr(e Expr) Expr {
	switch x := e.(type) {
	case *Unary:
		x.Right = optimizeExpr(x.Right)
		if _, ok := x.Right.(*Literal); ok {
			it := NewInterpreter(NewChecker(), func(string) {})
			if v, er := it.eval(x); er == nil {
				return &Literal{Value: v, Tok: x.Op}
			}
		}
	case *Binary:
		x.Left = optimizeExpr(x.Left)
		x.Right = optimizeExpr(x.Right)
		_, a := x.Left.(*Literal)
		_, b := x.Right.(*Literal)
		if a && b {
			it := NewInterpreter(NewChecker(), func(string) {})
			if v, er := it.evalBinary(x); er == nil {
				return &Literal{Value: v, Tok: x.Op}
			}
		}
	case *RangeExpr:
		x.Start = optimizeExpr(x.Start)
		x.End = optimizeExpr(x.End)
	case *Call:
		x.Callee = optimizeExpr(x.Callee)
		for j, q := range x.Args {
			x.Args[j] = optimizeExpr(q)
		}
	case *Index:
		x.Target = optimizeExpr(x.Target)
		x.Index = optimizeExpr(x.Index)
	case *Member:
		x.Target = optimizeExpr(x.Target)
	case *ListExpr:
		for j, q := range x.Items {
			x.Items[j] = optimizeExpr(q)
		}
	case *InterpolatedString:
		all := true
		var text string
		for j, q := range x.Exprs {
			x.Exprs[j] = optimizeExpr(q)
			if _, ok := x.Exprs[j].(*Literal); !ok {
				all = false
			}
		}
		if all {
			it := NewInterpreter(NewChecker(), func(string) {})
			if v, er := it.eval(x); er == nil {
				text = v.(string)
				return &Literal{Value: text, Tok: x.Tok}
			}
		}
	}
	return e
}
