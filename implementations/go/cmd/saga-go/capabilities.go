//go:build !sagaruntime

package main

import (
	"encoding/json"
	"fmt"
	"os"
	"sort"
)

type capabilityReport struct {
	Schema       int      `json:"schema"`
	Entry        string   `json:"entry"`
	Modules      []string `json:"modules"`
	Capabilities []string `json:"capabilities"`
	Policy       string   `json:"policy"`
}

var moduleCapability = map[string][]string{
	"io":       {"filesystem"},
	"net":      {"network"},
	"http":     {"network"},
	"security": {"filesystem", "network", "cryptography"},
	"crypto":   {"cryptography"},
	"db":       {"database", "filesystem"},
	"process":  {"process"},
	"game":     {"audio", "filesystem", "gamepad", "gpu", "graphics", "input", "terminal"},
	"task":     {"concurrency"},
	"compiler": {"build"},
	"machine":  {"device", "network", "realtime-control"},
	"drone":    {"device", "network", "realtime-control"},
}

func analyzeCapabilities(entry string) (capabilityReport, error) {
	stmts, err := loadProgram(entry)
	if err != nil {
		return capabilityReport{}, err
	}
	mods := map[string]bool{}
	caps := map[string]bool{}
	for _, s := range stmts {
		if u, ok := s.(*UseStmt); ok && u.Module != "" {
			mods[u.Module] = true
			for _, cap := range moduleCapability[u.Module] {
				caps[cap] = true
			}
		}
	}
	ml := make([]string, 0, len(mods))
	for m := range mods {
		ml = append(ml, m)
	}
	sort.Strings(ml)
	cl := make([]string, 0, len(caps))
	for c := range caps {
		cl = append(cl, c)
	}
	sort.Strings(cl)
	return capabilityReport{Schema: 1, Entry: entry, Modules: ml, Capabilities: cl, Policy: "explicit-module-imports"}, nil
}

func runCapabilities(args []string) int {
	if len(args) == 0 {
		fmt.Fprintln(os.Stderr, "source file required")
		return 64
	}
	asJSON := false
	for _, a := range args[1:] {
		if a == "--json" {
			asJSON = true
		} else {
			fmt.Fprintln(os.Stderr, "unknown capabilities option:", a)
			return 64
		}
	}
	r, err := analyzeCapabilities(args[0])
	if err != nil {
		return printDiagnostic(err)
	}
	if asJSON {
		b, _ := json.Marshal(r)
		fmt.Println(string(b))
		return 0
	}
	fmt.Println("modules:", r.Modules)
	fmt.Println("capabilities:", r.Capabilities)
	fmt.Println("policy:", r.Policy)
	return 0
}
