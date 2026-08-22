package main

import "fmt"

// loadObjectGraphProgram loads a path-independent, already-resolved Saga source
// graph. It is shared by native object bundles and keeps the same namespace
// semantics as the normal source loader without consulting the host filesystem.
func loadObjectGraphProgram(entry string, sources map[string]string, edges map[string]string) ([]Stmt, error) {
	seen := map[string]bool{}
	active := map[string]bool{}
	moduleBindings := map[string]string{}
	moduleNames := map[string]string{}

	var load func(string, bool, string) ([]Stmt, error)
	load = func(fileID string, imported bool, requestedAlias string) ([]Stmt, error) {
		if active[fileID] {
			return nil, &SagaError{Code: "SAGA-I001", ID: "SAGA-I111", Message: "cyclic object source import: " + fileID, File: fileID, Line: 1, Col: 1}
		}
		if seen[fileID] {
			if imported {
				previous := moduleBindings[fileID]
				requested := requestedAlias
				if requested == "" {
					requested = moduleNames[fileID]
				}
				if previous != "" && requested != "" && previous != requested {
					return nil, &SagaError{Code: "SAGA-P001", ID: "SAGA-P109", Message: "same module cannot be imported with multiple aliases: " + previous + " and " + requested, File: fileID, Line: 1, Col: 1}
				}
			}
			return nil, nil
		}
		raw, ok := sources[fileID]
		if !ok {
			return nil, fmt.Errorf("native object source unavailable: %s", fileID)
		}
		toks, err := lex(raw, "object://"+fileID)
		if err != nil {
			return nil, err
		}
		stmts, err := parse(toks)
		if err != nil {
			return nil, err
		}
		moduleName := ""
		var moduleTok Token
		for _, st := range stmts {
			if m, ok := st.(*ModuleDecl); ok {
				if moduleName != "" {
					return nil, &SagaError{Code: "SAGA-P001", ID: "SAGA-P102", Message: "only one module directive is allowed per source file", File: fileID, Line: m.Tok.Line, Col: m.Tok.Col}
				}
				moduleName, moduleTok = m.Name, m.Tok
			}
		}
		active[fileID] = true
		defer delete(active, fileID)
		dependencies := []Stmt{}
		locals := []Stmt{}
		for _, st := range stmts {
			if u, ok := st.(*UseStmt); ok && u.SourcePath != "" {
				dep, exists := edges[fileID+"\x00"+u.SourcePath]
				if !exists {
					return nil, fmt.Errorf("native object dependency edge unavailable: %s -> %s", fileID, u.SourcePath)
				}
				xs, e := load(dep, true, u.Alias)
				if e != nil {
					return nil, e
				}
				dependencies = append(dependencies, xs...)
				continue
			}
			if _, ok := st.(*ModuleDecl); ok {
				continue
			}
			locals = append(locals, st)
		}
		body := append(dependencies, locals...)
		seen[fileID] = true
		if imported && moduleName != "" {
			bind := requestedAlias
			if bind == "" {
				bind = moduleName
			}
			moduleBindings[fileID] = bind
			moduleNames[fileID] = moduleName
			return []Stmt{&SourceModuleStmt{Name: moduleName, BindName: bind, Stmts: body, Tok: moduleTok}}, nil
		}
		if imported && requestedAlias != "" && moduleName == "" {
			return nil, &SagaError{Code: "SAGA-P001", ID: "SAGA-P109", Message: "legacy source unit without module cannot use an alias", File: fileID, Line: 1, Col: 1}
		}
		if !imported && moduleName != "" {
			body = append([]Stmt{&ModuleDecl{Name: moduleName, Tok: moduleTok}}, body...)
		}
		return body, nil
	}
	return load(entry, false, "")
}

func executeObjectGraph(entry string, sources map[string]string, edges map[string]string) error {
	stmts, err := loadObjectGraphProgram(entry, sources, edges)
	if err != nil {
		return err
	}
	c := NewChecker()
	if err = c.Check(stmts); err != nil {
		return err
	}
	it := NewInterpreter(c, nil)
	return it.Interpret(stmts)
}
