//go:build !sagaruntime

package main

import (
	"bufio"
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"time"
)

const standardsSchema = 2

var standardsCountryRE = regexp.MustCompile(`^[A-Z]{2}$`)
var standardsEmailRE = regexp.MustCompile(`^[^@\s]+@[^@\s]+\.[^@\s]+$`)
var standardsProposerTypes = map[string]bool{
	"national_body": true, "committee_secretariat": true, "committee": true,
	"category_a_liaison": true, "technical_management_board": true, "chief_executive_officer": true,
}

type standardsRegistry struct{ Root string }

func openStandardsRegistry(root string) (*standardsRegistry, error) {
	if root == "" {
		root = ".saga-standards"
	}
	abs, err := filepath.Abs(root)
	if err != nil {
		return nil, err
	}
	return &standardsRegistry{Root: abs}, nil
}
func (r *standardsRegistry) registryPath() string { return filepath.Join(r.Root, "registry.json") }
func (r *standardsRegistry) eventPath() string    { return filepath.Join(r.Root, "events.jsonl") }
func (r *standardsRegistry) evidenceDir() string  { return filepath.Join(r.Root, "evidence") }
func standardsNow() string {
	return time.Now().UTC().Truncate(time.Second).Format("2006-01-02T15:04:05Z")
}
func standardsCanonical(v any) ([]byte, error) {
	var b bytes.Buffer
	e := json.NewEncoder(&b)
	e.SetEscapeHTML(false)
	e.SetIndent("", "")
	if err := e.Encode(v); err != nil {
		return nil, err
	}
	return bytes.TrimSpace(b.Bytes()), nil
}
func standardsSHA(b []byte) string { h := sha256.Sum256(b); return hex.EncodeToString(h[:]) }
func standardsWriteJSON(path string, v any) error {
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		return err
	}
	var b bytes.Buffer
	e := json.NewEncoder(&b)
	e.SetEscapeHTML(false)
	e.SetIndent("", "  ")
	if err := e.Encode(v); err != nil {
		return err
	}
	tmp, err := os.CreateTemp(filepath.Dir(path), ".saga-standards-*.tmp")
	if err != nil {
		return err
	}
	name := tmp.Name()
	defer os.Remove(name)
	if _, err = tmp.Write(b.Bytes()); err == nil {
		err = tmp.Sync()
	}
	if cerr := tmp.Close(); err == nil {
		err = cerr
	}
	if err != nil {
		return err
	}
	return os.Rename(name, path)
}
func standardsText(v, label string) (string, error) {
	v = strings.TrimSpace(v)
	if v == "" {
		return "", fmt.Errorf("%s must not be empty", label)
	}
	return v, nil
}
func standardsCountry(v string) (string, error) {
	v = strings.ToUpper(strings.TrimSpace(v))
	if !standardsCountryRE.MatchString(v) {
		return "", fmt.Errorf("country must be ISO 3166-1 alpha-2, e.g. JP")
	}
	return v, nil
}
func standardsEmail(v string) (string, error) {
	v = strings.TrimSpace(v)
	if !standardsEmailRE.MatchString(v) {
		return "", fmt.Errorf("invalid email address")
	}
	return v, nil
}
func (r *standardsRegistry) init(project string) error {
	if _, err := os.Stat(r.registryPath()); err == nil {
		return fmt.Errorf("standards registry already exists: %s", r.Root)
	}
	p, err := standardsText(project, "project")
	if err != nil {
		return err
	}
	if err = os.MkdirAll(r.Root, 0755); err != nil {
		return err
	}
	v := map[string]any{"schema_version": standardsSchema, "project": p, "created_at": standardsNow(), "proposer": nil, "project_leader": nil, "base_document": nil, "committee_context": nil, "np_ballot": nil, "experts": []any{}, "p_member_commitments": []any{}, "adoptions": []any{}, "implementations": []any{}, "independent_labs": []any{}, "market_evidence": []any{}}
	if err = standardsWriteJSON(r.registryPath(), v); err != nil {
		return err
	}
	return r.event("registry.initialized", map[string]any{"project": p})
}
func (r *standardsRegistry) load() (map[string]any, error) {
	b, err := os.ReadFile(r.registryPath())
	if err != nil {
		return nil, fmt.Errorf("standards registry not initialized: %w", err)
	}
	var v map[string]any
	if err = json.Unmarshal(b, &v); err != nil {
		return nil, err
	}
	if intFromAny(v["schema_version"]) != standardsSchema {
		return nil, fmt.Errorf("unsupported standards registry schema")
	}
	return v, nil
}
func intFromAny(v any) int {
	switch q := v.(type) {
	case float64:
		return int(q)
	case int:
		return q
	case json.Number:
		n, _ := q.Int64()
		return int(n)
	}
	return 0
}
func (r *standardsRegistry) save(v map[string]any) error {
	return standardsWriteJSON(r.registryPath(), v)
}
func (r *standardsRegistry) event(kind string, payload map[string]any) error {
	previous := strings.Repeat("0", 64)
	if f, err := os.Open(r.eventPath()); err == nil {
		sc := bufio.NewScanner(f)
		last := ""
		for sc.Scan() {
			if strings.TrimSpace(sc.Text()) != "" {
				last = sc.Text()
			}
		}
		f.Close()
		if last != "" {
			var e map[string]any
			if json.Unmarshal([]byte(last), &e) == nil {
				if h, ok := e["hash"].(string); ok {
					previous = h
				}
			}
		}
	}
	e := map[string]any{"time": standardsNow(), "kind": kind, "payload": payload, "previous": previous}
	canon, err := standardsCanonical(e)
	if err != nil {
		return err
	}
	e["hash"] = standardsSHA(canon)
	if err = os.MkdirAll(r.Root, 0755); err != nil {
		return err
	}
	f, err := os.OpenFile(r.eventPath(), os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0644)
	if err != nil {
		return err
	}
	defer f.Close()
	var b bytes.Buffer
	enc := json.NewEncoder(&b)
	enc.SetEscapeHTML(false)
	if err = enc.Encode(e); err != nil {
		return err
	}
	_, err = f.Write(b.Bytes())
	return err
}
func (r *standardsRegistry) storeEvidence(source string) (map[string]any, error) {
	abs, err := filepath.Abs(source)
	if err != nil {
		return nil, err
	}
	b, err := os.ReadFile(abs)
	if err != nil {
		return nil, fmt.Errorf("evidence file not found: %w", err)
	}
	digest := standardsSHA(b)
	ext := strings.ToLower(filepath.Ext(abs))
	if len(ext) > 16 {
		ext = ext[:16]
	}
	if err = os.MkdirAll(r.evidenceDir(), 0755); err != nil {
		return nil, err
	}
	dest := filepath.Join(r.evidenceDir(), digest+ext)
	if _, e := os.Stat(dest); errors.Is(e, os.ErrNotExist) {
		if err = os.WriteFile(dest, b, 0644); err != nil {
			return nil, err
		}
	}
	rel, _ := filepath.Rel(r.Root, dest)
	return map[string]any{"sha256": digest, "stored": filepath.ToSlash(rel), "original_name": filepath.Base(abs), "bytes": fmt.Sprint(len(b))}, nil
}
func anySlice(v any) []any {
	if a, ok := v.([]any); ok {
		return a
	}
	return []any{}
}
func obj(v any) map[string]any {
	if m, ok := v.(map[string]any); ok {
		return m
	}
	return nil
}
func str(v any) string { q, _ := v.(string); return q }
func (r *standardsRegistry) evidenceOK(v any) bool {
	e := obj(v)
	if e == nil {
		return false
	}
	rel, want := str(e["stored"]), str(e["sha256"])
	if rel == "" || want == "" {
		return false
	}
	p := filepath.Clean(filepath.Join(r.Root, filepath.FromSlash(rel)))
	root := filepath.Clean(r.Root) + string(os.PathSeparator)
	if p != filepath.Clean(r.Root) && !strings.HasPrefix(p, root) {
		return false
	}
	b, err := os.ReadFile(p)
	return err == nil && standardsSHA(b) == want
}
func (r *standardsRegistry) verifyEvidence() (bool, []string, error) {
	v, err := r.load()
	if err != nil {
		return false, nil, err
	}
	bad := []string{}
	check := func(label string, e any) {
		if !r.evidenceOK(e) {
			bad = append(bad, label)
		}
	}
	if q := obj(v["proposer"]); q != nil {
		check("proposer", q["evidence"])
	}
	if q := obj(v["project_leader"]); q != nil {
		check("project_leader", q["consent"])
	}
	if q := obj(v["base_document"]); q != nil {
		check("base_document", q["evidence"])
	}
	if q := obj(v["committee_context"]); q != nil {
		check("committee_context", q["evidence"])
	}
	if q := obj(v["np_ballot"]); q != nil {
		check("np_ballot", q["evidence"])
	}
	for _, pair := range [][2]string{{"experts", "consent"}, {"p_member_commitments", "evidence"}, {"adoptions", "evidence"}, {"implementations", "conformance_report"}, {"independent_labs", "report"}, {"market_evidence", "evidence"}} {
		for j, item := range anySlice(v[pair[0]]) {
			q := obj(item)
			check(fmt.Sprintf("%s[%d]", pair[0], j+1), q[pair[1]])
		}
	}
	return len(bad) == 0, bad, nil
}
func (r *standardsRegistry) verifyChain() (bool, string, error) {
	f, err := os.Open(r.eventPath())
	if err != nil {
		return false, "events.jsonl missing", nil
	}
	defer f.Close()
	previous := strings.Repeat("0", 64)
	sc := bufio.NewScanner(f)
	line := 0
	for sc.Scan() {
		if strings.TrimSpace(sc.Text()) == "" {
			continue
		}
		line++
		var e map[string]any
		if err = json.Unmarshal(sc.Bytes(), &e); err != nil {
			return false, fmt.Sprintf("event %d invalid json", line), nil
		}
		actual := str(e["hash"])
		delete(e, "hash")
		if str(e["previous"]) != previous {
			return false, fmt.Sprintf("event %d previous mismatch", line), nil
		}
		canon, _ := standardsCanonical(e)
		want := standardsSHA(canon)
		if actual != want {
			return false, fmt.Sprintf("event %d hash mismatch", line), nil
		}
		previous = actual
	}
	if err = sc.Err(); err != nil {
		return false, "", err
	}
	return true, previous, nil
}
func uniqueStrings(items []any, key string) map[string]bool {
	out := map[string]bool{}
	for _, it := range items {
		if v := str(obj(it)[key]); v != "" {
			out[v] = true
		}
	}
	return out
}
func (r *standardsRegistry) status() (map[string]any, error) {
	v, err := r.load()
	if err != nil {
		return nil, err
	}
	validBy := func(items []any, key string) []any {
		out := []any{}
		for _, it := range items {
			q := obj(it)
			if r.evidenceOK(q[key]) {
				out = append(out, it)
			}
		}
		return out
	}
	validObject := func(value any, key string) map[string]any {
		q := obj(value)
		if q == nil || !r.evidenceOK(q[key]) {
			return nil
		}
		return q
	}
	proposer := validObject(v["proposer"], "evidence")
	leader := validObject(v["project_leader"], "consent")
	base := validObject(v["base_document"], "evidence")
	committee := validObject(v["committee_context"], "evidence")
	ballot := validObject(v["np_ballot"], "evidence")
	experts := validBy(anySlice(v["experts"]), "consent")
	commit := validBy(anySlice(v["p_member_commitments"]), "evidence")
	adopt := validBy(anySlice(v["adoptions"]), "evidence")
	impls := validBy(anySlice(v["implementations"]), "conformance_report")
	labs := validBy(anySlice(v["independent_labs"]), "report")
	market := validBy(anySlice(v["market_evidence"]), "evidence")
	second := []any{}
	for _, it := range impls {
		q := obj(it)
		lvl := str(q["conformance_level"])
		if str(q["name"]) != "saga-python" && str(q["independent_from"]) == "saga-python" && (lvl == "core" || lvl == "full") {
			second = append(second, it)
		}
	}
	independentLabs := []any{}
	propName := ""
	if proposer != nil {
		propName = str(proposer["name"])
	}
	for _, it := range labs {
		q := obj(it)
		if propName == "" || !strings.EqualFold(str(q["organization"]), propName) {
			independentLabs = append(independentLabs, it)
		}
	}
	chainOK, head, _ := r.verifyChain()
	evOK, bad, _ := r.verifyEvidence()
	ec, eo := uniqueStrings(experts, "country"), uniqueStrings(experts, "organization")
	pc := uniqueStrings(commit, "country")
	ac, ao := uniqueStrings(adopt, "country"), uniqueStrings(adopt, "organization")
	mc := uniqueStrings(market, "country")

	pMemberCount := 0
	if committee != nil {
		pMemberCount = intFromAny(committee["p_members"])
	}
	requiredActive := 5
	if pMemberCount > 0 && pMemberCount <= 16 {
		requiredActive = 4
	}
	approvalCriterion := false
	ballotApprovals, ballotRejections, ballotAbstentions := 0, 0, 0
	if ballot != nil {
		ballotApprovals = intFromAny(ballot["approvals"])
		ballotRejections = intFromAny(ballot["rejections"])
		ballotAbstentions = intFromAny(ballot["abstentions"])
		voting := ballotApprovals + ballotRejections
		approvalCriterion = voting > 0 && ballotApprovals*3 >= voting*2
	}
	participationCriterion := len(pc) >= requiredActive
	preSubmission := map[string]bool{
		"eligible_proposer":           proposer != nil,
		"project_leader_with_consent": leader != nil,
		"base_document_or_outline":    base != nil,
		"market_relevance_evidence":   len(market) > 0,
		"tamper_evident_record":       chainOK && evOK,
	}
	preComplete := true
	for _, ok := range preSubmission {
		preComplete = preComplete && ok
	}
	maturity := map[string]bool{
		"international_expert_team":         len(experts) >= 5 && len(ec) >= 3 && len(eo) >= 3,
		"multi_country_adoption":            len(ac) >= 3 && len(ao) >= 3,
		"independent_second_implementation": len(second) > 0,
		"independent_conformance_lab":       len(independentLabs) > 0,
		"multi_country_market_evidence":     len(market) >= 3 && len(mc) >= 2,
	}
	maturityComplete := true
	for _, ok := range maturity {
		maturityComplete = maturityComplete && ok
	}
	return map[string]any{
		"project":                          v["project"],
		"pre_submission_evidence":          preSubmission,
		"pre_submission_evidence_complete": preComplete,
		"np_acceptance_evidence": map[string]any{
			"committee_p_members":              pMemberCount,
			"required_active_p_members":        requiredActive,
			"approvals":                        ballotApprovals,
			"rejections":                       ballotRejections,
			"abstentions":                      ballotAbstentions,
			"two_thirds_p_members_voting":      approvalCriterion,
			"active_participation_commitments": participationCriterion,
			"acceptance_evidence_complete":     ballot != nil && approvalCriterion && participationCriterion,
		},
		"engineering_maturity":          maturity,
		"engineering_maturity_complete": maturityComplete,
		"counts":                        map[string]any{"experts": len(experts), "expert_countries": len(ec), "expert_organizations": len(eo), "p_member_commitments": len(pc), "adoption_countries": len(ac), "adoption_organizations": len(ao), "implementations": len(impls), "qualifying_second_implementations": len(second), "independent_labs": len(independentLabs), "market_evidence": len(market), "market_countries": len(mc)},
		"event_chain":                   map[string]any{"valid": chainOK, "head": head},
		"evidence":                      map[string]any{"valid": evOK, "invalid_records": bad},
		"note":                          "Evidence tracking only. NP submission and acceptance remain decisions of the applicable standards body under its current directives.",
	}, nil
}
func parseStandardsArgs(args []string) (root, action string, opts map[string][]string, err error) {
	root = ".saga-standards"
	opts = map[string][]string{}
	i := 0
	for i < len(args) {
		if args[i] == "--root" {
			if i+1 >= len(args) {
				return "", "", nil, fmt.Errorf("--root requires a path")
			}
			root = args[i+1]
			i += 2
			continue
		}
		action = args[i]
		i++
		if action == "record" {
			if i >= len(args) || strings.HasPrefix(args[i], "--") {
				return "", "", nil, fmt.Errorf("standards record action required")
			}
			action = args[i]
			i++
		}
		break
	}
	if action == "" {
		return "", "", nil, fmt.Errorf("standards action required")
	}
	for i < len(args) {
		k := args[i]
		if !strings.HasPrefix(k, "--") {
			return "", "", nil, fmt.Errorf("unexpected argument: %s", k)
		}
		if i+1 >= len(args) || strings.HasPrefix(args[i+1], "--") {
			opts[k] = append(opts[k], "true")
			i++
			continue
		}
		opts[k] = append(opts[k], args[i+1])
		i += 2
	}
	return
}
func optOne(opts map[string][]string, k string, required bool) (string, error) {
	v := opts[k]
	if len(v) == 0 {
		if required {
			return "", fmt.Errorf("%s is required", k)
		}
		return "", nil
	}
	return v[len(v)-1], nil
}
func appendRecord(v map[string]any, key string, rec map[string]any) {
	a := anySlice(v[key])
	a = append(a, rec)
	v[key] = a
}
func (r *standardsRegistry) record(action string, opts map[string][]string) error {
	v, err := r.load()
	if err != nil {
		return err
	}
	evidence := func(flag string) (map[string]any, error) {
		p, e := optOne(opts, flag, true)
		if e != nil {
			return nil, e
		}
		return r.storeEvidence(p)
	}
	country := func() (string, error) {
		q, e := optOne(opts, "--country", true)
		if e != nil {
			return "", e
		}
		return standardsCountry(q)
	}
	switch action {
	case "set-proposer":
		name, e := optOne(opts, "--name", true)
		if e != nil {
			return e
		}
		typ, e := optOne(opts, "--type", true)
		if e != nil {
			return e
		}
		if !standardsProposerTypes[typ] {
			return fmt.Errorf("invalid proposer type")
		}
		c, e := country()
		if e != nil {
			return e
		}
		ev, e := evidence("--evidence")
		if e != nil {
			return e
		}
		rec := map[string]any{"name": name, "type": typ, "country": c, "evidence": ev, "recorded_at": standardsNow()}
		v["proposer"] = rec
		if e = r.save(v); e != nil {
			return e
		}
		return r.event("proposer.set", map[string]any{"name": name, "type": typ, "country": c, "evidence": str(ev["sha256"])})
	case "nominate-leader":
		name, e := optOne(opts, "--name", true)
		if e != nil {
			return e
		}
		email, e := optOne(opts, "--email", true)
		if e != nil {
			return e
		}
		email, e = standardsEmail(email)
		if e != nil {
			return e
		}
		org, e := optOne(opts, "--organization", true)
		if e != nil {
			return e
		}
		c, e := country()
		if e != nil {
			return e
		}
		ev, e := evidence("--consent")
		if e != nil {
			return e
		}
		rec := map[string]any{"name": name, "email": email, "organization": org, "country": c, "consent": ev, "nominated_at": standardsNow(), "status": "nominated_with_consent"}
		v["project_leader"] = rec
		if e = r.save(v); e != nil {
			return e
		}
		return r.event("project_leader.nominated", map[string]any{"name": name, "organization": org, "country": c, "consent": str(ev["sha256"])})
	case "set-base-document":
		title, e := optOne(opts, "--title", true)
		if e != nil {
			return e
		}
		ev, e := evidence("--evidence")
		if e != nil {
			return e
		}
		rec := map[string]any{"title": title, "evidence": ev, "recorded_at": standardsNow()}
		v["base_document"] = rec
		if e = r.save(v); e != nil {
			return e
		}
		return r.event("base_document.set", map[string]any{"title": title, "evidence": str(ev["sha256"])})
	case "set-committee":
		name, e := optOne(opts, "--name", true)
		if e != nil {
			return e
		}
		countText, e := optOne(opts, "--p-members", true)
		if e != nil {
			return e
		}
		var count int
		if _, e = fmt.Sscanf(countText, "%d", &count); e != nil || count <= 0 {
			return fmt.Errorf("--p-members must be a positive integer")
		}
		ev, e := evidence("--evidence")
		if e != nil {
			return e
		}
		rec := map[string]any{"name": name, "p_members": count, "evidence": ev, "recorded_at": standardsNow()}
		v["committee_context"] = rec
		if e = r.save(v); e != nil {
			return e
		}
		return r.event("committee_context.set", map[string]any{"name": name, "p_members": count, "evidence": str(ev["sha256"])})
	case "record-np-ballot":
		readCount := func(flag string) (int, error) {
			q, e := optOne(opts, flag, true)
			if e != nil {
				return 0, e
			}
			var n int
			if _, e = fmt.Sscanf(q, "%d", &n); e != nil || n < 0 {
				return 0, fmt.Errorf("%s must be a non-negative integer", flag)
			}
			return n, nil
		}
		approvals, e := readCount("--approvals")
		if e != nil {
			return e
		}
		rejections, e := readCount("--rejections")
		if e != nil {
			return e
		}
		abstentions, e := readCount("--abstentions")
		if e != nil {
			return e
		}
		ev, e := evidence("--evidence")
		if e != nil {
			return e
		}
		rec := map[string]any{"approvals": approvals, "rejections": rejections, "abstentions": abstentions, "evidence": ev, "recorded_at": standardsNow()}
		v["np_ballot"] = rec
		if e = r.save(v); e != nil {
			return e
		}
		return r.event("np_ballot.recorded", map[string]any{"approvals": approvals, "rejections": rejections, "abstentions": abstentions, "evidence": str(ev["sha256"])})
	case "add-expert":
		name, e := optOne(opts, "--name", true)
		if e != nil {
			return e
		}
		email, e := optOne(opts, "--email", true)
		if e != nil {
			return e
		}
		email, e = standardsEmail(email)
		if e != nil {
			return e
		}
		org, e := optOne(opts, "--organization", true)
		if e != nil {
			return e
		}
		c, e := country()
		if e != nil {
			return e
		}
		expertise, e := optOne(opts, "--expertise", true)
		if e != nil {
			return e
		}
		ev, e := evidence("--consent")
		if e != nil {
			return e
		}
		id := standardsSHA([]byte(strings.ToLower(email) + "|" + org + "|" + c))[:16]
		for _, it := range anySlice(v["experts"]) {
			if str(obj(it)["id"]) == id {
				return fmt.Errorf("expert already registered")
			}
		}
		rec := map[string]any{"id": id, "name": name, "email": email, "organization": org, "country": c, "expertise": expertise, "consent": ev, "joined_at": standardsNow()}
		appendRecord(v, "experts", rec)
		if e = r.save(v); e != nil {
			return e
		}
		return r.event("expert.added", map[string]any{"id": id, "organization": org, "country": c, "consent": str(ev["sha256"])})
	case "add-p-member":
		nb, e := optOne(opts, "--national-body", true)
		if e != nil {
			return e
		}
		c, e := country()
		if e != nil {
			return e
		}
		emails := opts["--expert-email"]
		if len(emails) == 0 {
			return fmt.Errorf("--expert-email is required")
		}
		known := map[string]bool{}
		for _, it := range anySlice(v["experts"]) {
			known[str(obj(it)["email"])] = true
		}
		for j, q := range emails {
			emails[j], e = standardsEmail(q)
			if e != nil {
				return e
			}
			if !known[emails[j]] {
				return fmt.Errorf("register expert first: %s", emails[j])
			}
		}
		sort.Strings(emails)
		ev, e := evidence("--evidence")
		if e != nil {
			return e
		}
		rec := map[string]any{"national_body": nb, "country": c, "expert_emails": emails, "evidence": ev, "recorded_at": standardsNow()}
		appendRecord(v, "p_member_commitments", rec)
		if e = r.save(v); e != nil {
			return e
		}
		return r.event("p_member.commitment_added", map[string]any{"national_body": nb, "country": c, "evidence": str(ev["sha256"])})
	case "add-adoption":
		org, e := optOne(opts, "--organization", true)
		if e != nil {
			return e
		}
		c, e := country()
		if e != nil {
			return e
		}
		uc, e := optOne(opts, "--use-case", true)
		if e != nil {
			return e
		}
		ev, e := evidence("--evidence")
		if e != nil {
			return e
		}
		rec := map[string]any{"organization": org, "country": c, "use_case": uc, "evidence": ev, "recorded_at": standardsNow()}
		appendRecord(v, "adoptions", rec)
		if e = r.save(v); e != nil {
			return e
		}
		return r.event("adoption.added", map[string]any{"organization": org, "country": c, "evidence": str(ev["sha256"])})
	case "add-implementation":
		name, e := optOne(opts, "--name", true)
		if e != nil {
			return e
		}
		lang, e := optOne(opts, "--language", true)
		if e != nil {
			return e
		}
		repo, e := optOne(opts, "--repository", true)
		if e != nil {
			return e
		}
		report, e := evidence("--report")
		if e != nil {
			return e
		}
		ind, _ := optOne(opts, "--independent-from", false)
		if ind == "" {
			ind = "saga-python"
		}
		level, _ := optOne(opts, "--level", false)
		if level == "" {
			level = "experimental"
		}
		if level != "experimental" && level != "core" && level != "full" {
			return fmt.Errorf("level must be experimental, core, or full")
		}
		rec := map[string]any{"name": name, "implementation_language": lang, "repository": repo, "independent_from": ind, "conformance_level": level, "conformance_report": report, "recorded_at": standardsNow()}
		appendRecord(v, "implementations", rec)
		if e = r.save(v); e != nil {
			return e
		}
		return r.event("implementation.added", map[string]any{"name": name, "language": lang, "level": level, "report": str(report["sha256"])})
	case "add-lab-report":
		org, e := optOne(opts, "--organization", true)
		if e != nil {
			return e
		}
		c, e := country()
		if e != nil {
			return e
		}
		scope, e := optOne(opts, "--scope", true)
		if e != nil {
			return e
		}
		rep, e := evidence("--report")
		if e != nil {
			return e
		}
		rec := map[string]any{"organization": org, "country": c, "scope": scope, "report": rep, "recorded_at": standardsNow()}
		appendRecord(v, "independent_labs", rec)
		if e = r.save(v); e != nil {
			return e
		}
		return r.event("independent_lab.report_added", map[string]any{"organization": org, "country": c, "report": str(rep["sha256"])})
	case "add-market-evidence":
		kind, e := optOne(opts, "--kind", true)
		if e != nil {
			return e
		}
		allowed := map[string]bool{"survey": true, "case_study": true, "procurement": true, "education": true, "industry_letter": true, "usage_metrics": true, "research": true}
		if !allowed[kind] {
			return fmt.Errorf("invalid market evidence kind")
		}
		title, e := optOne(opts, "--title", true)
		if e != nil {
			return e
		}
		c, e := country()
		if e != nil {
			return e
		}
		ev, e := evidence("--evidence")
		if e != nil {
			return e
		}
		rec := map[string]any{"kind": kind, "title": title, "country": c, "evidence": ev, "recorded_at": standardsNow()}
		appendRecord(v, "market_evidence", rec)
		if e = r.save(v); e != nil {
			return e
		}
		return r.event("market_evidence.added", map[string]any{"kind": kind, "country": c, "evidence": str(ev["sha256"])})
	default:
		return fmt.Errorf("unknown standards action: %s", action)
	}
}
func printStandardsJSON(v any) error {
	var b bytes.Buffer
	e := json.NewEncoder(&b)
	e.SetEscapeHTML(false)
	e.SetIndent("", "  ")
	if err := e.Encode(v); err != nil {
		return err
	}
	_, err := io.Copy(os.Stdout, &b)
	return err
}
func runStandardsCLI(args []string) int {
	if len(args) == 0 || args[0] == "--help" || args[0] == "-h" || args[0] == "help" {
		fmt.Println(`Usage: saga standards [--root DIR] COMMAND [options]

Commands:
  init [--project NAME]
  status [--json]
  verify [--json]
  record set-proposer --name N --type TYPE --country CC --evidence FILE
  record nominate-leader --name N --email E --organization O --country CC --consent FILE
  record set-base-document --title T --evidence FILE
  record set-committee --name N --p-members COUNT --evidence FILE
  record add-expert ...
  record add-p-member ...
  record add-market-evidence ...
  record add-adoption ...
  record add-implementation ...
  record add-lab-report ...
  record record-np-ballot --approvals N --rejections N --abstentions N --evidence FILE

The registry stores evidence by SHA-256 and hash-chains events. It records evidence; it does not grant ISO/IEC approval.`)
		return 0
	}
	root, action, opts, err := parseStandardsArgs(args)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 64
	}
	r, err := openStandardsRegistry(root)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 74
	}
	switch action {
	case "init":
		p, _ := optOne(opts, "--project", false)
		if p == "" {
			p = "Saga Programming Language"
		}
		err = r.init(p)
		if err == nil {
			fmt.Println("Initialized:", r.Root)
		}
	case "status":
		var v any
		v, err = r.status()
		if err == nil {
			err = printStandardsJSON(v)
		}
	case "verify":
		var chain bool
		var head string
		var evidence bool
		var bad []string
		chain, head, err = r.verifyChain()
		if err == nil {
			evidence, bad, err = r.verifyEvidence()
		}
		if err == nil {
			_ = printStandardsJSON(map[string]any{"valid": chain && evidence, "event_chain": map[string]any{"valid": chain, "head_or_error": head}, "evidence": map[string]any{"valid": evidence, "invalid_records": bad}})
			if !chain || !evidence {
				return 1
			}
		}
	default:
		err = r.record(action, opts)
		if err == nil {
			fmt.Println("Recorded:", action)
		}
	}
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 74
	}
	return 0
}
