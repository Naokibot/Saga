//go:build !sagaruntime

package main

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func TestPythonTranspilePreservesNegativeRemainderSemantics(t *testing.T) {
	py, err := exec.LookPath("python3")
	if err != nil {
		py, err = exec.LookPath("python")
	}
	if err != nil {
		t.Skip("Python unavailable")
	}
	dir := t.TempDir()
	src := filepath.Join(dir, "main.saga")
	if err = os.WriteFile(src, []byte("print(-2 % 7, 7 % -3, -7 % -3)\n"), 0644); err != nil {
		t.Fatal(err)
	}
	generated, err := transpilePython(src)
	if err != nil {
		t.Fatal(err)
	}
	outPath := filepath.Join(dir, "program.py")
	if err = os.WriteFile(outPath, []byte(generated), 0644); err != nil {
		t.Fatal(err)
	}
	out, err := exec.Command(py, outPath).CombinedOutput()
	if err != nil {
		t.Fatalf("generated Python failed: %v\n%s", err, out)
	}
	if got := strings.TrimSpace(string(out)); got != "-2 1 -1" {
		t.Fatalf("negative remainder mismatch: %q", got)
	}
}
