package main

import (
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"flag"
	"fmt"
	"io/fs"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
)

var version = "0.35.0"

func main() {
	prefixFlag := flag.String("prefix", "", "installation directory")
	uninstall := flag.Bool("uninstall", false, "remove Saga")
	noPath := flag.Bool("no-path", false, "do not add Saga bin directory to user PATH")
	checkOnly := flag.Bool("check-only", false, "verify embedded Saga Native payload only")
	flag.Parse()
	custom := *prefixFlag != ""
	prefix := *prefixFlag
	if prefix == "" {
		prefix = defaultPrefix()
	}
	abs, err := filepath.Abs(prefix)
	fatalIf(err)
	prefix = abs
	if *uninstall {
		fatalIf(removeInstall(prefix, custom))
		fmt.Println("Saga removed from", prefix)
		return
	}
	name := payloadName()
	data, err := fs.ReadFile(payload, "payload/"+name)
	fatalIf(err)
	runtimeData, err := fs.ReadFile(payload, "payload/"+runtimePayloadName())
	fatalIf(err)
	compilerSource, err := fs.ReadFile(payload, "payload/sagac.saga")
	fatalIf(err)
	digest := sha256.Sum256(data)
	runtimeDigest := sha256.Sum256(runtimeData)
	fmt.Println("Embedded Saga Native CLI SHA-256:", hex.EncodeToString(digest[:]))
	fmt.Println("Embedded Saga Runtime SHA-256:", hex.EncodeToString(runtimeDigest[:]))
	if *checkOnly {
		fmt.Println("Native payload check OK; no Python/Go/clang prerequisite is required")
		return
	}
	bin := launcherDir(prefix, custom)
	fatalIf(install(prefix, bin, data, runtimeData, compilerSource, digest, runtimeDigest, !*noPath))
	fmt.Println("Saga Native", version, "installed in", prefix)
	fmt.Println("No Python, Go, Java, Node, or clang runtime is required.")
	fmt.Println("Launchers:", bin)
	fmt.Println("Official compiler: sagac (written in Saga and built during installation)")
}

func payloadName() string {
	n := "saga-native-" + runtime.GOOS + "-" + runtime.GOARCH
	if runtime.GOOS == "windows" {
		n += ".exe"
	}
	return n
}
func runtimePayloadName() string {
	n := "saga-runtime-" + runtime.GOOS + "-" + runtime.GOARCH
	if runtime.GOOS == "windows" {
		n += ".exe"
	}
	return n
}
func defaultPrefix() string {
	if runtime.GOOS == "windows" {
		if v := os.Getenv("LOCALAPPDATA"); v != "" {
			return filepath.Join(v, "Programs", "Saga")
		}
	}
	home, e := os.UserHomeDir()
	if e != nil {
		return filepath.Join(".", "saga-native")
	}
	return filepath.Join(home, ".local", "share", "saga")
}
func launcherDir(prefix string, custom bool) string {
	if custom {
		return filepath.Join(prefix, "bin")
	}
	if runtime.GOOS == "windows" {
		if v := os.Getenv("LOCALAPPDATA"); v != "" {
			return filepath.Join(v, "Programs", "Saga", "bin")
		}
	}
	home, _ := os.UserHomeDir()
	return filepath.Join(home, ".local", "bin")
}
func install(prefix, bin string, data, runtimeData, compilerSource []byte, digest, runtimeDigest [32]byte, updatePath bool) error {
	if len(data) == 0 {
		return errors.New("embedded Saga Native payload is empty")
	}
	if err := os.MkdirAll(bin, 0755); err != nil {
		return err
	}
	runtimeDir := filepath.Join(prefix, "runtime")
	if err := os.MkdirAll(runtimeDir, 0755); err != nil {
		return err
	}
	native := filepath.Join(runtimeDir, "saga")
	if runtime.GOOS == "windows" {
		native += ".exe"
	}
	if err := os.WriteFile(native, data, 0755); err != nil {
		return err
	}
	gotData, err := os.ReadFile(native)
	if err != nil {
		return err
	}
	got := sha256.Sum256(gotData)
	if got != digest {
		return errors.New("installed Saga Native hash mismatch")
	}
	runtimeTemplate := filepath.Join(runtimeDir, "saga-runtime")
	if runtime.GOOS == "windows" {
		runtimeTemplate += ".exe"
	}
	if err := os.WriteFile(runtimeTemplate, runtimeData, 0755); err != nil {
		return err
	}
	rawRuntime, err := os.ReadFile(runtimeTemplate)
	if err != nil {
		return err
	}
	gotRuntime := sha256.Sum256(rawRuntime)
	if gotRuntime != runtimeDigest {
		return errors.New("installed Saga Runtime hash mismatch")
	}
	selfhostDir := filepath.Join(prefix, "selfhost")
	if err := os.MkdirAll(selfhostDir, 0755); err != nil {
		return err
	}
	compilerSrc := filepath.Join(selfhostDir, "sagac.saga")
	if err := os.WriteFile(compilerSrc, compilerSource, 0644); err != nil {
		return err
	}
	compilerBin := filepath.Join(runtimeDir, "sagac")
	ext := ""
	if runtime.GOOS == "windows" {
		ext = ".exe"
		compilerBin += ext
	}
	stage1 := filepath.Join(runtimeDir, "sagac-stage1"+ext)
	stage2 := filepath.Join(runtimeDir, "sagac-stage2"+ext)
	stage3 := filepath.Join(runtimeDir, "sagac-stage3"+ext)
	bootstrap := exec.Command(native, "_bootstrap-compiler", compilerSrc, "-o", stage1)
	if out, err := bootstrap.CombinedOutput(); err != nil {
		return fmt.Errorf("self-host compiler stage1 bootstrap failed: %s", strings.TrimSpace(string(out)))
	}
	if out, err := exec.Command(stage1, "self-build", compilerSrc, "-o", stage2).CombinedOutput(); err != nil {
		return fmt.Errorf("self-host compiler stage2 build failed: %s", strings.TrimSpace(string(out)))
	}
	if out, err := exec.Command(stage2, "self-build", compilerSrc, "-o", stage3).CombinedOutput(); err != nil {
		return fmt.Errorf("self-host compiler stage3 build failed: %s", strings.TrimSpace(string(out)))
	}
	b2, err := os.ReadFile(stage2)
	if err != nil {
		return err
	}
	b3, err := os.ReadFile(stage3)
	if err != nil {
		return err
	}
	h2, h3 := sha256.Sum256(b2), sha256.Sum256(b3)
	if h2 != h3 {
		return fmt.Errorf("self-host fixed point failed: stage2=%x stage3=%x", h2, h3)
	}
	if err := os.Rename(stage2, compilerBin); err != nil {
		return err
	}
	_ = os.Remove(stage1)
	_ = os.Remove(stage3)
	if out, err := exec.Command(compilerBin, "version").CombinedOutput(); err != nil || !strings.Contains(string(out), "Self-Hosted Compiler") {
		return fmt.Errorf("self-host compiler verification failed: %s", strings.TrimSpace(string(out)))
	}
	if err := writeLaunchers(bin, native, compilerBin); err != nil {
		return err
	}
	compilerData, err := os.ReadFile(compilerBin)
	if err != nil {
		return err
	}
	compilerDigest := sha256.Sum256(compilerData)
	if err := writeReceipt(prefix, bin, digest, runtimeDigest, compilerDigest); err != nil {
		return err
	}
	if runtime.GOOS == "windows" && updatePath {
		if err := addWindowsPath(bin); err != nil {
			fmt.Fprintln(os.Stderr, "Warning: PATH update failed:", err)
		}
	}
	out, err := exec.Command(native, "--version").CombinedOutput()
	if err != nil {
		return fmt.Errorf("post-install version check failed: %s", strings.TrimSpace(string(out)))
	}
	if !strings.Contains(string(out), version) {
		return fmt.Errorf("installed Saga Native version mismatch: %s", strings.TrimSpace(string(out)))
	}
	conf, err := exec.Command(native, "conformance", "--json").CombinedOutput()
	if err != nil {
		return fmt.Errorf("post-install conformance failed: %s", strings.TrimSpace(string(conf)))
	}
	if !strings.Contains(string(conf), `"pass":true`) {
		return fmt.Errorf("post-install conformance did not pass: %s", strings.TrimSpace(string(conf)))
	}
	info, err := exec.Command(native, "info").CombinedOutput()
	if err != nil {
		return err
	}
	if !strings.Contains(string(info), `"runtime_dependencies":[]`) {
		return errors.New("installed Saga Native does not report zero language-runtime dependencies")
	}
	return nil
}
func writeLaunchers(bin, native, compiler string) error {
	if runtime.GOOS == "windows" {
		body := "@echo off\r\n\"" + native + "\" %*\r\n"
		if err := os.WriteFile(filepath.Join(bin, "saga.cmd"), []byte(body), 0644); err != nil {
			return err
		}
		compilerBody := "@echo off\r\n\"" + compiler + "\" %*\r\n"
		return os.WriteFile(filepath.Join(bin, "sagac.cmd"), []byte(compilerBody), 0644)
	}
	body := "#!/bin/sh\nexec \"" + strings.ReplaceAll(native, "\"", "\\\"") + "\" \"$@\"\n"
	p := filepath.Join(bin, "saga")
	if err := os.WriteFile(p, []byte(body), 0755); err != nil {
		return err
	}
	if err := os.Chmod(p, 0755); err != nil {
		return err
	}
	compilerBody := "#!/bin/sh\nexec \"" + strings.ReplaceAll(compiler, "\"", "\\\"") + "\" \"$@\"\n"
	cp := filepath.Join(bin, "sagac")
	if err := os.WriteFile(cp, []byte(compilerBody), 0755); err != nil {
		return err
	}
	return os.Chmod(cp, 0755)
}
func writeReceipt(prefix, bin string, d, runtimeDigest, compiler [32]byte) error {
	s := fmt.Sprintf("Saga Native %s\nRuntime dependencies: none\nNative CLI SHA-256: %x\nMinimal Runtime SHA-256: %x\nSelf-host compiler SHA-256: %x\nLauncher: %s\n", version, d, runtimeDigest, compiler, bin)
	return os.WriteFile(filepath.Join(prefix, "INSTALL_RECEIPT.txt"), []byte(s), 0644)
}
func removeInstall(prefix string, custom bool) error {
	bin := launcherDir(prefix, custom)
	if custom {
		_ = os.RemoveAll(prefix)
		return nil
	}
	if runtime.GOOS == "windows" {
		_ = os.Remove(filepath.Join(bin, "saga.cmd"))
		_ = os.Remove(filepath.Join(bin, "sagac.cmd"))
	} else {
		_ = os.Remove(filepath.Join(bin, "saga"))
		_ = os.Remove(filepath.Join(bin, "sagac"))
	}
	return os.RemoveAll(prefix)
}
func addWindowsPath(bin string) error {
	ps, err := exec.LookPath("powershell.exe")
	if err != nil {
		return err
	}
	escaped := strings.ReplaceAll(bin, "'", "''")
	script := `$p=[Environment]::GetEnvironmentVariable('Path','User'); if(-not ($p -split ';' | Where-Object { $_ -eq '` + escaped + `' })){[Environment]::SetEnvironmentVariable('Path', (($p.TrimEnd(';') + ';` + escaped + `').Trim(';')), 'User')}`
	out, e := exec.Command(ps, "-NoProfile", "-NonInteractive", "-Command", script).CombinedOutput()
	if e != nil {
		return fmt.Errorf("%s", strings.TrimSpace(string(out)))
	}
	return nil
}
func fatalIf(err error) {
	if err != nil {
		fmt.Fprintln(os.Stderr, "Saga installer:", err)
		os.Exit(1)
	}
}
