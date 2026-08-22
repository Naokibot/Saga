package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

func lexicalSymlinkPath(path string) (string, bool) {
	if info, err := os.Lstat(path); err == nil && info.Mode()&os.ModeSymlink != 0 {
		return path, true
	}
	abs, err := filepath.Abs(path)
	if err != nil {
		return path, true
	}
	cwd, err := os.Getwd()
	if err != nil {
		return path, true
	}
	rel, err := filepath.Rel(cwd, abs)
	if err != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
		parent := filepath.Dir(path)
		if info, e := os.Lstat(parent); e == nil && info.Mode()&os.ModeSymlink != 0 {
			return parent, true
		}
		return "", false
	}
	cur := cwd
	for _, part := range strings.Split(rel, string(filepath.Separator)) {
		if part == "" || part == "." {
			continue
		}
		cur = filepath.Join(cur, part)
		if info, e := os.Lstat(cur); e == nil && info.Mode()&os.ModeSymlink != 0 {
			return cur, true
		}
	}
	return "", false
}

func hasSymlinkComponent(path, root string) bool {
	ap, err := filepath.Abs(path)
	if err != nil {
		return true
	}
	rr, err := filepath.Abs(root)
	if err != nil {
		return true
	}
	rel, err := filepath.Rel(rr, ap)
	if err != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
		return true
	}
	cur := rr
	for _, part := range strings.Split(rel, string(filepath.Separator)) {
		if part == "" || part == "." {
			continue
		}
		cur = filepath.Join(cur, part)
		fi, e := os.Lstat(cur)
		if e != nil {
			continue
		}
		if fi.Mode()&os.ModeSymlink != 0 {
			return true
		}
	}
	return false
}

type dependencyRecord struct {
	Version string `json:"version"`
	SHA256  string `json:"sha256"`
	Path    string `json:"path"`
}

type dependencyLock struct {
	Packages map[string]dependencyRecord `json:"packages"`
}

func verifyInstalledDependencyArtifact(root, name string, rec dependencyRecord, requiredRel string) error {
	if rec.Version == "" || len(rec.SHA256) != 64 || rec.Path == "" {
		return fmt.Errorf("invalid locked dependency record")
	}
	for _, c := range rec.SHA256 {
		if !strings.ContainsRune("0123456789abcdefABCDEF", c) {
			return fmt.Errorf("invalid locked dependency digest")
		}
	}
	base := filepath.Join(root, filepath.FromSlash(rec.Path))
	baseAbs, err := filepath.Abs(base)
	if err != nil {
		return err
	}
	rootAbs, err := filepath.Abs(root)
	if err != nil {
		return err
	}
	relBase, err := filepath.Rel(rootAbs, baseAbs)
	if err != nil || relBase == ".." || strings.HasPrefix(relBase, ".."+string(filepath.Separator)) {
		return fmt.Errorf("locked dependency path escapes project root")
	}
	if hasSymlinkComponent(baseAbs, rootAbs) {
		return fmt.Errorf("locked dependency path uses a symbolic link")
	}
	lockRaw, err := os.ReadFile(filepath.Join(baseAbs, "saga.lock"))
	if err != nil {
		return fmt.Errorf("installed package lock unavailable: %w", err)
	}
	if _, err = decodeJSONSaga(string(lockRaw)); err != nil {
		return fmt.Errorf("installed package lock is not strict JSON: %w", err)
	}
	var lock LockData
	if err = json.Unmarshal(lockRaw, &lock); err != nil {
		return fmt.Errorf("installed package lock malformed: %w", err)
	}
	if lock.Project.Name != name || lock.Project.Version != rec.Version {
		return fmt.Errorf("installed package lock identity mismatch")
	}
	required := filepath.ToSlash(filepath.Clean(filepath.FromSlash(requiredRel)))
	tracked := false
	for _, f := range lock.Files {
		if f.Path == required {
			tracked = true
			break
		}
	}
	if !tracked {
		return fmt.Errorf("package import is not tracked by saga.lock: %s", required)
	}
	ok, errs, err := verifyLock(baseAbs)
	if err != nil {
		return fmt.Errorf("installed package lock verification failed: %w", err)
	}
	if !ok {
		return fmt.Errorf("installed package lock verification failed: %s", strings.Join(errs, "; "))
	}
	tmp, err := os.CreateTemp("", "saga-dependency-*.sagapkg")
	if err != nil {
		return err
	}
	tmpPath := tmp.Name()
	if err = tmp.Close(); err != nil {
		_ = os.Remove(tmpPath)
		return err
	}
	_ = os.Remove(tmpPath)
	defer os.Remove(tmpPath)
	if _, err = packProject(baseAbs, tmpPath); err != nil {
		return fmt.Errorf("cannot reconstruct installed package artifact: %w", err)
	}
	actual, _, err := fileDigest(tmpPath)
	if err != nil {
		return err
	}
	if !strings.EqualFold(actual, rec.SHA256) {
		return fmt.Errorf("installed package no longer matches the locked registry artifact")
	}
	return nil
}

func resolvePackageImport(root, spec string) (string, error) {
	rest := strings.TrimPrefix(spec, "pkg:")
	parts := strings.SplitN(rest, "/", 2)
	if len(parts) != 2 || parts[0] == "" || parts[1] == "" {
		return "", &SagaError{Code: "SAGA-I001", ID: "SAGA-I120", Message: "pkg import must be pkg:name/path.saga", File: spec, Line: 1, Col: 1}
	}
	raw, e := os.ReadFile(filepath.Join(root, "saga.dependencies.json"))
	if e != nil {
		return "", e
	}
	if _, e = decodeJSONSaga(string(raw)); e != nil {
		return "", &SagaError{Code: "SAGA-I001", ID: "SAGA-I121", Message: "dependency lock is not strict JSON: " + e.Error(), File: spec, Line: 1, Col: 1}
	}
	var lock dependencyLock
	if e = json.Unmarshal(raw, &lock); e != nil {
		return "", e
	}
	rec, ok := lock.Packages[parts[0]]
	if !ok {
		return "", &SagaError{Code: "SAGA-I001", ID: "SAGA-I121", Message: "package not locked: " + parts[0], File: spec, Line: 1, Col: 1}
	}
	base := filepath.Join(root, filepath.FromSlash(rec.Path))
	target := filepath.Join(base, filepath.FromSlash(parts[1]))
	rel, e := filepath.Rel(base, target)
	if e != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
		return "", &SagaError{Code: "SAGA-I001", ID: "SAGA-I122", Message: "package import escapes package root", File: spec, Line: 1, Col: 1}
	}
	if e = verifyInstalledDependencyArtifact(root, parts[0], rec, filepath.ToSlash(parts[1])); e != nil {
		return "", &SagaError{Code: "SAGA-I001", ID: "SAGA-I123", Message: "package integrity verification failed: " + e.Error(), File: spec, Line: 1, Col: 1}
	}
	return target, nil
}
func sourceProjectRoot(entryAbs string) (string, error) {
	start := filepath.Dir(entryAbs)
	current := start
	for {
		manifest := filepath.Join(current, "saga.toml")
		if info, err := os.Lstat(manifest); err == nil {
			if info.Mode()&os.ModeSymlink != 0 {
				return "", &SagaError{Code: "SAGA-I001", ID: "SAGA-I112", Message: "project manifest may not be a symbolic link: " + manifest, File: manifest, Line: 1, Col: 1}
			}
			if !info.IsDir() {
				project, e := loadProject(manifest)
				if e != nil {
					return "", e
				}
				return project.Root, nil
			}
		} else if !os.IsNotExist(err) {
			return "", err
		}
		parent := filepath.Dir(current)
		if parent == current {
			return start, nil
		}
		current = parent
	}
}

func loadProgram(entry string) ([]Stmt, error) {
	abs, err := filepath.Abs(entry)
	if err != nil {
		return nil, err
	}
	root, err := sourceProjectRoot(abs)
	if err != nil {
		return nil, err
	}
	seen := map[string]bool{}
	active := map[string]bool{}
	moduleBindings := map[string]string{}
	moduleNames := map[string]string{}
	var load func(string, bool, string) ([]Stmt, error)
	load = func(path string, imported bool, requestedAlias string) ([]Stmt, error) {
		ap, err := filepath.Abs(path)
		if err != nil {
			return nil, err
		}
		if hasSymlinkComponent(ap, root) {
			return nil, &SagaError{Code: "SAGA-I001", ID: "SAGA-I112", Message: "source path uses a symbolic link: " + path, File: path, Line: 1, Col: 1}
		}
		if rp, e := filepath.EvalSymlinks(ap); e == nil {
			ap = rp
		}
		rel, err := filepath.Rel(root, ap)
		if err != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
			return nil, &SagaError{Code: "SAGA-I001", ID: "SAGA-I110", Message: "source import escapes project root: " + path, File: path, Line: 1, Col: 1}
		}
		if active[ap] {
			return nil, &SagaError{Code: "SAGA-I001", ID: "SAGA-I111", Message: "cyclic source import: " + path, File: path, Line: 1, Col: 1}
		}
		// Edition 1.0 legacy includes are idempotently flattened. Edition 2027
		// modules are also loaded once: importing the same module twice through
		// different aliases is intentionally rejected by the duplicate-binding
		// checker rather than duplicating module state.
		if seen[ap] {
			if imported {
				previous := moduleBindings[ap]
				requested := requestedAlias
				if requested == "" {
					requested = moduleNames[ap]
				}
				if previous != "" && requested != "" && previous != requested {
					return nil, &SagaError{Code: "SAGA-P001", ID: "SAGA-P109", Message: "same module cannot be imported with multiple aliases: " + previous + " and " + requested, File: path, Line: 1, Col: 1}
				}
			}
			return nil, nil
		}
		active[ap] = true
		defer delete(active, ap)
		raw, err := os.ReadFile(ap)
		if err != nil {
			return nil, err
		}
		if !validUTF8String(string(raw)) {
			return nil, &SagaError{Code: "SAGA-L001", ID: "SAGA-L104", Message: "source must be UTF-8", File: ap, Line: 1, Col: 1}
		}
		toks, err := lex(string(raw), ap)
		if err != nil {
			return nil, err
		}
		stmts, err := parse(toks)
		if err != nil {
			return nil, err
		}
		moduleName := ""
		var moduleTok Token
		for _, s := range stmts {
			if m, ok := s.(*ModuleDecl); ok {
				if moduleName != "" {
					return nil, &SagaError{Code: "SAGA-P001", ID: "SAGA-P102", Message: "only one module directive is allowed per source file", File: ap, Line: m.Tok.Line, Col: m.Tok.Col}
				}
				moduleName, moduleTok = m.Name, m.Tok
			}
		}
		out := []Stmt{}
		for _, s := range stmts {
			if u, ok := s.(*UseStmt); ok && u.SourcePath != "" {
				dep := filepath.Join(filepath.Dir(ap), filepath.FromSlash(u.SourcePath))
				if strings.HasPrefix(u.SourcePath, "pkg:") {
					dep, err = resolvePackageImport(root, u.SourcePath)
					if err != nil {
						return nil, err
					}
				}
				xs, e := load(dep, true, u.Alias)
				if e != nil {
					return nil, e
				}
				out = append(out, xs...)
			}
		}
		for _, s := range stmts {
			if _, ok := s.(*ModuleDecl); ok {
				continue
			}
			if u, ok := s.(*UseStmt); ok && u.SourcePath != "" {
				continue
			}
			out = append(out, s)
		}
		seen[ap] = true
		if imported && moduleName != "" {
			bind := requestedAlias
			if bind == "" {
				bind = moduleName
			}
			moduleBindings[ap] = bind
			moduleNames[ap] = moduleName
			var iface *ModuleInterface
			ifacePath := strings.TrimSuffix(ap, filepath.Ext(ap)) + ".smi.json"
			if _, statErr := os.Stat(ifacePath); statErr == nil {
				if v, verifyErr := verifyModuleInterface(ifacePath, ap); verifyErr == nil {
					iface = v
				}
			}
			return []Stmt{&SourceModuleStmt{Name: moduleName, BindName: bind, Stmts: out, Tok: moduleTok, Interface: iface}}, nil
		}
		if !imported && moduleName != "" {
			out = append([]Stmt{&ModuleDecl{Name: moduleName, Tok: moduleTok}}, out...)
		}
		return out, nil
	}
	return load(abs, false, "")
}

func validateStandardCoreUse(stmts []Stmt) error {
	for _, s := range stmts {
		if u, ok := s.(*UseStmt); ok && u.Module != "" && u.Module != "task" {
			return fmt.Errorf("hosted module %s is not Standard Core", u.Module)
		}
	}
	return nil
}
