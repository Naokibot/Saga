package main

import (
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"testing"
)

func TestBareMetalCortexM0AndSTM32BSP(t *testing.T) {
	if _, err := exec.LookPath("clang"); err != nil {
		t.Skip("clang unavailable")
	}
	if _, err := exec.LookPath("llvm-objcopy"); err != nil {
		t.Skip("llvm-objcopy unavailable")
	}
	d := t.TempDir()
	src := filepath.Join(d, "fw.saga")
	code := `edition 2027
use embedded
fn init()->unit {
  embedded.mmio_set_bits32(uint32(1073741824), uint32(1))
  embedded.nvic_enable(uint32(0))
}
@interrupt("SysTick")
fn tick()->unit { embedded.barrier() }
public fn reset()->unit {
  embedded.irq_disable()
  init()
  embedded.irq_enable()
  while true { embedded.wfi() }
}
`
	if err := os.WriteFile(src, []byte(code), 0644); err != nil {
		t.Fatal(err)
	}
	for _, tc := range []struct {
		name  string
		board bareBoard
		sp    uint32
	}{
		{"generic", boardGenericM0, boardGenericM0.RAMOrigin + boardGenericM0.RAMSize},
		{"stm32f030k6", boardSTM32F030K6, boardSTM32F030K6.RAMOrigin + boardSTM32F030K6.RAMSize},
	} {
		t.Run(tc.name, func(t *testing.T) {
			base := filepath.Join(d, tc.name)
			if _, err := buildBareMetalBoard(src, base, tc.board); err != nil {
				t.Fatal(err)
			}
			bin, err := os.ReadFile(base + ".bin")
			if err != nil {
				t.Fatal(err)
			}
			if len(bin) < 64 {
				t.Fatalf("firmware too small: %d", len(bin))
			}
			gotSP := uint32(bin[0]) | uint32(bin[1])<<8 | uint32(bin[2])<<16 | uint32(bin[3])<<24
			if gotSP != tc.sp {
				t.Fatalf("stack top got %#x want %#x", gotSP, tc.sp)
			}
			reset := uint32(bin[4]) | uint32(bin[5])<<8 | uint32(bin[6])<<16 | uint32(bin[7])<<24
			if reset&1 == 0 {
				t.Fatalf("reset vector not Thumb: %#x", reset)
			}
			systick := uint32(bin[60]) | uint32(bin[61])<<8 | uint32(bin[62])<<16 | uint32(bin[63])<<24
			if systick&1 == 0 {
				t.Fatalf("SysTick vector not Thumb: %#x", systick)
			}
			var meta map[string]any
			jb, err := os.ReadFile(base + ".json")
			if err != nil {
				t.Fatal(err)
			}
			if err := json.Unmarshal(jb, &meta); err != nil {
				t.Fatal(err)
			}
			if meta["board_profile"] != tc.board.Name {
				t.Fatalf("manifest board=%v", meta["board_profile"])
			}
		})
	}
}
