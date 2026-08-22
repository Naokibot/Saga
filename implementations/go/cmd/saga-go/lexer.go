package main

import (
	"fmt"
	"strings"
	"unicode"
	"unicode/utf8"
)

type Lexer struct {
	src            []rune
	pos, line, col int
	file           string
}

func lex(src, file string) ([]Token, error) {
	if !utf8.ValidString(src) {
		return nil, &SagaError{"SAGA-L001", "SAGA-L104", "source is not valid UTF-8", file, 1, 1}
	}
	l := &Lexer{src: []rune(src), line: 1, col: 1, file: file}
	out := []Token{}
	for !l.end() {
		c := l.peek()
		line, col := l.line, l.col
		if unicode.IsSpace(c) {
			l.advance()
			continue
		}
		if c == '#' || (c == '/' && l.peekN(1) == '/') {
			for !l.end() && l.peek() != '\n' {
				l.advance()
			}
			continue
		}
		if isBidiControl(c) {
			return nil, &SagaError{"SAGA-L001", "SAGA-L106", "bidirectional control character is not allowed outside strings", file, line, col}
		}
		if isStart(c) {
			start := l.pos
			l.advance()
			for !l.end() && isContinue(l.peek()) {
				l.advance()
			}
			text := string(l.src[start:l.pos])
			if normalizeNFC(text) != text {
				return nil, &SagaError{"SAGA-L001", "SAGA-L105", "identifier is not NFC-normalized", file, line, col}
			}
			k := IDENT
			if q, ok := keywords[text]; ok {
				k = q
			}
			out = append(out, Token{k, text, line, col, file})
			continue
		}
		if c >= '0' && c <= '9' {
			start := l.pos
			l.advance()
			for !l.end() && ((l.peek() >= '0' && l.peek() <= '9') || l.peek() == '_') {
				l.advance()
			}
			k := INTLIT
			if !l.end() && l.peek() == '.' && l.peekN(1) == '_' {
				return nil, &SagaError{"SAGA-L001", "SAGA-L103", "underscore cannot immediately follow decimal point", file, line, col}
			}
			if !l.end() && l.peek() == '.' && l.peekN(1) != '.' && l.peekN(1) >= '0' && l.peekN(1) <= '9' {
				k = DECLIT
				l.advance()
				for !l.end() && ((l.peek() >= '0' && l.peek() <= '9') || l.peek() == '_') {
					l.advance()
				}
			}
			raw := string(l.src[start:l.pos])
			for _, part := range strings.Split(raw, ".") {
				if part == "" || strings.HasPrefix(part, "_") || strings.HasSuffix(part, "_") || strings.Contains(part, "__") {
					return nil, &SagaError{"SAGA-L001", "SAGA-L103", "numeric separators must occur singly between ASCII digits", file, line, col}
				}
			}
			// Edition 2027 adds explicit IEEE literals. A suffix is required so the
			// existing exact decimal semantics remain unchanged.
			if !l.end() && l.peek() == 'f' {
				if l.peekN(1) == '3' && l.peekN(2) == '2' {
					l.advance()
					l.advance()
					l.advance()
					raw += "f32"
					k = FLOAT32LIT
				} else if l.peekN(1) == '6' && l.peekN(2) == '4' {
					l.advance()
					l.advance()
					l.advance()
					raw += "f64"
					k = FLOAT64LIT
				}
			}
			out = append(out, Token{k, raw, line, col, file})
			continue
		}
		if unicode.IsDigit(c) {
			return nil, &SagaError{"SAGA-L001", "SAGA-L103", "numeric literals use ASCII digits 0-9", file, line, col}
		}
		if c == '$' && (l.peekN(1) == '"' || l.peekN(1) == '\'') {
			l.advance()
			q := l.advance()
			var b strings.Builder
			for !l.end() && l.peek() != q {
				r := l.advance()
				if r == '\\' {
					if l.end() {
						return nil, &SagaError{"SAGA-L001", "SAGA-L102", "unterminated interpolated string escape", file, line, col}
					}
					e := l.advance()
					switch e {
					case 'n':
						b.WriteRune('\n')
					case 't':
						b.WriteRune('\t')
					case 'r':
						b.WriteRune('\r')
					case '\\', '"', '\'':
						b.WriteRune(e)
					case '$':
						b.WriteRune('$')
					default:
						return nil, &SagaError{"SAGA-L001", "SAGA-L101", fmt.Sprintf("unsupported escape \\%c", e), file, line, col}
					}
				} else {
					b.WriteRune(r)
				}
			}
			if l.end() {
				return nil, &SagaError{"SAGA-L001", "SAGA-L102", "unterminated interpolated string", file, line, col}
			}
			l.advance()
			out = append(out, Token{INTERPSTRING, b.String(), line, col, file})
			continue
		}
		if c == '"' || c == '\'' {
			q := c
			l.advance()
			var b strings.Builder
			for !l.end() && l.peek() != q {
				r := l.advance()
				if r == '\\' {
					if l.end() {
						return nil, &SagaError{"SAGA-L001", "SAGA-L102", "unterminated string escape", file, line, col}
					}
					e := l.advance()
					switch e {
					case 'n':
						b.WriteRune('\n')
					case 't':
						b.WriteRune('\t')
					case 'r':
						b.WriteRune('\r')
					case '\\', '"', '\'':
						b.WriteRune(e)
					default:
						return nil, &SagaError{"SAGA-L001", "SAGA-L101", fmt.Sprintf("unsupported escape \\%c", e), file, line, col}
					}
				} else {
					b.WriteRune(r)
				}
			}
			if l.end() {
				return nil, &SagaError{"SAGA-L001", "SAGA-L102", "unterminated string", file, line, col}
			}
			l.advance()
			out = append(out, Token{STRING, b.String(), line, col, file})
			continue
		}
		l.advance()
		add := func(k Kind, s string) { out = append(out, Token{k, s, line, col, file}) }
		switch c {
		case '(':
			add(LPAREN, "(")
		case ')':
			add(RPAREN, ")")
		case '{':
			add(LBRACE, "{")
		case '}':
			add(RBRACE, "}")
		case '[':
			add(LBRACKET, "[")
		case ']':
			add(RBRACKET, "]")
		case ',':
			add(COMMA, ",")
		case ':':
			add(COLON, ":")
		case ';':
			add(SEMICOLON, ";")
		case '@':
			add(AT, "@")
		case '?':
			add(QUESTION, "?")
		case '|':
			if l.match('>') {
				add(PIPE, "|>")
			} else {
				return nil, &SagaError{"SAGA-L001", "SAGA-L101", "unsupported character '|' (did you mean |>)", file, line, col}
			}
		case '+':
			add(PLUS, "+")
		case '%':
			add(PERCENT, "%")
		case '.':
			if l.match('.') {
				add(RANGE, "..")
			} else {
				add(DOT, ".")
			}
		case '-':
			if l.match('>') {
				add(ARROW, "->")
			} else {
				add(MINUS, "-")
			}
		case '*':
			if l.match('*') {
				add(POWER, "**")
			} else {
				add(STAR, "*")
			}
		case '/':
			add(SLASH, "/")
		case '=':
			if l.match('=') {
				add(EQEQ, "==")
			} else {
				add(EQUAL, "=")
			}
		case '!':
			if l.match('=') {
				add(BANGEQ, "!=")
			} else {
				add(BANG, "!")
			}
		case '<':
			if l.match('=') {
				add(LESSEQ, "<=")
			} else {
				add(LESS, "<")
			}
		case '>':
			if l.match('=') {
				add(GREATEREQ, ">=")
			} else {
				add(GREATER, ">")
			}
		default:
			return nil, &SagaError{"SAGA-L001", "SAGA-L101", fmt.Sprintf("unsupported character %q", c), file, line, col}
		}
	}
	out = append(out, Token{EOF, "", l.line, l.col, file})
	return out, nil
}
func (l *Lexer) end() bool { return l.pos >= len(l.src) }
func (l *Lexer) peek() rune {
	if l.end() {
		return 0
	}
	return l.src[l.pos]
}
func (l *Lexer) peekN(n int) rune {
	if l.pos+n >= len(l.src) {
		return 0
	}
	return l.src[l.pos+n]
}
func (l *Lexer) advance() rune {
	r := l.src[l.pos]
	l.pos++
	if r == '\n' {
		l.line++
		l.col = 1
	} else {
		l.col++
	}
	return r
}
func (l *Lexer) match(r rune) bool {
	if l.peek() != r {
		return false
	}
	l.advance()
	return true
}

func inRuneRanges(r rune, ranges []runeRange) bool {
	lo, hi := 0, len(ranges)
	for lo < hi {
		m := lo + (hi-lo)/2
		v := ranges[m]
		if r < v.lo {
			hi = m
		} else if r > v.hi {
			lo = m + 1
		} else {
			return true
		}
	}
	return false
}
func isStart(r rune) bool    { return r == '_' || inRuneRanges(r, xidStartRanges) }
func isContinue(r rune) bool { return r == '_' || inRuneRanges(r, xidContinueRanges) }
func isBidiControl(r rune) bool {
	switch r {
	case 0x061C, 0x200E, 0x200F, 0x202A, 0x202B, 0x202C, 0x202D, 0x202E, 0x2066, 0x2067, 0x2068, 0x2069:
		return true
	}
	return false
}

func decomposeRune(r rune, out *[]rune) {
	const (
		sBase  = 0xAC00
		lBase  = 0x1100
		vBase  = 0x1161
		tBase  = 0x11A7
		lCount = 19
		vCount = 21
		tCount = 28
		nCount = vCount * tCount
		sCount = lCount * nCount
	)
	if r >= sBase && r < sBase+sCount {
		sIndex := int(r - sBase)
		l := rune(lBase + sIndex/nCount)
		v := rune(vBase + (sIndex%nCount)/tCount)
		t := rune(tBase + sIndex%tCount)
		*out = append(*out, l, v)
		if t != tBase {
			*out = append(*out, t)
		}
		return
	}
	if seq, ok := canonicalDecomp[r]; ok {
		for _, p := range seq {
			decomposeRune(p, out)
		}
		return
	}
	*out = append(*out, r)
}
func composePair(a, b rune) (rune, bool) {
	const (
		sBase  = 0xAC00
		lBase  = 0x1100
		vBase  = 0x1161
		tBase  = 0x11A7
		lCount = 19
		vCount = 21
		tCount = 28
		nCount = vCount * tCount
		sCount = lCount * nCount
	)
	if a >= lBase && a < lBase+lCount && b >= vBase && b < vBase+vCount {
		return sBase + (a-lBase)*nCount + (b-vBase)*tCount, true
	}
	if a >= sBase && a < sBase+sCount && (a-sBase)%tCount == 0 && b > tBase && b < tBase+tCount {
		return a + (b - tBase), true
	}
	r, ok := canonicalCompose[[2]rune{a, b}]
	return r, ok
}
func normalizeNFC(text string) string {
	decomp := make([]rune, 0, len([]rune(text)))
	for _, r := range text {
		decomposeRune(r, &decomp)
	}
	for i := 1; i < len(decomp); i++ {
		c := combiningClass[decomp[i]]
		if c == 0 {
			continue
		}
		j := i
		for j > 0 {
			p := combiningClass[decomp[j-1]]
			if p == 0 || p <= c {
				break
			}
			decomp[j], decomp[j-1] = decomp[j-1], decomp[j]
			j--
		}
	}
	if len(decomp) == 0 {
		return ""
	}
	out := []rune{decomp[0]}
	starterPos := 0
	starter := decomp[0]
	lastCCC := uint8(0)
	for _, r := range decomp[1:] {
		ccc := combiningClass[r]
		if composed, ok := composePair(starter, r); ok && (lastCCC < ccc || lastCCC == 0) {
			out[starterPos] = composed
			starter = composed
			continue
		}
		out = append(out, r)
		if ccc == 0 {
			starterPos = len(out) - 1
			starter = r
		}
		lastCCC = ccc
	}
	return string(out)
}
