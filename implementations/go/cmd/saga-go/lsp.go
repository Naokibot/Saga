//go:build !sagaruntime

package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"sort"
	"strconv"
	"strings"
	"unicode/utf16"
)

type lspDoc struct {
	URI, Text string
	Version   int
}
type lspServer struct {
	docs map[string]lspDoc
	in   *bufio.Reader
	out  io.Writer
}

type lspMessage struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Method  string          `json:"method,omitempty"`
	Params  json.RawMessage `json:"params,omitempty"`
	Result  any             `json:"result,omitempty"`
	Error   any             `json:"error,omitempty"`
}

func runLSP() int {
	s := &lspServer{docs: map[string]lspDoc{}, in: bufio.NewReader(os.Stdin), out: os.Stdout}
	for {
		body, err := readLSPFrame(s.in)
		if err == io.EOF {
			return 0
		}
		if err != nil {
			fmt.Fprintln(os.Stderr, err)
			return 70
		}
		var m lspMessage
		if json.Unmarshal(body, &m) != nil {
			continue
		}
		if m.Method == "exit" {
			return 0
		}
		s.handle(m)
	}
}
func readLSPFrame(r *bufio.Reader) ([]byte, error) {
	n := -1
	for {
		line, err := r.ReadString('\n')
		if err != nil {
			return nil, err
		}
		line = strings.TrimSpace(line)
		if line == "" {
			break
		}
		parts := strings.SplitN(line, ":", 2)
		if len(parts) == 2 && strings.EqualFold(strings.TrimSpace(parts[0]), "Content-Length") {
			n, _ = strconv.Atoi(strings.TrimSpace(parts[1]))
		}
	}
	if n < 0 {
		return nil, fmt.Errorf("missing Content-Length")
	}
	b := make([]byte, n)
	_, err := io.ReadFull(r, b)
	return b, err
}
func (s *lspServer) send(v any) {
	b, _ := json.Marshal(v)
	fmt.Fprintf(s.out, "Content-Length: %d\r\n\r\n", len(b))
	s.out.Write(b)
}
func (s *lspServer) response(id json.RawMessage, result any) {
	s.send(map[string]any{"jsonrpc": "2.0", "id": json.RawMessage(id), "result": result})
}
func (s *lspServer) notify(method string, params any) {
	s.send(map[string]any{"jsonrpc": "2.0", "method": method, "params": params})
}

func (s *lspServer) handle(m lspMessage) {
	switch m.Method {
	case "initialize":
		s.response(m.ID, map[string]any{"capabilities": map[string]any{
			"textDocumentSync": 2, "completionProvider": map[string]any{"triggerCharacters": []string{"."}},
			"definitionProvider": true, "renameProvider": false, "documentFormattingProvider": true, "codeActionProvider": true,
			"executeCommandProvider": map[string]any{"commands": []string{"saga.explain"}},
			"semanticTokensProvider": map[string]any{"legend": map[string]any{"tokenTypes": []string{"keyword", "variable", "function", "type", "string", "number", "comment"}, "tokenModifiers": []string{}}, "full": true},
			"positionEncoding":       "utf-16"}, "serverInfo": map[string]any{"name": "Saga Native LSP", "version": sagaGoVersion}})
	case "initialized", "shutdown":
		if m.Method == "shutdown" {
			s.response(m.ID, nil)
		}
	case "textDocument/didOpen":
		var p struct {
			TextDocument struct {
				URI     string `json:"uri"`
				Text    string `json:"text"`
				Version int    `json:"version"`
			} `json:"textDocument"`
		}
		json.Unmarshal(m.Params, &p)
		s.docs[p.TextDocument.URI] = lspDoc{p.TextDocument.URI, p.TextDocument.Text, p.TextDocument.Version}
		s.publish(p.TextDocument.URI)
	case "textDocument/didChange":
		var p struct {
			TextDocument struct {
				URI     string `json:"uri"`
				Version int    `json:"version"`
			} `json:"textDocument"`
			ContentChanges []struct {
				Text string `json:"text"`
			} `json:"contentChanges"`
		}
		json.Unmarshal(m.Params, &p)
		if len(p.ContentChanges) > 0 {
			d := s.docs[p.TextDocument.URI]
			d.Text = p.ContentChanges[len(p.ContentChanges)-1].Text
			d.Version = p.TextDocument.Version
			s.docs[d.URI] = d
			s.publish(d.URI)
		}
	case "textDocument/didClose":
		var p struct {
			TextDocument struct {
				URI string `json:"uri"`
			} `json:"textDocument"`
		}
		json.Unmarshal(m.Params, &p)
		delete(s.docs, p.TextDocument.URI)
		s.notify("textDocument/publishDiagnostics", map[string]any{"uri": p.TextDocument.URI, "diagnostics": []any{}})
	case "textDocument/completion":
		s.response(m.ID, s.completion(m.Params))
	case "textDocument/definition":
		s.response(m.ID, s.definition(m.Params))
	case "textDocument/rename":
		// Scope-aware rename is intentionally not advertised until it can prove
		// that shadowed lexical bindings are not rewritten accidentally.
		s.response(m.ID, map[string]any{"changes": map[string]any{}})
	case "textDocument/formatting":
		s.response(m.ID, s.formatting(m.Params))
	case "textDocument/semanticTokens/full":
		s.response(m.ID, s.semanticTokens(m.Params))
	case "textDocument/codeAction":
		s.response(m.ID, s.codeActions(m.Params))
	case "workspace/executeCommand":
		var p struct {
			Command   string `json:"command"`
			Arguments []any  `json:"arguments"`
		}
		json.Unmarshal(m.Params, &p)
		if p.Command == "saga.explain" && len(p.Arguments) > 0 {
			id := fmt.Sprint(p.Arguments[0])
			text := "See: saga explain " + id
			if lesson, ok := diagnosticLessons[id]; ok {
				text = lesson.Title + ": " + lesson.Why
			}
			s.notify("window/showMessage", map[string]any{"type": 3, "message": text})
		}
		s.response(m.ID, nil)
	}
}
func (s *lspServer) publish(uri string) {
	d, ok := s.docs[uri]
	if !ok {
		return
	}
	diags := []any{}
	toks, err := lex(d.Text, uri)
	if err == nil {
		stmts, e := parse(toks)
		err = e
		if err == nil {
			err = NewChecker().Check(stmts)
		}
	}
	if err != nil {
		if se, ok := err.(*SagaError); ok {
			line := maxInt(se.Line-1, 0)
			col := utf16Col(d.Text, se.Line, se.Col)
			advice := diagnosticGuidance(se)
			diags = append(diags, map[string]any{"range": map[string]any{"start": map[string]int{"line": line, "character": col}, "end": map[string]int{"line": line, "character": col + 1}}, "severity": 1, "code": se.ID, "source": "saga", "message": se.Message, "data": map[string]any{"summary": advice.Summary, "notes": advice.Notes, "fixes": advice.Fixes, "root_cause": se.ID}})
		}
	}
	s.notify("textDocument/publishDiagnostics", map[string]any{"uri": uri, "version": d.Version, "diagnostics": diags})
}
func utf16Col(text string, line, col int) int {
	if line < 1 {
		return 0
	}
	ls := strings.Split(text, "\n")
	if line > len(ls) {
		return maxInt(col-1, 0)
	}
	rs := []rune(ls[line-1])
	n := col - 1
	if n < 0 {
		n = 0
	}
	if n > len(rs) {
		n = len(rs)
	}
	units := 0
	for _, r := range rs[:n] {
		units += len(utf16.Encode([]rune{r}))
	}
	return units
}
func positionFromParams(raw json.RawMessage) (string, int, int) {
	var p struct {
		TextDocument struct {
			URI string `json:"uri"`
		} `json:"textDocument"`
		Position struct{ Line, Character int } `json:"position"`
	}
	json.Unmarshal(raw, &p)
	return p.TextDocument.URI, p.Position.Line, p.Position.Character
}
func tokenAtUTF16(text string, line, ch int) (Token, bool) {
	toks, e := lex(text, "<lsp>")
	if e != nil {
		return Token{}, false
	}
	for _, t := range toks {
		if t.Line-1 == line {
			start := utf16Col(text, t.Line, t.Col)
			end := start + len(utf16.Encode([]rune(t.Lex)))
			if ch >= start && ch <= end {
				return t, true
			}
		}
	}
	return Token{}, false
}
func (s *lspServer) completion(raw json.RawMessage) any {
	uri, _, _ := positionFromParams(raw)
	d := s.docs[uri]
	set := map[string]string{}
	for k := range keywords {
		set[k] = "Keyword"
	}
	for k := range coreBuiltins {
		set[k] = "Function"
	}
	for _, k := range []string{"io", "json", "time", "math", "random", "crypto", "security", "game", "task", "sys", "compiler"} {
		set[k] = "Module"
	}
	if toks, e := lex(d.Text, uri); e == nil {
		for _, t := range toks {
			if t.Kind == IDENT {
				set[t.Lex] = "Variable"
			}
		}
	}
	keys := make([]string, 0, len(set))
	for k := range set {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	out := []any{}
	for _, k := range keys {
		kind := 6
		if set[k] == "Function" {
			kind = 3
		} else if set[k] == "Keyword" {
			kind = 14
		} else if set[k] == "Module" {
			kind = 9
		}
		out = append(out, map[string]any{"label": k, "kind": kind})
	}
	return out
}
func declarationTokens(text, uri string) map[string]Token {
	out := map[string]Token{}
	toks, e := lex(text, uri)
	if e != nil {
		return out
	}
	for j := 0; j+1 < len(toks); j++ {
		switch toks[j].Kind {
		case LET, VAR, FN, CLASS, INTERFACE, RECORD, ENUM:
			if toks[j+1].Kind == IDENT {
				out[toks[j+1].Lex] = toks[j+1]
			}
		}
	}
	return out
}
func (s *lspServer) definition(raw json.RawMessage) any {
	uri, line, ch := positionFromParams(raw)
	d := s.docs[uri]
	t, ok := tokenAtUTF16(d.Text, line, ch)
	if !ok {
		return nil
	}
	q, ok := declarationTokens(d.Text, uri)[t.Lex]
	if !ok {
		return nil
	}
	c := utf16Col(d.Text, q.Line, q.Col)
	return map[string]any{"uri": uri, "range": map[string]any{"start": map[string]int{"line": q.Line - 1, "character": c}, "end": map[string]int{"line": q.Line - 1, "character": c + len(utf16.Encode([]rune(q.Lex)))}}}
}
func (s *lspServer) rename(raw json.RawMessage) any {
	var p struct {
		TextDocument struct {
			URI string `json:"uri"`
		} `json:"textDocument"`
		Position struct{ Line, Character int } `json:"position"`
		NewName  string                        `json:"newName"`
	}
	json.Unmarshal(raw, &p)
	d := s.docs[p.TextDocument.URI]
	t, ok := tokenAtUTF16(d.Text, p.Position.Line, p.Position.Character)
	if !ok || t.Kind != IDENT {
		return map[string]any{"changes": map[string]any{}}
	}
	edits := []any{}
	toks, _ := lex(d.Text, p.TextDocument.URI)
	for _, q := range toks {
		if q.Kind == IDENT && q.Lex == t.Lex {
			c := utf16Col(d.Text, q.Line, q.Col)
			edits = append(edits, map[string]any{"range": map[string]any{"start": map[string]int{"line": q.Line - 1, "character": c}, "end": map[string]int{"line": q.Line - 1, "character": c + len(utf16.Encode([]rune(q.Lex)))}}, "newText": p.NewName})
		}
	}
	return map[string]any{"changes": map[string]any{p.TextDocument.URI: edits}}
}
func (s *lspServer) formatting(raw json.RawMessage) any {
	var p struct {
		TextDocument struct {
			URI string `json:"uri"`
		} `json:"textDocument"`
	}
	json.Unmarshal(raw, &p)
	d := s.docs[p.TextDocument.URI]
	lines := strings.Split(d.Text, "\n")
	endLine := len(lines)
	endChar := 0
	if endLine > 0 {
		endChar = len(utf16.Encode([]rune(lines[endLine-1])))
	}
	return []any{map[string]any{"range": map[string]any{"start": map[string]int{"line": 0, "character": 0}, "end": map[string]int{"line": maxInt(endLine-1, 0), "character": endChar}}, "newText": formatSagaSource(d.Text)}}
}
func (s *lspServer) semanticTokens(raw json.RawMessage) any {
	var p struct {
		TextDocument struct {
			URI string `json:"uri"`
		} `json:"textDocument"`
	}
	json.Unmarshal(raw, &p)
	d := s.docs[p.TextDocument.URI]
	toks, e := lex(d.Text, p.TextDocument.URI)
	if e != nil {
		return map[string]any{"data": []int{}}
	}
	prevL, prevC := 0, 0
	data := []int{}
	for _, t := range toks {
		typ := -1
		switch t.Kind {
		case LET, VAR, FN, RETURN, IF, ELSE, WHILE, FOR, IN, CLASS, INTERFACE, EXTENDS, IMPLEMENTS, PRIVATE, PUBLIC, TRY, CATCH, FINALLY, THROW, OVERRIDE, ABSTRACT, BREAK, CONTINUE, USE, RECORD, ENUM, MATCH, CASE, DEFAULT, TEST:
			typ = 0
		case IDENT:
			typ = 1
		case STRING, INTERPSTRING:
			typ = 4
		case INTLIT, DECLIT:
			typ = 5
		}
		if typ < 0 {
			continue
		}
		l := t.Line - 1
		c := utf16Col(d.Text, t.Line, t.Col)
		dl, dc := l-prevL, c
		if dl == 0 {
			dc = c - prevC
		}
		ln := len(utf16.Encode([]rune(t.Lex)))
		data = append(data, dl, dc, ln, typ, 0)
		prevL, prevC = l, c
	}
	return map[string]any{"data": data}
}

func (s *lspServer) codeActions(raw json.RawMessage) []any {
	var p struct {
		TextDocument struct {
			URI string `json:"uri"`
		} `json:"textDocument"`
		Context struct {
			Diagnostics []struct {
				Code    any            `json:"code"`
				Message string         `json:"message"`
				Data    map[string]any `json:"data"`
			} `json:"diagnostics"`
		} `json:"context"`
	}
	json.Unmarshal(raw, &p)
	out := []any{}
	for _, d := range p.Context.Diagnostics {
		id := fmt.Sprint(d.Code)
		if id == "" || id == "<nil>" {
			continue
		}
		out = append(out, map[string]any{"title": "Explain " + id, "kind": "quickfix", "command": map[string]any{"title": "Explain " + id, "command": "saga.explain", "arguments": []any{id}}})
		if rawFixes, ok := d.Data["fixes"].([]any); ok {
			for _, f := range rawFixes {
				if fm, ok := f.(map[string]any); ok {
					if title, _ := fm["title"].(string); title != "" {
						out = append(out, map[string]any{"title": title, "kind": "quickfix", "command": map[string]any{"title": title, "command": "saga.explain", "arguments": []any{id}}})
					}
				}
			}
		}
	}
	return out
}
