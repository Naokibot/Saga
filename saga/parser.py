from __future__ import annotations

from .ast_nodes import (
    Annotation, Assign, AwaitExpr, Binary, Block, BreakStmt, Call, ClassDecl, ClosureExpr, ContinueStmt, DeferStmt, EnumDecl, EnumVariantDecl,
    ExpressionStmt, FieldDecl, ForStmt, FunctionDecl, IfStmt, Index, ListLiteral, MatchCase, MatchStmt, MoveExpr,
    Literal, Member, ModuleDecl, Parameter, Program, PropagateExpr, RangeExpr, ReturnStmt, TaskGroupStmt, ThrowStmt,
    TryStmt, Unary, UseStmt, UsingStmt, VarDecl, Variable, WhileStmt,
)
from .errors import ParseError
from .tokens import Token, TokenKind


class Parser:
    def __init__(self, tokens: list[Token], filename: str = "<input>") -> None:
        self.tokens = tokens
        self.filename = filename
        self.current = 0
        self.nesting = 0
        self.allow_trailing_closure = True

    def parse(self) -> Program:
        statements = []
        while not self._at_end():
            statements.append(self._declaration())
        return Program(statements)

    def _declaration(self):
        annotations = self._annotations()
        visibility = "internal"
        visibility_token = None
        if self._match(TokenKind.PUBLIC):
            visibility = "public"; visibility_token = self._previous()
        elif self._match(TokenKind.INTERNAL):
            visibility = "internal"; visibility_token = self._previous()
        # ``private`` remains accepted at top level as a compatibility spelling
        # for module-internal declarations. Natural Core documents public/internal.
        elif self._match(TokenKind.PRIVATE):
            visibility = "internal"; visibility_token = self._previous()

        if self._match(TokenKind.MODULE):
            if annotations or visibility_token is not None:
                self._error(self._previous(), "module 宣言にアノテーションや visibility は付けられません")
            keyword = self._previous()
            name = self._consume_name("module 名が必要です")
            self._optional_semicolon()
            return ModuleDecl(keyword, name)

        abstract = self._match(TokenKind.ABSTRACT)
        async_modifier = False
        if self._check(TokenKind.ASYNC) and self._check_next(TokenKind.FN):
            self._advance(); async_modifier = True
        if self._match(TokenKind.USE):
            if annotations or abstract or async_modifier or visibility_token is not None:
                self._error(self._previous(), "use にアノテーション、visibility、abstract、async は付けられません")
            keyword = self._previous()
            if self._match_name():
                module = self._previous()
                source_path = None
            elif self._match(TokenKind.STRING):
                module = self._previous()
                source_path = str(module.literal)
                if not source_path or not (source_path.endswith(".saga") or source_path.startswith("pkg:")):
                    self._error(module, "ソース単位のパスは .saga ファイルまたは pkg:name/path.saga にしてください")
            else:
                self._error(self._peek(), "use の後に標準モジュール名または .saga パスが必要です")
            alias = None
            if self._match(TokenKind.AS):
                alias = self._consume_name("as の後にmodule aliasが必要です")
            self._optional_semicolon()
            return UseStmt(keyword, module, source_path, alias)
        if self._match(TokenKind.ENUM):
            if async_modifier:
                self._error(self._previous(), "enum に async は付けられません")
            if abstract:
                self._error(self._previous(), "enum に abstract は付けられません")
            if annotations:
                self._error(self._previous(), "enum annotations はまだサポートしていません")
            decl = self._enum(self._previous())
            decl.visibility = visibility
            return decl
        if self._match(TokenKind.INTERFACE):
            if async_modifier:
                self._error(self._previous(), "interface に async は付けられません")
            if abstract:
                self._error(self._previous(), "interface は最初から抽象的なので abstract は不要です")
            decl = self._class(self._previous(), annotations, interface=True, abstract=True)
            decl.visibility = visibility
            return decl
        if self._match(TokenKind.CLASS):
            if async_modifier:
                self._error(self._previous(), "class に async は付けられません")
            decl = self._class(self._previous(), annotations, interface=False, abstract=abstract)
            decl.visibility = visibility
            return decl
        if self._match(TokenKind.FN):
            decl = self._function(self._previous(), annotations, abstract=abstract, allow_abstract=False)
            decl.visibility = visibility
            decl.async_ = async_modifier
            return decl
        if self._match(TokenKind.LET, TokenKind.VAR):
            if async_modifier:
                self._error(self._previous(), "変数に async は付けられません")
            if abstract:
                self._error(self._previous(), "変数に abstract は付けられません")
            decl = self._variable(self._previous(), annotations)
            decl.visibility = visibility
            return decl
        if annotations or abstract or async_modifier or visibility_token is not None:
            self._error(self._peek(), "アノテーション、visibility、abstract の後には宣言が必要です")
        return self._statement()

    def _annotations(self) -> list[Annotation]:
        result: list[Annotation] = []
        while self._match(TokenKind.AT):
            name = self._consume_name("@ の後にアノテーション名が必要です")
            args = []
            if self._match(TokenKind.LPAREN):
                if not self._check(TokenKind.RPAREN):
                    while True:
                        args.append(self._expression())
                        if not self._match(TokenKind.COMMA):
                            break
                self._consume(TokenKind.RPAREN, "アノテーションを閉じる ')' が必要です")
            result.append(Annotation(name, args))
        return result

    def _type_params(self) -> list[str]:
        if not self._match(TokenKind.LBRACKET):
            return []
        result = []
        if not self._check(TokenKind.RBRACKET):
            while True:
                token = self._consume_name("型パラメータ名が必要です")
                if token.lexeme in result:
                    self._error(token, f"型パラメータ '{token.lexeme}' が重複しています")
                result.append(token.lexeme)
                if not self._match(TokenKind.COMMA):
                    break
        self._consume(TokenKind.RBRACKET, "型パラメータを閉じる ']' が必要です")
        return result

    def _function(
        self,
        keyword: Token,
        annotations: list[Annotation] | None = None,
        *,
        abstract: bool = False,
        allow_abstract: bool = False,
        override: bool = False,
    ) -> FunctionDecl:
        name = self._consume_name("関数名が必要です")
        type_params = self._type_params()
        self._consume(TokenKind.LPAREN, "関数名の後に '(' が必要です")
        params: list[Parameter] = []
        if not self._check(TokenKind.RPAREN):
            while True:
                param_name = self._consume_name("引数名が必要です")
                self._consume(TokenKind.COLON, "引数の型が必要です", "例: name: text")
                params.append(Parameter(param_name, self._parse_type()))
                if not self._match(TokenKind.COMMA):
                    break
        self._consume(TokenKind.RPAREN, "引数リストを閉じる ')' が必要です")

        return_type = None
        if self._match(TokenKind.ARROW):
            return_type = self._parse_type()

        if self._match(TokenKind.EQUAL):
            if abstract:
                self._error(name, "abstract 関数には処理を書けません")
            expression_body = self._expression()
            self._optional_semicolon()
            return FunctionDecl(keyword, name, params, return_type, None, expression_body, type_params, annotations or [], False, override)

        if self._check(TokenKind.LBRACE):
            if abstract:
                self._error(name, "abstract 関数には処理を書けません")
            body = self._block("関数本体には '{' が必要です")
            return FunctionDecl(keyword, name, params, return_type, body, None, type_params, annotations or [], False, override)

        if allow_abstract or abstract:
            if return_type is None:
                self._error(name, "抽象メソッドには戻り値型を書いてください", "戻り値がない場合は -> unit と書きます")
            self._optional_semicolon()
            return FunctionDecl(keyword, name, params, return_type, None, None, type_params, annotations or [], True, override)

        self._error(name, "関数本体が必要です", "1行関数なら fn add(a: int, b: int) = a + b と書けます")

    def _enum(self, keyword: Token) -> EnumDecl:
        name = self._consume_name("enum 名が必要です")
        self._consume(TokenKind.LBRACE, "enum 本体には '{' が必要です")
        variants: list[EnumVariantDecl] = []
        seen: set[str] = set()
        while not self._check(TokenKind.RBRACE) and not self._at_end():
            variant = self._consume_name("enum variant 名が必要です")
            if variant.lexeme in seen:
                self._error(variant, f"enum variant '{variant.lexeme}' が重複しています", diagnostic_id="SAGA-P102")
            payload_types: list[str] = []
            if self._match(TokenKind.LPAREN):
                if not self._check(TokenKind.RPAREN):
                    while True:
                        payload_types.append(self._parse_type())
                        if not self._match(TokenKind.COMMA):
                            break
                self._consume(TokenKind.RPAREN, "enum payload 型を閉じる ')' が必要です")
            seen.add(variant.lexeme)
            variants.append(EnumVariantDecl(variant, payload_types))
            if self._match(TokenKind.COMMA):
                continue
            if not self._check(TokenKind.RBRACE):
                self._error(self._peek(), "enum variant の後には ',' または '}' が必要です", diagnostic_id="SAGA-P102")
        self._consume(TokenKind.RBRACE, "enum 本体を閉じる '}' が必要です")
        if not variants:
            self._error(name, "enum には1つ以上のvariantが必要です", diagnostic_id="SAGA-P102")
        return EnumDecl(keyword, name, variants)

    def _class(self, keyword: Token, annotations: list[Annotation], *, interface: bool, abstract: bool) -> ClassDecl:
        name = self._consume_name("クラスまたはインターフェース名が必要です")
        type_params = self._type_params()
        fields: list[FieldDecl] = []
        if not interface and self._match(TokenKind.LPAREN):
            if not self._check(TokenKind.RPAREN):
                while True:
                    private = False
                    if self._match(TokenKind.PRIVATE): private = True
                    elif self._match(TokenKind.PUBLIC): private = False
                    mutable = self._match(TokenKind.VAR)
                    if not mutable:
                        self._match(TokenKind.LET)
                    field_name = self._consume_name("フィールド名が必要です")
                    self._consume(TokenKind.COLON, "フィールドの型が必要です")
                    fields.append(FieldDecl(field_name, self._parse_type(), mutable, private))
                    if not self._match(TokenKind.COMMA): break
            self._consume(TokenKind.RPAREN, "フィールド一覧を閉じる ')' が必要です")

        base_name = None
        if self._match(TokenKind.EXTENDS):
            if interface:
                self._error(self._previous(), "interface の継承は将来の複数interface継承として別途定義されます")
            base_name = self._parse_type()

        interfaces: list[str] = []
        if self._match(TokenKind.IMPLEMENTS):
            while True:
                interfaces.append(self._parse_type())
                if not self._match(TokenKind.COMMA): break

        self._consume(TokenKind.LBRACE, "クラス本体には '{' が必要です")
        methods: list[FunctionDecl] = []
        while not self._check(TokenKind.RBRACE) and not self._at_end():
            method_annotations = self._annotations()
            method_abstract = self._match(TokenKind.ABSTRACT)
            method_override = self._match(TokenKind.OVERRIDE)
            method_async = False
            if self._check(TokenKind.ASYNC) and self._check_next(TokenKind.FN):
                self._advance(); method_async = True
            if method_abstract and method_override:
                self._error(self._previous(), "abstract と override は同時に指定できません")
            self._consume(TokenKind.FN, "クラス本体には fn メソッドを書いてください")
            method = self._function(
                self._previous(), method_annotations,
                abstract=method_abstract or interface,
                allow_abstract=interface or abstract,
                override=method_override,
            )
            method.async_ = method_async
            methods.append(method)
        self._consume(TokenKind.RBRACE, "クラス本体を閉じる '}' が必要です")
        return ClassDecl(keyword, name, fields, methods, type_params, base_name, interfaces, annotations, abstract, interface)

    def _variable(self, keyword: Token, annotations: list[Annotation] | None = None) -> VarDecl:
        name = self._consume_name("変数名が必要です")
        type_name = None
        if self._match(TokenKind.COLON):
            type_name = self._parse_type()
        self._consume(TokenKind.EQUAL, "変数には初期値が必要です", "例: let score = 100")
        initializer = self._expression()
        self._optional_semicolon()
        return VarDecl(keyword, name, keyword.kind is TokenKind.VAR, type_name, initializer, annotations or [])

    def _statement(self):
        if self._check(TokenKind.DEFER) and self._contextual_defer_active():
            self._advance()
            keyword = self._previous()
            value = self._expression()
            self._optional_semicolon()
            return DeferStmt(keyword, value)
        if self._check(TokenKind.USING) and self._check_next_name():
            self._advance()
            keyword = self._previous()
            name = self._consume_name("using の後に資源名が必要です")
            self._consume(TokenKind.EQUAL, "using の資源には初期値が必要です")
            initializer = self._control_header_expression()
            body = self._block("using 資源の後に '{' が必要です")
            return UsingStmt(keyword, name, initializer, body)
        if self._check(TokenKind.TASKGROUP) and self._check_next(TokenKind.LBRACE):
            self._advance()
            keyword = self._previous()
            return TaskGroupStmt(keyword, self._block("taskgroup の後に '{' が必要です"))
        if self._match(TokenKind.MATCH): return self._match_stmt(self._previous())
        if self._match(TokenKind.UNLESS): return self._unless(self._previous())
        if self._match(TokenKind.IF): return self._if(self._previous())
        if self._match(TokenKind.WHILE): return self._while(self._previous())
        if self._match(TokenKind.FOR): return self._for(self._previous())
        if self._match(TokenKind.RETURN): return self._return(self._previous())
        if self._match(TokenKind.THROW):
            keyword = self._previous(); value = self._expression(); self._optional_semicolon(); return ThrowStmt(keyword, value)
        if self._match(TokenKind.TRY): return self._try(self._previous())
        if self._match(TokenKind.BREAK):
            token = self._previous(); self._optional_semicolon(); return BreakStmt(token)
        if self._match(TokenKind.CONTINUE):
            token = self._previous(); self._optional_semicolon(); return ContinueStmt(token)
        if self._check(TokenKind.LBRACE): return self._block("ブロックには '{' が必要です")
        expr = self._expression()
        if self._match(TokenKind.EQUAL):
            equals = self._previous()
            if not isinstance(expr, (Variable, Member)):
                self._error(equals, "代入先は変数またはオブジェクトのフィールドにしてください")
            value = self._expression(); self._optional_semicolon()
            return Assign(expr, equals, value)
        self._optional_semicolon()
        return ExpressionStmt(expr)

    def _unless(self, keyword: Token) -> IfStmt:
        condition = self._control_header_expression()
        not_token = Token(TokenKind.NOT, "not", None, keyword.line, keyword.column, keyword.filename)
        then_branch = self._block("unless 条件の後に '{' が必要です")
        else_branch = None
        if self._match(TokenKind.ELSE):
            else_branch = self._block("else の後に '{' が必要です")
        return IfStmt(keyword, Unary(not_token, condition), then_branch, else_branch)

    def _match_stmt(self, keyword: Token) -> MatchStmt:
        value = self._control_header_expression()
        self._consume(TokenKind.LBRACE, "match 値の後に '{' が必要です")
        cases: list[MatchCase] = []
        default = None
        while not self._check(TokenKind.RBRACE) and not self._at_end():
            if self._match(TokenKind.CASE):
                case_kw = self._previous()
                pattern = self._control_header_expression()
                body = self._block("case pattern の後に '{' が必要です")
                cases.append(MatchCase(case_kw, pattern, body))
                continue
            if self._match(TokenKind.DEFAULT):
                if default is not None:
                    self._error(self._previous(), "default case が重複しています", diagnostic_id="SAGA-P102")
                default = self._block("default の後に '{' が必要です")
                continue
            self._error(self._peek(), "match には case または default が必要です", diagnostic_id="SAGA-P102")
        self._consume(TokenKind.RBRACE, "match 本体を閉じる '}' が必要です")
        if not cases and default is None:
            self._error(keyword, "match には1つ以上のcaseが必要です", diagnostic_id="SAGA-P102")
        return MatchStmt(keyword, value, cases, default)

    def _if(self, keyword: Token) -> IfStmt:
        condition = self._control_header_expression()
        then_branch = self._block("if 条件の後に '{' が必要です")
        else_branch = None
        if self._match(TokenKind.ELSE):
            if self._match(TokenKind.IF):
                else_branch = Block([self._if(self._previous())])
            else:
                else_branch = self._block("else の後に '{' が必要です")
        return IfStmt(keyword, condition, then_branch, else_branch)

    def _while(self, keyword: Token) -> WhileStmt:
        return WhileStmt(keyword, self._control_header_expression(), self._block("while 条件の後に '{' が必要です"))

    def _for(self, keyword: Token) -> ForStmt:
        name = self._consume_name("for の後に変数名が必要です")
        self._consume(TokenKind.IN, "繰り返す対象の前に in が必要です", "例: for n in 1..5 { print(n) }")
        iterable = self._control_header_expression()
        return ForStmt(keyword, name, iterable, self._block("for の対象の後に '{' が必要です"))

    def _control_header_expression(self):
        """Parse an if/while/for header without stealing its body brace.

        A call immediately followed by ``{`` is normally a trailing-closure
        call. In a control header, however, that same brace is overwhelmingly
        the body delimiter (``if ready() { ... }``). We therefore make the
        ambiguous shorthand explicit: callback-bearing header expressions can
        still use trailing closures when parenthesized.
        """
        previous = self.allow_trailing_closure
        self.allow_trailing_closure = False
        try:
            return self._expression()
        finally:
            self.allow_trailing_closure = previous

    def _return(self, keyword: Token) -> ReturnStmt:
        value = None
        if not self._check(TokenKind.SEMICOLON) and not self._check(TokenKind.RBRACE):
            value = self._expression()
        self._optional_semicolon()
        return ReturnStmt(keyword, value)

    def _try(self, keyword: Token) -> TryStmt:
        try_block = self._block("try の後に '{' が必要です")
        catch_name = None; catch_block = None; finally_block = None
        if self._match(TokenKind.CATCH):
            catch_name = self._consume_name("catch の後にエラー変数名が必要です")
            catch_block = self._block("catch 変数の後に '{' が必要です")
        if self._match(TokenKind.FINALLY):
            finally_block = self._block("finally の後に '{' が必要です")
        if catch_block is None and finally_block is None:
            self._error(keyword, "try には catch または finally が必要です")
        return TryStmt(keyword, try_block, catch_name, catch_block, finally_block)

    def _block(self, message: str, hint: str | None = None) -> Block:
        self._consume(TokenKind.LBRACE, message, hint)
        statements = []
        while not self._check(TokenKind.RBRACE) and not self._at_end():
            statements.append(self._declaration())
        self._consume(TokenKind.RBRACE, "ブロックを閉じる '}' が必要です")
        return Block(statements)

    def _expression(self):
        self.nesting += 1
        try:
            return self._pipeline()
        finally:
            self.nesting -= 1

    def _pipeline(self):
        expr = self._or()
        natural_stages = {
            "map", "each", "fold", "none", "sorted", "sortedBy", "distinct",
            "take", "skip", "zip", "flatten", "flatMap", "chunk", "window",
            "group", "groupBy", "sum", "contains",
        }
        while self._match(TokenKind.PIPE):
            operator = self._previous()
            target = self._or()
            if self.allow_trailing_closure and isinstance(target, Variable) and self._check(TokenKind.LBRACE):
                closure = self._closure()
                target = Call(target, closure.brace, [closure])

            # Natural pipeline stages lower to the same typed extension calls
            # as method chaining.  This keeps ``values |> map { ... }`` and
            # ``values.map { ... }`` semantically identical instead of
            # inventing a second runtime dispatch path.
            if isinstance(target, Variable) and target.name.lexeme in natural_stages:
                member = Member(expr, operator, target.name)
                expr = Call(member, operator, [])
                continue
            if isinstance(target, Call) and isinstance(target.callee, Variable):
                name = target.callee.name.lexeme
                if name in natural_stages:
                    member = Member(expr, operator, target.callee.name)
                    expr = Call(member, target.paren, target.arguments)
                    continue
                if name == "reduce" and len(target.arguments) == 2 and isinstance(target.arguments[-1], ClosureExpr):
                    # ``values |> reduce(initial) { ... }`` is the natural
                    # method-shaped form.  The legacy callback-first form stays
                    # available as ``values |> reduce(function, initial)``.
                    member = Member(expr, operator, target.callee.name)
                    expr = Call(member, target.paren, target.arguments)
                    continue
                if name == "find" and len(target.arguments) == 1:
                    # One-argument find is the Option-returning Natural Core
                    # surface; the legacy two-argument stage keeps its fallback.
                    member = Member(expr, operator, target.callee.name)
                    expr = Call(member, target.paren, target.arguments)
                    continue

                # Transitional functional HOFs keep their historical argument
                # order.  The collection is the second argument for reduce and
                # find, not the final one; appending it silently changed the
                # meaning and made those pipeline forms uncompilable.
                if name in {"reduce", "find"}:
                    target.arguments.insert(1, expr)
                    expr = target
                    continue
                if name in {"transform", "filter", "any", "all"}:
                    target.arguments.append(expr)
                    expr = target
                    continue

            if isinstance(target, Call):
                target.arguments.insert(0, expr)
                expr = target
            else:
                expr = Call(target, operator, [expr])
        return expr

    def _or(self):
        expr = self._and()
        while self._match(TokenKind.OR): expr = Binary(expr, self._previous(), self._and())
        return expr

    def _and(self):
        expr = self._equality()
        while self._match(TokenKind.AND): expr = Binary(expr, self._previous(), self._equality())
        return expr

    def _equality(self):
        expr = self._comparison()
        while self._match(TokenKind.EQUAL_EQUAL, TokenKind.BANG_EQUAL): expr = Binary(expr, self._previous(), self._comparison())
        return expr

    def _comparison(self):
        expr = self._range()
        while self._match(TokenKind.LESS, TokenKind.LESS_EQUAL, TokenKind.GREATER, TokenKind.GREATER_EQUAL):
            expr = Binary(expr, self._previous(), self._range())
        return expr

    def _range(self):
        expr = self._term()
        if self._match(TokenKind.RANGE):
            op = self._previous(); expr = RangeExpr(expr, op, self._term())
            if self._match(TokenKind.RANGE): self._error(self._previous(), "範囲演算子 '..' を連続して使えません")
        return expr

    def _term(self):
        expr = self._factor()
        while self._match(TokenKind.PLUS, TokenKind.MINUS): expr = Binary(expr, self._previous(), self._factor())
        return expr

    def _factor(self):
        expr = self._unary()
        while self._match(TokenKind.STAR, TokenKind.SLASH, TokenKind.PERCENT): expr = Binary(expr, self._previous(), self._unary())
        return expr

    def _unary(self):
        self.nesting += 1
        try:
            if self._check(TokenKind.AWAIT) and self._contextual_unary_active():
                self._advance(); keyword = self._previous()
                return AwaitExpr(self._unary(), keyword)
            if self._check(TokenKind.MOVE) and self._contextual_unary_active():
                self._advance(); keyword = self._previous()
                return MoveExpr(self._unary(), keyword)
            if self._match(TokenKind.BANG, TokenKind.NOT, TokenKind.MINUS):
                return Unary(self._previous(), self._unary())
            return self._power()
        finally:
            self.nesting -= 1

    def _power(self):
        expr = self._call()
        if self._match(TokenKind.POWER): expr = Binary(expr, self._previous(), self._unary())
        return expr

    def _call(self):
        expr = self._primary()
        while True:
            if self._match(TokenKind.LPAREN):
                args = []
                if not self._check(TokenKind.RPAREN):
                    while True:
                        args.append(self._expression())
                        if not self._match(TokenKind.COMMA): break
                paren = self._consume(TokenKind.RPAREN, "呼び出しを閉じる ')' が必要です")
                expr = Call(expr, paren, args)
            elif self._match(TokenKind.LBRACKET):
                bracket = self._previous(); index = self._expression()
                self._consume(TokenKind.RBRACKET, "添字を閉じる ']' が必要です")
                expr = Index(expr, bracket, index)
            elif self._match(TokenKind.DOT):
                dot = self._previous()
                if self._peek().kind in {TokenKind.IDENT, TokenKind.ASYNC, TokenKind.AWAIT, TokenKind.DEFER, TokenKind.USING, TokenKind.TASKGROUP, TokenKind.MOVE}:
                    name = self._advance()
                else:
                    self._error(self._peek(), "'.' の後に名前が必要です")
                expr = Member(expr, dot, name)
            elif self._match(TokenKind.QUESTION):
                expr = PropagateExpr(expr, self._previous())
            elif isinstance(expr, (Variable, Member)) and self._can_start_bare_argument(expr):
                args = [self._or()]
                while self._match(TokenKind.COMMA):
                    args.append(self._or())
                expr = Call(expr, self._previous(), args)
            elif self.allow_trailing_closure and self._check(TokenKind.LBRACE) and isinstance(expr, (Call, Member)):
                closure = self._closure()
                # ``values.map { ... }`` is a call even though the parentheses
                # are intentionally omitted.  A previous ordinary call may also
                # accept a trailing block: ``repeat(3) { ... }``.
                if isinstance(expr, Call):
                    expr.arguments.append(closure)
                elif isinstance(expr, Member):
                    expr = Call(expr, closure.brace, [closure])
                else:
                    self._error(closure.brace, "この式にはブロックを渡せません")
            else:
                break
        return expr

    def _can_start_bare_argument(self, callee) -> bool:
        """Return true for same-line Ruby-like argument syntax.

        Newlines are deliberately significant only for this convenience rule;
        the rest of Saga remains semicolon-optional.  Requiring the first bare
        argument to share the callee's line prevents ``print`` on one line from
        accidentally consuming the next statement.
        """
        token = callee.name if isinstance(callee, (Variable, Member)) else None
        if token is None or self._peek().line != token.line:
            return False
        return self._peek().kind in {
            TokenKind.FALSE, TokenKind.TRUE, TokenKind.INT, TokenKind.DECIMAL,
            TokenKind.STRING, TokenKind.IDENT, TokenKind.LBRACKET, TokenKind.LPAREN,
        }

    def _closure(self) -> ClosureExpr:
        brace = self._consume(TokenKind.LBRACE, "クロージャには '{' が必要です")
        parameters: list[Token] = []
        implicit = True

        # Explicit form: { value -> ... } or { left, right -> ... }
        mark = self.current
        if self._check_name():
            candidate: list[Token] = [self._advance()]
            while self._match(TokenKind.COMMA):
                if not self._check_name():
                    self.current = mark
                    candidate = []
                    break
                candidate.append(self._advance())
            if candidate and self._match(TokenKind.ARROW):
                seen: set[str] = set()
                for parameter in candidate:
                    if parameter.lexeme in seen:
                        self._error(parameter, f"クロージャ引数 '{parameter.lexeme}' が重複しています")
                    seen.add(parameter.lexeme)
                parameters = candidate
                implicit = False
            else:
                self.current = mark

        statements = []
        while not self._check(TokenKind.RBRACE) and not self._at_end():
            statements.append(self._declaration())
        self._consume(TokenKind.RBRACE, "クロージャを閉じる '}' が必要です")
        return ClosureExpr(brace, parameters, Block(statements), implicit)

    def _primary(self):
        if self._match(TokenKind.FALSE): return Literal(False, self._previous())
        if self._match(TokenKind.TRUE): return Literal(True, self._previous())
        if self._match(TokenKind.INT, TokenKind.DECIMAL, TokenKind.STRING):
            token = self._previous(); return Literal(token.literal, token)
        # In expression position, a brace-delimited block is a first-class
        # lexical closure. Statement-leading braces are still handled by
        # _statement() as ordinary blocks, so this does not make control-flow
        # braces ambiguous.
        if self._check(TokenKind.LBRACE): return self._closure()
        if self._match_name(): return Variable(self._previous())
        if self._match(TokenKind.LBRACKET):
            token = self._previous(); elements = []
            if not self._check(TokenKind.RBRACKET):
                while True:
                    elements.append(self._expression())
                    if not self._match(TokenKind.COMMA): break
            self._consume(TokenKind.RBRACKET, "リストを閉じる ']' が必要です")
            return ListLiteral(elements, token)
        if self._match(TokenKind.LPAREN):
            # Parentheses are the explicit disambiguation boundary inside a
            # control-flow header, so trailing closures become available again
            # within them: if (values.any { it > 0 }) { ... }
            previous = self.allow_trailing_closure
            self.allow_trailing_closure = True
            try:
                expr = self._expression()
            finally:
                self.allow_trailing_closure = previous
            self._consume(TokenKind.RPAREN, "式を閉じる ')' が必要です"); return expr
        self._error(self._peek(), "式が必要です", diagnostic_id="SAGA-P102")

    def _parse_type(self) -> str:
        if self._match(TokenKind.FN):
            base = self._previous()
        else:
            base = self._consume_name("型名が必要です")
        text = base.lexeme
        while self._match(TokenKind.DOT):
            part = self._consume_name("'.' の後に型名が必要です")
            text += "." + part.lexeme
        if self._match(TokenKind.LBRACKET):
            args = []
            if not self._check(TokenKind.RBRACKET):
                while True:
                    args.append(self._parse_type())
                    if not self._match(TokenKind.COMMA): break
            self._consume(TokenKind.RBRACKET, "型引数を閉じる ']' が必要です")
            text += "[" + ",".join(args) + "]"
        return text

    def _optional_semicolon(self) -> None: self._match(TokenKind.SEMICOLON)

    @staticmethod
    def _contextual_name_kinds() -> set[TokenKind]:
        return {
            TokenKind.ASYNC, TokenKind.AWAIT, TokenKind.DEFER,
            TokenKind.USING, TokenKind.TASKGROUP, TokenKind.MOVE,
        }

    def _check_name(self) -> bool:
        return self._peek().kind is TokenKind.IDENT or self._peek().kind in self._contextual_name_kinds()

    def _check_next_name(self) -> bool:
        return self.current + 1 < len(self.tokens) and (
            self.tokens[self.current + 1].kind is TokenKind.IDENT
            or self.tokens[self.current + 1].kind in self._contextual_name_kinds()
        )

    def _match_name(self) -> bool:
        if self._check_name():
            self._advance(); return True
        return False

    def _consume_name(self, message: str, hint: str | None = None) -> Token:
        if self._check_name(): return self._advance()
        self._error(self._peek(), message, hint)

    def _check_next(self, kind: TokenKind) -> bool:
        return self.current + 1 < len(self.tokens) and self.tokens[self.current + 1].kind is kind

    def _contextual_unary_active(self) -> bool:
        if self.current + 1 >= len(self.tokens): return False
        if self.tokens[self.current + 1].line != self._peek().line: return False
        # A contextual word followed by a delimiter/operator is an ordinary
        # name (`print(await)`, `await + 1`, `move.field`, ...), not a prefix
        # operator. This keeps the 0.45 additions source-compatible.
        return self.tokens[self.current + 1].kind not in {
            TokenKind.LPAREN, TokenKind.RPAREN, TokenKind.LBRACKET, TokenKind.RBRACKET,
            TokenKind.RBRACE, TokenKind.COMMA, TokenKind.DOT, TokenKind.QUESTION,
            TokenKind.EQUAL, TokenKind.EQUAL_EQUAL, TokenKind.BANG_EQUAL,
            TokenKind.LESS, TokenKind.LESS_EQUAL, TokenKind.GREATER, TokenKind.GREATER_EQUAL,
            TokenKind.AND, TokenKind.OR, TokenKind.RANGE,
            TokenKind.PLUS, TokenKind.MINUS, TokenKind.STAR,
            TokenKind.SLASH, TokenKind.PERCENT, TokenKind.SEMICOLON, TokenKind.EOF,
        }

    def _contextual_defer_active(self) -> bool:
        if self.current + 1 >= len(self.tokens): return False
        if self.tokens[self.current + 1].line != self._peek().line: return False
        # `defer cleanup()` is the statement form; `defer = value`,
        # `defer + 1`, and `defer(...)` keep treating `defer` as a name.
        return self.tokens[self.current + 1].kind not in {
            TokenKind.LPAREN, TokenKind.RPAREN, TokenKind.LBRACKET, TokenKind.RBRACKET,
            TokenKind.RBRACE, TokenKind.COMMA, TokenKind.DOT, TokenKind.QUESTION,
            TokenKind.EQUAL, TokenKind.EQUAL_EQUAL, TokenKind.BANG_EQUAL,
            TokenKind.LESS, TokenKind.LESS_EQUAL, TokenKind.GREATER, TokenKind.GREATER_EQUAL,
            TokenKind.AND, TokenKind.OR, TokenKind.RANGE,
            TokenKind.PLUS, TokenKind.MINUS, TokenKind.STAR,
            TokenKind.SLASH, TokenKind.PERCENT, TokenKind.SEMICOLON, TokenKind.EOF,
        }

    def _match(self, *kinds: TokenKind) -> bool:
        for kind in kinds:
            if self._check(kind): self._advance(); return True
        return False

    def _consume(self, kind: TokenKind, message: str, hint: str | None = None) -> Token:
        if self._check(kind): return self._advance()
        detail = "SAGA-P101" if kind in {TokenKind.RPAREN, TokenKind.RBRACKET, TokenKind.RBRACE} else None
        self._error(self._peek(), message, hint, detail)

    def _check(self, kind: TokenKind) -> bool: return self._peek().kind is kind
    def _advance(self) -> Token:
        if not self._at_end(): self.current += 1
        return self._previous()
    def _at_end(self) -> bool: return self._peek().kind is TokenKind.EOF
    def _peek(self) -> Token: return self.tokens[self.current]
    def _previous(self) -> Token: return self.tokens[self.current - 1]

    def _error(self, token: Token, message: str, hint: str | None = None, diagnostic_id: str | None = None):
        raise ParseError(
            message, token.line, token.column, token.filename or self.filename, hint,
            end_column=token.column + max(len(token.lexeme), 1), detail_code=diagnostic_id,
        )
