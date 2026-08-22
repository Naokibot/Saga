package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestFormatSagaSourceIsIdempotent(t *testing.T) {
	input := "fn add(a:int,b:int)->int{\nreturn a+b   \n}\n\n"
	once := formatSagaSource(input)
	twice := formatSagaSource(once)
	if once != twice {
		t.Fatalf("formatter is not idempotent\nfirst=%q\nsecond=%q", once, twice)
	}
	want := "fn add(a:int,b:int)->int{\n    return a+b\n}\n"
	if once != want {
		t.Fatalf("unexpected format: %q", once)
	}
}

func TestLintDetectsPublicAny(t *testing.T) {
	toks, err := lex("fn pass(value:any)->any = value", "<lint>")
	if err != nil {
		t.Fatal(err)
	}
	stmts, err := parse(toks)
	if err != nil {
		t.Fatal(err)
	}
	warnings := lintStatements(stmts)
	if len(warnings) != 2 {
		t.Fatalf("expected parameter and return warnings, got %v", warnings)
	}
}

func TestCodegenJSONUsesStrictSagaJSON(t *testing.T) {
	d := t.TempDir()
	p := filepath.Join(d, "sample.json")
	if err := os.WriteFile(p, []byte(`{"a":1,"a":2}`), 0644); err != nil {
		t.Fatal(err)
	}
	if _, err := codegenJSON(p, "Sample"); err == nil {
		t.Fatal("codegen accepted duplicate JSON object keys")
	}
	if err := os.WriteFile(p, []byte(`{"a":1} trailing`), 0644); err != nil {
		t.Fatal(err)
	}
	if _, err := codegenJSON(p, "Sample"); err == nil {
		t.Fatal("codegen accepted trailing JSON content")
	}
}
