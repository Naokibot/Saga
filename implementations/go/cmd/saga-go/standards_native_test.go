//go:build !sagaruntime

package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestNativeStandardsRegistryEvidenceAndChain(t *testing.T) {
	root := filepath.Join(t.TempDir(), "registry")
	r, err := openStandardsRegistry(root)
	if err != nil {
		t.Fatal(err)
	}
	if err = r.init("Saga Programming Language"); err != nil {
		t.Fatal(err)
	}
	ev := filepath.Join(t.TempDir(), "evidence.txt")
	if err = os.WriteFile(ev, []byte("independent evidence\n"), 0644); err != nil {
		t.Fatal(err)
	}
	opts := map[string][]string{"--name": {"Example Standards Body"}, "--type": {"national_body"}, "--country": {"JP"}, "--evidence": {ev}}
	if err = r.record("set-proposer", opts); err != nil {
		t.Fatal(err)
	}
	chain, _, err := r.verifyChain()
	if err != nil || !chain {
		t.Fatalf("chain: %v %v", chain, err)
	}
	evidence, bad, err := r.verifyEvidence()
	if err != nil || !evidence || len(bad) != 0 {
		t.Fatalf("evidence: %v %v %v", evidence, bad, err)
	}
	st, err := r.status()
	if err != nil {
		t.Fatal(err)
	}
	criteria := st["pre_submission_evidence"].(map[string]bool)
	if !criteria["eligible_proposer"] {
		t.Fatal("proposer criterion should be true")
	}
	if st["pre_submission_evidence_complete"].(bool) {
		t.Fatal("must not report pre-submission evidence complete with only proposer evidence")
	}
	// Tamper evidence and require verification to fail.
	reg, _ := r.load()
	prop := obj(reg["proposer"])
	stored := obj(prop["evidence"])
	p := filepath.Join(root, filepath.FromSlash(str(stored["stored"])))
	if err = os.WriteFile(p, []byte("tampered"), 0644); err != nil {
		t.Fatal(err)
	}
	evidence, bad, err = r.verifyEvidence()
	if err != nil || evidence || len(bad) == 0 {
		t.Fatalf("tamper not detected: %v %v %v", evidence, bad, err)
	}
}

func TestStandardsRecordSubcommandParsing(t *testing.T) {
	root, action, opts, err := parseStandardsArgs([]string{"--root", "/tmp/registry", "record", "set-proposer", "--name", "Body"})
	if err != nil {
		t.Fatal(err)
	}
	if root != "/tmp/registry" || action != "set-proposer" || opts["--name"][0] != "Body" {
		t.Fatalf("unexpected parse: %q %q %#v", root, action, opts)
	}
}

func TestStandardsNPParticipationThreshold(t *testing.T) {
	root := filepath.Join(t.TempDir(), "registry")
	r, err := openStandardsRegistry(root)
	if err != nil {
		t.Fatal(err)
	}
	if err = r.init("Saga"); err != nil {
		t.Fatal(err)
	}
	ev := filepath.Join(t.TempDir(), "committee.txt")
	if err = os.WriteFile(ev, []byte("committee evidence"), 0644); err != nil {
		t.Fatal(err)
	}
	if err = r.record("set-committee", map[string][]string{"--name": {"Example TC"}, "--p-members": {"16"}, "--evidence": {ev}}); err != nil {
		t.Fatal(err)
	}
	st, err := r.status()
	if err != nil {
		t.Fatal(err)
	}
	np := st["np_acceptance_evidence"].(map[string]any)
	if intFromAny(np["required_active_p_members"]) != 4 {
		t.Fatalf("expected 4 for <=16 P-members: %#v", np)
	}
	if err = r.record("set-committee", map[string][]string{"--name": {"Example TC"}, "--p-members": {"17"}, "--evidence": {ev}}); err != nil {
		t.Fatal(err)
	}
	st, err = r.status()
	if err != nil {
		t.Fatal(err)
	}
	np = st["np_acceptance_evidence"].(map[string]any)
	if intFromAny(np["required_active_p_members"]) != 5 {
		t.Fatalf("expected 5 for >=17 P-members: %#v", np)
	}
}
