//go:build !linux

package main

import "fmt"

func machineHardwareCall(name string, args []Value) (Value, error) {
	return nil, fmt.Errorf("machine.%s hardware adapter is currently available on Linux; portable PID/profile/watchdog/safety APIs remain available", name)
}
