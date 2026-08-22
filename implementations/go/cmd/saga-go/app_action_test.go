package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"regexp"
	"runtime"
	"testing"
)

func TestUniversalAppNativeSystemSnapshot(t *testing.T) {
	raw, err := nativeAppInvoke("system.snapshot", "{}")
	if err != nil {
		t.Fatal(err)
	}
	var v map[string]any
	if err := json.Unmarshal([]byte(raw), &v); err != nil {
		t.Fatal(err)
	}
	if v["platform"] != runtime.GOOS || v["arch"] != runtime.GOARCH {
		t.Fatalf("unexpected snapshot: %v", v)
	}
}

func TestUniversalAppNativeFilesystemRoundTrip(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "nested", "x.txt")
	payload, _ := json.Marshal(map[string]any{"path": path, "text": "Saga 0.23"})
	if _, err := nativeAppInvoke("filesystem.write_text", string(payload)); err != nil {
		t.Fatal(err)
	}
	p2, _ := json.Marshal(map[string]any{"path": path})
	got, err := nativeAppInvoke("filesystem.read_text", string(p2))
	if err != nil {
		t.Fatal(err)
	}
	if got != "Saga 0.23" {
		t.Fatalf("got %q", got)
	}
	if _, err := os.Stat(path); err != nil {
		t.Fatal(err)
	}
}

func TestUniversalAppNativeUUID(t *testing.T) {
	got, err := nativeAppInvoke("crypto.random_uuid", "{}")
	if err != nil {
		t.Fatal(err)
	}
	if !regexp.MustCompile(`^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`).MatchString(got) {
		t.Fatalf("invalid UUID %q", got)
	}
}

func TestUniversalAppNativeRejectsUnknownOperation(t *testing.T) {
	if _, err := nativeAppInvoke("vendor.impossible", "{}"); err == nil {
		t.Fatal("expected unsupported operation error")
	}
}

func TestUniversalAppPayloadMustBeObject(t *testing.T) {
	if _, err := nativeAppInvoke("system.snapshot", "[]"); err == nil {
		t.Fatal("expected object payload error")
	}
}

func TestUniversalAppPayloadRejectsDuplicateKeys(t *testing.T) {
	if _, err := nativeAppInvoke("time.sleep_ms", `{"ms":0,"ms":1}`); err == nil {
		t.Fatal("expected duplicate app payload key to be rejected")
	}
}

func TestUniversalAppReadTextIsBoundedAndUTF8(t *testing.T) {
	dir := t.TempDir()
	tooLarge := filepath.Join(dir, "too-large.txt")
	f, err := os.Create(tooLarge)
	if err != nil {
		t.Fatal(err)
	}
	if _, err = f.Write(make([]byte, sagaHostedMaxTextBytes+1)); err != nil {
		_ = f.Close()
		t.Fatal(err)
	}
	if err = f.Close(); err != nil {
		t.Fatal(err)
	}
	payload, _ := json.Marshal(map[string]any{"path": tooLarge})
	if _, err := nativeAppInvoke("filesystem.read_text", string(payload)); err == nil {
		t.Fatal("oversized text file was accepted")
	}

	invalid := filepath.Join(dir, "invalid.txt")
	if err := os.WriteFile(invalid, []byte{0xff, 0xfe}, 0600); err != nil {
		t.Fatal(err)
	}
	payload, _ = json.Marshal(map[string]any{"path": invalid})
	if _, err := nativeAppInvoke("filesystem.read_text", string(payload)); err == nil {
		t.Fatal("invalid UTF-8 text file was accepted")
	}
}
