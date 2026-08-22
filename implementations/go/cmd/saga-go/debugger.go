//go:build !sagaruntime

package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"sort"
	"strconv"
	"strings"
	"time"
)

func debugEnvSnapshot(e *Env) map[string]string {
	out := map[string]string{}
	if e == nil {
		return out
	}
	chain := []*Env{}
	for current := e; current != nil; current = current.Parent {
		chain = append(chain, current)
	}
	// Outer scopes are applied first so inner lexical bindings shadow them.
	for i := len(chain) - 1; i >= 0; i-- {
		for name, cell := range chain[i].Values {
			if cell == nil {
				continue
			}
			switch cell.V.(type) {
			case *NativeFunc, CoreModule, *Class, *Function:
				continue
			}
			if cell.Moved {
				out[name] = "<moved>"
			} else {
				out[name] = formatValue(cell.V, false)
			}
		}
	}
	return out
}

func debugEnvSummary(e *Env) string {
	values := debugEnvSnapshot(e)
	keys := make([]string, 0, len(values))
	for k := range values {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	parts := make([]string, 0, len(keys))
	for _, k := range keys {
		parts = append(parts, k+"="+values[k])
	}
	return "{" + strings.Join(parts, ", ") + "}"
}

func writeJSONAtomic(path string, payload any) error {
	if path == "" {
		return nil
	}
	abs, err := filepath.Abs(path)
	if err != nil {
		return err
	}
	if err = os.MkdirAll(filepath.Dir(abs), 0755); err != nil {
		return err
	}
	f, err := os.CreateTemp(filepath.Dir(abs), "."+filepath.Base(abs)+".*.tmp")
	if err != nil {
		return err
	}
	tmp := f.Name()
	committed := false
	defer func() {
		_ = f.Close()
		if !committed {
			_ = os.Remove(tmp)
		}
	}()
	enc := json.NewEncoder(f)
	enc.SetIndent("", "  ")
	enc.SetEscapeHTML(false)
	if err = enc.Encode(payload); err != nil {
		return err
	}
	if err = f.Sync(); err != nil {
		return err
	}
	if err = f.Close(); err != nil {
		return err
	}
	if err = atomicReplacePath(tmp, abs); err != nil {
		return err
	}
	committed = true
	return nil
}

func runDebugger(args []string) int {
	if len(args) < 1 {
		fmt.Fprintln(os.Stderr, "source file required")
		return 64
	}
	path := args[0]
	breaks := map[int]bool{}
	trace := false
	watches := []string{}
	recordPath := ""
	maxEvents := 100000
	for j := 1; j < len(args); j++ {
		switch args[j] {
		case "--trace":
			trace = true
		case "--break":
			if j+1 >= len(args) {
				fmt.Fprintln(os.Stderr, "--break requires line")
				return 64
			}
			n, e := strconv.Atoi(args[j+1])
			if e != nil || n < 1 {
				fmt.Fprintln(os.Stderr, "invalid breakpoint")
				return 64
			}
			breaks[n] = true
			j++
		case "--watch":
			if j+1 >= len(args) || strings.TrimSpace(args[j+1]) == "" {
				fmt.Fprintln(os.Stderr, "--watch requires name")
				return 64
			}
			watches = append(watches, args[j+1])
			j++
		case "--record":
			if j+1 >= len(args) {
				fmt.Fprintln(os.Stderr, "--record requires path")
				return 64
			}
			recordPath = args[j+1]
			j++
		case "--max-events":
			if j+1 >= len(args) {
				fmt.Fprintln(os.Stderr, "--max-events requires integer")
				return 64
			}
			n, e := strconv.Atoi(args[j+1])
			if e != nil || n < 1 || n > 1000000 {
				fmt.Fprintln(os.Stderr, "--max-events must be 1..1000000")
				return 64
			}
			maxEvents = n
			j++
		default:
			fmt.Fprintln(os.Stderr, "unknown debug option:", args[j])
			return 64
		}
	}
	stmts, err := loadProgram(path)
	if err != nil {
		return printDiagnostic(err)
	}
	c := NewChecker()
	if err = c.Check(stmts); err != nil {
		return printDiagnostic(err)
	}
	it := NewInterpreter(c, nil)
	events := []map[string]any{}
	truncated := false
	it.DebugHook = func(t Token, e *Env) {
		values := debugEnvSnapshot(e)
		isBreak := breaks[t.Line]
		if trace || isBreak {
			label := "trace"
			if isBreak {
				label = "break"
			}
			watchText := ""
			if len(watches) > 0 {
				parts := []string{}
				for _, name := range watches {
					value, ok := values[name]
					if !ok {
						value = "<unbound>"
					}
					parts = append(parts, name+"="+value)
				}
				watchText = " watch={" + strings.Join(parts, ", ") + "}"
			}
			fmt.Fprintf(os.Stderr, "[%s] %s:%d:%d locals=%s%s\n", label, t.File, t.Line, t.Col, debugEnvSummary(e), watchText)
		}
		if recordPath != "" {
			if len(events) < maxEvents {
				watched := map[string]string{}
				for _, name := range watches {
					value, ok := values[name]
					if !ok {
						value = "<unbound>"
					}
					watched[name] = value
				}
				events = append(events, map[string]any{
					"seq": len(events), "file": t.File, "line": t.Line, "column": t.Col,
					"breakpoint": isBreak, "locals": values, "watch": watched,
				})
			} else {
				truncated = true
			}
		}
	}
	if err = it.Interpret(stmts); err != nil {
		return printDiagnostic(err)
	}
	if recordPath != "" {
		report := map[string]any{
			"schema": "saga.debug-record.v1", "implementation": "saga-native-go",
			"source": path, "events": events, "event_count": len(events), "max_events": maxEvents,
			"truncated": truncated, "watches": watches,
		}
		if err = writeJSONAtomic(recordPath, report); err != nil {
			fmt.Fprintln(os.Stderr, "write debug record:", err)
			return 74
		}
	}
	return 0
}

type profileLocation struct {
	File     string `json:"file"`
	Line     int    `json:"line"`
	Column   int    `json:"column"`
	Hits     int64  `json:"hits"`
	Interval int64  `json:"interval_ns"`
}

func runProfiler(args []string) int {
	if len(args) < 1 {
		fmt.Fprintln(os.Stderr, "source file required")
		return 64
	}
	path := args[0]
	reportPath := ""
	top := 20
	for j := 1; j < len(args); j++ {
		switch args[j] {
		case "--json":
			if j+1 >= len(args) {
				fmt.Fprintln(os.Stderr, "--json requires path")
				return 64
			}
			reportPath = args[j+1]
			j++
		case "--top":
			if j+1 >= len(args) {
				fmt.Fprintln(os.Stderr, "--top requires integer")
				return 64
			}
			n, e := strconv.Atoi(args[j+1])
			if e != nil || n < 1 || n > 1000 {
				fmt.Fprintln(os.Stderr, "--top must be 1..1000")
				return 64
			}
			top = n
			j++
		default:
			fmt.Fprintln(os.Stderr, "unknown profile option:", args[j])
			return 64
		}
	}
	stmts, err := loadProgram(path)
	if err != nil {
		return printDiagnostic(err)
	}
	c := NewChecker()
	if err = c.Check(stmts); err != nil {
		return printDiagnostic(err)
	}
	it := NewInterpreter(c, nil)
	locations := map[string]*profileLocation{}
	var previous *profileLocation
	var previousAt time.Time
	var before, after runtime.MemStats
	runtime.ReadMemStats(&before)
	started := time.Now()
	it.DebugHook = func(t Token, _ *Env) {
		now := time.Now()
		if previous != nil && !previousAt.IsZero() {
			previous.Interval += now.Sub(previousAt).Nanoseconds()
		}
		key := fmt.Sprintf("%s\x00%d\x00%d", t.File, t.Line, t.Col)
		row := locations[key]
		if row == nil {
			row = &profileLocation{File: t.File, Line: t.Line, Column: t.Col}
			locations[key] = row
		}
		row.Hits++
		previous = row
		previousAt = now
	}
	if err = it.Interpret(stmts); err != nil {
		return printDiagnostic(err)
	}
	ended := time.Now()
	if previous != nil && !previousAt.IsZero() {
		previous.Interval += ended.Sub(previousAt).Nanoseconds()
	}
	runtime.ReadMemStats(&after)
	rows := make([]profileLocation, 0, len(locations))
	var events int64
	for _, row := range locations {
		rows = append(rows, *row)
		events += row.Hits
	}
	sort.Slice(rows, func(i, j int) bool {
		if rows[i].Interval != rows[j].Interval {
			return rows[i].Interval > rows[j].Interval
		}
		if rows[i].File != rows[j].File {
			return rows[i].File < rows[j].File
		}
		if rows[i].Line != rows[j].Line {
			return rows[i].Line < rows[j].Line
		}
		return rows[i].Column < rows[j].Column
	})
	topRows := rows
	if len(topRows) > top {
		topRows = topRows[:top]
	}
	for _, row := range topRows {
		fmt.Printf("%10.3f ms  hits=%6d  %s:%d:%d\n", float64(row.Interval)/1e6, row.Hits, row.File, row.Line, row.Column)
	}
	peakDelta := uint64(0)
	if after.HeapSys > before.HeapSys {
		peakDelta = after.HeapSys - before.HeapSys
	}
	report := map[string]any{
		"schema": "saga.statement-profile.v1", "implementation": "saga-native-go", "source": path,
		"timing_model": "elapsed interval between consecutive Saga statement hooks attributed to the preceding statement; not CPU instruction attribution",
		"elapsed_ns":   ended.Sub(started).Nanoseconds(), "statement_events": events, "locations": rows,
		"top": topRows, "go_heap_alloc_bytes": after.HeapAlloc, "go_heap_sys_growth_bytes": peakDelta,
	}
	if reportPath != "" {
		if err = writeJSONAtomic(reportPath, report); err != nil {
			fmt.Fprintln(os.Stderr, "write profile report:", err)
			return 74
		}
	}
	fmt.Printf("elapsed=%.3f ms heap_alloc=%d bytes\n", float64(ended.Sub(started).Nanoseconds())/1e6, after.HeapAlloc)
	return 0
}
