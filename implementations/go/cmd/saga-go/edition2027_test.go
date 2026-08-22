package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func checkSagaSource(t *testing.T, src string) error {
	t.Helper()
	toks, err := lex(src, "<test>")
	if err != nil {
		return err
	}
	stmts, err := parse(toks)
	if err != nil {
		return err
	}
	return NewChecker().Check(stmts)
}

func sagaErrorID(err error) string {
	if e, ok := err.(*SagaError); ok {
		return e.ID
	}
	return ""
}

func TestEdition2027FloatAndFixedWidthIntegers(t *testing.T) {
	src := `
let a:float32=float32(1.5)
let b:float64=2.25f64
let i:int32=int32(2147483647)
let u:uint8=uint8(255)
print(a+float32(0.5))
print(b+float64(0.75))
print(i+int32(1))
print(u)
`
	got, err := runSagaForTest(t, src)
	if err != nil {
		t.Fatal(err)
	}
	if got != "2\n3\n2147483648\n255" {
		t.Fatalf("unexpected output %q", got)
	}
	if _, err = runSagaForTest(t, `print(uint8(256))`); err == nil {
		t.Fatal("expected fixed-width range error")
	}
}

func TestEdition2027ExactFloatBoundaryIsExplicit(t *testing.T) {
	err := checkSagaSource(t, `let x=1 + 1.0f64`)
	if sagaErrorID(err) != "SAGA-T170" {
		t.Fatalf("got %v", err)
	}
}

func TestEdition2027GenericConstraints(t *testing.T) {
	ok := `fn bigger[T](a:T,b:T)->T where T: Comparable { if a>b{return a}; return b }
print(bigger(2,5))`
	got, err := runSagaForTest(t, ok)
	if err != nil || got != "5" {
		t.Fatalf("got=%q err=%v", got, err)
	}
	bad := `class Box(let x:int) {}
fn id[T](x:T)->T where T: Hashable = x
print(id(Box(1)))`
	err = checkSagaSource(t, bad)
	if sagaErrorID(err) != "SAGA-T172" {
		t.Fatalf("expected constraint error, got %v", err)
	}
}

func TestEdition2027AssociatedTypes(t *testing.T) {
	src := `
interface Source { type Item; fn get()->Item }
class IntSource(let value:int) implements Source {
  type Item=int;
  override fn get()->int=self.value
}
fn first[T](x:T)->T.Item where T:Source=x.get()
print(first(IntSource(7)))
`
	got, err := runSagaForTest(t, src)
	if err != nil || got != "7" {
		t.Fatalf("got=%q err=%v", got, err)
	}
}

func TestEdition2027ResourceMoveUsingAndDefer(t *testing.T) {
	src := `
resource class Handle(let value:int) { fn close()->unit { print("close") } }
fn demo()->unit {
  defer print("defer-1")
  defer print("defer-2")
  let h=Handle(7)
  using owned=move h { print(owned.value) }
}
demo()
`
	got, err := runSagaForTest(t, src)
	if err != nil {
		t.Fatal(err)
	}
	if got != "7\nclose\ndefer-2\ndefer-1" {
		t.Fatalf("unexpected cleanup order %q", got)
	}
	bad := `resource class H(let x:int){}
let h=H(1)
let x=move h
print(h.x)`
	err = checkSagaSource(t, bad)
	if sagaErrorID(err) != "SAGA-T180" {
		t.Fatalf("expected static move error, got %v", err)
	}
}

func TestEdition2027TaskPoolUsingAndMove(t *testing.T) {
	src := `
use task
fn identity(value:int)->int=value
using pool=task.pool(1) {
  let pending=task.submit(pool,identity,9)
  print(task.await(pending))
}
var second=task.pool(1)
task.shutdown(move second)
second=task.pool(1)
task.shutdown(move second)
print("ok")
`
	got, err := runSagaForTest(t, src)
	if err != nil {
		t.Fatal(err)
	}
	if got != "9\nok" {
		t.Fatalf("unexpected task pool output %q", got)
	}
}

func TestEdition2027ResultPropagation(t *testing.T) {
	src := `
fn base(okay:bool)->result[int,text] { if okay{return ok(41)}; return err("bad") }
fn plus(okay:bool)->result[int,text] { let x=base(okay)?; return ok(x+1) }
print(unwrap_ok(plus(true)))
print(is_err(plus(false)))
`
	got, err := runSagaForTest(t, src)
	if err != nil || got != "42\ntrue" {
		t.Fatalf("got=%q err=%v", got, err)
	}
}

func TestEdition2027StructuredConcurrencyChannelActor(t *testing.T) {
	src := `
use task
async fn add(a:int,b:int)->int=a+b
fn handler(x:int)->int=x+10
taskgroup {
  let f=add(20,22)
  print(await f)
}
let ch=task.channel(1)
task.send(ch,5)
print(unwrap(task.recv(ch)))
task.close(ch)
let actor=task.actor(handler)
print(await task.ask(actor,5))
`
	got, err := runSagaForTest(t, src)
	if err != nil || got != "42\n5\n15" {
		t.Fatalf("got=%q err=%v", got, err)
	}
}

func TestEdition2027ComptimeActuallyFolds(t *testing.T) {
	src := `comptime fn square(x:int)->int=x*x
let answer=square(9)`
	toks, err := lex(src, "<test>")
	if err != nil {
		t.Fatal(err)
	}
	stmts, err := parse(toks)
	if err != nil {
		t.Fatal(err)
	}
	c := NewChecker()
	if err = c.Check(stmts); err != nil {
		t.Fatal(err)
	}
	out := optimizeProgram(stmts)
	v := out[1].(*VarDecl)
	lit, ok := v.Init.(*Literal)
	if !ok || formatValue(lit.Value, false) != "81" {
		t.Fatalf("comptime call was not folded: %#v", v.Init)
	}
	if err = checkSagaSource(t, `comptime fn f(x:int)->int=x+1
let y=2
print(f(y))`); sagaErrorID(err) != "SAGA-T179" {
		t.Fatalf("expected dynamic comptime rejection, got %v", err)
	}
}

func TestEdition2027DeriveIsHygienicAndStructural(t *testing.T) {
	src := `
@derive("Equal","Hash","Debug")
class Key(private let secret:int,let name:text){}
let a=Key(7,"x")
let b=Key(7,"x")
print(a==b)
let m=map_of(a,"ok")
print(map_get(m,b,"bad"))
print(a)
`
	got, err := runSagaForTest(t, src)
	if err != nil {
		t.Fatal(err)
	}
	if got != "true\nok\nKey(secret=7, name=x)" {
		t.Fatalf("unexpected derive output %q", got)
	}
}

func TestEdition2027UnsafeFFIIsFailClosed(t *testing.T) {
	err := checkSagaSource(t, `use ffi
print(ffi.call_i64("libc.so.6","labs",[-1]))`)
	if sagaErrorID(err) != "SAGA-T178" {
		t.Fatalf("expected unsafe boundary, got %v", err)
	}
	got, err := runSagaForTest(t, `use ffi
print(ffi.available())`)
	want := "false"
	if ffiAvailable() {
		want = "true"
	}
	if err != nil || got != want {
		t.Fatalf("ffi availability must match build profile: got=%q want=%q err=%v", got, want, err)
	}
}

func TestEdition2027SourceModuleNamespace(t *testing.T) {
	root := t.TempDir()
	module := `module models
public class User(let name:text){ fn greet()->text="Hello "+self.name }
public fn twice(x:int)->int=x*2
fn hidden()->int=99`
	main := `use "models.saga" as m
let u:m.User=m.User("Aki")
print(u.greet())
print(m.twice(21))`
	if err := os.WriteFile(filepath.Join(root, "models.saga"), []byte(module), 0644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "main.saga"), []byte(main), 0644); err != nil {
		t.Fatal(err)
	}
	stmts, err := loadProgram(filepath.Join(root, "main.saga"))
	if err != nil {
		t.Fatal(err)
	}
	c := NewChecker()
	if err = c.Check(stmts); err != nil {
		t.Fatal(err)
	}
	lines := []string{}
	it := NewInterpreter(c, func(s string) { lines = append(lines, s) })
	if err = it.Interpret(stmts); err != nil {
		t.Fatal(err)
	}
	if strings.Join(lines, "\n") != "Hello Aki\n42" {
		t.Fatalf("bad module output %q", strings.Join(lines, "\n"))
	}
	bad := `use "models.saga" as m
print(m.hidden())`
	if err = os.WriteFile(filepath.Join(root, "bad.saga"), []byte(bad), 0644); err != nil {
		t.Fatal(err)
	}
	stmts, err = loadProgram(filepath.Join(root, "bad.saga"))
	if err != nil {
		t.Fatal(err)
	}
	err = NewChecker().Check(stmts)
	if sagaErrorID(err) != "SAGA-T106" {
		t.Fatalf("private module export leaked: %v", err)
	}
}

func TestEdition2027ActorPreservesIsolatedStateAndStops(t *testing.T) {
	src := `
use task
fn make_counter()->fn[int,int] {
  var total=0
  fn handle(x:int)->int { total=total+x; return total }
  return handle
}
let actor=task.actor(make_counter())
print(await task.ask(actor,2))
print(await task.ask(actor,3))
task.stop(actor)
`
	got, err := runSagaForTest(t, src)
	if err != nil || got != "2\n5" {
		t.Fatalf("actor state was not isolated/persistent: got=%q err=%v", got, err)
	}
}

func TestEdition2027KeywordsRemainContextualForLegacyCode(t *testing.T) {
	src := `
let async=40
let resource=2
fn module(x:int)->int=x+1
fn await(x:int)->int=x
print(async+resource)
print(module(await(41)))
`
	got, err := runSagaForTest(t, src)
	if err != nil || got != "42\n42" {
		t.Fatalf("new contextual words broke legacy identifiers: got=%q err=%v", got, err)
	}
}

func TestEdition2027PortableGPUComputeIRFromSaga(t *testing.T) {
	src := `
use game
let ir="SIR1\nstage compute\nscale 2\nadd -1\nclamp 0 10\n"
let glsl=unwrap_ok(game.shader_ir_compile(ir,"glsl450"))
print(len(glsl)>0)
let values=unwrap_ok(game.shader_ir_compute_reference(ir,[float64(-2),float64(1),float64(8)]))
print(values)
`
	got, err := runSagaForTest(t, src)
	if err != nil || got != "true\n[0, 1, 10]" {
		t.Fatalf("portable compute IR failed: got=%q err=%v", got, err)
	}
}

func TestEdition2027EmbeddedWASMHasNoImports(t *testing.T) {
	root := t.TempDir()
	src := `edition 2027
public fn add(a:int,b:int)->int=a+b
public fn formula(x:int)->int=add(x,3)*2`
	in := filepath.Join(root, "embedded.saga")
	out := filepath.Join(root, "embedded.wasm")
	if err := os.WriteFile(in, []byte(src), 0644); err != nil {
		t.Fatal(err)
	}
	if _, err := buildEmbeddedWASM(in, out); err != nil {
		t.Fatal(err)
	}
	b, err := os.ReadFile(out)
	if err != nil {
		t.Fatal(err)
	}
	if len(b) < 8 || string(b[:4]) != "\x00asm" {
		t.Fatal("invalid wasm magic")
	}
	// The freestanding profile deliberately emits no section 2 (imports).
	for p := 8; p < len(b); {
		id := b[p]
		p++
		sz, n := readULEBForTest(b[p:])
		if n == 0 {
			t.Fatal("invalid wasm section length")
		}
		p += n
		if id == 2 {
			t.Fatal("embedded wasm unexpectedly contains imports")
		}
		p += int(sz)
		if p > len(b) {
			t.Fatal("truncated wasm section")
		}
	}
}

func readULEBForTest(b []byte) (uint64, int) {
	var v uint64
	for i, q := range b {
		v |= uint64(q&0x7f) << (7 * i)
		if q&0x80 == 0 {
			return v, i + 1
		}
		if i >= 9 {
			return 0, 0
		}
	}
	return 0, 0
}

func TestEdition2027ResourceReassignmentRestoresOwnership(t *testing.T) {
	src := `
resource class H(let x:int) {}
var h=H(1)
let first=move h
h=H(2)
print(h.x)
print(first.x)
`
	got, err := runSagaForTest(t, src)
	if err != nil || got != "2\n1" {
		t.Fatalf("resource reassignment failed to restore ownership: got=%q err=%v", got, err)
	}
}

func TestEdition2027NamespacedInterfaceConstraintAndAssociatedType(t *testing.T) {
	root := t.TempDir()
	module := `module models
public interface Source { type Item; fn get()->Item }
public class IntSource(let value:int) implements Source {
  type Item=int
  override fn get()->int=self.value
}`
	main := `edition 2027
use "models.saga" as models
fn first[T](source:T)->T.Item where T:models.Source=source.get()
print(first(models.IntSource(7)))`
	if err := os.WriteFile(filepath.Join(root, "models.saga"), []byte(module), 0644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "main.saga"), []byte(main), 0644); err != nil {
		t.Fatal(err)
	}
	stmts, err := loadProgram(filepath.Join(root, "main.saga"))
	if err != nil {
		t.Fatal(err)
	}
	c := NewChecker()
	if err = c.Check(stmts); err != nil {
		t.Fatal(err)
	}
	lines := []string{}
	it := NewInterpreter(c, func(s string) { lines = append(lines, s) })
	if err = it.Interpret(stmts); err != nil {
		t.Fatal(err)
	}
	if strings.Join(lines, "\n") != "7" {
		t.Fatalf("unexpected namespaced associated-type output %q", strings.Join(lines, "\n"))
	}
}

func TestEdition2027NamespacedGenericFunctionExportsQualifiedTypes(t *testing.T) {
	root := t.TempDir()
	module := `module models
public interface Source { type Item; fn get()->Item }
public class IntSource(let value:int) implements Source {
  type Item=int
  override fn get()->int=self.value
}
public fn first[T](source:T)->T.Item where T:Source=source.get()
public fn make()->IntSource=IntSource(9)`
	main := `edition 2027
use "models.saga" as m
print(m.first(m.IntSource(8)))
print(m.make().get())`
	if err := os.WriteFile(filepath.Join(root, "models.saga"), []byte(module), 0644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "main.saga"), []byte(main), 0644); err != nil {
		t.Fatal(err)
	}
	stmts, err := loadProgram(filepath.Join(root, "main.saga"))
	if err != nil {
		t.Fatal(err)
	}
	c := NewChecker()
	if err = c.Check(stmts); err != nil {
		t.Fatal(err)
	}
	lines := []string{}
	it := NewInterpreter(c, func(s string) { lines = append(lines, s) })
	if err = it.Interpret(stmts); err != nil {
		t.Fatal(err)
	}
	if strings.Join(lines, "\n") != "8\n9" {
		t.Fatalf("unexpected module-generic output %q", strings.Join(lines, "\n"))
	}
}

func TestEdition2027NamespacedGenericClassAndEnum(t *testing.T) {
	root := t.TempDir()
	module := `module api
public class Box[T](let value:T) where T:Hashable {}
public fn value_of[T](box:Box[T])->T=box.value
public enum Color{Red,Green}`
	main := `edition 2027
use "api.saga" as api
let b=api.Box(7)
print(api.value_of(b))
match api.Color.Green {
  case api.Color.Red { print("r") }
  case api.Color.Green { print("g") }
}`
	if err := os.WriteFile(filepath.Join(root, "api.saga"), []byte(module), 0644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "main.saga"), []byte(main), 0644); err != nil {
		t.Fatal(err)
	}
	stmts, err := loadProgram(filepath.Join(root, "main.saga"))
	if err != nil {
		t.Fatal(err)
	}
	c := NewChecker()
	if err = c.Check(stmts); err != nil {
		t.Fatal(err)
	}
	lines := []string{}
	it := NewInterpreter(c, func(s string) { lines = append(lines, s) })
	if err = it.Interpret(stmts); err != nil {
		t.Fatal(err)
	}
	if strings.Join(lines, "\n") != "7\ng" {
		t.Fatalf("unexpected namespaced generic/enum output %q", strings.Join(lines, "\n"))
	}
}

func TestDiagnosticsSuggestNearbyName(t *testing.T) {
	err := checkSagaSource(t, `let answer=42
print(answr)`)
	if sagaErrorID(err) != "SAGA-T102" || !strings.Contains(err.Error(), "did you mean `answer`") {
		t.Fatalf("expected spelling suggestion, got %v", err)
	}
}
