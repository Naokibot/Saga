package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

const moduleInterfaceSchema = "saga.module-interface.v1"
const moduleInterfaceLanguage = "0.35"

type ModuleInterface struct {
	Schema          string                   `json:"schema"`
	LanguageVersion string                   `json:"language_version"`
	Module          string                   `json:"module"`
	SourceSHA256    string                   `json:"source_sha256"`
	Exports         []map[string]interface{} `json:"exports"`
	Dependencies    []map[string]string      `json:"dependencies"`
	ABISHA256       string                   `json:"abi_sha256"`
	BuildSHA256     string                   `json:"build_sha256"`
}

func hashBytes(b []byte) string {
	h := sha256.Sum256(b)
	return hex.EncodeToString(h[:])
}
func canonicalJSON(v interface{}) ([]byte, error) { return json.Marshal(v) }
func hashCanonical(v interface{}) (string, error) {
	b, err := canonicalJSON(v)
	if err != nil {
		return "", err
	}
	return hashBytes(b), nil
}

func moduleNameFromSource(path string) (string, []Stmt, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return "", nil, err
	}
	toks, err := lex(string(raw), path)
	if err != nil {
		return "", nil, err
	}
	stmts, err := parse(toks)
	if err != nil {
		return "", nil, err
	}
	if len(stmts) == 0 {
		return "", nil, fmt.Errorf("separate compilation requires a leading module directive")
	}
	m, ok := stmts[0].(*ModuleDecl)
	if !ok {
		return "", nil, fmt.Errorf("separate compilation requires exactly one leading module directive: %s", path)
	}
	for _, st := range stmts[1:] {
		if _, dup := st.(*ModuleDecl); dup {
			return "", nil, fmt.Errorf("only one module directive is allowed: %s", path)
		}
	}
	return m.Name, stmts, nil
}

func sourceSHA(path string) (string, error) {
	b, err := os.ReadFile(path)
	if err != nil {
		return "", err
	}
	return hashBytes(b), nil
}

func moduleTypeText(t Type) string {
	if strings.HasPrefix(t.Name, "$") {
		return strings.TrimPrefix(t.Name, "$")
	}
	if t.Name == "fn" {
		parts := []string{}
		for _, a := range t.Args {
			parts = append(parts, moduleTypeText(a))
		}
		ret := "unit"
		if t.Result != nil {
			ret = moduleTypeText(*t.Result)
		}
		parts = append(parts, ret)
		return "fn[" + strings.Join(parts, ",") + "]"
	}
	name := t.Name
	if strings.HasPrefix(name, "object:") {
		name = strings.TrimPrefix(name, "object:")
	}
	if len(t.Args) == 0 {
		return name
	}
	parts := []string{}
	for _, a := range t.Args {
		parts = append(parts, moduleTypeText(a))
	}
	return name + "[" + strings.Join(parts, ",") + "]"
}

func moduleFnExport(name string, info FuncInfo) map[string]interface{} {
	params := []string{}
	for _, p := range info.Params {
		params = append(params, moduleTypeText(p))
	}
	retType := TUnit
	if info.HasRet {
		retType = info.Ret
	}
	if info.Decl != nil && info.Decl.Async {
		retType = futureT(retType)
	}
	ret := moduleTypeText(retType)
	return map[string]interface{}{"kind": "fn", "name": name, "type_params": append([]string{}, info.TypeParams...), "params": params, "return": ret}
}
func moduleClassExport(name string, info *ClassInfo) map[string]interface{} {
	kind := "class"
	if info.Interface {
		kind = "interface"
	}
	fields := []map[string]interface{}{}
	for _, fieldName := range info.OwnFieldOrder {
		f := info.OwnFields[fieldName]
		fields = append(fields, map[string]interface{}{"name": fieldName, "type": moduleTypeText(f.Typ), "mutable": f.Mutable, "private": f.Private})
	}
	methods := []map[string]interface{}{}
	methodNames := make([]string, 0, len(info.OwnMethods))
	for name := range info.OwnMethods {
		methodNames = append(methodNames, name)
	}
	sort.Strings(methodNames)
	for _, methodName := range methodNames {
		f := info.OwnMethods[methodName]
		params := []string{}
		for _, p := range f.Params {
			params = append(params, moduleTypeText(p))
		}
		retType := TUnit
		if f.HasRet {
			retType = f.Ret
		}
		if f.Decl != nil && f.Decl.Async {
			retType = futureT(retType)
		}
		ret := moduleTypeText(retType)
		methods = append(methods, map[string]interface{}{"name": methodName, "params": params, "return": ret, "type_params": append([]string{}, f.TypeParams...), "abstract": f.Abstract})
	}
	var base interface{} = nil
	if info.Decl.Base != nil {
		base = moduleTypeText(info.Base)
	}
	ifaces := []string{}
	for _, x := range info.Interfaces {
		ifaces = append(ifaces, moduleTypeText(x))
	}
	sort.Strings(ifaces)
	return map[string]interface{}{"kind": kind, "name": name, "type_params": append([]string{}, info.TypeParams...), "abstract": info.Abstract, "base": base, "interfaces": ifaces, "fields": fields, "methods": methods}
}

func validateCommonModuleInterfaceSurface(stmts []Stmt) error {
	for _, st := range stmts {
		switch d := st.(type) {
		case *FnDecl:
			if d.Visibility == "public" && (d.Comptime || d.ExternABI != "" || len(d.Constraints) > 0) {
				return fmt.Errorf("public function %s uses a Go-preview-only feature outside Natural Module Core 0.30 common ABI", d.Name)
			}
		case *ClassDecl:
			if d.Visibility != "public" {
				continue
			}
			if d.Record || d.Resource || len(d.Constraints) > 0 || len(d.AssociatedTypes) > 0 || len(d.RequiredAssocTypes) > 0 {
				return fmt.Errorf("public class %s uses a Go-preview-only feature outside Natural Module Core 0.30 common ABI", d.Name)
			}
			for _, m := range d.Methods {
				if m.Comptime || m.ExternABI != "" || len(m.Constraints) > 0 {
					return fmt.Errorf("public method %s.%s uses a Go-preview-only feature outside Natural Module Core 0.30 common ABI", d.Name, m.Name)
				}
			}
		}
	}
	return nil
}

func rejectModuleInterfaceOutput(path string) error {
	if !strings.HasSuffix(path, ".smi.json") {
		return fmt.Errorf("module interface output must end with .smi.json")
	}
	info, err := os.Lstat(path)
	if err == nil && info.Mode()&os.ModeSymlink != 0 {
		return fmt.Errorf("module interface output may not be a symbolic link: %s", path)
	}
	if err != nil && !os.IsNotExist(err) {
		return err
	}
	abs, err := filepath.Abs(path)
	if err != nil {
		return err
	}
	cwd, err := os.Getwd()
	if err != nil {
		return err
	}
	rel, err := filepath.Rel(cwd, abs)
	if err != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
		return nil
	}
	cur := cwd
	for _, part := range strings.Split(rel, string(filepath.Separator)) {
		if part == "" || part == "." {
			continue
		}
		cur = filepath.Join(cur, part)
		info, err := os.Lstat(cur)
		if err != nil {
			if os.IsNotExist(err) {
				continue
			}
			return err
		}
		if info.Mode()&os.ModeSymlink != 0 {
			return fmt.Errorf("module interface output may not contain a symbolic link: %s", cur)
		}
	}
	return nil
}

func buildModuleInterface(source, output string, recursive bool, active map[string]bool) (*ModuleInterface, error) {
	if bad, ok := lexicalSymlinkPath(source); ok {
		return nil, fmt.Errorf("module interface source may not use a symbolic link: %s", bad)
	}
	abs, err := filepath.Abs(source)
	if err != nil {
		return nil, err
	}
	if active == nil {
		active = map[string]bool{}
	}
	if active[abs] {
		return nil, fmt.Errorf("cyclic module interface compilation: %s", abs)
	}
	active[abs] = true
	defer delete(active, abs)
	moduleName, parsed, err := moduleNameFromSource(abs)
	if err != nil {
		return nil, err
	}
	deps := []map[string]string{}
	if recursive {
		for _, st := range parsed {
			u, ok := st.(*UseStmt)
			if !ok || u.SourcePath == "" || len(u.SourcePath) >= 4 && u.SourcePath[:4] == "pkg:" {
				continue
			}
			depPath := filepath.Join(filepath.Dir(abs), filepath.FromSlash(u.SourcePath))
			depName, _, e := moduleNameFromSource(depPath)
			if e != nil {
				continue
			}
			dep, e := buildModuleInterface(depPath, "", true, active)
			if e != nil {
				return nil, e
			}
			deps = append(deps, map[string]string{"module": depName, "abi_sha256": dep.ABISHA256, "source": u.SourcePath})
		}
	}
	sort.Slice(deps, func(i, j int) bool { return deps[i]["module"] < deps[j]["module"] })
	stmts, err := loadProgram(abs)
	if err != nil {
		return nil, err
	}
	if err = validateCommonModuleInterfaceSurface(stmts); err != nil {
		return nil, err
	}
	c := NewChecker()
	if err = c.Check(stmts); err != nil {
		return nil, err
	}
	exports := []map[string]interface{}{}
	for _, st := range stmts {
		switch d := st.(type) {
		case *VarDecl:
			if d.Visibility == "public" {
				if v, ok := c.find(d.Name); ok {
					exports = append(exports, map[string]interface{}{"kind": "var", "name": d.Name, "type": moduleTypeText(v.Typ), "mutable": d.Mutable})
				}
			}
		case *FnDecl:
			if d.Visibility == "public" {
				if f, ok := c.Functions[d.Name]; ok {
					exports = append(exports, moduleFnExport(d.Name, f))
				}
			}
		case *EnumDecl:
			if d.Visibility == "public" {
				variants := []map[string]interface{}{}
				for _, v := range d.Variants {
					payload := []string{}
					for _, r := range v.Payload {
						payload = append(payload, moduleTypeText(typeFromRef(r, map[string]bool{})))
					}
					variants = append(variants, map[string]interface{}{"name": v.Name, "payload": payload})
				}
				exports = append(exports, map[string]interface{}{"kind": "enum", "name": d.Name, "variants": variants})
			}
		case *ClassDecl:
			if d.Visibility == "public" {
				if cl := c.Classes[d.Name]; cl != nil {
					exports = append(exports, moduleClassExport(d.Name, cl))
				}
			}
		}
	}
	sort.Slice(exports, func(i, j int) bool {
		ki := exports[i]["kind"].(string) + "\x00" + exports[i]["name"].(string)
		kj := exports[j]["kind"].(string) + "\x00" + exports[j]["name"].(string)
		return ki < kj
	})
	abiPayload := map[string]interface{}{"schema": moduleInterfaceSchema, "module": moduleName, "exports": exports}
	abi, err := hashCanonical(abiPayload)
	if err != nil {
		return nil, err
	}
	srcHash, err := sourceSHA(abs)
	if err != nil {
		return nil, err
	}
	build, err := hashCanonical(map[string]interface{}{"source_sha256": srcHash, "abi_sha256": abi, "dependencies": deps})
	if err != nil {
		return nil, err
	}
	out := &ModuleInterface{Schema: moduleInterfaceSchema, LanguageVersion: moduleInterfaceLanguage, Module: moduleName, SourceSHA256: srcHash, Exports: exports, Dependencies: deps, ABISHA256: abi, BuildSHA256: build}
	target := output
	if target == "" {
		target = abs[:len(abs)-len(filepath.Ext(abs))] + ".smi.json"
	}
	if err = rejectModuleInterfaceOutput(target); err != nil {
		return nil, err
	}
	b, err := json.Marshal(out)
	if err != nil {
		return nil, err
	}
	b = append(b, '\n')
	if err = writeFileAtomic(target, b, 0644); err != nil {
		return nil, err
	}
	return out, nil
}

func verifyModuleInterface(path, source string) (*ModuleInterface, error) {
	b, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var m ModuleInterface
	if err = json.Unmarshal(b, &m); err != nil {
		return nil, err
	}
	if m.Schema != moduleInterfaceSchema || m.LanguageVersion != moduleInterfaceLanguage {
		return nil, fmt.Errorf("invalid module interface schema or language version")
	}
	abi, err := hashCanonical(map[string]interface{}{"schema": moduleInterfaceSchema, "module": m.Module, "exports": m.Exports})
	if err != nil {
		return nil, err
	}
	if abi != m.ABISHA256 {
		return nil, fmt.Errorf("module interface ABI hash mismatch")
	}
	build, err := hashCanonical(map[string]interface{}{"source_sha256": m.SourceSHA256, "abi_sha256": m.ABISHA256, "dependencies": m.Dependencies})
	if err != nil {
		return nil, err
	}
	if build != m.BuildSHA256 {
		return nil, fmt.Errorf("module interface build hash mismatch")
	}
	if source != "" {
		h, e := sourceSHA(source)
		if e != nil {
			return nil, e
		}
		if h != m.SourceSHA256 {
			return nil, fmt.Errorf("stale module interface")
		}
		for _, dep := range m.Dependencies {
			rel := dep["source"]
			if rel == "" || strings.HasPrefix(rel, "pkg:") {
				continue
			}
			depSource := filepath.Join(filepath.Dir(source), filepath.FromSlash(rel))
			depIface := strings.TrimSuffix(depSource, filepath.Ext(depSource)) + ".smi.json"
			nested, ve := verifyModuleInterface(depIface, depSource)
			if ve != nil {
				return nil, fmt.Errorf("stale dependency interface %s: %w", dep["module"], ve)
			}
			if nested.ABISHA256 != dep["abi_sha256"] {
				return nil, fmt.Errorf("stale dependency ABI for %s", dep["module"])
			}
		}
	}
	return &m, nil
}
