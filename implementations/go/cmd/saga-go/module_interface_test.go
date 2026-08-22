package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func writeModuleTestFile(t *testing.T, root, name, source string) string {
	t.Helper()
	path := filepath.Join(root, name)
	if err := os.WriteFile(path, []byte(source+"\n"), 0644); err != nil {
		t.Fatal(err)
	}
	return path
}

func TestModuleInterfaceCompileVerifyAndAttach(t *testing.T) {
	root := t.TempDir()
	module := writeModuleTestFile(t, root, "models.saga", `module models
public class User(let name:text){ fn greet()->text=self.name }
public fn twice(x:int)->int=x*2
public let answer:int=42`)
	iface, err := buildModuleInterface(module, "", true, nil)
	if err != nil {
		t.Fatal(err)
	}
	if iface.Schema != moduleInterfaceSchema || iface.LanguageVersion != moduleInterfaceLanguage {
		t.Fatalf("unexpected interface metadata: %#v", iface)
	}
	if iface.ABISHA256 != "ce27aea7e5c50d46a5d447ddb84b4770796969a24ca04e494bf1fa9b181bec2d" {
		t.Fatalf("unexpected stable ABI %s", iface.ABISHA256)
	}
	verified, err := verifyModuleInterface(filepath.Join(root, "models.smi.json"), module)
	if err != nil || verified.ABISHA256 != iface.ABISHA256 {
		t.Fatalf("verify failed: iface=%#v err=%v", verified, err)
	}
	main := writeModuleTestFile(t, root, "main.saga", `use "models.saga" as m
print(m.twice(m.answer))`)
	stmts, err := loadProgram(main)
	if err != nil {
		t.Fatal(err)
	}
	attached := false
	for _, st := range stmts {
		if m, ok := st.(*SourceModuleStmt); ok {
			attached = m.Interface != nil
		}
	}
	if !attached {
		t.Fatal("fresh .smi.json was not attached to source module")
	}
	if err = NewChecker().Check(stmts); err != nil {
		t.Fatal(err)
	}
}

func TestModuleInterfaceSupportsImportedBaseAtRuntime(t *testing.T) {
	root := t.TempDir()
	module := writeModuleTestFile(t, root, "models.saga", `module models
public class User(let name:text){ fn greet()->text="Hello "+self.name }`)
	if _, err := buildModuleInterface(module, "", true, nil); err != nil {
		t.Fatal(err)
	}
	main := writeModuleTestFile(t, root, "main.saga", `use "models.saga" as m
class Local(let id:int) extends m.User { fn label()->text=self.name+":"+text(self.id) }
let x=Local("Aki",7)
print(x.greet())
print(x.label())`)
	stmts, err := loadProgram(main)
	if err != nil {
		t.Fatal(err)
	}
	checker := NewChecker()
	if err = checker.Check(stmts); err != nil {
		t.Fatal(err)
	}
	lines := []string{}
	interp := NewInterpreter(checker, func(s string) { lines = append(lines, s) })
	if err = interp.Interpret(stmts); err != nil {
		t.Fatal(err)
	}
	if got := lines; len(got) != 2 || got[0] != "Hello Aki" || got[1] != "Aki:7" {
		t.Fatalf("unexpected output %#v", got)
	}
}

func TestModuleInterfaceStaleFallsBackToSourceChecking(t *testing.T) {
	root := t.TempDir()
	module := writeModuleTestFile(t, root, "models.saga", `module models
public fn twice(x:int)->int=x*2`)
	if _, err := buildModuleInterface(module, "", true, nil); err != nil {
		t.Fatal(err)
	}
	main := writeModuleTestFile(t, root, "main.saga", `use "models.saga" as m
print(m.twice(2))`)
	if _, err := loadProgram(main); err != nil {
		t.Fatal(err)
	}
	writeModuleTestFile(t, root, "models.saga", `module models
public fn twice(x:int)->int="bad"`)
	stmts, err := loadProgram(main)
	if err != nil {
		t.Fatal(err)
	}
	for _, st := range stmts {
		if m, ok := st.(*SourceModuleStmt); ok && m.Interface != nil {
			t.Fatal("stale interface was trusted")
		}
	}
	if err = NewChecker().Check(stmts); sagaErrorID(err) != "SAGA-T103" {
		t.Fatalf("expected source type error after fallback, got %v", err)
	}
}

func TestModuleInterfaceDependencyABIInvalidation(t *testing.T) {
	root := t.TempDir()
	dep := writeModuleTestFile(t, root, "dep.saga", `module dep
public fn value()->int=1`)
	parent := writeModuleTestFile(t, root, "parent.saga", `module parent
use "dep.saga" as d
public fn doubled()->int=d.value()*2`)
	first, err := buildModuleInterface(parent, "", true, nil)
	if err != nil {
		t.Fatal(err)
	}
	parentIface := filepath.Join(root, "parent.smi.json")
	writeModuleTestFile(t, root, "dep.saga", `module dep
public fn value()->int=2`)
	depIface, err := buildModuleInterface(dep, "", true, nil)
	if err != nil {
		t.Fatal(err)
	}
	if depIface.ABISHA256 != first.Dependencies[0]["abi_sha256"] {
		t.Fatalf("implementation-only change altered ABI: %s vs %s", depIface.ABISHA256, first.Dependencies[0]["abi_sha256"])
	}
	if _, err = verifyModuleInterface(parentIface, parent); err != nil {
		t.Fatalf("parent should stay fresh after implementation-only dependency change: %v", err)
	}
	writeModuleTestFile(t, root, "dep.saga", `module dep
public fn value()->text="2"`)
	if _, err = buildModuleInterface(dep, "", true, nil); err != nil {
		t.Fatal(err)
	}
	if _, err = verifyModuleInterface(parentIface, parent); err == nil {
		t.Fatal("expected parent interface invalidation after dependency ABI change")
	}
}

func TestModuleCanonicalAliasAndPublicBoundary(t *testing.T) {
	root := t.TempDir()
	writeModuleTestFile(t, root, "models.saga", `module models
public fn value()->int=1`)
	main := writeModuleTestFile(t, root, "main.saga", `use "models.saga" as m
use "models.saga"
print(m.value())`)
	_, err := loadProgram(main)
	if sagaErrorID(err) != "SAGA-P109" {
		t.Fatalf("expected canonical alias diagnostic, got %v", err)
	}

	writeModuleTestFile(t, root, "dep.saga", `module dep
public class User(let name:text){}`)
	facade := writeModuleTestFile(t, root, "facade.saga", `module facade
use "dep.saga" as d
public fn make()->d.User=d.User("x")`)
	stmts, err := loadProgram(facade)
	if err == nil {
		err = NewChecker().Check(stmts)
	}
	if sagaErrorID(err) != "SAGA-T118" {
		t.Fatalf("expected public dependency leak rejection, got %v", err)
	}
}

func TestModuleInterfaceMethodOrderDoesNotChangeABI(t *testing.T) {
	root := t.TempDir()
	module := writeModuleTestFile(t, root, "models.saga", `module models
public class User(let name:text){ fn a()->int=1 fn b()->int=2 }`)
	first, err := buildModuleInterface(module, "", true, nil)
	if err != nil {
		t.Fatal(err)
	}
	writeModuleTestFile(t, root, "models.saga", `module models
public class User(let name:text){ fn b()->int=2 fn a()->int=1 }`)
	second, err := buildModuleInterface(module, "", true, nil)
	if err != nil {
		t.Fatal(err)
	}
	if first.ABISHA256 != second.ABISHA256 {
		t.Fatalf("method reordering changed ABI %s -> %s", first.ABISHA256, second.ABISHA256)
	}
}

func TestModuleInterfaceRejectsBuildHashTamperAndSymlinkOutput(t *testing.T) {
	root := t.TempDir()
	module := writeModuleTestFile(t, root, "models.saga", `module models
public fn value()->int=1`)
	iface, err := buildModuleInterface(module, "", true, nil)
	if err != nil {
		t.Fatal(err)
	}
	ifacePath := filepath.Join(root, "models.smi.json")
	iface.BuildSHA256 = strings.Repeat("0", 64)
	b, err := json.Marshal(iface)
	if err != nil {
		t.Fatal(err)
	}
	if err = os.WriteFile(ifacePath, append(b, '\n'), 0644); err != nil {
		t.Fatal(err)
	}
	if _, err = verifyModuleInterface(ifacePath, module); err == nil || !strings.Contains(err.Error(), "build hash") {
		t.Fatalf("expected build hash rejection, got %v", err)
	}

	external := filepath.Join(root, "external.smi.json")
	if err = os.WriteFile(external, []byte("keep"), 0644); err != nil {
		t.Fatal(err)
	}
	linked := filepath.Join(root, "linked.smi.json")
	if err = os.Symlink(external, linked); err != nil {
		t.Skipf("symbolic links unavailable: %v", err)
	}
	if _, err = buildModuleInterface(module, linked, true, nil); err == nil || !strings.Contains(err.Error(), "symbolic link") {
		t.Fatalf("expected symlink output rejection, got %v", err)
	}
	got, err := os.ReadFile(external)
	if err != nil || string(got) != "keep" {
		t.Fatalf("external target changed: %q err=%v", got, err)
	}
}

func TestModulePublicBaseCannotLeakDependencyNominalType(t *testing.T) {
	root := t.TempDir()
	writeModuleTestFile(t, root, "dep.saga", `module dep
public class Base(let name:text){}`)
	facade := writeModuleTestFile(t, root, "facade.saga", `module facade
use "dep.saga" as d
public class Child(let id:int) extends d.Base {}`)
	stmts, err := loadProgram(facade)
	if err == nil {
		err = NewChecker().Check(stmts)
	}
	if sagaErrorID(err) != "SAGA-T118" {
		t.Fatalf("expected public dependency base leak rejection, got %v", err)
	}
}

func TestModuleInterfaceReconstructsInheritedConstructorShape(t *testing.T) {
	root := t.TempDir()
	module := writeModuleTestFile(t, root, "models.saga", `module models
public class Base(let name:text){ fn greet()->text="Hello "+self.name }
public class Child(let id:int) extends Base { fn label()->text=self.name+":"+text(self.id) }`)
	if _, err := buildModuleInterface(module, "", true, nil); err != nil {
		t.Fatal(err)
	}
	main := writeModuleTestFile(t, root, "main.saga", `use "models.saga" as m
let value:m.Child=m.Child("Aki",7)
print(value.greet())
print(value.label())`)
	stmts, err := loadProgram(main)
	if err != nil {
		t.Fatal(err)
	}
	checker := NewChecker()
	if err = checker.Check(stmts); err != nil {
		t.Fatal(err)
	}
	lines := []string{}
	interp := NewInterpreter(checker, func(s string) { lines = append(lines, s) })
	if err = interp.Interpret(stmts); err != nil {
		t.Fatal(err)
	}
	if len(lines) != 2 || lines[0] != "Hello Aki" || lines[1] != "Aki:7" {
		t.Fatalf("unexpected output %#v", lines)
	}
}

func TestLoadProgramUsesSagaTomlProjectRoot(t *testing.T) {
	root := t.TempDir()
	if err := os.MkdirAll(filepath.Join(root, "src"), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(root, "shared"), 0755); err != nil {
		t.Fatal(err)
	}
	manifest := `[project]
name = "module-parity"
version = "0.1.0"
language = "1.0"
entry = "src/main.saga"
`
	if err := os.WriteFile(filepath.Join(root, "saga.toml"), []byte(manifest), 0644); err != nil {
		t.Fatal(err)
	}
	writeModuleTestFile(t, filepath.Join(root, "shared"), "models.saga", `module models
public fn value()->int=42`)
	main := writeModuleTestFile(t, filepath.Join(root, "src"), "main.saga", `use "../shared/models.saga" as m
print(m.value())`)
	stmts, err := loadProgram(main)
	if err != nil {
		t.Fatal(err)
	}
	checker := NewChecker()
	if err = checker.Check(stmts); err != nil {
		t.Fatal(err)
	}
	lines := []string{}
	interp := NewInterpreter(checker, func(s string) { lines = append(lines, s) })
	if err = interp.Interpret(stmts); err != nil {
		t.Fatal(err)
	}
	if len(lines) != 1 || lines[0] != "42" {
		t.Fatalf("unexpected output %#v", lines)
	}
}
