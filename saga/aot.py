from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json, shutil, subprocess, tempfile, re, os

from . import ast_nodes as ast
from .api import compile_file
from .tokens import TokenKind

class AOTError(ValueError): pass

@dataclass(frozen=True, slots=True)
class BuildResult:
    target: str
    output: Path
    generated_c: Path | None = None
    wit: Path | None = None


def _protected_build_inputs(source: Path) -> set[Path]:
    from .source_units import load_program
    loaded = load_program(source)
    protected = {p.resolve() for p in loaded.files}
    manifest = loaded.root / "saga.toml"
    if manifest.is_file():
        protected.add(manifest.resolve())
    dep = loaded.root / "saga.dependencies.json"
    if dep.is_file():
        protected.add(dep.resolve())
    return protected

def _reject_symlink_output(path: Path) -> None:
    """Reject symlinks in the user-controlled portion of a build output path.

    Absolute platform prefixes may themselves be canonical symlinks (notably
    macOS ``/var``).  For absolute paths outside the current working tree, the
    explicitly named output itself is checked; relative/CWD-contained paths are
    checked component-by-component.
    """
    raw = path.expanduser()
    if raw.is_symlink():
        raise AOTError(f"build output path may not contain a symbolic link: {raw}")
    absolute = raw.absolute()
    cwd = Path.cwd().absolute()
    try:
        relative = absolute.relative_to(cwd)
    except ValueError:
        return
    current = cwd
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise AOTError(f"build output path may not contain a symbolic link: {current}")

def _reject_output_collision(source: Path, out: Path, *, extra_inputs: tuple[Path, ...] = ()) -> None:
    _reject_symlink_output(out)
    protected = _protected_build_inputs(source)
    protected.update(path.resolve() for path in extra_inputs)
    if out.resolve() in protected:
        raise AOTError(f"build output may not overwrite a build input: {out}")

def _compiler_temp_output(out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{out.name}.", suffix=".tmp", dir=out.parent)
    os.close(fd)
    return Path(name)

class CEmitter:
    """Small, auditable AOT backend for a checked int64 deployment subset.

    Saga's Standard Core ``int`` is arbitrary precision and integer division is
    exact rational division. The scalar backend therefore traps checked-int64
    overflow and rejects operations (such as ``/``) whose Standard semantics it
    cannot preserve, instead of silently changing results. Use the Standard
    bundle/reference runtime for the complete language.
    """
    def __init__(self, wasm: bool = False) -> None:
        self.wasm = wasm
        self.indent = 0
        self.lines: list[str] = []
        self.locals: list[set[str]] = [set()]
        self.local_types: list[dict[str, str]] = [{}]
        self.function_return_types: dict[str, str] = {}
        self.temp_counter = 0
        self.function_depth = 0
        self.top_level_bindings: set[str] = set()

    def emit(self, program: ast.Program) -> str:
        self.top_level_bindings = {
            stmt.name.lexeme for stmt in program.statements if isinstance(stmt, ast.VarDecl)
        }
        self.top_level_bindings.update(
            stmt.target.name.lexeme
            for stmt in program.statements
            if isinstance(stmt, ast.Assign) and isinstance(stmt.target, ast.Variable)
        )
        self.lines = [
            '#include <stdint.h>',
            '#include <stdbool.h>',
        ]
        if self.wasm:
            self.lines += ['extern void saga_print_i64(int64_t);']
            overflow_action = '__builtin_trap();'
            modulo_zero_action = '__builtin_trap();'
        else:
            self.lines += ['#include <stdio.h>', '#include <stdlib.h>']
            overflow_action = 'fputs("Saga scalar AOT integer overflow\\n", stderr); exit(70);'
            modulo_zero_action = 'fputs("Saga scalar AOT modulo by zero\\n", stderr); exit(71);'
        self.lines += [
            '',
            f'static void saga_int_overflow(void) {{ {overflow_action} }}',
            f'static void saga_modulo_zero(void) {{ {modulo_zero_action} }}',
            'static int64_t saga_checked_add(int64_t a, int64_t b) { int64_t r; if (__builtin_add_overflow(a,b,&r)) saga_int_overflow(); return r; }',
            'static int64_t saga_checked_sub(int64_t a, int64_t b) { int64_t r; if (__builtin_sub_overflow(a,b,&r)) saga_int_overflow(); return r; }',
            'static int64_t saga_checked_mul(int64_t a, int64_t b) { int64_t r; if (__builtin_mul_overflow(a,b,&r)) saga_int_overflow(); return r; }',
            'static int64_t saga_checked_neg(int64_t a) { if (a == INT64_MIN) saga_int_overflow(); return -a; }',
            'static int64_t saga_checked_abs(int64_t a) { return a < 0 ? saga_checked_neg(a) : a; }',
            'static int64_t saga_checked_mod(int64_t a, int64_t b) { if (b == 0) saga_modulo_zero(); if (a == INT64_MIN && b == -1) return 0; return a % b; }',
            '',
        ]
        functions = [stmt for stmt in program.statements if isinstance(stmt, ast.FunctionDecl)]
        self.function_return_types = {
            fn.name.lexeme: ("bool" if fn.return_type in {"bool", "Bool"} else "int" if fn.return_type in {"int", "Int"} else "unit")
            for fn in functions
        }
        for fn in functions:
            ret, params = self._function_signature(fn)
            self.lines.append(f'static {ret} {self._fn_name(fn.name.lexeme)}({params});')
        if functions:
            self.lines.append('')
        for stmt in program.statements:
            if isinstance(stmt, ast.FunctionDecl): self._function(stmt)
            elif isinstance(stmt, (ast.ClassDecl, ast.UseStmt)):
                if isinstance(stmt, ast.UseStmt):
                    raise AOTError('AOT scalar profile does not import hosted modules')
                raise AOTError('AOT scalar profile does not yet lower classes')
        self.lines.append('')
        self.lines.append('void _start(void) {' if self.wasm else 'int main(void) {')
        self.indent += 1; self.locals.append(set()); self.local_types.append({})
        for stmt in program.statements:
            if not isinstance(stmt, (ast.FunctionDecl, ast.ClassDecl, ast.UseStmt)): self._stmt(stmt)
        if not self.wasm: self._line('return 0;')
        self.locals.pop(); self.local_types.pop(); self.indent -= 1; self.lines.append('}')
        return '\n'.join(self.lines) + '\n'

    def _line(self, text=''): self.lines.append('    '*self.indent + text)
    def _has_local(self, name: str) -> bool:
        return any(name in scope for scope in reversed(self.locals))
    def _lookup_scalar_type(self, name: str) -> str | None:
        for scope in reversed(self.local_types):
            if name in scope:
                return scope[name]
        return None
    def _expr_scalar_type(self, expr: ast.Expr) -> str:
        if isinstance(expr, ast.Literal):
            if isinstance(expr.value, bool): return "bool"
            if isinstance(expr.value, int): return "int"
        if isinstance(expr, ast.Variable):
            return self._lookup_scalar_type(expr.name.lexeme) or "int"
        if isinstance(expr, ast.Unary):
            return "bool" if expr.operator.kind in {TokenKind.BANG, TokenKind.NOT} else "int"
        if isinstance(expr, ast.Binary):
            if expr.operator.kind in {TokenKind.EQUAL_EQUAL, TokenKind.BANG_EQUAL, TokenKind.LESS, TokenKind.LESS_EQUAL, TokenKind.GREATER, TokenKind.GREATER_EQUAL, TokenKind.AND, TokenKind.OR}:
                return "bool"
            return "int"
        if isinstance(expr, ast.Call) and isinstance(expr.callee, ast.Variable):
            if expr.callee.name.lexeme == "abs": return "int"
            return self.function_return_types.get(expr.callee.name.lexeme, "int")
        return "int"
    def _new_temp(self, prefix: str) -> str:
        self.temp_counter += 1
        return f"__saga_{prefix}_{self.temp_counter}"
    @staticmethod
    def _symbol(prefix: str, name: str) -> str:
        # Never emit a Saga identifier directly as C. Saga accepts Unicode and
        # names such as ``long``/``switch`` that are reserved by C; byte-hex
        # mangling is deterministic, collision-free and independent of locale.
        encoded = name.encode("utf-8").hex() or "00"
        return f"saga_{prefix}_{encoded}"
    @classmethod
    def _var_name(cls, name: str) -> str:
        return cls._symbol("v", name)
    @classmethod
    def _fn_name(cls, name: str) -> str:
        return cls._symbol("fn", name)
    @staticmethod
    def _c_string(value: str) -> str:
        # Encode UTF-8 bytes explicitly. JSON's surrogate-pair escapes are not
        # valid C universal-character names for non-BMP text.
        pieces = []
        for byte in value.encode("utf-8"):
            if 0x20 <= byte <= 0x7e and byte not in {0x22, 0x5c}:
                pieces.append(chr(byte))
            elif byte == 0x22:
                pieces.append('\\"')
            elif byte == 0x5c:
                pieces.append('\\\\')
            elif byte == 0x0a:
                pieces.append('\\n')
            elif byte == 0x0d:
                pieces.append('\\r')
            elif byte == 0x09:
                pieces.append('\\t')
            else:
                # C hex escapes consume an arbitrary number of following hex
                # digits ("\\xa9A" is one escape), so use fixed-width
                # three-digit octal escapes for byte-exact UTF-8 emission.
                pieces.append(f"\\{byte:03o}")
        return '"' + ''.join(pieces) + '"'
    @staticmethod
    def _contains_call(expr: ast.Expr) -> bool:
        if isinstance(expr, ast.Call): return True
        if isinstance(expr, ast.PropagateExpr): return CEmitter._contains_call(expr.value)
        if isinstance(expr, ast.Unary): return CEmitter._contains_call(expr.right)
        if isinstance(expr, ast.Binary): return CEmitter._contains_call(expr.left) or CEmitter._contains_call(expr.right)
        if isinstance(expr, ast.RangeExpr): return CEmitter._contains_call(expr.start) or CEmitter._contains_call(expr.end)
        if isinstance(expr, ast.Index): return CEmitter._contains_call(expr.target) or CEmitter._contains_call(expr.index)
        if isinstance(expr, ast.Member): return CEmitter._contains_call(expr.target)
        if isinstance(expr, ast.ListLiteral): return any(CEmitter._contains_call(item) for item in expr.elements)
        return False
    def _ctype(self, name: str | None) -> str:
        if name in {None, 'unit', 'Unit'}: return 'void'
        if name in {'int','Int','bool','Bool'}: return 'int64_t'
        raise AOTError(f'AOT scalar profile type not supported: {name}')
    def _function_signature(self, fn: ast.FunctionDecl) -> tuple[str, str]:
        if fn.type_params or fn.abstract or fn.override:
            raise AOTError('AOT scalar profile does not lower generic/abstract/override functions')
        if any(p.type_name in {None, 'unit', 'Unit'} for p in fn.parameters):
            raise AOTError('AOT scalar does not lower unit-valued function parameters yet; use the Standard profile')
        ret = self._ctype(fn.return_type)
        params = ', '.join(
            f'{self._ctype(p.type_name)} {self._var_name(p.name.lexeme)}' for p in fn.parameters
        ) or 'void'
        return ret, params

    def _function(self, fn: ast.FunctionDecl) -> None:
        ret, params = self._function_signature(fn)
        self.lines.append(f'static {ret} {self._fn_name(fn.name.lexeme)}({params}) {{')
        self.indent += 1
        self.locals.append({p.name.lexeme for p in fn.parameters})
        self.local_types.append({
            p.name.lexeme: ("bool" if p.type_name in {"bool", "Bool"} else "int")
            for p in fn.parameters
        })
        self.function_depth += 1
        try:
            if fn.expression_body is not None:
                if ret == 'void': self._line(self._expr(fn.expression_body)+';')
                else: self._line('return '+self._expr(fn.expression_body)+';')
            elif fn.body is not None:
                for st in fn.body.statements:
                    if isinstance(st, ast.FunctionDecl): raise AOTError('lexical closures are runtime-supported but not yet lowered by scalar AOT')
                    self._stmt(st)
        finally:
            self.function_depth -= 1
            self.locals.pop()
            self.local_types.pop()
            self.indent -= 1
        self.lines.append('}')
    def _stmt(self, st: ast.Stmt) -> None:
        if isinstance(st, ast.VarDecl):
            if st.type_name and self._ctype(st.type_name)!='int64_t': raise AOTError('unsupported variable type')
            self.locals[-1].add(st.name.lexeme)
            declared_kind = "bool" if st.type_name in {"bool", "Bool"} else self._expr_scalar_type(st.initializer)
            self.local_types[-1][st.name.lexeme] = declared_kind
            if declared_kind == "unit":
                if isinstance(st.initializer, ast.Call): self._line(self._expr(st.initializer) + ';')
                else: raise AOTError('AOT scalar unit bindings currently require a unit-returning direct call')
            else:
                self._line(f'int64_t {self._var_name(st.name.lexeme)} = {self._expr(st.initializer)};')
            return
        if isinstance(st, ast.Assign):
            if not isinstance(st.target, ast.Variable): raise AOTError('AOT supports scalar variable assignment only')
            name = st.target.name.lexeme
            if self.function_depth and not self._has_local(name) and name in self.top_level_bindings:
                raise AOTError(
                    f"AOT scalar functions do not lower top-level binding capture/mutation yet: {name}. "
                    "Use parameters/local bindings or the Standard profile"
                )
            if not self._has_local(name):
                # Mirrors Natural Saga's first-assignment binding for the
                # scalar native profile. The C backend still intentionally
                # rejects non-scalar natural features it cannot preserve.
                self.locals[-1].add(name)
                inferred_kind = self._expr_scalar_type(st.value)
                self.local_types[-1][name] = inferred_kind
                if inferred_kind == "unit":
                    if isinstance(st.value, ast.Call): self._line(self._expr(st.value) + ';')
                    else: raise AOTError('AOT scalar unit bindings currently require a unit-returning direct call')
                else:
                    self._line(f'int64_t {self._var_name(name)} = {self._expr(st.value)};')
            else:
                existing_kind = self._lookup_scalar_type(name)
                if existing_kind == "unit":
                    if isinstance(st.value, ast.Call): self._line(self._expr(st.value) + ';')
                    else: raise AOTError('AOT scalar unit assignment currently requires a unit-returning direct call')
                else:
                    self._line(f'{self._var_name(name)} = {self._expr(st.value)};')
            return
        if isinstance(st, ast.ExpressionStmt):
            if isinstance(st.expression, ast.Call) and isinstance(st.expression.callee, ast.Variable) and st.expression.callee.name.lexeme=='print':
                args = st.expression.arguments
                if self.wasm:
                    if len(args) != 1 or (args and isinstance(args[0], ast.Literal) and isinstance(args[0].value, str)):
                        raise AOTError('WASM scalar print currently supports exactly one int value')
                    if self._expr_scalar_type(args[0]) == "bool":
                        raise AOTError('WASM scalar print cannot preserve Saga true/false text formatting yet')
                    self._line(f'saga_print_i64({self._expr(args[0])});')
                else:
                    # Saga evaluates all arguments left-to-right before print itself
                    # emits anything. Materialize scalar arguments first so later
                    # argument side effects cannot be interleaved with outer output.
                    prepared: list[tuple[str, str | ast.Expr]] = []
                    for arg in args:
                        if isinstance(arg, ast.Literal) and isinstance(arg.value, str):
                            prepared.append(("text", arg))
                            continue
                        kind = self._expr_scalar_type(arg)
                        if kind == "unit":
                            if isinstance(arg, ast.Call):
                                self._line(self._expr(arg) + ';')
                            elif not isinstance(arg, ast.Variable):
                                raise AOTError('AOT scalar cannot materialize this unit-valued print argument')
                            prepared.append(("unit", arg))
                            continue
                        temp = self._new_temp('print_arg')
                        self._line(f'int64_t {temp} = {self._expr(arg)};')
                        prepared.append((kind, temp))
                    for index, (kind, payload) in enumerate(prepared):
                        if index: self._line('fputc(32, stdout);')
                        if kind == "text":
                            assert isinstance(payload, ast.Literal) and isinstance(payload.value, str)
                            encoded_len = len(payload.value.encode("utf-8"))
                            self._line(f'fwrite({self._c_string(payload.value)}, 1, {encoded_len}, stdout);')
                        elif kind == "bool":
                            assert isinstance(payload, str)
                            self._line(f'fputs(({payload}) ? "true" : "false", stdout);')
                        elif kind == "unit":
                            self._line('fputs("unit", stdout);')
                        else:
                            assert isinstance(payload, str)
                            self._line(f'printf("%lld", (long long)({payload}));')
                    self._line("fputc('\\n', stdout);")
            else: self._line(self._expr(st.expression)+';')
            return
        if isinstance(st, ast.IfStmt):
            self._line(f'if ({self._expr(st.condition)}) {{'); self.indent+=1; self.locals.append(set()); self.local_types.append({})
            for q in st.then_branch.statements: self._stmt(q)
            self.locals.pop(); self.local_types.pop(); self.indent-=1; self._line('}')
            if st.else_branch:
                self._line('else {'); self.indent+=1; self.locals.append(set()); self.local_types.append({})
                for q in st.else_branch.statements: self._stmt(q)
                self.locals.pop(); self.local_types.pop(); self.indent-=1; self._line('}')
            return
        if isinstance(st, ast.WhileStmt):
            self._line(f'while ({self._expr(st.condition)}) {{'); self.indent+=1; self.locals.append(set()); self.local_types.append({})
            for q in st.body.statements: self._stmt(q)
            self.locals.pop(); self.local_types.pop(); self.indent-=1; self._line('}'); return
        if isinstance(st, ast.ForStmt):
            if not isinstance(st.iterable, ast.RangeExpr): raise AOTError('AOT for currently requires an integer range')
            a,b=self._expr(st.iterable.start),self._expr(st.iterable.end); n=st.name.lexeme
            start_tmp, end_tmp, step_tmp = self._new_temp('range_start'), self._new_temp('range_end'), self._new_temp('range_step')
            keep_tmp = self._new_temp('range_keep')
            self._line('{'); self.indent += 1; self.locals.append(set()); self.local_types.append({})
            self._line(f'int64_t {start_tmp} = {a};')
            self._line(f'int64_t {end_tmp} = {b};')
            self._line(f'int64_t {step_tmp} = ({end_tmp} >= {start_tmp}) ? 1 : -1;')
            cn = self._var_name(n)
            # Put termination/update in the C for-update expression so Saga
            # `continue` still advances and terminates on the inclusive endpoint.
            # Avoid incrementing the endpoint itself, which would overflow at
            # INT64_MAX/INT64_MIN even though Saga's finite range is complete.
            self._line(
                f'for (int64_t {cn} = {start_tmp}, {keep_tmp} = 1; {keep_tmp}; '
                f'{keep_tmp} = ({cn} == {end_tmp}) ? 0 : ({cn} = saga_checked_add({cn}, {step_tmp}), 1)) {{'
            )
            self.indent+=1; self.locals.append({n}); self.local_types.append({n: "int"})
            for q in st.body.statements: self._stmt(q)
            self.locals.pop(); self.local_types.pop(); self.indent-=1; self._line('}')
            self.locals.pop(); self.local_types.pop(); self.indent -= 1; self._line('}'); return
        if isinstance(st, ast.ReturnStmt): self._line('return'+((' '+self._expr(st.value)) if st.value else '')+';'); return
        if isinstance(st, ast.BreakStmt): self._line('break;'); return
        if isinstance(st, ast.ContinueStmt): self._line('continue;'); return
        if isinstance(st, ast.Block):
            self._line('{'); self.indent+=1; self.locals.append(set()); self.local_types.append({})
            for q in st.statements: self._stmt(q)
            self.locals.pop(); self.local_types.pop(); self.indent-=1; self._line('}'); return
        raise AOTError(f'AOT scalar profile statement not supported: {type(st).__name__}')
    def _expr(self, e: ast.Expr) -> str:
        if isinstance(e, ast.Literal):
            if isinstance(e.value,bool): return '1' if e.value else '0'
            if isinstance(e.value,int):
                if not -(2**63) <= e.value <= 2**63 - 1:
                    raise AOTError('AOT scalar int literal exceeds the checked int64 deployment subset')
                return str(e.value)
            if isinstance(e.value,str) and not self.wasm: return self._c_string(e.value)
            raise AOTError('AOT scalar expression supports int/bool (and native text print)')
        if isinstance(e, ast.Variable):
            name = e.name.lexeme
            if self._lookup_scalar_type(name) == "unit":
                raise AOTError('AOT scalar cannot materialize a unit binding as a C scalar value')
            if self.function_depth and not self._has_local(name) and name in self.top_level_bindings:
                raise AOTError(
                    f"AOT scalar functions do not lower top-level binding capture yet: {name}. "
                    "Use parameters/local bindings or the Standard profile"
                )
            return self._var_name(name)
        if isinstance(e, ast.Unary):
            if e.operator.kind in {TokenKind.BANG, TokenKind.NOT}: return f'(!{self._expr(e.right)})'
            if e.operator.kind is TokenKind.MINUS:
                if isinstance(e.right, ast.Literal) and isinstance(e.right.value, int) and not isinstance(e.right.value, bool):
                    value = -e.right.value
                    if not -(2**63) <= value <= 2**63 - 1:
                        raise AOTError('AOT scalar integer negation exceeds the checked int64 deployment subset')
                    return str(value)
                return f'saga_checked_neg({self._expr(e.right)})'
            raise AOTError('unsupported AOT unary operator')
        if isinstance(e, ast.Binary):
            kind = e.operator.kind
            if self._contains_call(e.left) and self._contains_call(e.right):
                raise AOTError('AOT scalar cannot preserve Saga left-to-right evaluation for calls on both sides of an operator yet')
            left, right = self._expr(e.left), self._expr(e.right)
            if kind is TokenKind.PLUS: return f'saga_checked_add({left}, {right})'
            if kind is TokenKind.MINUS: return f'saga_checked_sub({left}, {right})'
            if kind is TokenKind.STAR: return f'saga_checked_mul({left}, {right})'
            if kind is TokenKind.SLASH: raise AOTError('AOT scalar does not lower exact rational division; use the Standard profile')
            if kind is TokenKind.POWER: raise AOTError('power requires runtime exact-numeric lowering')
            if kind is TokenKind.PERCENT: return f'saga_checked_mod({left}, {right})'
            m={TokenKind.EQUAL_EQUAL:'==',TokenKind.BANG_EQUAL:'!=',TokenKind.LESS:'<',TokenKind.LESS_EQUAL:'<=',TokenKind.GREATER:'>',TokenKind.GREATER_EQUAL:'>=',TokenKind.AND:'&&',TokenKind.OR:'||'}
            if kind not in m: raise AOTError('unsupported AOT operator')
            return f'({left} {m[kind]} {right})'
        if isinstance(e, ast.Call):
            if isinstance(e.callee, ast.Variable):
                n=e.callee.name.lexeme
                if sum(1 for arg in e.arguments if self._contains_call(arg)) > 1:
                    raise AOTError('AOT scalar cannot preserve Saga left-to-right evaluation for multiple effectful call arguments yet')
                rendered = [self._expr(a) for a in e.arguments]
                if n=='abs':
                    if len(rendered) != 1: raise AOTError('abs requires one scalar argument')
                    arg = rendered[0]
                    return f'saga_checked_abs({arg})'
                return f'{self._fn_name(n)}({", ".join(rendered)})'
            raise AOTError('AOT scalar profile supports direct function calls only')
        if isinstance(e, ast.PropagateExpr):
            raise AOTError('AOT scalar does not lower postfix ? propagation; use the Standard/reference profile')
        raise AOTError(f'AOT scalar expression not supported: {type(e).__name__}')

def emit_c(source: str|Path, *, wasm: bool=False) -> str:
    loaded=compile_file(str(Path(source).expanduser()))
    return CEmitter(wasm=wasm).emit(loaded.program)

def build(source: str|Path, target: str, output: str|Path|None=None, *, clang: str|None=None) -> BuildResult:
    source_input = Path(source).expanduser()
    # Validate the caller-provided path before canonicalizing it so the scalar
    # build path cannot bypass the source loader's no-symlink entry policy.
    compile_file(str(source_input))
    source=source_input.resolve(); clang=clang or shutil.which('clang')
    if not clang: raise AOTError('clang is required for native/WASM AOT builds')
    out=Path(output).expanduser() if output else source.with_suffix('.wasm' if target=='wasm' else '')
    if target=='native' and not output: out=source.parent/(source.stem + ('.exe' if os.name=='nt' else ''))
    _reject_symlink_output(out)
    out=out.resolve()
    compiler_path = Path(clang).resolve()
    _reject_output_collision(source, out, extra_inputs=(compiler_path,))
    if target == 'wasm':
        _reject_output_collision(source, out.with_suffix('.wit'), extra_inputs=(compiler_path,))
    c=emit_c(source_input, wasm=(target=='wasm'))
    builddir=Path(tempfile.mkdtemp(prefix='saga-aot-')); cpath=builddir/'program.c'; cpath.write_text(c,encoding='utf-8')
    tmp_out=_compiler_temp_output(out)
    try:
        if target=='native': cmd=[clang,'-O2','-std=c11',str(cpath),'-o',str(tmp_out)]
        elif target=='wasm': cmd=[clang,'--target=wasm32','-O2','-nostdlib',str(cpath),'-Wl,--no-entry','-Wl,--export=_start','-Wl,--allow-undefined','-o',str(tmp_out)]
        else: raise AOTError('target must be native or wasm')
        proc=subprocess.run(cmd,text=True,capture_output=True)
        if proc.returncode: raise AOTError(proc.stderr.strip() or 'compiler failed')
        os.replace(tmp_out,out)
    finally:
        tmp_out.unlink(missing_ok=True)
    wit=None
    if target=='wasm':
        wit=out.with_suffix('.wit'); wit.write_text('''package saga:program@0.50.0;\n\nworld program {\n  import print-i64: func(value: s64);\n  export run: func();\n}\n''',encoding='utf-8')
    return BuildResult(target,out,cpath,wit)


def _embedded_standard_graph(loaded) -> tuple[dict[str, str], dict[str, str], str]:
    """Build a path-independent embedded source graph for Standard bundles.

    The normal source loader has already validated project/package containment,
    cycles and symlink policy. The standalone binary embeds opaque virtual file
    ids plus resolved dependency edges instead of flattening namespaced modules
    or leaking build-machine absolute paths.
    """
    from .lexer import Lexer
    from .parser import Parser
    from .source_units import _package_dependency

    file_ids = {path: f"f{index:04d}:{path.name}" for index, path in enumerate(loaded.files)}
    sources = {file_ids[path]: loaded.sources[path] for path in loaded.files}
    edges: dict[str, str] = {}
    for path in loaded.files:
        program = Parser(Lexer(loaded.sources[path], str(path)).scan_tokens(), str(path)).parse()
        for statement in program.statements:
            if not isinstance(statement, ast.UseStmt) or statement.source_path is None:
                continue
            if statement.source_path.startswith("pkg:"):
                dependency = _package_dependency(loaded.root, statement.source_path).resolve()
            else:
                dependency = (path.parent / statement.source_path).resolve()
            target = file_ids.get(dependency)
            if target is None:
                raise AOTError(
                    f"embedded source graph is missing dependency {statement.source_path} from {path}"
                )
            edges[file_ids[path] + "\x00" + statement.source_path] = target
    return sources, edges, file_ids[loaded.entry]


def _embedded_standard_go(loaded, *, package_name: str = "main") -> str:
    sources, edges, entry = _embedded_standard_graph(loaded)
    source_items = "\n".join(
        f"    {json.dumps(key)}: {json.dumps(value, ensure_ascii=False)},"
        for key, value in sorted(sources.items())
    )
    edge_items = "\n".join(
        f"    {json.dumps(key)}: {json.dumps(value)},"
        for key, value in sorted(edges.items())
    )
    template = r'''package main

import "fmt"

const sagaEmbeddedEntry = __ENTRY__

var sagaEmbeddedSources = map[string]string{
__SOURCES__
}

var sagaEmbeddedEdges = map[string]string{
__EDGES__
}

func loadEmbeddedProgram() ([]Stmt, error) {
    seen := map[string]bool{}
    active := map[string]bool{}
    moduleBindings := map[string]string{}
    moduleNames := map[string]string{}

    var load func(string, bool, string) ([]Stmt, error)
    load = func(fileID string, imported bool, requestedAlias string) ([]Stmt, error) {
        if active[fileID] {
            return nil, &SagaError{Code:"SAGA-I001", ID:"SAGA-I111", Message:"cyclic embedded source import: "+fileID, File:fileID, Line:1, Col:1}
        }
        if seen[fileID] {
            if imported {
                previous := moduleBindings[fileID]
                requested := requestedAlias
                if requested == "" { requested = moduleNames[fileID] }
                if previous != "" && requested != "" && previous != requested {
                    return nil, &SagaError{Code:"SAGA-P001", ID:"SAGA-P109", Message:"same module cannot be imported with multiple aliases: "+previous+" and "+requested, File:fileID, Line:1, Col:1}
                }
            }
            return nil, nil
        }
        raw, ok := sagaEmbeddedSources[fileID]
        if !ok { return nil, fmt.Errorf("embedded Saga source unavailable: %s", fileID) }
        toks, err := lex(raw, fileID)
        if err != nil { return nil, err }
        stmts, err := parse(toks)
        if err != nil { return nil, err }

        moduleName := ""
        var moduleTok Token
        for _, st := range stmts {
            if m, ok := st.(*ModuleDecl); ok {
                if moduleName != "" {
                    return nil, &SagaError{Code:"SAGA-P001", ID:"SAGA-P102", Message:"only one module directive is allowed per source file", File:fileID, Line:m.Tok.Line, Col:m.Tok.Col}
                }
                moduleName, moduleTok = m.Name, m.Tok
            }
        }

        active[fileID] = true
        defer delete(active, fileID)
        dependencies := []Stmt{}
        locals := []Stmt{}
        for _, st := range stmts {
            if u, ok := st.(*UseStmt); ok && u.SourcePath != "" {
                dep, exists := sagaEmbeddedEdges[fileID+"\x00"+u.SourcePath]
                if !exists { return nil, fmt.Errorf("embedded dependency edge unavailable: %s -> %s", fileID, u.SourcePath) }
                xs, e := load(dep, true, u.Alias)
                if e != nil { return nil, e }
                dependencies = append(dependencies, xs...)
                continue
            }
            if _, ok := st.(*ModuleDecl); ok { continue }
            locals = append(locals, st)
        }
        body := append(dependencies, locals...)
        seen[fileID] = true
        if imported && moduleName != "" {
            bind := requestedAlias
            if bind == "" { bind = moduleName }
            moduleBindings[fileID] = bind
            moduleNames[fileID] = moduleName
            return []Stmt{&SourceModuleStmt{Name:moduleName, BindName:bind, Stmts:body, Tok:moduleTok}}, nil
        }
        if imported && requestedAlias != "" && moduleName == "" {
            return nil, &SagaError{Code:"SAGA-P001", ID:"SAGA-P109", Message:"legacy source unit without module cannot use an alias", File:fileID, Line:1, Col:1}
        }
        if !imported && moduleName != "" {
            body = append([]Stmt{&ModuleDecl{Name:moduleName, Tok:moduleTok}}, body...)
        }
        return body, nil
    }
    return load(sagaEmbeddedEntry, false, "")
}
'''
    return (
        template.replace("package main", f"package {package_name}", 1)
        .replace("__ENTRY__", json.dumps(entry))
        .replace("__SOURCES__", source_items)
        .replace("__EDGES__", edge_items)
    )


def _combined_source(source: Path) -> str:
    from .source_units import load_program
    import re
    loaded = load_program(source)
    chunks=[]
    for path in loaded.files:
        text=loaded.sources[path]
        # Source-unit imports are already resolved in dependency order. Hosted
        # module imports (use task) remain in the embedded program.
        text=re.sub(r'(?m)^\s*use\s+["\'][^"\']+\.saga["\']\s*;?\s*$', '', text)
        chunks.append(f'// bundled from {path.name}\n{text}')
    return '\n'.join(chunks)


def _natural_029_features(program: ast.Program) -> set[str]:
    """Return Natural-0.29 syntax still outside the Go Standard bundle.

    The independent Go frontend now implements the complete Natural Core 0.29
    surface covered by the cross-implementation conformance inventory, including
    natural bindings, closures, pipelines, extension calls and same-line bare
    arguments.  Keep this walker as the single future fail-closed hook: if a new
    reference-only syntax form is introduced, it must be added here before a
    Standard bundle can claim parity.
    """
    found: set[str] = set()

    def expr(value: ast.Expr, declared: set[str]) -> None:
        if isinstance(value, ast.ClosureExpr):
            inner = set(declared)
            if value.parameters:
                inner.update(token.lexeme for token in value.parameters)
            # An omitted parameter is contextual and does not create a source
            # binding unless the closure is actually used by a one-argument
            # API. The detector only cares about first-assignment declarations,
            # so preserving lexical captures here is the important part.
            block(value.body.statements, inner)
            return
        if isinstance(value, ast.Call):
            # Parenthesized, pipeline, trailing-block and same-line bare calls
            # are all parsed by both the reference and Go frontends.
            expr(value.callee, declared)
            for argument in value.arguments: expr(argument, declared)
            return
        if isinstance(value, ast.Binary): expr(value.left, declared); expr(value.right, declared); return
        if isinstance(value, ast.RangeExpr): expr(value.start, declared); expr(value.end, declared); return
        if isinstance(value, ast.Unary): expr(value.right, declared); return
        if isinstance(value, ast.PropagateExpr):
            # Postfix propagation is implemented by both the Python reference
            # and the independent Go frontend. It is therefore not a Natural
            # parity blocker for Standard bundles.
            expr(value.value, declared); return
        if isinstance(value, ast.ListLiteral):
            for item in value.elements: expr(item, declared)
            return
        if isinstance(value, ast.Index): expr(value.target, declared); expr(value.index, declared); return
        if isinstance(value, ast.Member): expr(value.target, declared); return

    def block(statements: list[ast.Stmt], inherited: set[str]) -> None:
        local = set(inherited)
        for statement in statements:
            stmt(statement, local)

    def stmt(value: ast.Stmt, declared: set[str]) -> None:
        if isinstance(value, ast.VarDecl):
            expr(value.initializer, declared); declared.add(value.name.lexeme); return
        if isinstance(value, ast.Assign):
            if isinstance(value.target, ast.Variable) and value.target.name.lexeme not in declared:
                # Natural first assignment is implemented by the Go frontend
                # and runtime; keep scope tracking only for nested analysis.
                declared.add(value.target.name.lexeme)
            else:
                expr(value.target, declared)
            expr(value.value, declared); return
        if isinstance(value, ast.ExpressionStmt): expr(value.expression, declared); return
        if isinstance(value, ast.IfStmt):
            expr(value.condition, declared); block(value.then_branch.statements, declared)
            if value.else_branch: block(value.else_branch.statements, declared)
            return
        if isinstance(value, ast.WhileStmt): expr(value.condition, declared); block(value.body.statements, declared); return
        if isinstance(value, ast.ForStmt):
            expr(value.iterable, declared); inner=set(declared); inner.add(value.name.lexeme); block(value.body.statements, inner); return
        if isinstance(value, ast.ReturnStmt) and value.value is not None: expr(value.value, declared); return
        if isinstance(value, ast.ThrowStmt): expr(value.value, declared); return
        if isinstance(value, ast.TryStmt):
            block(value.try_block.statements, declared)
            if value.catch_block:
                inner=set(declared)
                if value.catch_name: inner.add(value.catch_name.lexeme)
                block(value.catch_block.statements, inner)
            if value.finally_block: block(value.finally_block.statements, declared)
            return
        if isinstance(value, ast.FunctionDecl):
            inner=set(declared)
            inner.update(p.name.lexeme for p in value.parameters)
            if value.expression_body: expr(value.expression_body, inner)
            if value.body: block(value.body.statements, inner)
            declared.add(value.name.lexeme); return
        if isinstance(value, ast.ClassDecl):
            for method in value.methods: stmt(method, {"self"})
            declared.add(value.name.lexeme); return
        if isinstance(value, ast.Block): block(value.statements, declared)

    block(program.statements, set())
    return found


def build_standard_bundle(source: str|Path, target: str, output: str|Path|None=None) -> BuildResult:
    """Compile Standard Core to a standalone native or WASI binary.

    This is a runtime-AOT backend: Saga source is embedded into the independent
    Go Standard Core implementation and the pair is compiled by the Go toolchain.
    It preserves the Go implementation's Standard Core semantics, including
    exact numbers, OOP, generics, exceptions and lexical closures.
    """
    import os, json as _json
    source_input = Path(source).expanduser()
    loaded = compile_file(str(source_input))
    source=loaded.entry; go=shutil.which('go')
    if not go: raise AOTError('Go toolchain is required for Standard Core bundles')
    natural = _natural_029_features(loaded.program)
    if natural:
        raise AOTError(
            "This Natural 0.29 source uses syntax that the independent Go Standard bundle does not yet parse: "
            + ", ".join(sorted(natural)) + ". Use the reference runtime for this source until the "
            "independent frontend implements the same syntax."
        )
    go_root=Path(__file__).resolve().parents[1]/'implementations'/'go'
    tmp=Path(tempfile.mkdtemp(prefix='saga-go-bundle-'))
    shutil.copy2(go_root/'go.mod', tmp/'go.mod')
    dst=tmp/'cmd'/'saga-bundle'; shutil.copytree(go_root/'cmd'/'saga-go', dst)
    main=dst/'main.go'; text=main.read_text(encoding='utf-8')
    replacement='''func main() {\n\tstmts, err := loadEmbeddedProgram()\n\tif err != nil { os.Exit(printDiagnostic(err)) }\n\tc := NewChecker()\n\tif err = c.Check(stmts); err != nil { os.Exit(printDiagnostic(err)) }\n\tit := NewInterpreter(c, nil)\n\tif err = it.Interpret(stmts); err != nil { os.Exit(printDiagnostic(err)) }\n}\n'''
    # Replace the bootstrap CLI main regardless of the exact release's main-body
    # shape. Saga Native 0.12 performs standalone-payload detection in main(),
    # so a literal string replacement would silently leave a CLI binary.
    text, count = re.subn(r'func main\(\) \{.*?\n\}\nfunc runCLI', replacement + 'func runCLI', text, count=1, flags=re.S)
    if count != 1:
        raise AOTError('could not locate Saga Native main function for embedded bundle build')
    main.write_text(text,encoding='utf-8')
    (dst/'embedded_source.go').write_text(_embedded_standard_go(loaded), encoding='utf-8')
    if output: out=Path(output).expanduser()
    else: out=source.parent/(source.stem + ('.wasm' if target=='wasm' else ('.exe' if os.name=='nt' else '')))
    _reject_symlink_output(out)
    out=out.resolve()
    compiler_path = Path(go).resolve()
    _reject_output_collision(source, out, extra_inputs=(compiler_path,))
    if target == 'wasm':
        _reject_output_collision(source, out.with_suffix('.wit'), extra_inputs=(compiler_path,))
    env=os.environ.copy()
    if target=='wasm': env.update({'GOOS':'wasip1','GOARCH':'wasm','CGO_ENABLED':'0'})
    elif target!='native': raise AOTError('target must be native or wasm')
    tmp_out=_compiler_temp_output(out)
    try:
        proc=subprocess.run([go,'build','-trimpath','-ldflags=-s -w','-o',str(tmp_out),'./cmd/saga-bundle'],cwd=tmp,env=env,text=True,capture_output=True)
        if proc.returncode: raise AOTError(proc.stderr.strip() or 'Go Standard Core bundle build failed')
        os.replace(tmp_out,out)
    finally:
        tmp_out.unlink(missing_ok=True)
    wit=None
    if target=='wasm':
        wit=out.with_suffix('.wit'); wit.write_text('''package saga:standard-core@0.50.0;\n\nworld saga-program {\n  export run: func();\n}\n''',encoding='utf-8')
    return BuildResult(target,out,None,wit)
