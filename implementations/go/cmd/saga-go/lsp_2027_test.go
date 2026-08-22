package main

import (
	"encoding/json"
	"testing"
)

func TestLSPDiagnostics2CodeAction(t *testing.T) {
	s := &lspServer{}
	raw := json.RawMessage(`{"textDocument":{"uri":"file:///x.saga"},"context":{"diagnostics":[{"code":"SAGA-T170","message":"mixed numeric families","data":{"fixes":[{"title":"Convert explicitly to float64","replacement":"float64(value)"}]}}]}}`)
	actions := s.codeActions(raw)
	if len(actions) < 2 {
		t.Fatalf("expected explain + guided fix actions, got %#v", actions)
	}
	first := actions[0].(map[string]any)
	if first["title"] != "Explain SAGA-T170" {
		t.Fatalf("unexpected action %#v", first)
	}
}
