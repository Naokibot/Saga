//go:build !sagaruntime

package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestDebuggerRecordWatchAndProfiler037(t *testing.T) {
	root := t.TempDir()
	source := filepath.Join(root, "main.saga")
	if err := os.WriteFile(source, []byte("var total: int = 0\nfor i in 1..5 { total = total + i }\nprint(total)\n"), 0644); err != nil {
		t.Fatal(err)
	}
	record := filepath.Join(root, "debug.json")
	if code := runDebugger([]string{source, "--watch", "total", "--record", record, "--max-events", "100"}); code != 0 {
		t.Fatalf("debug exit=%d", code)
	}
	var debug map[string]any
	raw, err := os.ReadFile(record)
	if err != nil {
		t.Fatal(err)
	}
	if err = json.Unmarshal(raw, &debug); err != nil {
		t.Fatal(err)
	}
	if debug["schema"] != "saga.debug-record.v1" || debug["truncated"] != false {
		t.Fatalf("debug report=%v", debug)
	}
	if count, ok := debug["event_count"].(float64); !ok || count < 1 {
		t.Fatalf("debug event count=%v", debug["event_count"])
	}

	profile := filepath.Join(root, "profile.json")
	if code := runProfiler([]string{source, "--json", profile, "--top", "5"}); code != 0 {
		t.Fatalf("profile exit=%d", code)
	}
	var prof map[string]any
	raw, err = os.ReadFile(profile)
	if err != nil {
		t.Fatal(err)
	}
	if err = json.Unmarshal(raw, &prof); err != nil {
		t.Fatal(err)
	}
	if prof["schema"] != "saga.statement-profile.v1" {
		t.Fatalf("profile schema=%v", prof["schema"])
	}
	if events, ok := prof["statement_events"].(float64); !ok || events < 1 {
		t.Fatalf("profile events=%v", prof["statement_events"])
	}
}
