//go:build linux && !sagaruntime

package main

import (
	"encoding/binary"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestMachineEncoderAndMotorSafety(t *testing.T) {
	enc, err := newMachineEncoder(1000, 2)
	if err != nil {
		t.Fatal(err)
	}
	if err = enc.update(0, 1_000_000_000); err != nil {
		t.Fatal(err)
	}
	if err = enc.update(1000, 2_000_000_000); err != nil {
		t.Fatal(err)
	}
	if got := machineNumberFromFloat(enc.PositionDegrees).String(); got != "180" {
		t.Fatalf("position=%s", got)
	}
	if got := machineNumberFromFloat(enc.VelocityRPM).String(); got != "30" {
		t.Fatalf("velocity=%s", got)
	}

	root := t.TempDir()
	makePWM := func(name string) *machinePWM {
		path := filepath.Join(root, name)
		if err := os.MkdirAll(path, 0755); err != nil {
			t.Fatal(err)
		}
		for _, file := range []string{"duty_cycle", "enable"} {
			if err := os.WriteFile(filepath.Join(path, file), []byte("0"), 0644); err != nil {
				t.Fatal(err)
			}
		}
		return &machinePWM{path: path, period: 20_000_000}
	}
	fwd, rev := makePWM("fwd"), makePWM("rev")
	latch := &MachineSafety{}
	motor := &machineMotor{forward: fwd, reverse: rev, deadband: 0.05, safety: latch}
	if err := motor.write(0.6); err != nil {
		t.Fatal(err)
	}
	if b, _ := os.ReadFile(filepath.Join(fwd.path, "duty_cycle")); string(b) != "12000000" {
		t.Fatalf("forward duty=%s", b)
	}
	if b, _ := os.ReadFile(filepath.Join(rev.path, "duty_cycle")); string(b) != "0" {
		t.Fatalf("reverse duty=%s", b)
	}
	if err := latch.trip("guard open"); err != nil {
		t.Fatal(err)
	}
	if err := motor.write(0.5); err == nil {
		t.Fatal("expected safety latch to block motor")
	}
	if b, _ := os.ReadFile(filepath.Join(fwd.path, "duty_cycle")); string(b) != "0" {
		t.Fatalf("forward not stopped: %s", b)
	}
	if b, _ := os.ReadFile(filepath.Join(rev.path, "duty_cycle")); string(b) != "0" {
		t.Fatalf("reverse not stopped: %s", b)
	}
}

func TestMachineCANExtendedIDSetsEFFFlag(t *testing.T) {
	r, w, err := os.Pipe()
	if err != nil {
		t.Fatal(err)
	}
	defer r.Close()
	defer w.Close()
	dev := &machineCAN{fd: int(w.Fd()), fdMode: false}
	if err := dev.send(0x12345, []byte{0x42}); err != nil {
		t.Fatal(err)
	}
	frame := make([]byte, 16)
	if _, err := r.Read(frame); err != nil {
		t.Fatal(err)
	}
	wireID := binary.LittleEndian.Uint32(frame[:4])
	if wireID != uint32(0x12345)|machineCANEFFFlag {
		t.Fatalf("wire CAN id=%#x", wireID)
	}
}

func TestMachineSafetyTripStopsRegisteredMotorImmediately(t *testing.T) {
	root := t.TempDir()
	makePWM := func(name string) *machinePWM {
		path := filepath.Join(root, name)
		if err := os.MkdirAll(path, 0755); err != nil {
			t.Fatal(err)
		}
		for _, file := range []string{"duty_cycle", "enable"} {
			if err := os.WriteFile(filepath.Join(path, file), []byte("0"), 0644); err != nil {
				t.Fatal(err)
			}
		}
		return &machinePWM{path: path, period: 20_000_000}
	}
	fwd, rev := makePWM("fwd"), makePWM("rev")
	latch := &MachineSafety{}
	motor := &machineMotor{forward: fwd, reverse: rev, deadband: 0.05, safety: latch}
	if err := latch.registerStop(motor.stop); err != nil {
		t.Fatal(err)
	}
	if err := motor.write(0.7); err != nil {
		t.Fatal(err)
	}
	if err := latch.trip("guard open"); err != nil {
		t.Fatal(err)
	}
	if b, _ := os.ReadFile(filepath.Join(fwd.path, "duty_cycle")); string(b) != "0" {
		t.Fatalf("forward not stopped immediately: %s", b)
	}
	if b, _ := os.ReadFile(filepath.Join(rev.path, "duty_cycle")); string(b) != "0" {
		t.Fatalf("reverse not stopped immediately: %s", b)
	}
}

func TestMachineI2CCombinedTransferRejectsOversizedSegments(t *testing.T) {
	f, err := os.CreateTemp(t.TempDir(), "i2c-placeholder")
	if err != nil {
		t.Fatal(err)
	}
	defer f.Close()
	dev := &machineI2C{file: f, address: 0x40}
	if _, err := dev.writeRead(make([]byte, 65536), 1); err == nil || !strings.Contains(err.Error(), "65535") {
		t.Fatalf("expected oversized write rejection, got %v", err)
	}
	if _, err := dev.writeRead([]byte{1}, 65536); err == nil || !strings.Contains(err.Error(), "65535") {
		t.Fatalf("expected oversized read rejection, got %v", err)
	}
}

func TestMachineClosedI2CReadFailsWithoutPanic(t *testing.T) {
	dev := &machineI2C{}
	if _, err := dev.read(1); err == nil || !strings.Contains(err.Error(), "closed") {
		t.Fatalf("expected closed I2C error, got %v", err)
	}
	if _, err := dev.writeRead([]byte{0}, 1); err == nil || !strings.Contains(err.Error(), "closed") {
		t.Fatalf("expected closed I2C error, got %v", err)
	}
}
