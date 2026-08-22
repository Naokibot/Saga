package main

type Kind int

const (
	EOF Kind = iota
	IDENT
	INTLIT
	DECLIT
	FLOAT32LIT
	FLOAT64LIT
	STRING
	INTERPSTRING
	LET
	VAR
	FN
	RETURN
	IF
	UNLESS
	ELSE
	WHILE
	FOR
	IN
	TRUE
	FALSE
	CLASS
	INTERFACE
	EXTENDS
	IMPLEMENTS
	PRIVATE
	PUBLIC
	TRY
	CATCH
	FINALLY
	THROW
	OVERRIDE
	ABSTRACT
	BREAK
	CONTINUE
	USE
	RECORD
	ENUM
	MATCH
	CASE
	DEFAULT
	TEST
	EDITION
	MODULE
	AS
	INTERNAL
	WHERE
	TYPE
	RESOURCE
	USING
	DEFER
	MOVE
	ASYNC
	AWAIT
	TASKGROUP
	UNSAFE
	EXTERN
	COMPTIME
	AND
	OR
	NOT
	LPAREN
	RPAREN
	LBRACE
	RBRACE
	LBRACKET
	RBRACKET
	COMMA
	COLON
	SEMICOLON
	DOT
	AT
	RANGE
	ARROW
	PLUS
	MINUS
	STAR
	SLASH
	PERCENT
	POWER
	EQUAL
	EQEQ
	BANGEQ
	BANG
	LESS
	LESSEQ
	GREATER
	GREATEREQ
	QUESTION
	PIPE
)

type Token struct {
	Kind Kind
	Lex  string
	Line int
	Col  int
	File string
}

var keywords = map[string]Kind{
	"let": LET, "var": VAR, "fn": FN, "return": RETURN, "if": IF, "unless": UNLESS, "else": ELSE, "while": WHILE, "for": FOR, "in": IN,
	"true": TRUE, "false": FALSE, "class": CLASS, "interface": INTERFACE, "extends": EXTENDS, "implements": IMPLEMENTS,
	"private": PRIVATE, "public": PUBLIC, "try": TRY, "catch": CATCH, "finally": FINALLY, "throw": THROW,
	"override": OVERRIDE, "abstract": ABSTRACT, "break": BREAK, "continue": CONTINUE, "use": USE,
	"record": RECORD, "enum": ENUM, "match": MATCH, "case": CASE, "default": DEFAULT, "test": TEST,
	"edition": EDITION, "module": MODULE, "as": AS, "internal": INTERNAL, "where": WHERE, "type": TYPE,
	"resource": RESOURCE, "using": USING, "defer": DEFER, "move": MOVE, "async": ASYNC, "await": AWAIT,
	"taskgroup": TASKGROUP, "unsafe": UNSAFE, "extern": EXTERN, "comptime": COMPTIME,
	"and": AND, "or": OR, "not": NOT,
}

type SagaError struct {
	Code, ID, Message, File string
	Line, Col               int
}

func (e *SagaError) Error() string { return e.Message }
func diag(code, id, msg string, t Token) error {
	return &SagaError{code, id, msg, t.File, t.Line, t.Col}
}
