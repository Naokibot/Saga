package main

import "testing"

func TestGoSelfConformanceIncludesRuntimeDiagnostics(t *testing.T) {
	doc := runGoSelfConformance()
	if pass, _ := doc["pass"].(bool); !pass {
		t.Fatalf("self conformance failed: %#v", doc)
	}
	if total, _ := doc["total"].(int); total < 44 {
		t.Fatalf("expected expanded Natural 0.29 corpus, got %d cases", total)
	}
}
