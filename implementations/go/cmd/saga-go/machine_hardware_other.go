//go:build !linux

package main

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

func validateNonLinuxIIOPath(path string) error {
	clean, err := filepath.Abs(path)
	if err != nil {
		return err
	}
	root, err := filepath.Abs(filepath.FromSlash("/sys/bus/iio/devices"))
	if err != nil {
		return err
	}
	rel, err := filepath.Rel(root, clean)
	if err != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(os.PathSeparator)) || filepath.IsAbs(rel) {
		return fmt.Errorf("iio_read is restricted to /sys/bus/iio/devices")
	}
	return nil
}

func machineHardwareCall(name string, args []Value) (Value, error) {
	// Keep security semantics consistent across hosts: reject an invalid IIO
	// filesystem target before reporting that the hardware adapter is Linux-only.
	// Non-Linux builds never dereference the path, so lexical containment is
	// sufficient here; Linux performs the full symlink-resolved check before I/O.
	if name == "iio_read" && len(args) > 0 {
		path, err := machineText(args[0], "path")
		if err != nil {
			return nil, err
		}
		if err := validateNonLinuxIIOPath(path); err != nil {
			return nil, err
		}
	}
	return nil, fmt.Errorf("machine.%s hardware adapter is currently available on Linux; portable PID/profile/watchdog/safety APIs remain available", name)
}
