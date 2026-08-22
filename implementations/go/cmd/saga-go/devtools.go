//go:build !sagaruntime

package main

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

func sagaSourceFiles(path string) ([]string, error) {
	abs, err := filepath.Abs(path)
	if err != nil {
		return nil, err
	}
	st, err := os.Stat(abs)
	if err != nil {
		return nil, err
	}
	if !st.IsDir() {
		if filepath.Ext(abs) != ".saga" {
			return nil, fmt.Errorf("expected .saga file: %s", path)
		}
		return []string{abs}, nil
	}
	out := []string{}
	err = filepath.WalkDir(abs, func(p string, d os.DirEntry, e error) error {
		if e != nil {
			return e
		}
		if d.IsDir() {
			name := d.Name()
			if name == ".git" || name == "build" || name == "dist" || name == ".saga" {
				return filepath.SkipDir
			}
			return nil
		}
		if strings.EqualFold(filepath.Ext(p), ".saga") {
			out = append(out, p)
		}
		return nil
	})
	sort.Strings(out)
	return out, err
}

func braceDelta(line string) (leadingClose, opens, closes int) {
	inString := false
	escaped := false
	first := true
	rs := []rune(line)
	for j := 0; j < len(rs); j++ {
		r := rs[j]
		if !inString && (r == '#' || (r == '/' && j+1 < len(rs) && rs[j+1] == '/')) {
			break
		}
		if r == '"' {
			if !escaped {
				inString = !inString
			}
			escaped = false
			continue
		}
		if inString {
			if r == '\\' && !escaped {
				escaped = true
			} else {
				escaped = false
			}
			continue
		}
		if r == ' ' || r == '\t' {
			continue
		}
		if first {
			if r == '}' {
				leadingClose = 1
			}
			first = false
		}
		if r == '{' {
			opens++
		}
		if r == '}' {
			closes++
		}
	}
	return
}

func formatSagaSource(source string) string {
	source = strings.ReplaceAll(source, "\r\n", "\n")
	source = strings.ReplaceAll(source, "\r", "\n")
	lines := strings.Split(source, "\n")
	out := make([]string, 0, len(lines))
	indent := 0
	blank := false
	for _, raw := range lines {
		text := strings.TrimSpace(raw)
		if text == "" {
			if len(out) > 0 && !blank {
				out = append(out, "")
			}
			blank = true
			continue
		}
		blank = false
		leading, opens, closes := braceDelta(text)
		level := indent
		if leading > 0 && level > 0 {
			level--
		}
		out = append(out, strings.Repeat("    ", level)+text)
		indent += opens - closes
		if indent < 0 {
			indent = 0
		}
	}
	for len(out) > 0 && out[len(out)-1] == "" {
		out = out[:len(out)-1]
	}
	return strings.Join(out, "\n") + "\n"
}

func runFormat(path string, check bool) int {
	files, err := sagaSourceFiles(path)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 66
	}
	changed := []string{}
	for _, p := range files {
		raw, e := os.ReadFile(p)
		if e != nil {
			fmt.Fprintln(os.Stderr, e)
			return 66
		}
		formatted := formatSagaSource(string(raw))
		if formatted != string(raw) {
			changed = append(changed, p)
			if !check {
				if e = os.WriteFile(p, []byte(formatted), 0644); e != nil {
					fmt.Fprintln(os.Stderr, e)
					return 66
				}
			}
		}
	}
	if check && len(changed) > 0 {
		for _, p := range changed {
			fmt.Println("needs formatting:", p)
		}
		return 7
	}
	if check {
		fmt.Printf("format check: %d file(s) OK\n", len(files))
	} else {
		fmt.Printf("formatted: %d file(s), changed %d\n", len(files), len(changed))
	}
	return 0
}

func typeRefContainsAny(t TypeRef) bool {
	if strings.EqualFold(t.Name, "any") {
		return true
	}
	for _, a := range t.Args {
		if typeRefContainsAny(a) {
			return true
		}
	}
	return false
}

func lintStatements(stmts []Stmt) []string {
	warnings := []string{}
	for _, st := range stmts {
		switch d := st.(type) {
		case *FnDecl:
			for _, p := range d.Params {
				if typeRefContainsAny(p.Type) {
					warnings = append(warnings, fmt.Sprintf("%s:%d public function %s uses any in parameter %s", d.Tok.File, d.Tok.Line, d.Name, p.Name))
				}
			}
			if d.Return != nil && typeRefContainsAny(*d.Return) {
				warnings = append(warnings, fmt.Sprintf("%s:%d public function %s returns any", d.Tok.File, d.Tok.Line, d.Name))
			}
		case *ClassDecl:
			for _, f := range d.Fields {
				if typeRefContainsAny(f.Type) {
					warnings = append(warnings, fmt.Sprintf("%s:%d field %s.%s uses any", d.Tok.File, d.Tok.Line, d.Name, f.Name))
				}
			}
		}
	}
	return warnings
}

func runLint(path string, denyWarnings bool) int {
	files, err := sagaSourceFiles(path)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 66
	}
	warnings := []string{}
	for _, p := range files {
		stmts, e := loadProgram(p)
		if e != nil {
			return printDiagnostic(e)
		}
		c := NewChecker()
		if e = c.Check(stmts); e != nil {
			return printDiagnostic(e)
		}
		warnings = append(warnings, lintStatements(stmts)...)
	}
	for _, w := range warnings {
		fmt.Println("warning:", w)
	}
	if denyWarnings && len(warnings) > 0 {
		return 7
	}
	fmt.Printf("lint: %d file(s), %d warning(s)\n", len(files), len(warnings))
	return 0
}

func runNativeTests(path string) int {
	project, err := loadProject(path)
	testRoot := ""
	if err == nil {
		testRoot = project.TestDir
	} else {
		abs, e := filepath.Abs(path)
		if e != nil {
			fmt.Fprintln(os.Stderr, e)
			return 66
		}
		st, e := os.Stat(abs)
		if e != nil {
			fmt.Fprintln(os.Stderr, e)
			return 66
		}
		if st.IsDir() {
			testRoot = filepath.Join(abs, "tests")
		} else {
			testRoot = abs
		}
	}
	files, err := sagaSourceFiles(testRoot)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 66
	}
	passed, total := 0, 0
	for _, p := range files {
		stmts, e := loadProgram(p)
		if e != nil {
			total++
			fmt.Println("FAIL", p)
			printDiagnostic(e)
			continue
		}
		c := NewChecker()
		if e = c.Check(stmts); e != nil {
			total++
			fmt.Println("FAIL", p)
			printDiagnostic(e)
			continue
		}
		it := NewInterpreter(c, func(string) {})
		if e = it.Interpret(stmts); e != nil {
			total++
			fmt.Println("FAIL", p)
			printDiagnostic(e)
			continue
		}
		tests := []*TestDecl{}
		for _, st := range stmts {
			if td, ok := st.(*TestDecl); ok {
				tests = append(tests, td)
			}
		}
		if len(tests) == 0 {
			total++
			passed++
			fmt.Println("PASS", p)
			continue
		}
		for _, td := range tests {
			total++
			e = it.RunTest(td)
			if e != nil {
				fmt.Printf("FAIL %s :: %s\n", p, td.Name)
				printDiagnostic(e)
			} else {
				passed++
				fmt.Printf("PASS %s :: %s\n", p, td.Name)
			}
		}
	}
	fmt.Printf("%d/%d Saga tests passed\n", passed, total)
	if passed != total {
		return 7
	}
	return 0
}

func sourceBraceBalance(source string) int {
	balance := 0
	inString, escaped := false, false
	rs := []rune(source)
	for j := 0; j < len(rs); j++ {
		r := rs[j]
		if !inString && (r == '#' || (r == '/' && j+1 < len(rs) && rs[j+1] == '/')) {
			for j < len(rs) && rs[j] != '\n' {
				j++
			}
			continue
		}
		if r == '"' {
			if !escaped {
				inString = !inString
			}
			escaped = false
			continue
		}
		if inString {
			if r == '\\' && !escaped {
				escaped = true
			} else {
				escaped = false
			}
			continue
		}
		if r == '{' {
			balance++
		}
		if r == '}' {
			balance--
		}
	}
	return balance
}

func runRepl() int {
	checker := NewChecker()
	interpreter := NewInterpreter(checker, nil)
	scanner := bufio.NewScanner(os.Stdin)
	interactive := false
	if st, err := os.Stdin.Stat(); err == nil {
		interactive = (st.Mode() & os.ModeCharDevice) != 0
	}
	pending := ""
	for {
		if interactive {
			if pending == "" {
				fmt.Print("saga> ")
			} else {
				fmt.Print("...> ")
			}
		}
		if !scanner.Scan() {
			break
		}
		line := scanner.Text()
		if pending == "" && strings.HasPrefix(strings.TrimSpace(line), ":") {
			switch strings.TrimSpace(line) {
			case ":quit", ":exit":
				return 0
			case ":help":
				fmt.Println(":help  :quit  :exit")
				continue
			default:
				fmt.Println("unknown REPL command")
				continue
			}
		}
		pending += line + "\n"
		if sourceBraceBalance(pending) > 0 {
			continue
		}
		toks, err := lex(pending, "<repl>")
		var stmts []Stmt
		if err == nil {
			stmts, err = parse(toks)
		}
		if err == nil {
			err = checker.Check(stmts)
		}
		if err == nil {
			err = interpreter.Interpret(stmts)
		}
		if err != nil {
			printDiagnostic(err)
		}
		pending = ""
	}
	if err := scanner.Err(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 74
	}
	if strings.TrimSpace(pending) != "" {
		fmt.Fprintln(os.Stderr, "incomplete Saga input")
		return 3
	}
	return 0
}
