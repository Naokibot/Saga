package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestCanonicalBundlePayload(t *testing.T) {
	a, err := canonicalBundleBytes(bundlePayload{Schema: 2, Entry: "main.saga", Files: map[string]string{"z.saga": "print(2)\r\n", "main.saga": "print(1)\n"}})
	if err != nil {
		t.Fatal(err)
	}
	b, err := canonicalBundleBytes(bundlePayload{Schema: 2, Entry: "main.saga", Files: map[string]string{"main.saga": "print(1)\n", "z.saga": "print(2)\n"}})
	if err != nil {
		t.Fatal(err)
	}
	if string(a) != string(b) {
		t.Fatalf("bundle payload is not canonical:\n%s\n%s", a, b)
	}
}

func TestBundleRejectsUnsafePath(t *testing.T) {
	p := &bundlePayload{Schema: 2, Entry: "../main.saga", Files: map[string]string{"../main.saga": "print(1)"}}
	if err := executeBundle(p); err == nil {
		t.Fatal("unsafe bundle path was accepted")
	}
}

func TestRunSourceFile(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "main.saga")
	if err := os.WriteFile(path, []byte("let x=1\nprint(x)\n"), 0644); err != nil {
		t.Fatal(err)
	}
	if err := runSourceFile(path); err != nil {
		t.Fatal(err)
	}
}

func TestBuildStandaloneRefusesToOverwriteSource(t *testing.T) {
	dir := t.TempDir()
	source := filepath.Join(dir, "main.saga")
	if err := os.WriteFile(source, []byte("print(42)\n"), 0644); err != nil {
		t.Fatal(err)
	}
	if _, err := buildStandalone(source, source); err == nil {
		t.Fatal("standalone build overwrote its source input")
	}
	got, err := os.ReadFile(source)
	if err != nil || string(got) != "print(42)\n" {
		t.Fatalf("source changed after rejected build: %q err=%v", got, err)
	}
}

func TestBuildStandaloneRefusesToOverwriteRuntimeTemplate(t *testing.T) {
	dir := t.TempDir()
	source := filepath.Join(dir, "main.saga")
	if err := os.WriteFile(source, []byte("print(42)\n"), 0644); err != nil {
		t.Fatal(err)
	}
	current, err := os.Executable()
	if err != nil {
		t.Fatal(err)
	}
	template := filepath.Join(dir, "saga-runtime")
	raw, err := os.ReadFile(current)
	if err != nil {
		t.Fatal(err)
	}
	if err = os.WriteFile(template, raw, 0755); err != nil {
		t.Fatal(err)
	}
	t.Setenv("SAGA_RUNTIME_TEMPLATE", template)
	before, _, err := fileDigest(template)
	if err != nil {
		t.Fatal(err)
	}
	if _, err = buildStandalone(source, template); err == nil {
		t.Fatal("standalone build overwrote its runtime template")
	}
	after, _, err := fileDigest(template)
	if err != nil {
		t.Fatal(err)
	}
	if before != after {
		t.Fatal("runtime template changed after rejected build")
	}
}

func TestBuildStandaloneCacheDetectsTamperedOutput(t *testing.T) {
	dir := t.TempDir()
	source := filepath.Join(dir, "main.saga")
	out := filepath.Join(dir, "app")
	if err := os.WriteFile(source, []byte("print(42)\n"), 0644); err != nil {
		t.Fatal(err)
	}
	if _, err := buildStandalone(source, out); err != nil {
		t.Fatal(err)
	}
	original, _, err := fileDigest(out)
	if err != nil {
		t.Fatal(err)
	}
	f, err := os.OpenFile(out, os.O_WRONLY, 0)
	if err != nil {
		t.Fatal(err)
	}
	if _, err = f.WriteAt([]byte{0}, 0); err != nil {
		_ = f.Close()
		t.Fatal(err)
	}
	_ = f.Close()
	tampered, _, err := fileDigest(out)
	if err != nil || tampered == original {
		t.Fatalf("test failed to tamper output: %v", err)
	}
	if _, err = buildStandalone(source, out); err != nil {
		t.Fatal(err)
	}
	rebuilt, _, err := fileDigest(out)
	if err != nil {
		t.Fatal(err)
	}
	if rebuilt != original {
		t.Fatalf("tampered cached output was not rebuilt: got %s want %s", rebuilt, original)
	}
}

func TestBuildStandaloneRefusesCachePathCollision(t *testing.T) {
	dir := t.TempDir()
	source := filepath.Join(dir, "artifact.saga-cache")
	out := filepath.Join(dir, "artifact")
	if err := os.WriteFile(source, []byte("print(42)\n"), 0644); err != nil {
		t.Fatal(err)
	}
	if _, err := buildStandalone(source, out); err == nil {
		t.Fatal("standalone build cache overwrote a source input")
	}
	got, err := os.ReadFile(source)
	if err != nil || string(got) != "print(42)\n" {
		t.Fatalf("source changed after cache collision: %q err=%v", got, err)
	}
}
