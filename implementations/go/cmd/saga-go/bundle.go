package main

import (
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path"
	"path/filepath"
	"sort"
	"strings"
)

// Saga standalone applications are a Saga Native executable plus a canonical
// source payload. The payload format is deliberately language-neutral JSON;
// the footer is fixed-width and versioned so future implementations can read it.
var bundleMagic = [8]byte{'S', 'A', 'G', 'A', 'B', 'N', 'D', '2'}

const bundleFooterSize = 8 + 8 + 32

type bundlePayload struct {
	Schema int               `json:"schema"`
	Kind   string            `json:"kind,omitempty"`
	Entry  string            `json:"entry"`
	Files  map[string]string `json:"files"`
}

func canonicalBundleBytes(p bundlePayload) ([]byte, error) {
	// encoding/json deterministically sorts string map keys. Normalize line
	// endings so the same Saga sources create the same payload on every host.
	clean := map[string]string{}
	keys := make([]string, 0, len(p.Files))
	for k, v := range p.Files {
		keys = append(keys, filepath.ToSlash(k))
		clean[filepath.ToSlash(k)] = strings.ReplaceAll(v, "\r\n", "\n")
	}
	sort.Strings(keys)
	ordered := make(map[string]string, len(clean))
	for _, k := range keys {
		ordered[k] = clean[k]
	}
	p.Files = ordered
	return json.Marshal(p)
}

func readEmbeddedBundle(exe string) (*bundlePayload, error) {
	f, err := os.Open(exe)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	st, err := f.Stat()
	if err != nil {
		return nil, err
	}
	if st.Size() < bundleFooterSize {
		return nil, nil
	}
	footer := make([]byte, bundleFooterSize)
	if _, err = f.ReadAt(footer, st.Size()-bundleFooterSize); err != nil {
		return nil, err
	}
	if string(footer[:8]) != string(bundleMagic[:]) {
		return nil, nil
	}
	n := int64(binary.LittleEndian.Uint64(footer[8:16]))
	if n < 2 || n > st.Size()-bundleFooterSize {
		return nil, errors.New("invalid Saga bundle length")
	}
	payload := make([]byte, n)
	if _, err = f.ReadAt(payload, st.Size()-bundleFooterSize-n); err != nil {
		return nil, err
	}
	want := footer[16:48]
	got := sha256.Sum256(payload)
	if !equalBytes(want, got[:]) {
		return nil, errors.New("Saga standalone bundle payload hash mismatch")
	}
	var p bundlePayload
	if err = json.Unmarshal(payload, &p); err != nil {
		return nil, fmt.Errorf("invalid Saga bundle payload: %w", err)
	}
	if p.Schema != 2 || p.Entry == "" || len(p.Files) == 0 {
		return nil, errors.New("unsupported Saga bundle payload")
	}
	if p.Kind == "" {
		p.Kind = "app"
	}
	if p.Kind != "app" && p.Kind != "compiler" {
		return nil, errors.New("unsupported Saga bundle kind")
	}
	return &p, nil
}
func equalBytes(a, b []byte) bool {
	if len(a) != len(b) {
		return false
	}
	var x byte
	for i := range a {
		x |= a[i] ^ b[i]
	}
	return x == 0
}

// nativeRuntimePrefixSize returns the byte length of the native Saga runtime
// before any embedded Saga bundle. A self-hosted compiler is itself a Saga
// standalone bundle, so the next compiler generation must copy only this
// stable native runtime prefix before appending its new compiler source.
func nativeRuntimePrefixSize(exe string) (int64, error) {
	f, err := os.Open(exe)
	if err != nil {
		return 0, err
	}
	defer f.Close()
	st, err := f.Stat()
	if err != nil {
		return 0, err
	}
	if st.Size() < bundleFooterSize {
		return st.Size(), nil
	}
	footer := make([]byte, bundleFooterSize)
	if _, err = f.ReadAt(footer, st.Size()-bundleFooterSize); err != nil {
		return 0, err
	}
	if string(footer[:8]) != string(bundleMagic[:]) {
		return st.Size(), nil
	}
	n := int64(binary.LittleEndian.Uint64(footer[8:16]))
	if n < 2 || n > st.Size()-bundleFooterSize {
		return 0, errors.New("invalid Saga bundle length")
	}
	return st.Size() - bundleFooterSize - n, nil
}

func normalizeBundlePath(rel string) (string, error) {
	rel = strings.ReplaceAll(rel, "\\", "/")
	if strings.HasPrefix(rel, "/") {
		return "", errors.New("bundle contains absolute path")
	}
	clean := path.Clean(rel)
	if clean == "." || clean == ".." || strings.HasPrefix(clean, "../") {
		return "", errors.New("bundle contains unsafe path")
	}
	return clean, nil
}

func bundlePackageImport(p *bundlePayload, spec string) (string, error) {
	rest := strings.TrimPrefix(spec, "pkg:")
	parts := strings.SplitN(rest, "/", 2)
	if len(parts) != 2 || parts[0] == "" || parts[1] == "" {
		return "", errors.New("invalid pkg import in bundle")
	}
	raw, ok := p.Files["saga.dependencies.json"]
	if !ok {
		return "", errors.New("bundle package import requires saga.dependencies.json")
	}
	var deps dependencyLock
	if err := json.Unmarshal([]byte(raw), &deps); err != nil {
		return "", fmt.Errorf("invalid bundled dependency manifest: %w", err)
	}
	rec, ok := deps.Packages[parts[0]]
	if !ok {
		return "", fmt.Errorf("package not locked in bundle: %s", parts[0])
	}
	return normalizeBundlePath(path.Join(strings.ReplaceAll(rec.Path, "\\", "/"), parts[1]))
}

func loadBundleProgram(p *bundlePayload) ([]Stmt, error) {
	entry, err := normalizeBundlePath(p.Entry)
	if err != nil {
		return nil, err
	}
	seen := map[string]bool{}
	active := map[string]bool{}
	var load func(string) ([]Stmt, error)
	load = func(rel string) ([]Stmt, error) {
		rel, err = normalizeBundlePath(rel)
		if err != nil {
			return nil, err
		}
		if active[rel] {
			return nil, fmt.Errorf("cyclic bundled source import: %s", rel)
		}
		if seen[rel] {
			return nil, nil
		}
		src, ok := p.Files[rel]
		if !ok {
			return nil, fmt.Errorf("bundled source is missing: %s", rel)
		}
		active[rel] = true
		defer delete(active, rel)
		toks, e := lex(src, "bundle://"+rel)
		if e != nil {
			return nil, e
		}
		stmts, e := parse(toks)
		if e != nil {
			return nil, e
		}
		out := []Stmt{}
		for _, s := range stmts {
			if u, ok := s.(*UseStmt); ok && u.SourcePath != "" {
				dep := path.Join(path.Dir(rel), strings.ReplaceAll(u.SourcePath, "\\", "/"))
				if strings.HasPrefix(u.SourcePath, "pkg:") {
					dep, e = bundlePackageImport(p, u.SourcePath)
					if e != nil {
						return nil, e
					}
				}
				xs, er := load(dep)
				if er != nil {
					return nil, er
				}
				out = append(out, xs...)
			}
		}
		for _, s := range stmts {
			if u, ok := s.(*UseStmt); ok && u.SourcePath != "" {
				continue
			}
			out = append(out, s)
		}
		seen[rel] = true
		return out, nil
	}
	return load(entry)
}

func executeBundle(p *bundlePayload) error {
	oldToolchain := sagaToolchainMode
	sagaToolchainMode = p.Kind == "compiler"
	defer func() { sagaToolchainMode = oldToolchain }()
	stmts, err := loadBundleProgram(p)
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

func runSourceFile(path string) error {
	stmts, err := loadProgram(path)
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

func runtimeTemplateExecutable(current string) string {
	if env := strings.TrimSpace(os.Getenv("SAGA_RUNTIME_TEMPLATE")); env != "" {
		if st, err := os.Stat(env); err == nil && !st.IsDir() {
			return env
		}
	}
	dir := filepath.Dir(current)
	names := []string{"saga-runtime", "saga-runtime.exe"}
	for _, n := range names {
		p := filepath.Join(dir, n)
		if st, err := os.Stat(p); err == nil && !st.IsDir() {
			return p
		}
	}
	return current
}

func runtimePrefixDigest(exe string, n int64) (string, error) {
	f, err := os.Open(exe)
	if err != nil {
		return "", err
	}
	defer f.Close()
	h := sha256.New()
	if _, err = io.CopyN(h, f, n); err != nil {
		return "", err
	}
	return hex.EncodeToString(h.Sum(nil)), nil
}
func incrementalCacheKey(payload []byte, runtimeDigest, kind string) string {
	h := sha256.New()
	h.Write([]byte("SagaBuildCacheV2\n" + sagaGoVersion + "\n" + kind + "\n" + runtimeDigest + "\n"))
	h.Write(payload)
	return hex.EncodeToString(h.Sum(nil))
}

type standaloneCacheRecord struct {
	Schema       int    `json:"schema"`
	CacheKey     string `json:"cache_key"`
	OutputSHA256 string `json:"output_sha256"`
}

func canonicalBuildPathIdentity(p string) string {
	abs, err := filepath.Abs(p)
	if err != nil {
		abs = filepath.Clean(p)
	}
	abs = filepath.Clean(abs)
	if real, e := filepath.EvalSymlinks(abs); e == nil {
		return filepath.Clean(real)
	}
	parent := filepath.Dir(abs)
	if realParent, e := filepath.EvalSymlinks(parent); e == nil {
		return filepath.Join(filepath.Clean(realParent), filepath.Base(abs))
	}
	return abs
}

func standaloneOutputConflicts(out, cache, template, root string, files []string) error {
	protected := map[string]string{}
	for _, f := range files {
		protected[canonicalBuildPathIdentity(f)] = f
	}
	for _, f := range []string{filepath.Join(root, "saga.toml"), filepath.Join(root, "saga.dependencies.json"), template} {
		if st, err := os.Stat(f); err == nil && !st.IsDir() {
			protected[canonicalBuildPathIdentity(f)] = f
		}
	}
	for _, candidate := range []struct{ name, path string }{{"build output", out}, {"build cache", cache}} {
		if original, ok := protected[canonicalBuildPathIdentity(candidate.path)]; ok {
			return fmt.Errorf("%s may not overwrite a build input: %s", candidate.name, original)
		}
	}
	return nil
}

func validStandaloneCache(cachePath, outAbs, cacheKey string) bool {
	raw, err := os.ReadFile(cachePath)
	if err != nil {
		return false
	}
	if _, err = decodeJSONSaga(string(raw)); err != nil {
		return false
	}
	var rec standaloneCacheRecord
	if json.Unmarshal(raw, &rec) != nil || rec.Schema != 2 || rec.CacheKey != cacheKey || len(rec.OutputSHA256) != 64 {
		return false
	}
	st, err := os.Stat(outAbs)
	if err != nil || st.IsDir() {
		return false
	}
	actual, _, err := fileDigest(outAbs)
	return err == nil && strings.EqualFold(actual, rec.OutputSHA256)
}

func writeStandaloneCache(cachePath, cacheKey, outAbs string) error {
	digest, _, err := fileDigest(outAbs)
	if err != nil {
		return err
	}
	rec := standaloneCacheRecord{Schema: 2, CacheKey: cacheKey, OutputSHA256: digest}
	b, err := json.Marshal(rec)
	if err != nil {
		return err
	}
	b = append(b, '\n')
	return writeFileAtomic(cachePath, b, 0644)
}
func buildStandalone(input, output string) (string, error) {
	return buildStandaloneKind(input, output, "app")
}

func buildStandaloneKind(input, output, kind string) (string, error) {
	if kind != "app" && kind != "compiler" {
		return "", errors.New("invalid Saga bundle kind")
	}
	inAbs, err := filepath.Abs(input)
	if err != nil {
		return "", err
	}
	st, err := os.Stat(inAbs)
	if err != nil {
		return "", err
	}
	root := filepath.Dir(inAbs)
	entry := filepath.Base(inAbs)
	if st.IsDir() {
		p, e := loadProject(inAbs)
		if e != nil {
			return "", e
		}
		root = p.Root
		inAbs = p.Entry
		rel, e := filepath.Rel(root, p.Entry)
		if e != nil {
			return "", e
		}
		entry = filepath.ToSlash(rel)
	}
	// Validate exactly what will be bundled before producing an executable.
	stmts, e := loadProgram(inAbs)
	if e != nil {
		return "", e
	}
	c := NewChecker()
	if e = c.Check(stmts); e != nil {
		return "", e
	}
	files, e := collectSourceFiles(inAbs, root)
	if e != nil {
		return "", e
	}
	// Include dependency manifest when pkg: imports are present.
	depManifest := filepath.Join(root, "saga.dependencies.json")
	if _, e = os.Stat(depManifest); e == nil {
		files = append(files, depManifest)
	}
	m := map[string]string{}
	for _, f := range files {
		rel, e := filepath.Rel(root, f)
		if e != nil {
			return "", e
		}
		rel = filepath.ToSlash(rel)
		b, e := os.ReadFile(f)
		if e != nil {
			return "", e
		}
		m[rel] = string(b)
	}
	payload, e := canonicalBundleBytes(bundlePayload{Schema: 2, Kind: kind, Entry: entry, Files: m})
	if e != nil {
		return "", e
	}
	exe, e := os.Executable()
	if e != nil {
		return "", e
	}
	// The developer CLI prefers a sibling Saga Runtime template so generated
	// applications do not carry the registry/LSP/debug/codegen tool surface.
	// A self-hosted compiler bundle still falls back to its own stable runtime
	// prefix, preserving the stage-N fixed point.
	template := runtimeTemplateExecutable(exe)
	runtimeSize, e := nativeRuntimePrefixSize(template)
	if e != nil {
		return "", e
	}
	if output == "" {
		output = filepath.Join(filepath.Dir(inAbs), strings.TrimSuffix(filepath.Base(inAbs), filepath.Ext(inAbs)))
		if os.PathSeparator == '\\' {
			output += ".exe"
		}
	}
	outAbs, e := filepath.Abs(output)
	if e != nil {
		return "", e
	}
	runtimeDigest, e := runtimePrefixDigest(template, runtimeSize)
	if e != nil {
		return "", e
	}
	cacheKey := incrementalCacheKey(payload, runtimeDigest, kind)
	cachePath := outAbs + ".saga-cache"
	if e = standaloneOutputConflicts(outAbs, cachePath, template, root, files); e != nil {
		return "", e
	}
	if kind == "app" && validStandaloneCache(cachePath, outAbs, cacheKey) {
		fmt.Println("Incremental build cache: HIT")
		return outAbs, nil
	}
	if e = os.MkdirAll(filepath.Dir(outAbs), 0755); e != nil {
		return "", e
	}
	src, e := os.Open(template)
	if e != nil {
		return "", e
	}
	defer src.Close()
	dst, e := os.CreateTemp(filepath.Dir(outAbs), "."+filepath.Base(outAbs)+"-*.tmp")
	if e != nil {
		return "", e
	}
	tmpOut := dst.Name()
	ok := false
	defer func() {
		_ = dst.Close()
		if !ok {
			_ = os.Remove(tmpOut)
		}
	}()
	if e = dst.Chmod(0755); e != nil && os.PathSeparator != '\\' {
		return "", e
	}
	if _, e = io.CopyN(dst, src, runtimeSize); e != nil {
		return "", e
	}
	if _, e = dst.Write(payload); e != nil {
		return "", e
	}
	footer := make([]byte, bundleFooterSize)
	copy(footer[:8], bundleMagic[:])
	binary.LittleEndian.PutUint64(footer[8:16], uint64(len(payload)))
	h := sha256.Sum256(payload)
	copy(footer[16:48], h[:])
	if _, e = dst.Write(footer); e != nil {
		return "", e
	}
	if e = dst.Sync(); e != nil {
		return "", e
	}
	if e = dst.Close(); e != nil {
		return "", e
	}
	if e = atomicReplacePath(tmpOut, outAbs); e != nil {
		return "", e
	}
	ok = true
	if kind == "app" {
		if e = writeStandaloneCache(cachePath, cacheKey, outAbs); e != nil {
			return "", fmt.Errorf("standalone built but cache metadata could not be committed: %w", e)
		}
	}
	fmt.Println("Standalone payload SHA-256:", hex.EncodeToString(h[:]))
	return outAbs, nil
}
