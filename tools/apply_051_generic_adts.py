#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one occurrence, found {count}: {old[:100]!r}")
    write(path, text.replace(old, new, 1))


def regex_once(path: str, pattern: str, replacement: str) -> None:
    text = read(path)
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE | re.DOTALL)
    if count != 1:
        raise RuntimeError(f"{path}: expected one regex match, found {count}: {pattern[:100]!r}")
    write(path, updated)


# ---------- Python reference implementation ----------
replace_once(
    "saga/ast_nodes.py",
    '''class EnumDecl(Stmt):\n    keyword: Token\n    name: Token\n    variants: list[EnumVariantDecl]\n    visibility: str = "internal"\n''',
    '''class EnumDecl(Stmt):\n    keyword: Token\n    name: Token\n    variants: list[EnumVariantDecl]\n    visibility: str = "internal"\n    type_params: list[str] = field(default_factory=list)\n''',
)

replace_once(
    "saga/parser.py",
    '''    def _enum(self, keyword: Token) -> EnumDecl:\n        name = self._consume_name("enum 名が必要です")\n        self._consume(TokenKind.LBRACE, "enum 本体には '{' が必要です")\n''',
    '''    def _enum(self, keyword: Token) -> EnumDecl:\n        name = self._consume_name("enum 名が必要です")\n        type_params = self._type_params()\n        self._consume(TokenKind.LBRACE, "enum 本体には '{' が必要です")\n''',
)
replace_once(
    "saga/parser.py",
    '''        return EnumDecl(keyword, name, variants)\n''',
    '''        return EnumDecl(keyword, name, variants, type_params=type_params)\n''',
)

replace_once(
    "saga/checker.py",
    '''        self.enums: dict[str, set[str]] = {}\n        self.enum_payloads: dict[str, dict[str, tuple[Type, ...]]] = {}\n''',
    '''        self.enums: dict[str, set[str]] = {}\n        self.enum_payloads: dict[str, dict[str, tuple[Type, ...]]] = {}\n        self.enum_type_params: dict[str, list[str]] = {}\n''',
)
replace_once(
    "saga/checker.py",
    '''        payloads: dict[str, tuple[Type, ...]] = {}\n        for variant in stmt.variants:\n            try:\n                payloads[variant.name.lexeme] = tuple(parse_type(text) for text in variant.payload_types)\n            except ValueError as exc:\n                self._error(variant.name, str(exc), diagnostic_id="SAGA-T106")\n        self.enums[name] = set(variants)\n        self.enum_payloads[name] = payloads\n        self.scopes[-1][name] = VariableInfo(Type(f"enumtype:{name}"), False)\n''',
    '''        if len(set(stmt.type_params)) != len(stmt.type_params):\n            self._error(stmt.name, f"enum '{name}' の型引数が重複しています", diagnostic_id="SAGA-T108")\n        type_vars = set(stmt.type_params)\n        payloads: dict[str, tuple[Type, ...]] = {}\n        for variant in stmt.variants:\n            try:\n                payloads[variant.name.lexeme] = tuple(parse_type(text, type_vars) for text in variant.payload_types)\n            except ValueError as exc:\n                self._error(variant.name, str(exc), diagnostic_id="SAGA-T106")\n        self.enums[name] = set(variants)\n        self.enum_payloads[name] = payloads\n        self.enum_type_params[name] = list(stmt.type_params)\n        self.scopes[-1][name] = VariableInfo(Type(f"enumtype:{name}"), False)\n''',
)
replace_once(
    "saga/checker.py",
    '''            if name in self.enums:\n                if value.args:\n                    self._error(token, f"enum型 '{name}' は型引数を取りません")\n                return\n''',
    '''            if name in self.enums:\n                params = self.enum_type_params.get(name, [])\n                if len(value.args) != len(params):\n                    self._error(token, f"enum型 '{name}' には {len(params)} 個の型引数が必要です", diagnostic_id="SAGA-T103")\n                return\n''',
)
replace_once(
    "saga/checker.py",
    '''        if isinstance(expr, ast.Member): return self._check_member(expr)\n''',
    '''        if isinstance(expr, ast.Member): return self._check_member(expr, expected)\n''',
)
replace_once(
    "saga/checker.py",
    '''    def _check_member(self, expr: ast.Member) -> Type:\n        target = self._check_expr(expr.target)\n        if target.name.startswith("enumtype:"):\n            enum_name = target.name.split(":", 1)[1]\n            variants = self.enums.get(enum_name)\n            if variants is None or expr.name.lexeme not in variants:\n                self._error(expr.name, f"enum variant '{enum_name}.{expr.name.lexeme}' が見つかりません", diagnostic_id="SAGA-T106")\n            payload = self.enum_payloads.get(enum_name, {}).get(expr.name.lexeme, ())\n            result = Type(f"object:{enum_name}")\n            return FUNCTION(list(payload), result) if payload else result\n''',
    '''    def _check_member(self, expr: ast.Member, expected: Type | None = None) -> Type:\n        target = self._check_expr(expr.target)\n        if target.name.startswith("enumtype:"):\n            enum_name = target.name.split(":", 1)[1]\n            variants = self.enums.get(enum_name)\n            if variants is None or expr.name.lexeme not in variants:\n                self._error(expr.name, f"enum variant '{enum_name}.{expr.name.lexeme}' が見つかりません", diagnostic_id="SAGA-T106")\n            payload = self.enum_payloads.get(enum_name, {}).get(expr.name.lexeme, ())\n            params = self.enum_type_params.get(enum_name, [])\n            result = Type(f"object:{enum_name}", tuple(TYPEVAR(name) for name in params))\n            if payload:\n                return FUNCTION(list(payload), result)\n            if not params:\n                return result\n            if expected is not None and expected.name == result.name and len(expected.args) == len(params):\n                return expected\n            self._error(\n                expr.name,\n                f"generic enum variant '{enum_name}.{expr.name.lexeme}' の型引数を推論できません",\n                f"例: let value: {enum_name}[int] = {enum_name}.{expr.name.lexeme}",\n                "SAGA-T113",\n            )\n''',
)
replace_once(
    "saga/checker.py",
    '''        mapping: dict[str, Type] = {}\n        for expected, actual in zip(callee_type.args, arg_types):\n            matcher = self._unify_native_contract if native_contract else self._unify\n            if not matcher(expected, actual, mapping): self._error(expr.paren, f"引数の型が一致しません。必要: {expected}、実際: {actual}", diagnostic_id="SAGA-T105")\n        return substitute(callee_type.result or ANY, mapping)\n''',
    '''        mapping: dict[str, Type] = {}\n        for parameter_type, actual in zip(callee_type.args, arg_types):\n            matcher = self._unify_native_contract if native_contract else self._unify\n            if not matcher(parameter_type, actual, mapping): self._error(expr.paren, f"引数の型が一致しません。必要: {parameter_type}、実際: {actual}", diagnostic_id="SAGA-T105")\n        enum_constructor = None\n        if isinstance(expr.callee, ast.Member):\n            target_type = self._check_expr(expr.callee.target)\n            if target_type.name.startswith("enumtype:"):\n                enum_constructor = target_type.name.split(":", 1)[1]\n        raw_result = callee_type.result or ANY\n        if enum_constructor is not None and expected is not None and expected.name == raw_result.name:\n            self._unify(raw_result, expected, mapping)\n        resolved = substitute(raw_result, mapping)\n        if enum_constructor is not None and self._contains_typevar(resolved):\n            self._error(\n                expr.paren,\n                f"generic enum constructor '{enum_constructor}.{expr.callee.name.lexeme}' の型引数を完全に推論できません",\n                f"変数または戻り値に {enum_constructor}[...] の型注釈を追加してください",\n                "SAGA-T113",\n            )\n        return resolved\n\n    @staticmethod\n    def _contains_typevar(value: Type) -> bool:\n        if is_typevar(value):\n            return True\n        if any(TypeChecker._contains_typevar(arg) for arg in value.args):\n            return True\n        return value.result is not None and TypeChecker._contains_typevar(value.result)\n''',
)

# Specialize match payload bindings using the concrete ADT type arguments.
regex_once(
    "saga/checker.py",
    r'''    def _enum_match_pattern\(self, expr: ast\.Expr, enum_name: str \| None\) -> tuple\[str, dict\[str, VariableInfo\]\] \| None:\n.*?        return variant, bindings\n''',
    '''    def _enum_match_pattern(self, expr: ast.Expr, enum_type: Type | None) -> tuple[str, dict[str, VariableInfo]] | None:\n        if enum_type is None or not enum_type.name.startswith("object:"):\n            return None\n        enum_name = enum_type.name.split(":", 1)[1]\n        if enum_name not in self.enums:\n            return None\n        callee: ast.Expr = expr.callee if isinstance(expr, ast.Call) else expr\n        qname = self._qualified_expr_name(callee)\n        if not qname or "." not in qname:\n            return None\n        owner, variant = qname.rsplit(".", 1)\n        if owner != enum_name or variant not in self.enums.get(enum_name, set()):\n            return None\n        params = self.enum_type_params.get(enum_name, [])\n        mapping = {name: arg for name, arg in zip(params, enum_type.args)}\n        payload = tuple(substitute(t, mapping) for t in self.enum_payloads.get(enum_name, {}).get(variant, ()))\n        args = expr.arguments if isinstance(expr, ast.Call) else []\n        if len(args) != len(payload):\n            token = getattr(expr, "paren", None) or getattr(expr, "name", None) or getattr(callee, "name", None)\n            self._error(token, f"enum variant '{enum_name}.{variant}' は {len(payload)} 個のpayloadを必要とします", diagnostic_id="SAGA-T103")\n        bindings: dict[str, VariableInfo] = {}\n        for arg, typ in zip(args, payload):\n            if not isinstance(arg, ast.Variable):\n                token = getattr(arg, "name", None) or getattr(expr, "paren", None)\n                self._error(token, "matchのpayload patternには変数名または '_' を書いてください", diagnostic_id="SAGA-T103")\n            name = arg.name.lexeme\n            if name == "_":\n                continue\n            if name in bindings:\n                self._error(arg.name, f"match payload変数 '{name}' が重複しています", diagnostic_id="SAGA-T108")\n            bindings[name] = VariableInfo(typ, False)\n        return variant, bindings\n''',
)
replace_once(
    "saga/checker.py",
    '''                enum_pattern = self._enum_match_pattern(case.pattern, enum_name)\n''',
    '''                enum_pattern = self._enum_match_pattern(case.pattern, value_type if enum_name is not None else None)\n''',
)

# Preserve generic enums across namespaced source modules and .smi interfaces.
replace_once(
    "saga/checker.py",
    '''            if item.get("kind") == "enum":\n                name = str(item["name"]); qualified = f"{bind}.{name}"\n                raw_variants = item.get("variants", [])\n''',
    '''            if item.get("kind") == "enum":\n                name = str(item["name"]); qualified = f"{bind}.{name}"\n                type_params = [str(v) for v in item.get("type_params", [])]\n                vars_ = set(type_params)\n                raw_variants = item.get("variants", [])\n''',
)
replace_once(
    "saga/checker.py",
    '''                    parsed = tuple(self._qualify_module_type(self._interface_type(t), bind, public_classes) for t in payload_text)\n                    payloads[vname] = parsed\n                self.enums[qualified] = variants\n                self.enum_payloads[qualified] = payloads\n''',
    '''                    parsed = tuple(self._qualify_module_type(self._interface_type(t, vars_), bind, public_classes) for t in payload_text)\n                    payloads[vname] = parsed\n                self.enums[qualified] = variants\n                self.enum_payloads[qualified] = payloads\n                self.enum_type_params[qualified] = type_params\n''',
)
replace_once(
    "saga/checker.py",
    '''                self.enum_payloads[qualified] = {\n                    variant: tuple(self._qualify_module_type(t, bind, public_names) for t in payload)\n                    for variant, payload in child.enum_payloads.get(d.name.lexeme, {}).items()\n                }\n                members[d.name.lexeme] = Type(f"enumtype:{qualified}")\n''',
    '''                self.enum_payloads[qualified] = {\n                    variant: tuple(self._qualify_module_type(t, bind, public_names) for t in payload)\n                    for variant, payload in child.enum_payloads.get(d.name.lexeme, {}).items()\n                }\n                self.enum_type_params[qualified] = list(child.enum_type_params.get(d.name.lexeme, []))\n                members[d.name.lexeme] = Type(f"enumtype:{qualified}")\n''',
)
replace_once(
    "saga/module_interface.py",
    '''                exports.append({\n                    "kind": "enum", "name": stmt.name.lexeme,\n                    # Declaration order is ABI-significant because the Native\n''',
    '''                exports.append({\n                    "kind": "enum", "name": stmt.name.lexeme,\n                    "type_params": list(stmt.type_params),\n                    # Declaration order is ABI-significant because the Native\n''',
)

# ---------- Independent Go implementation ----------
replace_once(
    "implementations/go/cmd/saga-go/ast.go",
    '''type EnumDecl struct {\n\tName       string\n\tVariants   []EnumVariant\n\tVisibility string\n\tTok        Token\n}\n''',
    '''type EnumDecl struct {\n\tName       string\n\tTypeParams []string\n\tVariants   []EnumVariant\n\tVisibility string\n\tTok        Token\n}\n''',
)
replace_once(
    "implementations/go/cmd/saga-go/parser.go",
    '''\tname, e := p.needContextualName("enum name")\n\tif e != nil {\n\t\treturn nil, e\n\t}\n\td := &EnumDecl{Name: name.Lex, Tok: name}\n''',
    '''\tname, e := p.needContextualName("enum name")\n\tif e != nil {\n\t\treturn nil, e\n\t}\n\ttypeParams, e := p.typeParams()\n\tif e != nil {\n\t\treturn nil, e\n\t}\n\td := &EnumDecl{Name: name.Lex, TypeParams: typeParams, Tok: name}\n''',
)
replace_once(
    "implementations/go/cmd/saga-go/checker.go",
    '''\tEnums              map[string]map[string]bool\n\tEnumPayloads       map[string]map[string][]Type\n''',
    '''\tEnums              map[string]map[string]bool\n\tEnumPayloads       map[string]map[string][]Type\n\tEnumTypeParams     map[string][]string\n''',
)
replace_once(
    "implementations/go/cmd/saga-go/checker.go",
    '''Enums: map[string]map[string]bool{}, EnumPayloads: map[string]map[string][]Type{}, SourceModules:''',
    '''Enums: map[string]map[string]bool{}, EnumPayloads: map[string]map[string][]Type{}, EnumTypeParams: map[string][]string{}, SourceModules:''',
)
replace_once(
    "implementations/go/cmd/saga-go/checker.go",
    '''\tvariants := map[string]bool{}\n\tpayloads := map[string][]Type{}\n\tfor _, v := range d.Variants {\n''',
    '''\tif hasDupStrings(d.TypeParams) {\n\t\treturn c.err(d.Tok, "SAGA-T108", "duplicate enum type parameter")\n\t}\n\tvars := map[string]bool{}\n\tfor _, name := range d.TypeParams {\n\t\tvars[name] = true\n\t}\n\tvariants := map[string]bool{}\n\tpayloads := map[string][]Type{}\n\tfor _, v := range d.Variants {\n''',
)
replace_once(
    "implementations/go/cmd/saga-go/checker.go",
    '''\t\tfor _, r := range v.Payload {\n\t\t\tpayloads[v.Name] = append(payloads[v.Name], typeFromRef(r, map[string]bool{}))\n\t\t}\n\t}\n\tc.Enums[d.Name] = variants\n\tc.EnumPayloads[d.Name] = payloads\n''',
    '''\t\tfor _, r := range v.Payload {\n\t\t\tpayloads[v.Name] = append(payloads[v.Name], typeFromRef(r, vars))\n\t\t}\n\t}\n\tc.Enums[d.Name] = variants\n\tc.EnumPayloads[d.Name] = payloads\n\tc.EnumTypeParams[d.Name] = append([]string{}, d.TypeParams...)\n''',
)
replace_once(
    "implementations/go/cmd/saga-go/checker.go",
    '''\tcase *Member:\n\t\treturn c.checkMember(v)\n''',
    '''\tcase *Member:\n\t\treturn c.checkMember(v, expected)\n''',
)
replace_once(
    "implementations/go/cmd/saga-go/checker.go",
    '''func (c *Checker) checkMember(v *Member) (Type, error) {\n''',
    '''func (c *Checker) checkMember(v *Member, expected *Type) (Type, error) {\n''',
)
replace_once(
    "implementations/go/cmd/saga-go/checker.go",
    '''\tif strings.HasPrefix(t.Name, "enumtype:") {\n\t\tn := strings.TrimPrefix(t.Name, "enumtype:")\n\t\tif c.Enums[n][v.Name] {\n\t\t\tps := c.EnumPayloads[n][v.Name]\n\t\t\tif len(ps) > 0 {\n\t\t\t\treturn fnT(ps, objectT(n)), nil\n\t\t\t}\n\t\t\treturn objectT(n), nil\n\t\t}\n\t\treturn TAny, c.err(v.Tok, "SAGA-T106", "unknown enum variant "+n+"."+v.Name)\n\t}\n''',
    '''\tif strings.HasPrefix(t.Name, "enumtype:") {\n\t\tn := strings.TrimPrefix(t.Name, "enumtype:")\n\t\tif c.Enums[n][v.Name] {\n\t\t\tps := c.EnumPayloads[n][v.Name]\n\t\t\tparams := c.EnumTypeParams[n]\n\t\t\tretArgs := []Type{}\n\t\t\tfor _, name := range params {\n\t\t\t\tretArgs = append(retArgs, typeVar(name))\n\t\t\t}\n\t\t\tresult := objectT(n, retArgs...)\n\t\t\tif len(ps) > 0 {\n\t\t\t\treturn fnT(ps, result), nil\n\t\t\t}\n\t\t\tif len(params) == 0 {\n\t\t\t\treturn result, nil\n\t\t\t}\n\t\t\tif expected != nil && expected.Name == result.Name && len(expected.Args) == len(params) {\n\t\t\t\treturn *expected, nil\n\t\t\t}\n\t\t\treturn TAny, c.err(v.Tok, "SAGA-T113", "cannot infer generic enum variant "+n+"."+v.Name+"; add a "+n+"[...] type annotation")\n\t\t}\n\t\treturn TAny, c.err(v.Tok, "SAGA-T106", "unknown enum variant "+n+"."+v.Name)\n\t}\n''',
)

# Generic constructor inference can combine payload inference with contextual result type.
replace_once(
    "implementations/go/cmd/saga-go/checker.go",
    '''\tm := map[string]Type{}\n\tfor i := range args {\n\t\tif !unify(ct.Args[i], args[i], m) && !c.assignable(ct.Args[i], args[i]) {\n\t\t\treturn TAny, c.err(v.Args[i].token(), "SAGA-T105", fmt.Sprintf("argument %d type mismatch: expected %s, got %s", i+1, ct.Args[i], args[i]))\n\t\t}\n\t}\n''',
    '''\tm := map[string]Type{}\n\tfor i := range args {\n\t\tif !unify(ct.Args[i], args[i], m) && !c.assignable(ct.Args[i], args[i]) {\n\t\t\treturn TAny, c.err(v.Args[i].token(), "SAGA-T105", fmt.Sprintf("argument %d type mismatch: expected %s, got %s", i+1, ct.Args[i], args[i]))\n\t\t}\n\t}\n\tenumConstructor := ""\n\tif member, ok := v.Callee.(*Member); ok {\n\t\tif targetType, err := c.checkExpr(member.Target, nil); err == nil && strings.HasPrefix(targetType.Name, "enumtype:") {\n\t\t\tenumConstructor = strings.TrimPrefix(targetType.Name, "enumtype:")\n\t\t}\n\t}\n\tif enumConstructor != "" && expected != nil && ct.Result != nil && expected.Name == ct.Result.Name {\n\t\tunify(*ct.Result, *expected, m)\n\t}\n''',
)
replace_once(
    "implementations/go/cmd/saga-go/checker.go",
    '''\tresolved := substitute(*ct.Result, m)\n\treturn c.resolveAssociatedType(resolved, m, v.Tok)\n}\n\nfunc (c *Checker) checkClosure''',
    '''\tresolved := substitute(*ct.Result, m)\n\tif enumConstructor != "" && containsTypeVar(resolved) {\n\t\treturn TAny, c.err(v.Tok, "SAGA-T113", "cannot fully infer generic enum constructor "+enumConstructor+"; add an explicit "+enumConstructor+"[...] result type")\n\t}\n\treturn c.resolveAssociatedType(resolved, m, v.Tok)\n}\n\nfunc containsTypeVar(t Type) bool {\n\tif isTypeVar(t) {\n\t\treturn true\n\t}\n\tfor _, arg := range t.Args {\n\t\tif containsTypeVar(arg) {\n\t\t\treturn true\n\t\t}\n\t}\n\treturn t.Result != nil && containsTypeVar(*t.Result)\n}\n\nfunc (c *Checker) checkClosure''',
)

# Concrete enum arguments specialize payload variables in match cases.
regex_once(
    "implementations/go/cmd/saga-go/checker.go",
    r'''func \(c \*Checker\) enumMatchPattern\(e Expr, enumName string\) \(string, map\[string\]VarInfo, bool, error\) \{.*?\n\treturn variant, bindings, true, nil\n\}\n''',
    '''func (c *Checker) enumMatchPattern(e Expr, enumType Type) (string, map[string]VarInfo, bool, error) {\n\tenumName := objectTypeName(enumType)\n\tif enumName == "" || c.Enums[enumName] == nil {\n\t\treturn "", nil, false, nil\n\t}\n\tcallee := e\n\targs := []Expr{}\n\tif call, ok := e.(*Call); ok {\n\t\tcallee = call.Callee\n\t\targs = call.Args\n\t}\n\tq, ok := sourceQualifiedExprName(callee)\n\tif !ok || !strings.Contains(q, ".") {\n\t\treturn "", nil, false, nil\n\t}\n\tidx := strings.LastIndex(q, ".")\n\towner, variant := q[:idx], q[idx+1:]\n\tif owner != enumName || !c.Enums[enumName][variant] {\n\t\treturn "", nil, false, nil\n\t}\n\tmapping := typeParamMap(c.EnumTypeParams[enumName], enumType.Args)\n\trawPayload := c.EnumPayloads[enumName][variant]\n\tpayload := make([]Type, 0, len(rawPayload))\n\tfor _, typ := range rawPayload {\n\t\tpayload = append(payload, substitute(typ, mapping))\n\t}\n\tif len(args) != len(payload) {\n\t\treturn "", nil, true, c.err(e.token(), "SAGA-T103", fmt.Sprintf("enum variant %s.%s expects %d payload values", enumName, variant, len(payload)))\n\t}\n\tbindings := map[string]VarInfo{}\n\tfor idx, arg := range args {\n\t\tv, ok := arg.(*Variable)\n\t\tif !ok {\n\t\t\treturn "", nil, true, c.err(arg.token(), "SAGA-T103", "match payload pattern must be a variable or _")\n\t\t}\n\t\tif v.Name == "_" {\n\t\t\tcontinue\n\t\t}\n\t\tif _, exists := bindings[v.Name]; exists {\n\t\t\treturn "", nil, true, c.err(v.Tok, "SAGA-T108", "duplicate match payload variable "+v.Name)\n\t\t}\n\t\tbindings[v.Name] = VarInfo{Typ: payload[idx]}\n\t}\n\treturn variant, bindings, true, nil\n}\n''',
)
replace_once(
    "implementations/go/cmd/saga-go/checker.go",
    '''\t\t\tvariant, bindings, matched, pe := c.enumMatchPattern(mc.Pattern, enumName)\n''',
    '''\t\t\tvariant, bindings, matched, pe := c.enumMatchPattern(mc.Pattern, vt)\n''',
)

# Preserve type parameters through source modules.
replace_once(
    "implementations/go/cmd/saga-go/checker.go",
    '''\t\t\t\tc.Enums[qualified] = variants\n\t\t\t\tc.EnumPayloads[qualified] = payloads\n\t\t\t\tmembers[d.Name] = Type{Name: "enumtype:" + qualified}\n''',
    '''\t\t\t\tc.Enums[qualified] = variants\n\t\t\t\tc.EnumPayloads[qualified] = payloads\n\t\t\t\tc.EnumTypeParams[qualified] = append([]string{}, child.EnumTypeParams[d.Name]...)\n\t\t\t\tmembers[d.Name] = Type{Name: "enumtype:" + qualified}\n''',
)

# Go module interface export: generic enum parameters are ABI-significant.
replace_once(
    "implementations/go/cmd/saga-go/module_interface.go",
    '''\t\tcase *EnumDecl:\n\t\t\tif d.Visibility == "public" {\n\t\t\t\tvariants := []map[string]interface{}{}\n\t\t\t\tfor _, v := range d.Variants {\n\t\t\t\t\tpayload := []string{}\n\t\t\t\t\tfor _, r := range v.Payload {\n\t\t\t\t\t\tpayload = append(payload, moduleTypeText(typeFromRef(r, map[string]bool{})))\n\t\t\t\t\t}\n\t\t\t\t\tvariants = append(variants, map[string]interface{}{"name": v.Name, "payload": payload})\n\t\t\t\t}\n\t\t\t\texports = append(exports, map[string]interface{}{"kind": "enum", "name": d.Name, "variants": variants})\n\t\t\t}\n''',
    '''\t\tcase *EnumDecl:\n\t\t\tif d.Visibility == "public" {\n\t\t\t\tvariants := []map[string]interface{}{}\n\t\t\t\tvars := map[string]bool{}\n\t\t\t\tfor _, name := range d.TypeParams {\n\t\t\t\t\tvars[name] = true\n\t\t\t\t}\n\t\t\t\tfor _, v := range d.Variants {\n\t\t\t\t\tpayload := []string{}\n\t\t\t\t\tfor _, r := range v.Payload {\n\t\t\t\t\t\tpayload = append(payload, moduleTypeText(typeFromRef(r, vars)))\n\t\t\t\t\t}\n\t\t\t\t\tvariants = append(variants, map[string]interface{}{"name": v.Name, "payload": payload})\n\t\t\t\t}\n\t\t\t\texports = append(exports, map[string]interface{}{"kind": "enum", "name": d.Name, "type_params": append([]string{}, d.TypeParams...), "variants": variants})\n\t\t\t}\n''',
)

# Import generic enums from .smi.json in the Go implementation.
replace_once(
    "implementations/go/cmd/saga-go/checker.go",
    '''\t\tif (kind == "class" || kind == "interface") && name != "" {\n\t\t\tpublicClasses[name] = true\n\t\t}\n''',
    '''\t\tif (kind == "class" || kind == "interface" || kind == "enum") && name != "" {\n\t\t\tpublicClasses[name] = true\n\t\t}\n''',
)
replace_once(
    "implementations/go/cmd/saga-go/checker.go",
    '''\t\tcase "var":\n''',
    '''\t\tcase "enum":\n\t\t\tqualified := bind + "." + name\n\t\t\ttypeParams := interfaceStringList(item["type_params"])\n\t\t\tvariants := map[string]bool{}\n\t\t\tpayloads := map[string][]Type{}\n\t\t\tfor _, rawVariant := range interfaceMapList(item["variants"]) {\n\t\t\t\tvariantName, _ := rawVariant["name"].(string)\n\t\t\t\tif variantName == "" {\n\t\t\t\t\tcontinue\n\t\t\t\t}\n\t\t\t\tvariants[variantName] = true\n\t\t\t\tfor _, raw := range interfaceStringList(rawVariant["payload"]) {\n\t\t\t\t\tt, err := moduleInterfaceType(raw, typeParams)\n\t\t\t\t\tif err != nil {\n\t\t\t\t\t\treturn err\n\t\t\t\t\t}\n\t\t\t\t\tpayloads[variantName] = append(payloads[variantName], qualifySourceModuleType(t, bind, publicClasses))\n\t\t\t\t}\n\t\t\t}\n\t\t\tc.Enums[qualified] = variants\n\t\t\tc.EnumPayloads[qualified] = payloads\n\t\t\tc.EnumTypeParams[qualified] = append([]string{}, typeParams...)\n\t\t\tmembers[name] = Type{Name: "enumtype:" + qualified}\n\t\tcase "var":\n''',
)

# ---------- Version and public documentation ----------
replace_once("pyproject.toml", 'version = "0.50.0"', 'version = "0.51.0"')
replace_once("saga/__init__.py", '__version__ = "0.50.0"', '__version__ = "0.51.0"')

go_version_hits = []
for path in (ROOT / "implementations/go/cmd/saga-go").glob("*.go"):
    text = path.read_text(encoding="utf-8")
    if re.search(r'\bsagaGoVersion\s*=\s*"0\.50\.0"', text):
        go_version_hits.append(path)
if len(go_version_hits) != 1:
    raise RuntimeError(f"expected one sagaGoVersion 0.50.0 definition, found {go_version_hits}")
p = go_version_hits[0]
p.write_text(re.sub(r'(\bsagaGoVersion\s*=\s*)"0\.50\.0"', r'\1"0.51.0"', p.read_text(encoding="utf-8"), count=1), encoding="utf-8")

# Add the 0.51 regression suite to normal CI.
replace_once(
    ".github/workflows/saga-ci.yml",
    '''          python -m unittest\n          tests.test_control_ga_050\n''',
    '''          python -m unittest\n          tests.test_generic_adts_051\n          tests.test_control_ga_050\n''',
)

# Public language example.
write(
    "examples/generic_adts_051.saga",
    '''enum Maybe[T] {\n    None,\n    Some(T)\n}\n\nenum Either[L, R] {\n    Left(L),\n    Right(R)\n}\n\nlet answer = Maybe.Some(42)\nmatch answer {\n    case Maybe.Some(value) { print(value) }\n    case Maybe.None { print(0) }\n}\n\nlet state: Either[int, text] = Either.Left(7)\nmatch state {\n    case Either.Left(value) { print(value) }\n    case Either.Right(message) { print(message) }\n}\n''',
)

write(
    "docs/GENERIC_ADTS_0.51.md",
    '''# Saga 0.51 Generic Algebraic Data Types\n\nSaga 0.51 extends the existing tagged-enum and exhaustive-match core with generic algebraic data types (ADTs).\n\n```saga\nenum Maybe[T] {\n    None,\n    Some(T)\n}\n\nlet inferred = Maybe.Some(42)       // Maybe[int]\nlet empty: Maybe[int] = Maybe.None // contextual type for a nullary variant\n\nmatch inferred {\n    case Maybe.Some(value) { print(value) } // value: int\n    case Maybe.None { print(0) }\n}\n```\n\n## Type inference\n\nPayload-bearing constructors infer type arguments by unification. If a constructor cannot determine every enum parameter from its payload, an expected type may complete the mapping:\n\n```saga\nenum Either[L, R] { Left(L), Right(R) }\nlet value: Either[int, text] = Either.Left(7)\n```\n\nA generic nullary variant has no payload from which to infer parameters, so it requires a contextual type. This is rejected intentionally:\n\n```saga\nlet value = Maybe.None // SAGA-T113\n```\n\n## Match typing\n\nExhaustive matching remains mandatory when no `default` is present. Payload bindings are specialized from the matched value, so `Maybe[int]` makes `Some(value)` bind `value` as `int`, not `any` or an unresolved type variable.\n\n## Compatibility\n\nNon-generic enums keep their 0.50 behavior and runtime representation. Type parameters are compile-time information and do not change the existing tagged-value runtime layout. Namespaced source modules and `.smi.json` interfaces preserve enum type parameters as ABI-significant metadata.\n''',
)

# Python + cross-implementation regression.
write(
    "tests/test_generic_adts_051.py",
    '''from __future__ import annotations\n\nimport json\nimport shutil\nimport subprocess\nimport tempfile\nimport unittest\nfrom pathlib import Path\n\nfrom saga.api import compile_source, run_file, run_source\nfrom saga.errors import TypeCheckError\nfrom saga.module_interface import build_module_interface\n\n\nclass GenericADTs051Tests(unittest.TestCase):\n    def run_program(self, source: str) -> list[str]:\n        output: list[str] = []\n        run_source(source, output=output.append)\n        return output\n\n    def test_payload_constructor_infers_type_and_match_specializes_binding(self):\n        source = \"\"\"\n        enum Maybe[T] { None, Some(T) }\n        let value = Maybe.Some(42)\n        match value {\n            case Maybe.Some(item) { let checked: int = item; print(checked) }\n            case Maybe.None { print(0) }\n        }\n        \"\"\"\n        self.assertEqual(self.run_program(source), [\"42\"])\n\n    def test_nullary_generic_variant_uses_contextual_type(self):\n        source = \"\"\"\n        enum Maybe[T] { None, Some(T) }\n        let value: Maybe[int] = Maybe.None\n        match value {\n            case Maybe.Some(item) { print(item) }\n            case Maybe.None { print(\"empty\") }\n        }\n        \"\"\"\n        self.assertEqual(self.run_program(source), [\"empty\"])\n\n    def test_nullary_generic_variant_without_context_is_rejected(self):\n        source = \"\"\"\n        enum Maybe[T] { None, Some(T) }\n        let value = Maybe.None\n        \"\"\"\n        with self.assertRaises(TypeCheckError) as caught:\n            compile_source(source)\n        self.assertIn(\"SAGA-T113\", str(caught.exception))\n\n    def test_context_completes_partially_inferred_enum_parameters(self):\n        source = \"\"\"\n        enum Either[L, R] { Left(L), Right(R) }\n        let value: Either[int, text] = Either.Left(7)\n        match value {\n            case Either.Left(item) { let checked: int = item; print(checked) }\n            case Either.Right(message) { let checked: text = message; print(checked) }\n        }\n        \"\"\"\n        self.assertEqual(self.run_program(source), [\"7\"])\n\n    def test_generic_enum_arity_is_checked(self):\n        source = \"\"\"\n        enum Maybe[T] { None, Some(T) }\n        let value: Maybe[int, text] = Maybe.Some(1)\n        \"\"\"\n        with self.assertRaises(TypeCheckError):\n            compile_source(source)\n\n    def test_module_interface_preserves_generic_enum_abi(self):\n        with tempfile.TemporaryDirectory() as td:\n            root = Path(td)\n            module = root / \"maybe.saga\"\n            module.write_text(\n                \"module maybe\\npublic enum Maybe[T] { None, Some(T) }\\n\",\n                encoding=\"utf-8\",\n            )\n            interface = build_module_interface(module, root=root)\n            export = next(item for item in interface[\"exports\"] if item[\"name\"] == \"Maybe\")\n            self.assertEqual(export[\"type_params\"], [\"T\"])\n            self.assertEqual(export[\"variants\"][1][\"payload\"], [\"T\"])\n\n    @unittest.skipUnless(shutil.which(\"go\"), \"Go toolchain required\")\n    def test_python_and_go_share_generic_adt_runtime_and_module_abi(self):\n        source = \"\"\"\n        enum Maybe[T] { None, Some(T) }\n        enum Either[L, R] { Left(L), Right(R) }\n        let value = Maybe.Some(42)\n        match value {\n            case Maybe.Some(item) { print(item) }\n            case Maybe.None { print(0) }\n        }\n        let side: Either[int, text] = Either.Left(7)\n        match side {\n            case Either.Left(item) { print(item) }\n            case Either.Right(message) { print(message) }\n        }\n        \"\"\"\n        py_output = self.run_program(source)\n        self.assertEqual(py_output, [\"42\", \"7\"])\n        with tempfile.TemporaryDirectory() as td:\n            root = Path(td)\n            program = root / \"main.saga\"\n            program.write_text(source, encoding=\"utf-8\")\n            go_dir = Path(__file__).resolve().parents[1] / \"implementations\" / \"go\" / \"cmd\" / \"saga-go\"\n            go_run = subprocess.run(\n                [\"go\", \"run\", \".\", \"run\", str(program)],\n                cwd=go_dir, text=True, capture_output=True, timeout=90,\n            )\n            self.assertEqual(go_run.returncode, 0, go_run.stdout + go_run.stderr)\n            self.assertEqual(go_run.stdout.strip().splitlines(), py_output)\n\n            module = root / \"maybe.saga\"\n            module.write_text(\n                \"module maybe\\npublic enum Maybe[T] { None, Some(T) }\\n\",\n                encoding=\"utf-8\",\n            )\n            py_iface = build_module_interface(module, output=root / \"python.smi.json\")\n            go_compile = subprocess.run(\n                [\"go\", \"run\", \".\", \"module\", \"compile\", str(module), str(root / \"go.smi.json\")],\n                cwd=go_dir, text=True, capture_output=True, timeout=90,\n            )\n            self.assertEqual(go_compile.returncode, 0, go_compile.stdout + go_compile.stderr)\n            go_iface = json.loads((root / \"go.smi.json\").read_text(encoding=\"utf-8\"))\n            self.assertEqual(py_iface[\"exports\"], go_iface[\"exports\"])\n            self.assertEqual(py_iface[\"abi_sha256\"], go_iface[\"abi_sha256\"])\n\n\nif __name__ == \"__main__\":\n    unittest.main()\n''',
)

write(
    "implementations/go/cmd/saga-go/generic_adts_051_test.go",
    '''package main\n\nimport (\n    "strings"\n    "testing"\n)\n\nfunc TestGenericADT051InferenceAndMatch(t *testing.T) {\n    src := `enum Maybe[T] { None, Some(T) }\nlet value = Maybe.Some(42)\nmatch value {\ncase Maybe.Some(item) { let checked: int = item; print(checked) }\ncase Maybe.None { print(0) }\n}`\n    out, err := runSagaForTest(t, src)\n    if err != nil {\n        t.Fatal(err)\n    }\n    if out != "42" {\n        t.Fatalf("output=%q", out)\n    }\n}\n\nfunc TestGenericADT051ContextCompletesTypeParameters(t *testing.T) {\n    src := `enum Either[L, R] { Left(L), Right(R) }\nlet value: Either[int, text] = Either.Left(7)\nmatch value {\ncase Either.Left(item) { let checked: int = item; print(checked) }\ncase Either.Right(message) { let checked: text = message; print(checked) }\n}`\n    out, err := runSagaForTest(t, src)\n    if err != nil {\n        t.Fatal(err)\n    }\n    if out != "7" {\n        t.Fatalf("output=%q", out)\n    }\n}\n\nfunc TestGenericADT051NullaryVariantNeedsContext(t *testing.T) {\n    _, err := runSagaForTest(t, `enum Maybe[T] { None, Some(T) }\nlet value = Maybe.None`)\n    if err == nil || !strings.Contains(err.Error(), "SAGA-T113") {\n        t.Fatalf("expected SAGA-T113, got %v", err)\n    }\n}\n''',
)

print("Saga 0.51 Generic ADT patch staged successfully")
