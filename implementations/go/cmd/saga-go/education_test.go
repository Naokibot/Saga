package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestCreateProjectLevelsCompile(t *testing.T) {
	for _, level := range []string{"beginner", "standard", "advanced"} {
		root := filepath.Join(t.TempDir(), "project")
		if err := createProject(root, level); err != nil {
			t.Fatalf("%s: %v", level, err)
		}
		stmts, err := loadProgram(filepath.Join(root, "main.saga"))
		if err != nil {
			t.Fatalf("%s parse: %v", level, err)
		}
		c := NewChecker()
		if err := c.Check(stmts); err != nil {
			t.Fatalf("%s check: %v", level, err)
		}
	}
}

func TestCompilerAuthorityIsFailClosed(t *testing.T) {
	old := sagaToolchainMode
	sagaToolchainMode = false
	defer func() { sagaToolchainMode = old }()
	toks, err := lex("use compiler\ncompiler.build(\"missing.saga\",\"out\")", "<test>")
	if err != nil {
		t.Fatal(err)
	}
	stmts, err := parse(toks)
	if err != nil {
		t.Fatal(err)
	}
	c := NewChecker()
	if err = c.Check(stmts); err != nil {
		t.Fatal(err)
	}
	it := NewInterpreter(c, nil)
	err = it.Interpret(stmts)
	se, ok := err.(*SagaError)
	if !ok || se.ID != "SAGA-R103" {
		t.Fatalf("expected SAGA-R103, got %#v", err)
	}
}

func TestNativeRuntimePrefixSizeOnSyntheticBundle(t *testing.T) {
	root := t.TempDir()
	path := filepath.Join(root, "runtime")
	runtimeBytes := []byte("NATIVE-RUNTIME")
	payload, err := canonicalBundleBytes(bundlePayload{Schema: 2, Kind: "compiler", Entry: "sagac.saga", Files: map[string]string{"sagac.saga": "print(1)\n"}})
	if err != nil {
		t.Fatal(err)
	}
	footer := make([]byte, bundleFooterSize)
	copy(footer[:8], bundleMagic[:])
	// construct using same layout helper logic without importing encoding here via helper file
	if err := writeSyntheticBundle(path, runtimeBytes, payload, footer); err != nil {
		t.Fatal(err)
	}
	n, err := nativeRuntimePrefixSize(path)
	if err != nil {
		t.Fatal(err)
	}
	if n != int64(len(runtimeBytes)) {
		t.Fatalf("prefix=%d want=%d", n, len(runtimeBytes))
	}
	_ = os.Remove(path)
}
