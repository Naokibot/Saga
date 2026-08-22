package main

import (
	"path/filepath"
	"testing"
)

func TestCustomPrefixOwnsLaunchers(t *testing.T) {
	p := filepath.Join("tmp", "custom-saga")
	if got, want := launcherDir(p, true), filepath.Join(p, "bin"); got != want {
		t.Fatalf("got %q want %q", got, want)
	}
}
func TestPayloadName(t *testing.T) {
	if payloadName() == "" {
		t.Fatal("empty payload name")
	}
}

func TestReleaseVersion(t *testing.T) {
	if got, want := version, "0.35.0"; got != want {
		t.Fatalf("installer version %q does not match release %q", got, want)
	}
}
