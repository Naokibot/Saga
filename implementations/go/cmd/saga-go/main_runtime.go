//go:build sagaruntime

package main

import (
	"fmt"
	"os"
)

// The runtime build intentionally contains no development CLI entry points.
// It executes only verified SAGABND2 application/compiler bundles.
func main() {
	exe, err := os.Executable()
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(70)
	}
	payload, err := readEmbeddedBundle(exe)
	if err != nil {
		fmt.Fprintln(os.Stderr, "invalid Saga standalone executable:", err)
		os.Exit(70)
	}
	if payload == nil {
		fmt.Fprintln(os.Stderr, "Saga Runtime is an internal execution component; use the `saga` CLI to run or build source programs.")
		os.Exit(64)
	}
	sagaProcessArgs = append([]string{}, os.Args[1:]...)
	if err = executeBundle(payload); err != nil {
		os.Exit(printDiagnostic(err))
	}
}
