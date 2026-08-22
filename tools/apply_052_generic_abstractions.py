#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected exactly one occurrence, found {count}: {old[:100]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


# ---------------------------------------------------------------------------
# Python type system: type-constructor variables / applied higher-kinded types.
# ---------------------------------------------------------------------------
replace_once(
    "saga/typesys.py",
    '''        if self.name == "typevar":
            return self.args[0].name if self.args else "T"
        if self.args:
''',
    '''        if self.name == "typevar":
            return self.args[0].name if self.args else "T"
        if self.name.startswith("typector:"):
            return self.name.split(":", 1)[1]
        if self.name == "typeapply" and self.args:
            constructor, *arguments = self.args
            return f"{constructor}[{', '.join(str(arg) for arg in arguments)}]"
        if self.args:
''',
)
replace_once(
    "saga/typesys.py",
    '''def TYPEVAR(name: str) -> Type:
    return Type("typevar", (Type(name),))


NATIVE_ALIASES = {
''',
    '''def TYPEVAR(name: str) -> Type:
    return Type("typevar", (Type(name),))


def TYPECTOR(name: str) -> Type:
    """A unary-or-higher type constructor captured during HKT inference."""
    return Type(f"typector:{name}")


def TYPEAPPLY(constructor: Type, args: list[Type] | tuple[Type, ...]) -> Type:
    return Type("typeapply", (constructor, *tuple(args)))


def is_typector(value: Type) -> bool:
    return value.name.startswith("typector:")


def typector_name(value: Type) -> str:
    return value.name.split(":", 1)[1]


NATIVE_ALIASES = {
''',
)
replace_once(
    "saga/typesys.py",
    '''            self.pos += 1
            lower = name.lower()
            if lower == "list":
''',
    '''            self.pos += 1
            # A declared type variable used in constructor position (F[A]) is
            # an applied higher-kinded variable, not a nominal object named F.
            # Its kind arity is inferred from the number of applied arguments.
            if name in self.type_vars:
                return TYPEAPPLY(base, args)
            lower = name.lower()
            if lower == "list":
''',
)
replace_once(
    "saga/typesys.py",
    '''def substitute(value: Type, mapping: dict[str, Type]) -> Type:
    if is_typevar(value):
        return mapping.get(typevar_name(value), value)
    if value.name == "fn":
''',
    '''def substitute(value: Type, mapping: dict[str, Type]) -> Type:
    if is_typevar(value):
        return mapping.get(typevar_name(value), value)
    if value.name == "typeapply" and value.args:
        constructor = substitute(value.args[0], mapping)
        arguments = tuple(substitute(arg, mapping) for arg in value.args[1:])
        if is_typector(constructor):
            return Type(typector_name(constructor), arguments)
        return TYPEAPPLY(constructor, arguments)
    if value.name == "fn":
''',
)
replace_once(
    "saga/typesys.py",
    '''def _unify_invariant(pattern: Type, actual: Type, mapping: dict[str, Type]) -> bool:
    """Unify a generic argument without introducing numeric covariance.

    Saga generic parameters are invariant. Type variables may still bind to the
    corresponding actual type, but concrete generic arguments must match their
    structure exactly.
    """
    if is_typevar(pattern):
''',
    '''def _unify_invariant(pattern: Type, actual: Type, mapping: dict[str, Type]) -> bool:
    """Unify a generic argument without introducing numeric covariance.

    Saga generic parameters are invariant. Type variables may still bind to the
    corresponding actual type, but concrete generic arguments must match their
    structure exactly.
    """
    if pattern.name == "typeapply" and pattern.args:
        constructor, *arguments = pattern.args
        if not is_typevar(constructor) or len(arguments) != len(actual.args):
            return False
        name = typevar_name(constructor)
        candidate = TYPECTOR(actual.name)
        existing = mapping.get(name)
        if existing is None:
            mapping[name] = candidate
        elif existing != candidate:
            return False
        return all(_unify_invariant(p, a, mapping) for p, a in zip(arguments, actual.args))
    if is_typevar(pattern):
''',
)
replace_once(
    "saga/typesys.py",
    '''def unify(pattern: Type, actual: Type, mapping: dict[str, Type]) -> bool:
    if is_typevar(pattern):
''',
    '''def unify(pattern: Type, actual: Type, mapping: dict[str, Type]) -> bool:
    if pattern.name == "typeapply" and pattern.args:
        constructor, *arguments = pattern.args
        if not is_typevar(constructor) or len(arguments) != len(actual.args):
            return False
        name = typevar_name(constructor)
        candidate = TYPECTOR(actual.name)
        existing = mapping.get(name)
        if existing is None:
            mapping[name] = candidate
        elif existing != candidate:
            return False
        return all(unify(p, a, mapping) for p, a in zip(arguments, actual.args))
    if is_typevar(pattern):
''',
)

# ---------------------------------------------------------------------------
# Python checker: intrinsic Option/Result ADTs, HKT inference, generic methods.
# ---------------------------------------------------------------------------
replace_once(
    "saga/checker.py",
    '''    is_assignable, is_numeric, is_typevar, parse_type, substitute, typevar_name, TYPEVAR,
''',
    '''    is_assignable, is_numeric, is_typevar, parse_type, substitute, typevar_name, TYPECTOR, TYPEVAR,
''',
)
replace_once(
    "saga/checker.py",
    '''}


class TypeChecker:
''',
    '''}
BUILTINS.update({"Option", "Result"})


class TypeChecker:
''',
)
replace_once(
    "saga/checker.py",
    '''        self.source_modules: dict[str, SourceModuleInfo] = {}

    def check(self, program: ast.Program) -> None:
''',
    '''        self.source_modules: dict[str, SourceModuleInfo] = {}

        # Option/Result are intrinsic Generic ADTs. Their runtime representation
        # stays compatible with the long-standing some/none/ok/err helpers while
        # the type checker exposes the same constructor/match model as user ADTs.
        self.enums.update({"Option": {"Some", "None"}, "Result": {"Ok", "Err"}})
        self.enum_payloads.update({
            "Option": {"Some": (TYPEVAR("T"),), "None": ()},
            "Result": {"Ok": (TYPEVAR("T"),), "Err": (TYPEVAR("E"),)},
        })
        self.enum_type_params.update({"Option": ["T"], "Result": ["T", "E"]})
        self.scopes[0]["Option"] = VariableInfo(Type("enumtype:Option"), False)
        self.scopes[0]["Result"] = VariableInfo(Type("enumtype:Result"), False)

    def check(self, program: ast.Program) -> None:
''',
)
replace_once(
    "saga/checker.py",
    '''    def _validate_type_reference(self, value: Type, token: Token) -> None:
        if is_typevar(value) or value == ANY:
            return
        if value.name == "fn":
''',
    '''    def _validate_type_reference(self, value: Type, token: Token) -> None:
        if is_typevar(value) or value == ANY or value.name.startswith("typector:"):
            return
        if value.name == "typeapply":
            if not value.args or not is_typevar(value.args[0]):
                self._error(token, "higher-kinded application requires a type-constructor variable", diagnostic_id="SAGA-T103")
            for argument in value.args[1:]:
                self._validate_type_reference(argument, token)
            return
        if value.name == "fn":
''',
)
replace_once(
    "saga/checker.py",
    '''    def _require_override_compatible(self, parent: FunctionInfo, child: FunctionInfo, token: Token) -> None:
        if len(parent.params) != len(child.params) or any(a != b for a, b in zip(parent.params, child.params)):
            self._error(token, "オーバーライドするメソッドの引数型を親と揃えてください")
        if parent.return_type and child.return_type and not self._is_assignable(parent.return_type, child.return_type):
            self._error(token, "オーバーライドするメソッドの戻り値型が親と互換ではありません")
''',
    '''    def _require_override_compatible(self, parent: FunctionInfo, child: FunctionInfo, token: Token) -> None:
        if len(parent.type_params) != len(child.type_params):
            self._error(token, "オーバーライドするgeneric methodの型パラメータ数を親と揃えてください")
        # Generic method parameters are alpha-equivalent: an interface may use
        # U while its implementation uses V. Normalize the implementation's
        # method-local variables to the contract names before comparing types.
        alpha = {
            child_name: TYPEVAR(parent_name)
            for parent_name, child_name in zip(parent.type_params, child.type_params)
        }
        child_params = [substitute(value, alpha) for value in child.params]
        child_return = substitute(child.return_type, alpha) if child.return_type else None
        if len(parent.params) != len(child_params) or any(a != b for a, b in zip(parent.params, child_params)):
            self._error(token, "オーバーライドするメソッドの引数型を親と揃えてください")
        if parent.return_type and child_return and not self._is_assignable(parent.return_type, child_return):
            self._error(token, "オーバーライドするメソッドの戻り値型が親と互換ではありません")
''',
)
replace_once(
    "saga/checker.py",
    '''    def _enum_match_pattern(self, expr: ast.Expr, enum_type: Type | None) -> tuple[str, dict[str, VariableInfo]] | None:
        if enum_type is None or not enum_type.name.startswith("object:"):
            return None
        enum_name = enum_type.name.split(":", 1)[1]
        if enum_name not in self.enums:
            return None
''',
    '''    def _enum_identity(self, value: Type | None) -> tuple[str, tuple[Type, ...]] | None:
        if value is None:
            return None
        if value.name == "option" and len(value.args) == 1:
            return "Option", value.args
        if value.name == "result" and len(value.args) == 2:
            return "Result", value.args
        if value.name.startswith("object:"):
            name = value.name.split(":", 1)[1]
            if name in self.enums:
                return name, value.args
        return None

    def _enum_match_pattern(self, expr: ast.Expr, enum_type: Type | None) -> tuple[str, dict[str, VariableInfo]] | None:
        identity = self._enum_identity(enum_type)
        if identity is None:
            return None
        enum_name, enum_args = identity
''',
)
replace_once(
    "saga/checker.py",
    '''        mapping = {name: arg for name, arg in zip(params, enum_type.args)}
''',
    '''        mapping = {name: arg for name, arg in zip(params, enum_args)}
''',
)
replace_once(
    "saga/checker.py",
    '''            value_type = self._check_expr(stmt.value)
            enum_name = value_type.name.split(":", 1)[1] if value_type.name.startswith("object:") and value_type.name.split(":", 1)[1] in self.enums else None
''',
    '''            value_type = self._check_expr(stmt.value)
            enum_identity = self._enum_identity(value_type)
            enum_name = enum_identity[0] if enum_identity is not None else None
''',
)
replace_once(
    "saga/checker.py",
    '''            result = Type(f"object:{enum_name}", tuple(TYPEVAR(name) for name in params))
            if payload:
''',
    '''            if enum_name == "Option":
                result = OPTION(TYPEVAR("T"))
            elif enum_name == "Result":
                result = RESULT(TYPEVAR("T"), TYPEVAR("E"))
            else:
                result = Type(f"object:{enum_name}", tuple(TYPEVAR(name) for name in params))
            if payload:
''',
)
replace_once(
    "saga/checker.py",
    '''    def _unify_invariant(self, pattern: Type, actual: Type, mapping: dict[str, Type]) -> bool:
        if is_typevar(pattern):
''',
    '''    def _unify_invariant(self, pattern: Type, actual: Type, mapping: dict[str, Type]) -> bool:
        if pattern.name == "typeapply" and pattern.args:
            constructor, *arguments = pattern.args
            if not is_typevar(constructor) or len(arguments) != len(actual.args):
                return False
            name = typevar_name(constructor)
            candidate = TYPECTOR(actual.name)
            existing = mapping.get(name)
            if existing is None:
                mapping[name] = candidate
            elif existing != candidate:
                return False
            return all(self._unify_invariant(p, a, mapping) for p, a in zip(arguments, actual.args))
        if is_typevar(pattern):
''',
)
replace_once(
    "saga/checker.py",
    '''    def _unify(self, pattern: Type, actual: Type, mapping: dict[str, Type]) -> bool:
        if is_typevar(pattern):
''',
    '''    def _unify(self, pattern: Type, actual: Type, mapping: dict[str, Type]) -> bool:
        if pattern.name == "typeapply" and pattern.args:
            constructor, *arguments = pattern.args
            if not is_typevar(constructor) or len(arguments) != len(actual.args):
                return False
            name = typevar_name(constructor)
            candidate = TYPECTOR(actual.name)
            existing = mapping.get(name)
            if existing is None:
                mapping[name] = candidate
            elif existing != candidate:
                return False
            return all(self._unify(p, a, mapping) for p, a in zip(arguments, actual.args))
        if is_typevar(pattern):
''',
)

# ---------------------------------------------------------------------------
# Python runtime: make intrinsic ADT constructors use existing wrappers.
# ---------------------------------------------------------------------------
replace_once(
    "saga/interpreter.py",
    '''from .typesys import ANY, BOOL, BYTES, CLASS_VALUE, DATETIME, DECIMAL, DURATION, ERROR, INT, RATIONAL, TEXT, UNIT, FUNCTION, Type, is_assignable, is_typevar, parse_type, substitute, typevar_name, unify
''',
    '''from .typesys import ANY, BOOL, BYTES, CLASS_VALUE, DATETIME, DECIMAL, DURATION, ERROR, INT, RATIONAL, TEXT, UNIT, FUNCTION, TYPECTOR, Type, is_assignable, is_typevar, parse_type, substitute, typevar_name, unify
''',
)
replace_once(
    "saga/interpreter.py",
    '''    def __call__(self, *args: object) -> EnumValue:
        if len(args) != len(self.payload_types):
            raise NativeFailure(
                f"{self.enum_type.qualified_name}.{self.variant} は "
                f"{len(self.payload_types)} 個のpayloadを必要とします"
            )
        return EnumValue(self.enum_type.qualified_name, self.variant, tuple(args))
''',
    '''    def __call__(self, *args: object) -> object:
        if len(args) != len(self.payload_types):
            raise NativeFailure(
                f"{self.enum_type.qualified_name}.{self.variant} は "
                f"{len(self.payload_types)} 個のpayloadを必要とします"
            )
        if self.enum_type.qualified_name == "Option" and self.variant == "Some":
            return OptionValue.some(args[0])
        if self.enum_type.qualified_name == "Result" and self.variant == "Ok":
            return ResultValue.success(args[0])
        if self.enum_type.qualified_name == "Result" and self.variant == "Err":
            return ResultValue.failure(args[0])
        return EnumValue(self.enum_type.qualified_name, self.variant, tuple(args))
''',
)
replace_once(
    "saga/interpreter.py",
    '''    def _register_builtins(self) -> None:
        from .checker import BUILTINS
        for name in BUILTINS: self.globals.define(name, BuiltinFunction(name), False)
''',
    '''    def _register_builtins(self) -> None:
        from .checker import BUILTINS
        for name in BUILTINS:
            if name not in {"Option", "Result"}:
                self.globals.define(name, BuiltinFunction(name), False)
        option_enum = EnumType("Option", {"Some": ("T",), "None": ()})
        result_enum = EnumType("Result", {"Ok": ("T",), "Err": ("E",)})
        self.enums.update({"Option": option_enum, "Result": result_enum})
        self.globals.define("Option", option_enum, False)
        self.globals.define("Result", result_enum, False)
''',
)
replace_once(
    "saga/interpreter.py",
    '''    def _match_enum_payload_pattern(
        self, value: object, pattern: ast.Expr
    ) -> tuple[bool, dict[str, object] | None]:
        """Recognize a payload enum pattern without evaluating its bind variables.

        The boolean distinguishes "not an enum payload pattern" from "recognized
        enum pattern whose variant did not match".  Conflating those states made
        a failed `Some(item)` case fall back to normal expression evaluation,
        where `item` was incorrectly looked up as a runtime variable.
        """
        if not isinstance(value, EnumValue) or not isinstance(pattern, ast.Call):
            return False, None
        callee = pattern.callee
        if not isinstance(callee, ast.Member):
            return False, None
        qname = self._qualified_expr_name_runtime(callee.target)
        if qname is None:
            return False, None
        expected_enum = qname
        # Module aliases are part of the observable enum identity in the
        # interpreter. Accept exact identity and the local/unqualified form.
        if value.enum_name != expected_enum and not value.enum_name.endswith("." + expected_enum):
            return False, None
        if value.variant != callee.name.lexeme or len(value.payload) != len(pattern.arguments):
            return True, None
        bindings: dict[str, object] = {}
        for expr, item in zip(pattern.arguments, value.payload):
            if not isinstance(expr, ast.Variable):
                return True, None
            name = expr.name.lexeme
            if name != "_":
                bindings[name] = item
        return True, bindings
''',
    '''    @staticmethod
    def _enum_runtime_parts(value: object) -> tuple[str, str, tuple[object, ...]] | None:
        if isinstance(value, EnumValue):
            return value.enum_name, value.variant, value.payload
        if isinstance(value, OptionValue):
            return ("Option", "Some", (value.value,)) if value.present else ("Option", "None", ())
        if isinstance(value, ResultValue):
            return ("Result", "Ok", (value.value,)) if value.ok else ("Result", "Err", (value.value,))
        return None

    def _match_enum_payload_pattern(
        self, value: object, pattern: ast.Expr
    ) -> tuple[bool, dict[str, object] | None]:
        """Recognize a payload ADT pattern without evaluating bind variables."""
        parts = self._enum_runtime_parts(value)
        if parts is None or not isinstance(pattern, ast.Call):
            return False, None
        enum_name, variant, payload = parts
        callee = pattern.callee
        if not isinstance(callee, ast.Member):
            return False, None
        qname = self._qualified_expr_name_runtime(callee.target)
        if qname is None:
            return False, None
        expected_enum = qname
        if enum_name != expected_enum and not enum_name.endswith("." + expected_enum):
            return False, None
        if variant != callee.name.lexeme or len(payload) != len(pattern.arguments):
            return True, None
        bindings: dict[str, object] = {}
        for expr, item in zip(pattern.arguments, payload):
            if not isinstance(expr, ast.Variable):
                return True, None
            name = expr.name.lexeme
            if name != "_":
                bindings[name] = item
        return True, bindings
''',
)
replace_once(
    "saga/interpreter.py",
    '''        if isinstance(target, EnumType):
            if name in target.variants:
                payload_types = target.variants[name]
                if payload_types:
                    return EnumConstructor(target, name, payload_types)
                return EnumValue(target.qualified_name, name)
            self._runtime_error(expr.name, f"enum variant '{target.qualified_name}.{name}' が見つかりません", diagnostic_id="SAGA-R123")
''',
    '''        if isinstance(target, EnumType):
            if name in target.variants:
                payload_types = target.variants[name]
                if payload_types:
                    return EnumConstructor(target, name, payload_types)
                if target.qualified_name == "Option" and name == "None":
                    return OptionValue.none()
                return EnumValue(target.qualified_name, name)
            self._runtime_error(expr.name, f"enum variant '{target.qualified_name}.{name}' が見つかりません", diagnostic_id="SAGA-R123")
''',
)
replace_once(
    "saga/interpreter.py",
    '''        if is_typevar(pattern):
            name = typevar_name(pattern)
            if name in mapping:
                return
            actual = self._runtime_type_of(value)
            if actual is not None and actual != ANY:
                mapping[name] = actual
            return
''',
    '''        if pattern.name == "typeapply" and pattern.args:
            constructor, *arguments = pattern.args
            actual = self._runtime_type_of(value)
            if actual is None or len(arguments) != len(actual.args) or not is_typevar(constructor):
                return
            name = typevar_name(constructor)
            candidate = TYPECTOR(actual.name)
            existing = mapping.get(name)
            if existing is None:
                mapping[name] = candidate
            elif existing != candidate:
                return
            for expected_arg, actual_arg in zip(arguments, actual.args):
                unify(expected_arg, actual_arg, mapping)
            return
        if is_typevar(pattern):
            name = typevar_name(pattern)
            if name in mapping:
                return
            actual = self._runtime_type_of(value)
            if actual is not None and actual != ANY:
                mapping[name] = actual
            return
''',
)

# ---------------------------------------------------------------------------
# Go type system: same applied-constructor representation and inference.
# ---------------------------------------------------------------------------
replace_once(
    "implementations/go/cmd/saga-go/types.go",
    '''\tif len(t.Args) > 0 {
''',
    '''\tif strings.HasPrefix(t.Name, "typector:") {
\t\treturn strings.TrimPrefix(t.Name, "typector:")
\t}
\tif t.Name == "typeapply" && len(t.Args) > 0 {
\t\ta := []string{}
\t\tfor _, x := range t.Args[1:] {
\t\t\ta = append(a, x.String())
\t\t}
\t\treturn t.Args[0].String() + "[" + strings.Join(a, ", ") + "]"
\t}
\tif len(t.Args) > 0 {
''',
)
replace_once(
    "implementations/go/cmd/saga-go/types.go",
    '''func typeVar(n string) Type               { return Type{Name: "$" + n} }
func isTypeVar(t Type) bool               { return strings.HasPrefix(t.Name, "$") }
''',
    '''func typeVar(n string) Type               { return Type{Name: "$" + n} }
func isTypeVar(t Type) bool               { return strings.HasPrefix(t.Name, "$") }
func typeCtor(n string) Type              { return Type{Name: "typector:" + n} }
func isTypeCtor(t Type) bool              { return strings.HasPrefix(t.Name, "typector:") }
func typeApply(ctor Type, args ...Type) Type {
\treturn Type{Name: "typeapply", Args: append([]Type{ctor}, args...)}
}
''',
)
# Replace complete substitute/typeFromRef/unify region to avoid partial-order bugs.
types_text = read("implementations/go/cmd/saga-go/types.go")
start = types_text.index("func substitute(t Type, m map[string]Type) Type {")
end = types_text.index("\nfunc objectTypeName", start)
new_region = r'''func substitute(t Type, m map[string]Type) Type {
	if isTypeVar(t) {
		if x, ok := m[strings.TrimPrefix(t.Name, "$")]; ok {
			return x
		}
		return t
	}
	if t.Name == "typeapply" && len(t.Args) > 0 {
		ctor := substitute(t.Args[0], m)
		applied := []Type{}
		for _, a := range t.Args[1:] {
			applied = append(applied, substitute(a, m))
		}
		if isTypeCtor(ctor) {
			return Type{Name: strings.TrimPrefix(ctor.Name, "typector:"), Args: applied}
		}
		return typeApply(ctor, applied...)
	}
	r := Type{Name: t.Name}
	for _, a := range t.Args {
		r.Args = append(r.Args, substitute(a, m))
	}
	if t.Result != nil {
		x := substitute(*t.Result, m)
		r.Result = &x
	}
	return r
}
func typeFromRef(r TypeRef, vars map[string]bool) Type {
	n := r.Name
	aliases := map[string]Type{"int": TInt, "Int": TInt, "integer": TInt, "int8": TInt8, "int16": TInt16, "int32": TInt32, "int64": TInt64, "uint8": TUInt8, "uint16": TUInt16, "uint32": TUInt32, "uint64": TUInt64, "decimal": TDecimal, "Decimal": TDecimal, "number": TDecimal, "rational": TRational, "Rational": TRational, "fraction": TRational, "float32": TFloat32, "Float32": TFloat32, "float64": TFloat64, "Float64": TFloat64, "bool": TBool, "Bool": TBool, "boolean": TBool, "text": TText, "Text": TText, "string": TText, "String": TText, "unit": TUnit, "Unit": TUnit, "range": TRange, "Range": TRange, "any": TAny, "Any": TAny, "bytes": TBytes, "Bytes": TBytes, "error": TError, "Error": TError}
	args := []Type{}
	for _, a := range r.Args {
		args = append(args, typeFromRef(a, vars))
	}
	if vars[n] {
		if len(args) > 0 {
			return typeApply(typeVar(n), args...)
		}
		return typeVar(n)
	}
	if dot := strings.IndexByte(n, '.'); dot > 0 {
		prefix, assoc := n[:dot], n[dot+1:]
		if vars[prefix] && assoc != "" {
			return Type{Name: "assoc:$" + prefix + "." + assoc}
		}
	}
	if a, ok := aliases[n]; ok {
		return a
	}
	switch strings.ToLower(n) {
	case "list":
		if len(args) == 1 { return listT(args[0]) }
	case "map":
		if len(args) == 2 { return mapT(args[0], args[1]) }
	case "set":
		if len(args) == 1 { return setT(args[0]) }
	case "option":
		if len(args) == 1 { return optionT(args[0]) }
	case "result":
		if len(args) == 2 { return resultT(args[0], args[1]) }
	case "future":
		if len(args) == 1 { return futureT(args[0]) }
	case "channel":
		if len(args) == 1 { return channelT(args[0]) }
	case "actor":
		if len(args) == 2 { return actorT(args[0], args[1]) }
	case "fn":
		if len(args) >= 1 { return fnT(args[:len(args)-1], args[len(args)-1]) }
	}
	return objectT(n, args...)
}
func unify(pattern, actual Type, m map[string]Type) bool {
	if pattern.Name == "typeapply" && len(pattern.Args) > 0 {
		ctor := pattern.Args[0]
		applied := pattern.Args[1:]
		if !isTypeVar(ctor) || len(applied) != len(actual.Args) {
			return false
		}
		name := strings.TrimPrefix(ctor.Name, "$")
		candidate := typeCtor(actual.Name)
		if existing, ok := m[name]; ok {
			if !sameType(existing, candidate) { return false }
		} else {
			m[name] = candidate
		}
		for idx := range applied {
			if !unify(applied[idx], actual.Args[idx], m) { return false }
		}
		return true
	}
	if isTypeVar(pattern) {
		n := strings.TrimPrefix(pattern.Name, "$")
		if x, ok := m[n]; ok { return sameType(x, actual) }
		m[n] = actual
		return true
	}
	if pattern.Name == "any" || actual.Name == "any" { return true }
	if pattern.Name != actual.Name || len(pattern.Args) != len(actual.Args) { return false }
	for i := range pattern.Args {
		if !unify(pattern.Args[i], actual.Args[i], m) { return false }
	}
	if (pattern.Result == nil) != (actual.Result == nil) { return false }
	if pattern.Result != nil && !unify(*pattern.Result, *actual.Result, m) { return false }
	return true
}
'''
write("implementations/go/cmd/saga-go/types.go", types_text[:start] + new_region + types_text[end:])

# ---------------------------------------------------------------------------
# Go checker: intrinsic Option/Result ADTs + alpha-equivalent generic methods.
# ---------------------------------------------------------------------------
replace_once(
    "implementations/go/cmd/saga-go/checker.go",
    '''func NewChecker() *Checker {
\treturn &Checker{Scopes: []map[string]VarInfo{{}}, Functions: map[string]FuncInfo{}, Classes: map[string]*ClassInfo{}, LocalFunctions: map[*FnDecl]FuncInfo{}, Enums: map[string]map[string]bool{}, EnumPayloads: map[string]map[string][]Type{}, EnumTypeParams: map[string][]string{}, SourceModules: map[string]SourceModuleInfo{}, CurrentConstraints: map[string][]Type{}}
}
''',
    '''func NewChecker() *Checker {
\tc := &Checker{Scopes: []map[string]VarInfo{{}}, Functions: map[string]FuncInfo{}, Classes: map[string]*ClassInfo{}, LocalFunctions: map[*FnDecl]FuncInfo{}, Enums: map[string]map[string]bool{}, EnumPayloads: map[string]map[string][]Type{}, EnumTypeParams: map[string][]string{}, SourceModules: map[string]SourceModuleInfo{}, CurrentConstraints: map[string][]Type{}}
\tc.Enums["Option"] = map[string]bool{"Some": true, "None": true}
\tc.EnumPayloads["Option"] = map[string][]Type{"Some": {typeVar("T")}, "None": {}}
\tc.EnumTypeParams["Option"] = []string{"T"}
\tc.Enums["Result"] = map[string]bool{"Ok": true, "Err": true}
\tc.EnumPayloads["Result"] = map[string][]Type{"Ok": {typeVar("T")}, "Err": {typeVar("E")}}
\tc.EnumTypeParams["Result"] = []string{"T", "E"}
\tc.Scopes[0]["Option"] = VarInfo{Typ: Type{Name: "enumtype:Option"}}
\tc.Scopes[0]["Result"] = VarInfo{Typ: Type{Name: "enumtype:Result"}}
\treturn c
}
''',
)
replace_once(
    "implementations/go/cmd/saga-go/checker.go",
    '''"unwrap_result_or": true}
''',
    '''"unwrap_result_or": true, "Option": true, "Result": true}
''',
)
replace_once(
    "implementations/go/cmd/saga-go/checker.go",
    '''func (c *Checker) overrideCompatible(a, b FuncInfo, t Token) error {
\tif len(a.Params) != len(b.Params) {
\t\treturn c.err(t, "SAGA-T103", "override parameter count differs")
\t}
\tfor i := range a.Params {
\t\tif !sameType(a.Params[i], b.Params[i]) {
\t\t\treturn c.err(t, "SAGA-T103", "override parameter type differs")
\t\t}
\t}
\tif a.HasRet && b.HasRet && !c.assignable(a.Ret, b.Ret) {
\t\treturn c.err(t, "SAGA-T103", fmt.Sprintf("override return type is incompatible: contract %s, implementation %s", a.Ret, b.Ret))
\t}
\treturn nil
}
''',
    '''func (c *Checker) overrideCompatible(a, b FuncInfo, t Token) error {
\tif len(a.TypeParams) != len(b.TypeParams) {
\t\treturn c.err(t, "SAGA-T103", "override generic method type-parameter count differs")
\t}
\talpha := map[string]Type{}
\tfor idx, childName := range b.TypeParams {
\t\talpha[childName] = typeVar(a.TypeParams[idx])
\t}
\tparams := make([]Type, 0, len(b.Params))
\tfor _, param := range b.Params { params = append(params, substitute(param, alpha)) }
\tret := b.Ret
\tif b.HasRet { ret = substitute(b.Ret, alpha) }
\tif len(a.Params) != len(params) {
\t\treturn c.err(t, "SAGA-T103", "override parameter count differs")
\t}
\tfor i := range a.Params {
\t\tif !sameType(a.Params[i], params[i]) {
\t\t\treturn c.err(t, "SAGA-T103", "override parameter type differs")
\t\t}
\t}
\tif a.HasRet && b.HasRet && !c.assignable(a.Ret, ret) {
\t\treturn c.err(t, "SAGA-T103", fmt.Sprintf("override return type is incompatible: contract %s, implementation %s", a.Ret, ret))
\t}
\treturn nil
}
''',
)
# Replace enum-match helper with intrinsic-wrapper-aware identity.
go_checker = read("implementations/go/cmd/saga-go/checker.go")
match_start = go_checker.index("func (c *Checker) enumMatchPattern(")
match_end = go_checker.index("\nfunc sourceQualifiedExprName", match_start)
new_match = r'''func (c *Checker) enumIdentity(t Type) (string, []Type, bool) {
	if t.Name == "option" && len(t.Args) == 1 { return "Option", t.Args, true }
	if t.Name == "result" && len(t.Args) == 2 { return "Result", t.Args, true }
	name := objectTypeName(t)
	if name != "" && c.Enums[name] != nil { return name, t.Args, true }
	return "", nil, false
}

func (c *Checker) enumMatchPattern(e Expr, enumType Type) (string, map[string]VarInfo, bool, error) {
	enumName, enumArgs, ok := c.enumIdentity(enumType)
	if !ok { return "", nil, false, nil }
	callee := e
	args := []Expr{}
	if call, isCall := e.(*Call); isCall {
		callee = call.Callee
		args = call.Args
	}
	q, ok := sourceQualifiedExprName(callee)
	if !ok || !strings.Contains(q, ".") { return "", nil, false, nil }
	idx := strings.LastIndex(q, ".")
	owner, variant := q[:idx], q[idx+1:]
	if owner != enumName || !c.Enums[enumName][variant] { return "", nil, false, nil }
	mapping := typeParamMap(c.EnumTypeParams[enumName], enumArgs)
	rawPayload := c.EnumPayloads[enumName][variant]
	payload := make([]Type, 0, len(rawPayload))
	for _, typ := range rawPayload { payload = append(payload, substitute(typ, mapping)) }
	if len(args) != len(payload) {
		return "", nil, true, c.err(e.token(), "SAGA-T103", fmt.Sprintf("enum variant %s.%s expects %d payload values", enumName, variant, len(payload)))
	}
	bindings := map[string]VarInfo{}
	for idx, arg := range args {
		v, isVariable := arg.(*Variable)
		if !isVariable { return "", nil, true, c.err(arg.token(), "SAGA-T103", "match payload pattern must be a variable or _") }
		if v.Name == "_" { continue }
		if _, exists := bindings[v.Name]; exists { return "", nil, true, c.err(v.Tok, "SAGA-T108", "duplicate match payload variable "+v.Name) }
		bindings[v.Name] = VarInfo{Typ: payload[idx]}
	}
	return variant, bindings, true, nil
}
'''
write("implementations/go/cmd/saga-go/checker.go", go_checker[:match_start] + new_match + go_checker[match_end:])
replace_once(
    "implementations/go/cmd/saga-go/checker.go",
    '''\t\tseen := map[string]bool{}
\t\tenumName := ""
\t\tif strings.HasPrefix(vt.Name, "object:") {
\t\t\tn := strings.TrimPrefix(vt.Name, "object:")
\t\t\tif c.Enums[n] != nil {
\t\t\t\tenumName = n
\t\t\t}
\t\t}
''',
    '''\t\tseen := map[string]bool{}
\t\tenumName, _, _ := c.enumIdentity(vt)
''',
)
replace_once(
    "implementations/go/cmd/saga-go/checker.go",
    '''\t\t\tresult := objectT(n, retArgs...)
\t\t\tif len(ps) > 0 {
''',
    '''\t\t\tresult := objectT(n, retArgs...)
\t\t\tif n == "Option" { result = optionT(typeVar("T")) }
\t\t\tif n == "Result" { result = resultT(typeVar("T"), typeVar("E")) }
\t\t\tif len(ps) > 0 {
''',
)

# ---------------------------------------------------------------------------
# Go runtime: expose Option/Result constructors while preserving wrappers.
# ---------------------------------------------------------------------------
replace_once(
    "implementations/go/cmd/saga-go/runtime.go",
    '''\tfor name := range coreBuiltins {
\t\tn := name
\t\tg.define(n, &NativeFunc{Name: n, Call: func(i *Interpreter, args []Value) (Value, error) { return i.callBuiltin(n, args) }}, false)
\t}
\treturn in
}
''',
    '''\tfor name := range coreBuiltins {
\t\tn := name
\t\tif n == "Option" || n == "Result" { continue }
\t\tg.define(n, &NativeFunc{Name: n, Call: func(i *Interpreter, args []Value) (Value, error) { return i.callBuiltin(n, args) }}, false)
\t}
\tg.define("Option", EnumType{Name: "Option", Variants: map[string]int{"Some": 1, "None": 0}}, false)
\tg.define("Result", EnumType{Name: "Result", Variants: map[string]int{"Ok": 1, "Err": 1}}, false)
\treturn in
}
''',
)
replace_once(
    "implementations/go/cmd/saga-go/runtime.go",
    '''func (i *Interpreter) exec(s Stmt) error {
''',
    '''func enumRuntimeParts(v Value) (string, string, []Value, bool) {
\tswitch q := v.(type) {
\tcase EnumValue:
\t\treturn q.Enum, q.Variant, q.Payload, true
\tcase OptionValue:
\t\tif q.Present { return "Option", "Some", []Value{q.Value}, true }
\t\treturn "Option", "None", nil, true
\tcase ResultValue:
\t\tif q.OK { return "Result", "Ok", []Value{q.Value}, true }
\t\treturn "Result", "Err", []Value{q.Value}, true
\tdefault:
\t\treturn "", "", nil, false
\t}
}

func (i *Interpreter) exec(s Stmt) error {
''',
)
replace_once(
    "implementations/go/cmd/saga-go/runtime.go",
    '''\t\t\tif ev, ok := v.(EnumValue); ok {
''',
    '''\t\t\tif enumName, enumVariant, enumPayload, ok := enumRuntimeParts(v); ok {
''',
)
replace_once(
    "implementations/go/cmd/saga-go/runtime.go",
    '''\t\t\t\t\t\tif qok && (ev.Enum == owner || strings.HasSuffix(ev.Enum, "."+owner)) {
''',
    '''\t\t\t\t\t\tif qok && (enumName == owner || strings.HasSuffix(enumName, "."+owner)) {
''',
)
replace_once(
    "implementations/go/cmd/saga-go/runtime.go",
    '''\t\t\t\t\t\t\tif ev.Variant != m.Name || len(ev.Payload) != len(call.Args) {
''',
    '''\t\t\t\t\t\t\tif enumVariant != m.Name || len(enumPayload) != len(call.Args) {
''',
)
replace_once(
    "implementations/go/cmd/saga-go/runtime.go",
    '''\t\t\t\t\t\t\t\t\tenv.define(vr.Name, ev.Payload[idx], false)
''',
    '''\t\t\t\t\t\t\t\t\tenv.define(vr.Name, enumPayload[idx], false)
''',
)
replace_once(
    "implementations/go/cmd/saga-go/runtime.go",
    '''\tcase EnumType:
\t\tif arity, ok := q.Variants[name]; ok {
\t\t\tif arity > 0 {
\t\t\t\treturn &EnumConstructor{Enum: q.Name, Variant: name, Arity: arity}, nil
\t\t\t}
\t\t\treturn EnumValue{Enum: q.Name, Variant: name}, nil
\t\t}
''',
    '''\tcase EnumType:
\t\tif arity, ok := q.Variants[name]; ok {
\t\t\tif arity > 0 {
\t\t\t\treturn &EnumConstructor{Enum: q.Name, Variant: name, Arity: arity}, nil
\t\t\t}
\t\t\tif q.Name == "Option" && name == "None" { return OptionValue{Present: false}, nil }
\t\t\treturn EnumValue{Enum: q.Name, Variant: name}, nil
\t\t}
''',
)
replace_once(
    "implementations/go/cmd/saga-go/runtime.go",
    '''\tcase *EnumConstructor:
\t\tif len(args) != f.Arity {
\t\t\treturn nil, i.rerr(t, "SAGA-R136", fmt.Sprintf("%s.%s expects %d payload values", f.Enum, f.Variant, f.Arity))
\t\t}
\t\treturn EnumValue{Enum: f.Enum, Variant: f.Variant, Payload: append([]Value{}, args...)}, nil
''',
    '''\tcase *EnumConstructor:
\t\tif len(args) != f.Arity {
\t\t\treturn nil, i.rerr(t, "SAGA-R136", fmt.Sprintf("%s.%s expects %d payload values", f.Enum, f.Variant, f.Arity))
\t\t}
\t\tif f.Enum == "Option" && f.Variant == "Some" { return OptionValue{Present: true, Value: args[0]}, nil }
\t\tif f.Enum == "Result" && f.Variant == "Ok" { return ResultValue{OK: true, Value: args[0]}, nil }
\t\tif f.Enum == "Result" && f.Variant == "Err" { return ResultValue{OK: false, Value: args[0]}, nil }
\t\treturn EnumValue{Enum: f.Enum, Variant: f.Variant, Payload: append([]Value{}, args...)}, nil
''',
)

# ---------------------------------------------------------------------------
# Release identity, examples, docs and regression tests.
# ---------------------------------------------------------------------------
replace_once("pyproject.toml", 'version = "0.51.0"', 'version = "0.52.0"')
replace_once("saga/__init__.py", '__version__ = "0.51.0"', '__version__ = "0.52.0"')
replace_once("implementations/go/cmd/saga-go/version.go", 'const sagaGoVersion = "0.51.0"', 'const sagaGoVersion = "0.52.0"')

write(
    "examples/generic_abstractions_052.saga",
    '''fn keep[F, A](value: F[A]) -> F[A] = value

let maybe = keep(Option.Some(42))
match maybe {
    case Option.Some(value) { print(value) }
    case Option.None { print(0) }
}

let result: Result[int, text] = Result.Ok(7)
match result {
    case Result.Ok(value) { print(value) }
    case Result.Err(message) { print(message) }
}
''',
)

write(
    "docs/GENERIC_ABSTRACTIONS_0.52.md",
    '''# Saga 0.52 Generic Abstraction Foundations

Saga 0.52 builds on the 0.51 Generic ADT implementation in three connected areas.

## Option and Result are intrinsic Generic ADTs

`Option[T]` and `Result[T, E]` now participate in the same constructor and exhaustive-match model as user-defined generic enums:

```saga
let value = Option.Some(42)
let empty: Option[int] = Option.None
let outcome: Result[int, text] = Result.Ok(7)

match value {
    case Option.Some(item) { print(item) }
    case Option.None { print(0) }
}
```

The established `some`, `none`, `ok`, `err`, `is_some`, `is_ok`, unwrap helpers, and `?` propagation remain source-compatible. Both spellings use the same runtime wrappers, so existing APIs do not fork into two representations.

## Generic method and interface contracts

Method-local generic parameter names are alpha-equivalent across an interface contract and its implementation. An interface may call its parameter `U` while an implementation calls the corresponding parameter `V`; compatibility depends on structure and generic arity rather than spelling.

Saga continues to use `interface` as its trait-style contract surface instead of introducing a second overlapping `trait` keyword.

## Higher-kinded type foundation

A declared type variable may now appear in constructor position:

```saga
fn keep[F, A](value: F[A]) -> F[A] = value
```

Calling `keep([1, 2, 3])` infers `F` as the `list` type constructor and `A` as `int`. Calling it with `Option.Some(42)` infers the `Option`/`option` constructor and `int`.

Internally, Saga distinguishes a type-constructor binding from an ordinary type binding and reconstructs applied result types after substitution. The arity (kind) is inferred from each `F[...]` application and checked during unification.

### Deliberate boundary

0.52 is the higher-kinded *foundation*, not a claim of a finished kind calculus. Explicit kind annotation syntax such as `F[_]`, higher-rank kinds, type lambdas, and a dedicated trait/type-class declaration syntax are intentionally deferred. The new representation and inference path are designed so those features can be added without replacing the 0.51 Generic ADT model.
''',
)

write(
    "tests/test_generic_abstractions_052.py",
    '''from __future__ import annotations

import unittest

from saga.api import compile_source, run_source
from saga.typesys import INT, TEXT, OPTION, TYPECTOR, parse_type, substitute, unify


class GenericAbstractions052Tests(unittest.TestCase):
    def run_program(self, source: str) -> list[str]:
        output: list[str] = []
        run_source(source, output=output.append)
        return output

    def test_option_adt_constructor_and_exhaustive_match(self):
        source = """
        let value = Option.Some(42)
        match value {
            case Option.Some(item) { print(item) }
            case Option.None { print(0) }
        }
        """
        self.assertEqual(self.run_program(source), ["42"])

    def test_option_none_uses_context_and_legacy_some_shares_representation(self):
        source = """
        let empty: Option[int] = Option.None
        match empty {
            case Option.Some(item) { print(item) }
            case Option.None { print("empty") }
        }
        let legacy = some(5)
        match legacy {
            case Option.Some(item) { print(item) }
            case Option.None { print(0) }
        }
        print(is_some(Option.Some(9)))
        """
        self.assertEqual(self.run_program(source), ["empty", "5", "true"])

    def test_result_adt_constructor_and_legacy_helpers_share_representation(self):
        source = """
        let outcome: Result[int, text] = Result.Ok(7)
        match outcome {
            case Result.Ok(value) { print(value) }
            case Result.Err(message) { print(message) }
        }
        let legacy = err("boom")
        match legacy {
            case Result.Ok(value) { print(value) }
            case Result.Err(message) { print(message) }
        }
        print(is_ok(Result.Ok(1)))
        """
        self.assertEqual(self.run_program(source), ["7", "boom", "true"])

    def test_legacy_question_propagation_remains_compatible(self):
        source = """
        fn increment(value: option[int]) -> option[int] {
            let item = value?
            return some(item + 1)
        }
        let result = increment(Option.Some(4))
        match result {
            case Option.Some(value) { print(value) }
            case Option.None { print(0) }
        }
        """
        self.assertEqual(self.run_program(source), ["5"])

    def test_higher_kinded_type_application_unifies_constructor_and_argument(self):
        pattern = parse_type("F[A]", {"F", "A"})
        mapping = {}
        self.assertTrue(unify(pattern, OPTION(INT), mapping))
        self.assertEqual(mapping["F"], TYPECTOR("option"))
        self.assertEqual(mapping["A"], INT)
        result = substitute(parse_type("F[B]", {"F", "B"}), {**mapping, "B": TEXT})
        self.assertEqual(result, OPTION(TEXT))

    def test_language_level_hkt_inference_works_for_list_and_option(self):
        source = """
        fn keep[F, A](value: F[A]) -> F[A] = value
        let values = keep([1, 2, 3])
        print(len(values))
        let maybe = keep(Option.Some(9))
        match maybe {
            case Option.Some(value) { print(value) }
            case Option.None { print(0) }
        }
        """
        self.assertEqual(self.run_program(source), ["3", "9"])

    def test_generic_interface_method_is_alpha_equivalent(self):
        source = """
        interface Transformer[T] {
            fn transform[U](value: T, mapper: fn[T, U]) -> U
        }
        class Identity[T] implements Transformer[T] {
            override fn transform[V](value: T, mapper: fn[T, V]) -> V = mapper(value)
        }
        """
        compile_source(source)


if __name__ == "__main__":
    unittest.main()
''',
)

write(
    "implementations/go/cmd/saga-go/generic_abstractions_052_test.go",
    '''package main

import "testing"

func TestGenericAbstractions052OptionAndResultADTs(t *testing.T) {
    src := `let value = Option.Some(42)
match value {
case Option.Some(item) { print(item) }
case Option.None { print(0) }
}
let result: Result[int, text] = Result.Ok(7)
match result {
case Result.Ok(item) { print(item) }
case Result.Err(message) { print(message) }
}`
    out, err := runSagaForTest(t, src)
    if err != nil { t.Fatal(err) }
    if out != "42\n7" { t.Fatalf("output=%q", out) }
}

func TestGenericAbstractions052LegacyWrappersMatchNewADTPatterns(t *testing.T) {
    src := `let value = some(5)
match value {
case Option.Some(item) { print(item) }
case Option.None { print(0) }
}
let result = err("boom")
match result {
case Result.Ok(item) { print(item) }
case Result.Err(message) { print(message) }
}`
    out, err := runSagaForTest(t, src)
    if err != nil { t.Fatal(err) }
    if out != "5\nboom" { t.Fatalf("output=%q", out) }
}

func TestGenericAbstractions052HigherKindedInference(t *testing.T) {
    src := `fn keep[F, A](value: F[A]) -> F[A] = value
let values = keep([1, 2, 3])
print(len(values))
let maybe = keep(Option.Some(9))
match maybe {
case Option.Some(item) { print(item) }
case Option.None { print(0) }
}`
    out, err := runSagaForTest(t, src)
    if err != nil { t.Fatal(err) }
    if out != "3\n9" { t.Fatalf("output=%q", out) }
}

func TestGenericAbstractions052GenericInterfaceMethodAlphaEquivalence(t *testing.T) {
    src := `interface Transformer[T] {
fn transform[U](value: T, mapper: fn[T, U]) -> U
}
class Identity[T] implements Transformer[T] {
override fn transform[V](value: T, mapper: fn[T, V]) -> V = mapper(value)
}
print(1)`
    out, err := runSagaForTest(t, src)
    if err != nil { t.Fatal(err) }
    if out != "1" { t.Fatalf("output=%q", out) }
}
''',
)

print("Saga 0.52 generic abstraction patch staged successfully")
