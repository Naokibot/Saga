package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"strings"
)

type diagnosticFix struct {
	Title       string `json:"title"`
	Replacement string `json:"replacement,omitempty"`
}

type diagnosticAdvice struct {
	Summary string          `json:"summary,omitempty"`
	Notes   []string        `json:"notes,omitempty"`
	Fixes   []diagnosticFix `json:"fixes,omitempty"`
}

// diagnosticGuidance is deliberately keyed by stable diagnostic identity and
// semantic message fragments, not localized presentation text. This keeps the
// JSON/LSP contract stable while allowing beginner-oriented explanations to
// improve without changing compiler semantics.
func diagnosticGuidance(e *SagaError) diagnosticAdvice {
	a := diagnosticAdvice{}
	switch e.ID {
	case "SAGA-T170":
		a.Summary = "exact numbers and binary floating-point values are intentionally kept separate"
		a.Notes = []string{"Use decimal/rational when exact arithmetic matters; use float32/float64 for graphics, scientific or native floating-point work."}
		a.Fixes = []diagnosticFix{{Title: "Convert explicitly to float64", Replacement: "float64(value)"}, {Title: "Keep the operation exact", Replacement: "decimal(value)"}}
	case "SAGA-T172":
		a.Summary = "a generic argument does not provide every capability required by its where-clause"
		a.Notes = []string{"Read the constraint after `where`; either pass a type that satisfies it or change the generic contract."}
	case "SAGA-T173":
		a.Summary = "an associated type could not be resolved from the selected concrete type"
		a.Notes = []string{"Implement the required associated type with `type Name = ConcreteType` on the conforming class."}
	case "SAGA-T175":
		a.Summary = "await can only consume a future"
		a.Fixes = []diagnosticFix{{Title: "Await an async call", Replacement: "await async_function()"}}
	case "SAGA-T176":
		a.Summary = "move is reserved for resource values with explicit lifetime semantics"
	case "SAGA-T177":
		a.Summary = "the ? operator returns early on none/err, so the containing function must return a compatible option/result"
	case "SAGA-T178":
		a.Summary = "foreign calls cross Saga's safety boundary"
		a.Fixes = []diagnosticFix{{Title: "Make the boundary visible", Replacement: "unsafe { foreign_call(...) }"}}
	case "SAGA-R181":
		a.Summary = "this resource was already moved and cannot be used through its old binding"
		a.Notes = []string{"Use the destination binding after move, or avoid moving the resource until its final owner is known."}
	}
	msg := strings.ToLower(e.Message)
	if strings.Contains(msg, "argument type mismatch") || strings.Contains(msg, "cannot assign") {
		if a.Summary == "" {
			a.Summary = "the value's type does not match the type required at this location"
		}
		a.Notes = append(a.Notes, "Saga does not silently perform lossy or ambiguous conversions. Convert explicitly or change the declared type.")
	}
	if strings.Contains(msg, "unknown variable") || strings.Contains(msg, "unknown name") {
		a.Notes = append(a.Notes, "Check spelling and imports/module qualification. `saga lsp` can provide completion and symbol lookup.")
	}
	return a
}

func sourceDiagnosticLine(file string, line int) string {
	if file == "" || line <= 0 {
		return ""
	}
	f, err := os.Open(file)
	if err != nil {
		return ""
	}
	defer f.Close()
	s := bufio.NewScanner(f)
	for i := 1; s.Scan(); i++ {
		if i == line {
			return s.Text()
		}
	}
	return ""
}

func printDiagnostic(err error) int {
	if e, ok := err.(*SagaError); ok {
		advice := diagnosticGuidance(e)
		if sagaDiagnosticFormat == "json" {
			data := map[string]any{
				"schema":                      "saga.diagnostic.v2",
				"code":                        e.Code,
				"id":                          e.ID,
				"message":                     e.Message,
				"file":                        e.File,
				"line":                        e.Line,
				"column":                      e.Col,
				"primary":                     true,
				"summary":                     advice.Summary,
				"notes":                       advice.Notes,
				"fixes":                       advice.Fixes,
				"suppressed_dependent_errors": 0,
			}
			b, _ := json.Marshal(data)
			fmt.Fprintln(os.Stderr, string(b))
		} else {
			fmt.Fprintf(os.Stderr, "error[%s]: %s\n", e.ID, localizedMessage(e))
			if e.File != "" && e.Line > 0 {
				fmt.Fprintf(os.Stderr, "  --> %s:%d:%d\n", e.File, e.Line, e.Col)
				if line := sourceDiagnosticLine(e.File, e.Line); line != "" {
					fmt.Fprintf(os.Stderr, "%4d | %s\n", e.Line, line)
					col := e.Col
					if col < 1 {
						col = 1
					}
					fmt.Fprintf(os.Stderr, "     | %s^\n", strings.Repeat(" ", col-1))
				}
			}
			if advice.Summary != "" {
				fmt.Fprintf(os.Stderr, "  why: %s\n", advice.Summary)
			}
			for _, note := range advice.Notes {
				fmt.Fprintf(os.Stderr, "  note: %s\n", note)
			}
			for _, fix := range advice.Fixes {
				if fix.Replacement == "" {
					fmt.Fprintf(os.Stderr, "  fix: %s\n", fix.Title)
				} else {
					fmt.Fprintf(os.Stderr, "  fix: %s -> %s\n", fix.Title, fix.Replacement)
				}
			}
			if _, ok := diagnosticLessons[e.ID]; ok {
				fmt.Fprintf(os.Stderr, "  help: saga explain %s\n", e.ID)
			}
		}
		switch e.Code {
		case "SAGA-L001":
			return 2
		case "SAGA-P001":
			return 3
		case "SAGA-T001":
			return 4
		case "SAGA-R001":
			return 5
		default:
			return 70
		}
	}
	fmt.Fprintln(os.Stderr, err)
	return 70
}
