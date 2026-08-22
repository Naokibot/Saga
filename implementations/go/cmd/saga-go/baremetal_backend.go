package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
)

type cortexM0Compiler struct{ funcs map[string]*FnDecl }

func cBareType(t *TypeRef) (string, error) {
	if t == nil || t.Name == "unit" {
		return "void", nil
	}
	switch t.Name {
	case "int", "int32":
		return "int32_t", nil
	case "uint32":
		return "uint32_t", nil
	case "int16":
		return "int16_t", nil
	case "uint16":
		return "uint16_t", nil
	case "int8":
		return "int8_t", nil
	case "uint8":
		return "uint8_t", nil
	case "bool":
		return "bool", nil
	}
	return "", fmt.Errorf("bare-metal Cortex-M0 does not support type %s", t.Name)
}
func bareCName(n string) string { return "saga_" + n }
func (b *cortexM0Compiler) expr(x Expr) (string, error) {
	switch q := x.(type) {
	case *Literal:
		switch v := q.Value.(type) {
		case bool:
			if v {
				return "true", nil
			}
			return "false", nil
		case Number:
			i, ok := v.Int()
			if !ok {
				return "", fmt.Errorf("bare-metal only supports integer exact literals")
			}
			return i.String(), nil
		}
	case *Variable:
		return q.Name, nil
	case *Unary:
		r, e := b.expr(q.Right)
		if e != nil {
			return "", e
		}
		op := map[Kind]string{MINUS: "-", NOT: "!"}[q.Op.Kind]
		if op == "" {
			return "", fmt.Errorf("unsupported unary")
		}
		return "(" + op + r + ")", nil
	case *Binary:
		l, e := b.expr(q.Left)
		if e != nil {
			return "", e
		}
		r, e := b.expr(q.Right)
		if e != nil {
			return "", e
		}
		ops := map[Kind]string{PLUS: "+", MINUS: "-", STAR: "*", SLASH: "/", PERCENT: "%", EQEQ: "==", BANGEQ: "!=", LESS: "<", LESSEQ: "<=", GREATER: ">", GREATEREQ: ">=", AND: "&&", OR: "||"}
		op := ops[q.Op.Kind]
		if op == "" {
			return "", fmt.Errorf("unsupported binary operator")
		}
		return "(" + l + " " + op + " " + r + ")", nil
	case *Call:
		args := []string{}
		for _, a := range q.Args {
			s, e := b.expr(a)
			if e != nil {
				return "", e
			}
			args = append(args, s)
		}
		if m, ok := q.Callee.(*Member); ok {
			if v, ok := m.Target.(*Variable); ok && v.Name == "embedded" {
				names := map[string]string{"mmio_read8": "saga_mmio_read8", "mmio_read16": "saga_mmio_read16", "mmio_read32": "saga_mmio_read32", "mmio_write8": "saga_mmio_write8", "mmio_write16": "saga_mmio_write16", "mmio_write32": "saga_mmio_write32", "mmio_set_bits32": "saga_mmio_set_bits32", "mmio_clear_bits32": "saga_mmio_clear_bits32", "irq_enable": "saga_irq_enable", "irq_disable": "saga_irq_disable", "barrier": "saga_barrier", "wfi": "saga_wfi", "nvic_enable": "saga_nvic_enable", "nvic_disable": "saga_nvic_disable", "nvic_set_priority": "saga_nvic_set_priority", "critical_enter": "saga_critical_enter", "critical_exit": "saga_critical_exit", "os_tick": "saga_os_tick", "ticks": "saga_ticks", "yield": "saga_yield", "delay_ticks": "saga_delay_ticks", "system_reset": "saga_system_reset", "panic": "saga_panic"}
				n := names[m.Name]
				if n == "" {
					return "", fmt.Errorf("unsupported embedded intrinsic %s", m.Name)
				}
				return n + "(" + strings.Join(args, ",") + ")", nil
			}
		}
		if v, ok := q.Callee.(*Variable); ok {
			switch v.Name {
			case "int32", "uint32", "int16", "uint16", "int8", "uint8":
				return "(" + v.Name + "_t)(" + strings.Join(args, ",") + ")", nil
			case "bool":
				return "(bool)(" + strings.Join(args, ",") + ")", nil
			}
			return bareCName(v.Name) + "(" + strings.Join(args, ",") + ")", nil
		}
	}
	return "", fmt.Errorf("unsupported bare-metal expression %T", x)
}
func (b *cortexM0Compiler) stmt(s Stmt, ind string) (string, error) {
	var o strings.Builder
	switch q := s.(type) {
	case *VarDecl:
		ct := "int32_t"
		if q.Type != nil {
			var e error
			ct, e = cBareType(q.Type)
			if e != nil {
				return "", e
			}
		}
		x, e := b.expr(q.Init)
		if e != nil {
			return "", e
		}
		o.WriteString(ind + ct + " " + q.Name + " = " + x + ";\n")
	case *Assign:
		v, ok := q.Target.(*Variable)
		if !ok {
			return "", fmt.Errorf("bare-metal assignment target must be local variable")
		}
		x, e := b.expr(q.Value)
		if e != nil {
			return "", e
		}
		o.WriteString(ind + v.Name + " = " + x + ";\n")
	case *ExprStmt:
		x, e := b.expr(q.Expr)
		if e != nil {
			return "", e
		}
		o.WriteString(ind + x + ";\n")
	case *ReturnStmt:
		if q.Value == nil {
			o.WriteString(ind + "return;\n")
		} else {
			x, e := b.expr(q.Value)
			if e != nil {
				return "", e
			}
			o.WriteString(ind + "return " + x + ";\n")
		}
	case *IfStmt:
		c, e := b.expr(q.Cond)
		if e != nil {
			return "", e
		}
		o.WriteString(ind + "if (" + c + ") {\n")
		z, e := b.block(q.Then, ind+"  ")
		if e != nil {
			return "", e
		}
		o.WriteString(z + ind + "}")
		if q.Else != nil {
			o.WriteString(" else {\n")
			switch el := q.Else.(type) {
			case *Block:
				z, e = b.block(el, ind+"  ")
			case *IfStmt:
				z, e = b.stmt(el, ind+"  ")
			default:
				return "", fmt.Errorf("unsupported else")
			}
			if e != nil {
				return "", e
			}
			o.WriteString(z + ind + "}")
		}
		o.WriteString("\n")
	case *WhileStmt:
		c, e := b.expr(q.Cond)
		if e != nil {
			return "", e
		}
		z, e := b.block(q.Body, ind+"  ")
		if e != nil {
			return "", e
		}
		o.WriteString(ind + "while (" + c + ") {\n" + z + ind + "}\n")
	case *ForStmt:
		r, ok := q.Iterable.(*RangeExpr)
		if !ok {
			return "", fmt.Errorf("bare-metal for supports integer ranges")
		}
		a, e := b.expr(r.Start)
		if e != nil {
			return "", e
		}
		zv, e := b.expr(r.End)
		if e != nil {
			return "", e
		}
		body, e := b.block(q.Body, ind+"  ")
		if e != nil {
			return "", e
		}
		o.WriteString(ind + "for (int32_t " + q.Name + " = " + a + "; " + q.Name + " <= " + zv + "; " + q.Name + "++) {\n" + body + ind + "}\n")
	case *BreakStmt:
		o.WriteString(ind + "break;\n")
	case *ContinueStmt:
		o.WriteString(ind + "continue;\n")
	case *Block:
		z, e := b.block(q, ind)
		return z, e
	default:
		return "", fmt.Errorf("unsupported bare-metal statement %T", s)
	}
	return o.String(), nil
}
func (b *cortexM0Compiler) block(bl *Block, ind string) (string, error) {
	var o strings.Builder
	for _, s := range bl.Stmts {
		z, e := b.stmt(s, ind)
		if e != nil {
			return "", e
		}
		o.WriteString(z)
	}
	return o.String(), nil
}
func annotationText(d *FnDecl, name string) (string, bool) {
	for _, a := range d.Annotations {
		if a.Name == name && len(a.Args) == 1 {
			if l, ok := a.Args[0].(*Literal); ok {
				if s, ok := l.Value.(string); ok {
					return s, true
				}
			}
		}
	}
	return "", false
}
func cortexVectorIndex(s string) (int, error) {
	switch s {
	case "NMI":
		return 2, nil
	case "HardFault":
		return 3, nil
	case "SVC":
		return 11, nil
	case "PendSV":
		return 14, nil
	case "SysTick":
		return 15, nil
	}
	if strings.HasPrefix(s, "IRQ") {
		n, e := strconv.Atoi(strings.TrimPrefix(s, "IRQ"))
		if e == nil && n >= 0 && n < 32 {
			return 16 + n, nil
		}
	}
	return 0, fmt.Errorf("unsupported interrupt %q; use NMI, HardFault, SVC, PendSV, SysTick, or IRQ0..IRQ31", s)
}
func (b *cortexM0Compiler) emitFunction(f *FnDecl) (string, error) {
	rt, e := cBareType(f.Return)
	if e != nil {
		return "", e
	}
	ps := []string{}
	for _, p := range f.Params {
		t, e := cBareType(&p.Type)
		if e != nil {
			return "", e
		}
		ps = append(ps, t+" "+p.Name)
	}
	body, e := b.block(f.Body, "  ")
	if e != nil {
		return "", fmt.Errorf("%s: %w", f.Name, e)
	}
	attrs := ""
	if _, ok := annotationText(f, "interrupt"); ok {
		attrs = "__attribute__((used)) "
	}
	return attrs + rt + " " + bareCName(f.Name) + "(" + strings.Join(ps, ",") + ") {\n" + body + "}\n", nil
}

type bareBoard struct {
	Name, CPU, Triple string
	FlashOrigin       uint32
	FlashSize         uint32
	RAMOrigin         uint32
	RAMSize           uint32
}

var boardGenericM0 = bareBoard{Name: "generic-cortex-m0", CPU: "cortex-m0", Triple: "armv6m-none-eabi", FlashOrigin: 0x00000000, FlashSize: 256 * 1024, RAMOrigin: 0x20000000, RAMSize: 64 * 1024}
var boardSTM32F030K6 = bareBoard{Name: "stm32f030k6", CPU: "cortex-m0", Triple: "armv6m-none-eabi", FlashOrigin: 0x08000000, FlashSize: 32 * 1024, RAMOrigin: 0x20000000, RAMSize: 4 * 1024}

func buildBareMetalCortexM0(input, output string) (string, error) {
	return buildBareMetalBoard(input, output, boardGenericM0)
}
func buildBareMetalSTM32F030K6(input, output string) (string, error) {
	return buildBareMetalBoard(input, output, boardSTM32F030K6)
}
func buildBareMetalBoard(input, output string, board bareBoard) (string, error) {
	stmts, e := loadProgram(input)
	if e != nil {
		return "", e
	}
	c := NewChecker()
	if e = c.Check(stmts); e != nil {
		return "", e
	}
	b := &cortexM0Compiler{funcs: map[string]*FnDecl{}}
	interrupts := map[int]string{}
	hasReset := false
	funcs := []*FnDecl{}
	for _, s := range stmts {
		switch q := s.(type) {
		case *FnDecl:
			if q.Async || q.ExternABI != "" || len(q.TypeParams) > 0 {
				return "", fmt.Errorf("bare-metal function %s cannot be async/extern/generic", q.Name)
			}
			if q.Body == nil {
				return "", fmt.Errorf("bare-metal function %s requires block body", q.Name)
			}
			funcs = append(funcs, q)
			b.funcs[q.Name] = q
			if q.Name == "reset" {
				hasReset = true
			}
			if n, ok := annotationText(q, "interrupt"); ok {
				idx, e := cortexVectorIndex(n)
				if e != nil {
					return "", e
				}
				if _, dup := interrupts[idx]; dup {
					return "", fmt.Errorf("duplicate interrupt vector %d", idx)
				}
				interrupts[idx] = q.Name
			}
		case *UseStmt:
			if q.Module != "embedded" {
				return "", fmt.Errorf("bare-metal profile only permits use embedded")
			}
		case *EditionDecl, *ModuleDecl:
		default:
			return "", fmt.Errorf("bare-metal top-level supports function declarations only; got %T", s)
		}
	}
	if !hasReset {
		return "", fmt.Errorf("bare-metal Cortex-M0 requires fn reset()->unit")
	}
	var src strings.Builder
	src.WriteString(`#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#define SAGA_MMIO(T,A) (*(volatile T*)(uintptr_t)(A))
static inline uint8_t saga_mmio_read8(uint32_t a){return SAGA_MMIO(uint8_t,a);}
static inline uint16_t saga_mmio_read16(uint32_t a){return SAGA_MMIO(uint16_t,a);}
static inline uint32_t saga_mmio_read32(uint32_t a){return SAGA_MMIO(uint32_t,a);}
static inline void saga_mmio_write8(uint32_t a,uint8_t v){SAGA_MMIO(uint8_t,a)=v;}
static inline void saga_mmio_write16(uint32_t a,uint16_t v){SAGA_MMIO(uint16_t,a)=v;}
static inline void saga_mmio_write32(uint32_t a,uint32_t v){SAGA_MMIO(uint32_t,a)=v;}
static inline void saga_mmio_set_bits32(uint32_t a,uint32_t mask){SAGA_MMIO(uint32_t,a)|=mask;}
static inline void saga_mmio_clear_bits32(uint32_t a,uint32_t mask){SAGA_MMIO(uint32_t,a)&=~mask;}
static inline void saga_irq_enable(void){__asm volatile("cpsie i" ::: "memory");}
static inline void saga_irq_disable(void){__asm volatile("cpsid i" ::: "memory");}
static inline void saga_barrier(void){__asm volatile("dmb" ::: "memory");}
static inline void saga_wfi(void){__asm volatile("wfi" ::: "memory");}
static inline void saga_nvic_enable(uint32_t irq){SAGA_MMIO(uint32_t,0xE000E100u + ((irq>>5)*4u))=(1u<<(irq&31u));}
static inline void saga_nvic_disable(uint32_t irq){SAGA_MMIO(uint32_t,0xE000E180u + ((irq>>5)*4u))=(1u<<(irq&31u));}
static inline void saga_nvic_set_priority(uint32_t irq,uint32_t pri){SAGA_MMIO(uint8_t,0xE000E400u + irq)=(uint8_t)(pri<<6);}
static volatile uint32_t saga_kernel_ticks = 0;
static inline uint32_t saga_critical_enter(void){uint32_t p;__asm volatile("mrs %0, primask\n cpsid i":"=r"(p)::"memory");return p;}
static inline void saga_critical_exit(uint32_t p){if((p&1u)==0u){__asm volatile("cpsie i" ::: "memory");}}
static inline void saga_os_tick(void){saga_kernel_ticks++;}
static inline uint32_t saga_ticks(void){return saga_kernel_ticks;}
static inline void saga_yield(void){saga_wfi();}
static inline void saga_delay_ticks(uint32_t n){uint32_t start=saga_kernel_ticks;while((uint32_t)(saga_kernel_ticks-start)<n){saga_wfi();}}
__attribute__((noreturn)) static inline void saga_system_reset(void){saga_irq_disable();saga_barrier();SAGA_MMIO(uint32_t,0xE000ED0Cu)=0x05FA0004u;saga_barrier();for(;;){saga_wfi();}}
__attribute__((noreturn)) static inline void saga_panic(uint32_t code){(void)code;saga_irq_disable();for(;;){saga_wfi();}}
`)
	for _, f := range funcs {
		z, e := b.emitFunction(f)
		if e != nil {
			return "", e
		}
		src.WriteString(z + "\n")
	}
	src.WriteString("extern uint32_t __stack_top, _sidata, _sdata, _edata, _sbss, _ebss;\nvoid Default_Handler(void){for(;;){saga_wfi();}}\nvoid Reset_Handler(void){uint32_t *src=&_sidata,*dst=&_sdata;while(dst<&_edata){*dst++=*src++;}for(dst=&_sbss;dst<&_ebss;){*dst++=0;}saga_barrier();saga_reset();for(;;){saga_wfi();}}\n")
	vec := make([]string, 48)
	for i := range vec {
		vec[i] = "Default_Handler"
	}
	vec[0] = "(void*)&__stack_top"
	vec[1] = "Reset_Handler"
	for idx, n := range interrupts {
		vec[idx] = bareCName(n)
	}
	src.WriteString("__attribute__((section(\".isr_vector\"),used)) const void *vectors[48] = {\n")
	for i, v := range vec {
		src.WriteString(fmt.Sprintf("  [%d] = (void*)%s,\n", i, v))
	}
	src.WriteString("};\n")
	base := output
	if base == "" {
		base = strings.TrimSuffix(input, filepath.Ext(input)) + ".cortex-m0"
	}
	if strings.HasSuffix(base, ".elf") {
		base = strings.TrimSuffix(base, ".elf")
	}
	dir := filepath.Dir(base)
	if e = os.MkdirAll(dir, 0755); e != nil {
		return "", e
	}
	cfile := base + ".c"
	ldfile := base + ".ld"
	elf := base + ".elf"
	bin := base + ".bin"
	manifest := base + ".json"
	lds := fmt.Sprintf("ENTRY(Reset_Handler)\nMEMORY { FLASH (rx) : ORIGIN = 0x%08x, LENGTH = %d\n         RAM (rwx) : ORIGIN = 0x%08x, LENGTH = %d }\n__stack_top = ORIGIN(RAM)+LENGTH(RAM);\nSECTIONS { .isr_vector : { KEEP(*(.isr_vector)) } > FLASH .text : { *(.text*) *(.rodata*) } > FLASH .data : { _sdata = .; *(.data*) _edata = .; } > RAM AT>FLASH _sidata = LOADADDR(.data); .bss (NOLOAD) : { _sbss = .; *(.bss*) *(COMMON) _ebss = .; } > RAM }\n", board.FlashOrigin, board.FlashSize, board.RAMOrigin, board.RAMSize)
	if e = os.WriteFile(cfile, []byte(src.String()), 0644); e != nil {
		return "", e
	}
	if e = os.WriteFile(ldfile, []byte(lds), 0644); e != nil {
		return "", e
	}
	clang, er := exec.LookPath("clang")
	if er != nil {
		return "", fmt.Errorf("Cortex-M0 backend requires LLVM clang/lld: %w", er)
	}
	cmd := exec.Command(clang, "--target="+board.Triple, "-mcpu="+board.CPU, "-mthumb", "-fuse-ld=lld", "-ffreestanding", "-fno-builtin", "-fno-exceptions", "-fdata-sections", "-ffunction-sections", "-nostdlib", "-Wl,--gc-sections", "-Wl,-T,"+ldfile, "-o", elf, cfile)
	if out, er := cmd.CombinedOutput(); er != nil {
		return "", fmt.Errorf("Cortex-M0 link failed: %v\n%s", er, out)
	}
	objcopy, er := exec.LookPath("llvm-objcopy")
	if er != nil {
		return "", fmt.Errorf("Cortex-M0 backend requires llvm-objcopy: %w", er)
	}
	if out, er := exec.Command(objcopy, "-O", "binary", elf, bin).CombinedOutput(); er != nil {
		return "", fmt.Errorf("objcopy failed: %v\n%s", er, out)
	}
	ints := map[string]int{}
	for idx, n := range interrupts {
		ints[n] = idx
	}
	meta := map[string]any{"schema": 2, "target": board.Triple, "cpu": board.CPU, "board_profile": board.Name, "flash_origin": fmt.Sprintf("0x%08x", board.FlashOrigin), "flash_size": board.FlashSize, "ram_origin": fmt.Sprintf("0x%08x", board.RAMOrigin), "ram_size": board.RAMSize, "vector_entries": 48, "interrupts": ints, "source": filepath.Base(input), "elf": filepath.Base(elf), "bin": filepath.Base(bin), "bsp": "volatile-mmio+cortex-m-exception-vector+irq-control+nvic+wfi+dmb", "toolchain_backend": "llvm-clang-lld"}
	jb, _ := json.MarshalIndent(meta, "", "  ")
	if e = os.WriteFile(manifest, jb, 0644); e != nil {
		return "", e
	}
	return elf, nil
}

var _ = bytes.MinRead
