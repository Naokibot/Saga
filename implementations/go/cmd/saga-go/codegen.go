//go:build !sagaruntime

package main

import (
	"fmt"
	"os"
	"regexp"
	"sort"
	"strings"
	"unicode"
)

func sagaIdentifier(s string) bool {
	rs := []rune(s)
	if len(rs) == 0 || !isStart(rs[0]) {
		return false
	}
	for _, r := range rs[1:] {
		if !isContinue(r) {
			return false
		}
	}
	return normalizeNFC(s) == s
}
func inferSagaJSONType(v Value) string {
	switch x := v.(type) {
	case OptionValue:
		if !x.Present {
			return "option[any]"
		}
		return "option[" + inferSagaJSONType(x.Value) + "]"
	case bool:
		return "bool"
	case string:
		return "text"
	case Number:
		if x.Kind == "decimal" {
			return "decimal"
		}
		if x.Kind == "int" {
			return "int"
		}
		return "rational"
	case []Value:
		if len(x) == 0 {
			return "list[any]"
		}
		t := inferSagaJSONType(x[0])
		for _, q := range x[1:] {
			if inferSagaJSONType(q) != t {
				return "list[any]"
			}
		}
		return "list[" + t + "]"
	case MapValue:
		return "map[text, any]"
	}
	return "any"
}
func codegenJSON(input, name string) (string, error) {
	b, e := os.ReadFile(input)
	if e != nil {
		return "", e
	}
	v, e := decodeJSONSaga(string(b))
	if e != nil {
		return "", e
	}
	obj, ok := v.(MapValue)
	if !ok {
		return "", fmt.Errorf("top-level JSON must be an object")
	}
	if !sagaIdentifier(name) {
		return "", fmt.Errorf("invalid Saga record name: %s", name)
	}
	fields := map[string]Value{}
	for _, ent := range obj.Entries {
		k, ok := ent.Key.(string)
		if !ok {
			return "", fmt.Errorf("JSON object key is not text")
		}
		if !sagaIdentifier(k) {
			return "", fmt.Errorf("JSON key %q is not a Saga identifier", k)
		}
		fields[k] = ent.Value
	}
	keys := make([]string, 0, len(fields))
	for k := range fields {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	parts := []string{}
	for _, k := range keys {
		parts = append(parts, k+": "+inferSagaJSONType(fields[k]))
	}
	return "record " + name + "(" + strings.Join(parts, ", ") + ")\n", nil
}

var createTableRE = regexp.MustCompile(`(?is)create\s+table\s+([\pL_][\pL\pN_]*)\s*\((.*?)\)\s*;?`)

func sqlTypeToSaga(t string) string {
	u := strings.ToUpper(strings.TrimSpace(strings.Fields(t)[0]))
	switch {
	case strings.Contains(u, "INT"):
		return "int"
	case strings.Contains(u, "REAL") || strings.Contains(u, "FLOAT") || strings.Contains(u, "DOUBLE") || strings.Contains(u, "DECIMAL") || strings.Contains(u, "NUMERIC"):
		return "decimal"
	case strings.Contains(u, "BOOL"):
		return "bool"
	case strings.Contains(u, "BLOB") || strings.Contains(u, "BINARY"):
		return "bytes"
	default:
		return "text"
	}
}
func splitSQLCols(s string) []string {
	out := []string{}
	depth := 0
	start := 0
	for j, r := range s {
		if r == '(' {
			depth++
		}
		if r == ')' {
			depth--
		}
		if r == ',' && depth == 0 {
			out = append(out, s[start:j])
			start = j + 1
		}
	}
	out = append(out, s[start:])
	return out
}
func codegenSQL(input string) (string, error) {
	b, e := os.ReadFile(input)
	if e != nil {
		return "", e
	}
	matches := createTableRE.FindAllStringSubmatch(string(b), -1)
	if len(matches) == 0 {
		return "", fmt.Errorf("no CREATE TABLE statements found")
	}
	var out strings.Builder
	for _, m := range matches {
		name := m[1]
		rs := []rune(name)
		if len(rs) > 0 {
			rs[0] = unicode.ToUpper(rs[0])
		}
		recordName := string(rs)
		parts := []string{}
		for _, raw := range splitSQLCols(m[2]) {
			f := strings.Fields(strings.TrimSpace(raw))
			if len(f) < 2 {
				continue
			}
			kw := strings.ToUpper(f[0])
			if kw == "PRIMARY" || kw == "FOREIGN" || kw == "UNIQUE" || kw == "CHECK" || kw == "CONSTRAINT" {
				continue
			}
			if !sagaIdentifier(f[0]) {
				return "", fmt.Errorf("SQL column %q is not a Saga identifier", f[0])
			}
			parts = append(parts, f[0]+": "+sqlTypeToSaga(f[1]))
		}
		fmt.Fprintf(&out, "record %s(%s)\n", recordName, strings.Join(parts, ", "))
	}
	return out.String(), nil
}
func runCodegen(args []string) int {
	if len(args) < 2 {
		fmt.Fprintln(os.Stderr, "usage: saga codegen <json|sql> input [--name Name] [-o output]")
		return 64
	}
	kind, input := args[0], args[1]
	name := "Generated"
	out := ""
	for j := 2; j < len(args); j++ {
		switch args[j] {
		case "--name":
			if j+1 >= len(args) {
				return 64
			}
			name = args[j+1]
			j++
		case "-o", "--output":
			if j+1 >= len(args) {
				return 64
			}
			out = args[j+1]
			j++
		default:
			fmt.Fprintln(os.Stderr, "unknown codegen option:", args[j])
			return 64
		}
	}
	var text string
	var err error
	if kind == "json" {
		text, err = codegenJSON(input, name)
	} else if kind == "sql" {
		text, err = codegenSQL(input)
	} else {
		fmt.Fprintln(os.Stderr, "codegen kind must be json or sql")
		return 64
	}
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 65
	}
	if out != "" {
		if err = os.WriteFile(out, []byte(text), 0644); err != nil {
			fmt.Fprintln(os.Stderr, err)
			return 74
		}
	} else {
		fmt.Print(text)
	}
	return 0
}
