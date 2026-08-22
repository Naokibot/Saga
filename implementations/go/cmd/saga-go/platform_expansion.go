package main

import (
	"bytes"
	"context"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"math"
	"net"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"sort"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"time"
)

const sagaHTTPServerMaxBody = 8 << 20

var sagaNativeAppOperations = []string{
	"system.snapshot", "system.cwd", "system.home_dir", "system.temp_dir", "system.pid",
	"filesystem.read_text", "filesystem.write_text", "filesystem.exists", "filesystem.remove", "filesystem.list", "filesystem.mkdir", "filesystem.rename", "filesystem.stat",
	"time.unix_ms", "time.sleep_ms", "crypto.random_uuid", "process.run", "network.http_get",
}

var sagaNativeAppCapabilities = []string{"system", "filesystem", "time", "crypto", "process", "network", "http", "database", "game"}

func containsText(xs []string, q string) bool {
	for _, x := range xs {
		if x == q {
			return true
		}
	}
	return false
}

func appJSON(payload string) (map[string]any, error) {
	if strings.TrimSpace(payload) == "" {
		return map[string]any{}, nil
	}
	// Validate with Saga's strict decoder first so duplicate object keys and
	// trailing content cannot be interpreted differently by two host adapters.
	strict, err := decodeJSONSaga(payload)
	if err != nil {
		return nil, fmt.Errorf("invalid app payload JSON: %w", err)
	}
	if _, ok := strict.(MapValue); !ok {
		return nil, fmt.Errorf("app payload JSON must be an object")
	}
	var m map[string]any
	if err := json.Unmarshal([]byte(payload), &m); err != nil {
		return nil, fmt.Errorf("invalid app payload JSON: %w", err)
	}
	return m, nil
}

func appJSONString(v any) (string, error) {
	b, err := json.Marshal(v)
	if err != nil {
		return "", err
	}
	return string(b), nil
}

func appString(m map[string]any, key string) string {
	if v, ok := m[key].(string); ok {
		return v
	}
	return ""
}
func appInt(m map[string]any, key string, def int) int {
	if v, ok := m[key].(float64); ok {
		return int(v)
	}
	return def
}

const sagaHostedMaxTextBytes = 8 << 20

type sagaCappedBuffer struct {
	buf       bytes.Buffer
	max       int
	truncated bool
}

func (b *sagaCappedBuffer) Write(p []byte) (int, error) {
	original := len(p)
	remaining := b.max - b.buf.Len()
	if remaining > 0 {
		if len(p) > remaining {
			_, _ = b.buf.Write(p[:remaining])
			b.truncated = true
		} else {
			_, _ = b.buf.Write(p)
		}
	} else if len(p) > 0 {
		b.truncated = true
	}
	return original, nil
}

func runBoundedProcess(argv []string, cwd string, timeout time.Duration) (string, error, bool, bool) {
	if len(argv) == 0 || argv[0] == "" {
		return "", fmt.Errorf("empty command"), false, false
	}
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()
	cmd := exec.CommandContext(ctx, argv[0], argv[1:]...)
	if cwd != "" {
		cmd.Dir = cwd
	}
	var out sagaCappedBuffer
	out.max = sagaHostedMaxTextBytes
	cmd.Stdout = &out
	cmd.Stderr = &out
	err := cmd.Run()
	timedOut := ctx.Err() == context.DeadlineExceeded
	if out.truncated && err == nil {
		err = fmt.Errorf("process output exceeded %d bytes", sagaHostedMaxTextBytes)
	}
	return out.buf.String(), err, timedOut, out.truncated
}

func readBoundedUTF8Text(r io.Reader, label string) (string, error) {
	b, err := io.ReadAll(io.LimitReader(r, sagaHostedMaxTextBytes+1))
	if err != nil {
		return "", err
	}
	if len(b) > sagaHostedMaxTextBytes {
		return "", fmt.Errorf("%s exceeds %d bytes", label, sagaHostedMaxTextBytes)
	}
	if !validUTF8String(string(b)) {
		return "", fmt.Errorf("%s is not valid UTF-8", label)
	}
	return string(b), nil
}

func readBoundedHTTPText(r io.Reader) (string, error) {
	return readBoundedUTF8Text(r, "HTTP response body")
}

func newExplicitHTTPClient(timeout time.Duration) *http.Client {
	return &http.Client{Timeout: timeout, Transport: &http.Transport{Proxy: nil}, CheckRedirect: func(req *http.Request, via []*http.Request) error { return http.ErrUseLastResponse }}
}

func nativeAppInvoke(op, payload string) (string, error) {
	m, err := appJSON(payload)
	if err != nil {
		return "", err
	}
	switch op {
	case "system.snapshot":
		home, _ := os.UserHomeDir()
		cwd, _ := os.Getwd()
		return appJSONString(map[string]any{"platform": runtime.GOOS, "arch": runtime.GOARCH, "cpu_count": runtime.NumCPU(), "page_size": os.Getpagesize(), "pid": os.Getpid(), "cwd": cwd, "home_dir": home, "temp_dir": os.TempDir()})
	case "system.cwd":
		v, e := os.Getwd()
		return v, e
	case "system.home_dir":
		return os.UserHomeDir()
	case "system.temp_dir":
		return os.TempDir(), nil
	case "system.pid":
		return strconv.Itoa(os.Getpid()), nil
	case "filesystem.read_text":
		f, e := os.Open(appString(m, "path"))
		if e != nil {
			return "", e
		}
		defer f.Close()
		return readBoundedUTF8Text(f, "file")
	case "filesystem.write_text":
		path := appString(m, "path")
		if path == "" {
			return "", fmt.Errorf("path required")
		}
		dir := filepath.Dir(path)
		if dir != "." {
			if e := os.MkdirAll(dir, 0755); e != nil {
				return "", e
			}
		}
		if e := os.WriteFile(path, []byte(appString(m, "text")), 0644); e != nil {
			return "", e
		}
		return "", nil
	case "filesystem.exists":
		_, e := os.Stat(appString(m, "path"))
		return strconv.FormatBool(e == nil), nil
	case "filesystem.remove":
		e := os.Remove(appString(m, "path"))
		if e != nil && !os.IsNotExist(e) {
			return "", e
		}
		return "", nil
	case "filesystem.mkdir":
		e := os.MkdirAll(appString(m, "path"), 0755)
		return "", e
	case "filesystem.rename":
		e := os.Rename(appString(m, "from"), appString(m, "to"))
		return "", e
	case "filesystem.list":
		es, e := os.ReadDir(appString(m, "path"))
		if e != nil {
			return "", e
		}
		out := make([]string, 0, len(es))
		for _, x := range es {
			out = append(out, x.Name())
		}
		sort.Strings(out)
		return appJSONString(out)
	case "filesystem.stat":
		st, e := os.Stat(appString(m, "path"))
		if e != nil {
			return "", e
		}
		return appJSONString(map[string]any{"name": st.Name(), "size": st.Size(), "mode": st.Mode().String(), "is_dir": st.IsDir(), "modified_unix_ms": st.ModTime().UnixMilli()})
	case "time.unix_ms":
		return strconv.FormatInt(time.Now().UnixMilli(), 10), nil
	case "time.sleep_ms":
		ms := appInt(m, "ms", 0)
		if ms < 0 || ms > 86400000 {
			return "", fmt.Errorf("ms must be 0..86400000")
		}
		time.Sleep(time.Duration(ms) * time.Millisecond)
		return "", nil
	case "crypto.random_uuid":
		var b [16]byte
		if _, e := rand.Read(b[:]); e != nil {
			return "", e
		}
		b[6] = (b[6] & 0x0f) | 0x40
		b[8] = (b[8] & 0x3f) | 0x80
		return fmt.Sprintf("%08x-%04x-%04x-%04x-%012x", b[0:4], b[4:6], b[6:8], b[8:10], b[10:16]), nil
	case "process.run":
		raw, ok := m["argv"].([]any)
		if !ok || len(raw) == 0 {
			return "", fmt.Errorf("argv array required")
		}
		argv := make([]string, len(raw))
		for j, v := range raw {
			q, ok := v.(string)
			if !ok || q == "" && j == 0 {
				return "", fmt.Errorf("argv must contain text and argv[0] must be non-empty")
			}
			argv[j] = q
		}
		timeout := appInt(m, "timeout_ms", 30000)
		if timeout < 1 || timeout > 300000 {
			return "", fmt.Errorf("timeout_ms must be 1..300000")
		}
		out, runErr, timedOut, truncated := runBoundedProcess(argv, appString(m, "cwd"), time.Duration(timeout)*time.Millisecond)
		res := map[string]any{"output": out, "success": runErr == nil, "timeout": timedOut, "output_truncated": truncated}
		if runErr != nil {
			res["error"] = runErr.Error()
		}
		return appJSONString(res)
	case "network.http_get":
		u := appString(m, "url")
		if u == "" {
			return "", fmt.Errorf("url required")
		}
		timeout := appInt(m, "timeout_ms", 15000)
		if timeout < 1 || timeout > 60000 {
			return "", fmt.Errorf("timeout_ms must be 1..60000")
		}
		parsed, e := url.Parse(u)
		if e != nil || (parsed.Scheme != "http" && parsed.Scheme != "https") || parsed.Host == "" {
			return "", fmt.Errorf("url must be absolute http/https")
		}
		client := newExplicitHTTPClient(time.Duration(timeout) * time.Millisecond)
		resp, e := client.Get(u)
		if e != nil {
			return "", e
		}
		defer resp.Body.Close()
		body, e := readBoundedHTTPText(resp.Body)
		if e != nil {
			return "", e
		}
		return appJSONString(map[string]any{"status": resp.StatusCode, "content_type": resp.Header.Get("Content-Type"), "body": body, "redirect_location": resp.Header.Get("Location")})
	}
	return "", fmt.Errorf("app operation unsupported on native host: %s", op)
}

type sagaHTTPResponse struct {
	Status      int
	ContentType string
	Body        string
	Ack         chan error
}

type HTTPRequestValue struct {
	Method   string
	Path     string
	Body     string
	Header   http.Header
	Query    url.Values
	response chan sagaHTTPResponse
	ctxDone  <-chan struct{}
	done     atomic.Bool
}

type HTTPServerValue struct {
	Listener net.Listener
	Server   *http.Server
	Requests chan *HTTPRequestValue
	Done     chan struct{}
	closed   atomic.Bool
	doneOnce sync.Once
}

func (s *HTTPServerValue) markClosed() {
	s.closed.Store(true)
	s.doneOnce.Do(func() { close(s.Done) })
}

func newSagaHTTPServer(host string, port int) (*HTTPServerValue, error) {
	if port < 0 || port > 65535 {
		return nil, fmt.Errorf("port must be 0..65535")
	}
	ln, err := net.Listen("tcp", net.JoinHostPort(host, fmt.Sprintf("%d", port)))
	if err != nil {
		return nil, err
	}
	v := &HTTPServerValue{Listener: ln, Requests: make(chan *HTTPRequestValue, 64), Done: make(chan struct{})}
	v.Server = &http.Server{
		ReadHeaderTimeout: 10 * time.Second,
		ReadTimeout:       30 * time.Second,
		IdleTimeout:       60 * time.Second,
		Handler: http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			limited := io.LimitReader(r.Body, sagaHTTPServerMaxBody+1)
			b, err := io.ReadAll(limited)
			if err != nil {
				http.Error(w, "request read error", http.StatusBadRequest)
				return
			}
			if len(b) > sagaHTTPServerMaxBody {
				http.Error(w, "request body too large", http.StatusRequestEntityTooLarge)
				return
			}
			if !validUTF8String(string(b)) {
				http.Error(w, "request body is not valid UTF-8", http.StatusBadRequest)
				return
			}
			req := &HTTPRequestValue{Method: r.Method, Path: r.URL.Path, Body: string(b), Header: r.Header.Clone(), Query: r.URL.Query(), response: make(chan sagaHTTPResponse, 1), ctxDone: r.Context().Done()}
			select {
			case v.Requests <- req:
			case <-r.Context().Done():
				return
			}
			select {
			case resp := <-req.response:
				if resp.ContentType != "" {
					w.Header().Set("Content-Type", resp.ContentType)
				}
				w.WriteHeader(resp.Status)
				_, writeErr := io.WriteString(w, resp.Body)
				if resp.Ack != nil {
					resp.Ack <- writeErr
				}
			case <-r.Context().Done():
				return
			}
		}),
	}
	go func() { _ = v.Server.Serve(ln); v.markClosed() }()
	return v, nil
}

func sagaAwaitHTTPResponseAck(ack <-chan error, ctxDone <-chan struct{}) (error, bool) {
	select {
	case e := <-ack:
		return e, true
	case <-ctxDone:
		// net/http cancels the request context as the handler returns. The
		// buffered acknowledgement is sent before that return. If both are
		// ready, consume the acknowledgement rather than reporting a false
		// request-close failure.
		select {
		case e := <-ack:
			return e, true
		default:
			return nil, false
		}
	}
}

func sagaServerPort(s *HTTPServerValue) int {
	if s == nil || s.Listener == nil {
		return 0
	}
	if a, ok := s.Listener.Addr().(*net.TCPAddr); ok {
		return a.Port
	}
	return 0
}

func mapTextPairs(v MapValue) (map[string]string, error) {
	out := map[string]string{}
	for _, e := range v.Entries {
		k, ok := e.Key.(string)
		if !ok {
			return nil, fmt.Errorf("map key must be text")
		}
		val, ok := e.Value.(string)
		if !ok {
			return nil, fmt.Errorf("map value must be text")
		}
		out[k] = val
	}
	return out, nil
}

func sagaHTMLEscape(s string) string {
	r := strings.NewReplacer("&", "&amp;", "<", "&lt;", ">", "&gt;", "\"", "&quot;", "'", "&#39;")
	return r.Replace(s)
}

func sagaHTMLElement(tag string, attrs MapValue, body string) (string, error) {
	if tag == "" {
		return "", fmt.Errorf("tag must not be empty")
	}
	for _, r := range tag {
		if !(r >= 'a' && r <= 'z' || r >= 'A' && r <= 'Z' || r >= '0' && r <= '9' || r == '-' || r == ':') {
			return "", fmt.Errorf("invalid tag")
		}
	}
	kv, err := mapTextPairs(attrs)
	if err != nil {
		return "", err
	}
	keys := make([]string, 0, len(kv))
	for k := range kv {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	var b strings.Builder
	b.WriteByte('<')
	b.WriteString(tag)
	for _, k := range keys {
		if k == "" {
			return "", fmt.Errorf("empty attribute name")
		}
		for _, r := range k {
			if !(r >= 'a' && r <= 'z' || r >= 'A' && r <= 'Z' || r >= '0' && r <= '9' || r == '-' || r == '_' || r == ':') {
				return "", fmt.Errorf("invalid attribute name")
			}
		}
		b.WriteByte(' ')
		b.WriteString(k)
		b.WriteString("=\"")
		b.WriteString(sagaHTMLEscape(kv[k]))
		b.WriteByte('"')
	}
	b.WriteByte('>')
	b.WriteString(body)
	b.WriteString("</")
	b.WriteString(tag)
	b.WriteByte('>')
	return b.String(), nil
}

func sagaRouteMatch(pattern, path string) (MapValue, bool) {
	trim := func(s string) []string {
		s = strings.Trim(s, "/")
		if s == "" {
			return nil
		}
		return strings.Split(s, "/")
	}
	p, q := trim(pattern), trim(path)
	out := MapValue{}
	i := 0
	for i < len(p) {
		if strings.HasPrefix(p[i], "*") {
			name := strings.TrimPrefix(p[i], "*")
			if name == "" {
				name = "rest"
			}
			out = mapPut(out, name, strings.Join(q[minInt(i, len(q)):], "/"))
			return out, true
		}
		if i >= len(q) {
			return MapValue{}, false
		}
		if strings.HasPrefix(p[i], ":") {
			name := strings.TrimPrefix(p[i], ":")
			if name == "" {
				return MapValue{}, false
			}
			out = mapPut(out, name, q[i])
		} else if p[i] != q[i] {
			return MapValue{}, false
		}
		i++
	}
	return out, i == len(q)
}

func minInt(a, b int) int {
	if a < b {
		return a
	}
	return b
}

var sagaDBPathLocks sync.Map

func canonicalDBLockIdentity(path string) string {
	abs, err := filepath.Abs(path)
	if err != nil {
		abs = filepath.Clean(path)
	}
	abs = filepath.Clean(abs)
	if real, e := filepath.EvalSymlinks(abs); e == nil {
		return filepath.Clean(real)
	}
	parent := filepath.Dir(abs)
	if realParent, e := filepath.EvalSymlinks(parent); e == nil {
		return filepath.Join(filepath.Clean(realParent), filepath.Base(abs))
	}
	return abs
}

func safeLockIdentity(path string) string {
	h := sha256.Sum256([]byte(path))
	return hex.EncodeToString(h[:])
}

func sagaDBPathLock(path string) *sync.Mutex {
	path = canonicalDBLockIdentity(path)
	v, _ := sagaDBPathLocks.LoadOrStore(path, &sync.Mutex{})
	return v.(*sync.Mutex)
}

type KVTxValue struct {
	DB           *KVDBValue
	Data         MapValue
	BaseRevision string
	Active       bool
}

const sagaMissingDBRevision = "missing"

func kvDataBytes(data MapValue) ([]byte, error) {
	obj := map[string]any{}
	for _, e := range data.Entries {
		k, ok := e.Key.(string)
		if !ok {
			return nil, fmt.Errorf("database keys must be text")
		}
		if _, dup := obj[k]; dup {
			return nil, fmt.Errorf("duplicate database key: %s", k)
		}
		v, err := valueToJSON(e.Value)
		if err != nil {
			return nil, err
		}
		obj[k] = v
	}
	return json.Marshal(obj)
}

func kvRevisionBytes(b []byte) string {
	h := sha256.Sum256(b)
	return hex.EncodeToString(h[:])
}

func loadKVDataUnlocked(path string) (MapValue, string, error) {
	b, err := os.ReadFile(path)
	if os.IsNotExist(err) {
		return MapValue{}, sagaMissingDBRevision, nil
	}
	if err != nil {
		return MapValue{}, "", err
	}
	v, err := decodeJSONSaga(string(b))
	if err != nil {
		return MapValue{}, "", fmt.Errorf("invalid database file: %w", err)
	}
	m, ok := v.(MapValue)
	if !ok {
		return MapValue{}, "", fmt.Errorf("database root must be a JSON object")
	}
	return m, kvRevisionBytes(b), nil
}

func persistKVDataUnlocked(path string, data MapValue) (string, error) {
	b, err := kvDataBytes(data)
	if err != nil {
		return "", err
	}
	dir := filepath.Dir(path)
	if dir != "." {
		if err = os.MkdirAll(dir, 0755); err != nil {
			return "", err
		}
	}
	tmp, err := os.CreateTemp(dir, "."+filepath.Base(path)+".tmp-*")
	if err != nil {
		return "", err
	}
	tmpName := tmp.Name()
	ok := false
	defer func() {
		_ = tmp.Close()
		if !ok {
			_ = os.Remove(tmpName)
		}
	}()
	if err = tmp.Chmod(0600); err != nil {
		return "", err
	}
	if _, err = tmp.Write(b); err != nil {
		return "", err
	}
	if err = tmp.Sync(); err != nil {
		return "", err
	}
	if err = tmp.Close(); err != nil {
		return "", err
	}
	if err = os.Rename(tmpName, path); err != nil {
		return "", err
	}
	ok = true
	return kvRevisionBytes(b), nil
}

func refreshKVDBLocked(db *KVDBValue) error {
	return withKVFileLock(db.Path, false, func() error {
		data, rev, err := loadKVDataUnlocked(db.Path)
		if err != nil {
			return err
		}
		db.Data = data
		db.Revision = rev
		return nil
	})
}

func mutateKVDBLocked(db *KVDBValue, mutate func(MapValue) MapValue) error {
	lock := sagaDBPathLock(db.Path)
	lock.Lock()
	defer lock.Unlock()
	return withKVFileLock(db.Path, true, func() error {
		current, _, err := loadKVDataUnlocked(db.Path)
		if err != nil {
			return err
		}
		next := mutate(current)
		rev, err := persistKVDataUnlocked(db.Path, next)
		if err != nil {
			return err
		}
		db.Data = snapshotMapValue(next)
		db.Revision = rev
		return nil
	})
}

func snapshotMapValue(m MapValue) MapValue {
	return snapshotValue(m, map[*Instance]*Instance{}).(MapValue)
}

func floatLike(v Value) (float64, error) {
	switch x := v.(type) {
	case Number:
		return numberToFloat(x)
	case FloatValue:
		return x.V, nil
	default:
		return 0, fmt.Errorf("number required")
	}
}

type Vec3 struct{ X, Y, Z float64 }
type Mesh3D struct {
	Vertices []Vec3
	Indices  []int
	Pos, Rot Vec3
	Scale    Vec3
}
type Camera3D struct {
	Pos, Target    Vec3
	FOV, Near, Far float64
}

func newCubeMesh(size float64) *Mesh3D {
	h := size / 2
	v := []Vec3{{-h, -h, -h}, {h, -h, -h}, {h, h, -h}, {-h, h, -h}, {-h, -h, h}, {h, -h, h}, {h, h, h}, {-h, h, h}}
	idx := []int{0, 1, 2, 0, 2, 3, 4, 6, 5, 4, 7, 6, 0, 4, 5, 0, 5, 1, 3, 2, 6, 3, 6, 7, 1, 5, 6, 1, 6, 2, 0, 3, 7, 0, 7, 4}
	return &Mesh3D{Vertices: v, Indices: idx, Scale: Vec3{1, 1, 1}}
}
func cross3(a, b Vec3) Vec3  { return Vec3{a.Y*b.Z - a.Z*b.Y, a.Z*b.X - a.X*b.Z, a.X*b.Y - a.Y*b.X} }
func dot3(a, b Vec3) float64 { return a.X*b.X + a.Y*b.Y + a.Z*b.Z }
func sub3(a, b Vec3) Vec3    { return Vec3{a.X - b.X, a.Y - b.Y, a.Z - b.Z} }
func norm3(a Vec3) Vec3 {
	l := math.Sqrt(dot3(a, a))
	if l == 0 {
		return Vec3{}
	}
	return Vec3{a.X / l, a.Y / l, a.Z / l}
}
func transformMeshVertex(v Vec3, m *Mesh3D) Vec3 {
	v = Vec3{v.X * m.Scale.X, v.Y * m.Scale.Y, v.Z * m.Scale.Z}
	sx, cx := math.Sincos(m.Rot.X)
	sy, cy := math.Sincos(m.Rot.Y)
	sz, cz := math.Sincos(m.Rot.Z)
	v = Vec3{v.X, v.Y*cx - v.Z*sx, v.Y*sx + v.Z*cx}
	v = Vec3{v.X*cy + v.Z*sy, v.Y, -v.X*sy + v.Z*cy}
	v = Vec3{v.X*cz - v.Y*sz, v.X*sz + v.Y*cz, v.Z}
	return Vec3{v.X + m.Pos.X, v.Y + m.Pos.Y, v.Z + m.Pos.Z}
}

type projected3 struct {
	x, y, z float64
	ok      bool
}

func project3(v Vec3, c *Camera3D, w, h int) projected3 {
	fwd := norm3(sub3(c.Target, c.Pos))
	right := norm3(cross3(fwd, Vec3{0, 1, 0}))
	if dot3(right, right) == 0 {
		right = Vec3{1, 0, 0}
	}
	up := cross3(right, fwd)
	r := sub3(v, c.Pos)
	x, y, z := dot3(r, right), dot3(r, up), dot3(r, fwd)
	if z <= c.Near || z >= c.Far {
		return projected3{ok: false}
	}
	f := float64(w) * 0.5 / math.Tan(c.FOV*math.Pi/360)
	return projected3{x: float64(w)/2 + x/z*f, y: float64(h)/2 - y/z*f, z: z, ok: true}
}
func edge3(ax, ay, bx, by, cx, cy float64) float64 { return (cx-ax)*(by-ay) - (cy-ay)*(bx-ax) }
func renderTriangle3D(f *PixelBuffer, a, b, c projected3, rgba [4]byte) bool {
	if !a.ok || !b.ok || !c.ok {
		return false
	}
	area := edge3(a.x, a.y, b.x, b.y, c.x, c.y)
	if math.Abs(area) < 1e-9 {
		return false
	}
	minx := maxInt0(int(math.Floor(math.Min(a.x, math.Min(b.x, c.x)))))
	maxx := minInt(f.W-1, int(math.Ceil(math.Max(a.x, math.Max(b.x, c.x)))))
	miny := maxInt0(int(math.Floor(math.Min(a.y, math.Min(b.y, c.y)))))
	maxy := minInt(f.H-1, int(math.Ceil(math.Max(a.y, math.Max(b.y, c.y)))))
	drawn := false
	for y := miny; y <= maxy; y++ {
		for x := minx; x <= maxx; x++ {
			px, py := float64(x)+.5, float64(y)+.5
			w0 := edge3(b.x, b.y, c.x, c.y, px, py) / area
			w1 := edge3(c.x, c.y, a.x, a.y, px, py) / area
			w2 := 1 - w0 - w1
			if w0 >= 0 && w1 >= 0 && w2 >= 0 || w0 <= 0 && w1 <= 0 && w2 <= 0 {
				invz := w0/a.z + w1/b.z + w2/c.z
				if invz <= 0 {
					continue
				}
				z := 1 / invz
				off := y*f.W + x
				if z < f.Depth[off] {
					f.Depth[off] = z
					f.setPixel(x, y, rgba[0], rgba[1], rgba[2], rgba[3])
					drawn = true
				}
			}
		}
	}
	return drawn
}
func maxInt0(v int) int {
	if v < 0 {
		return 0
	}
	return v
}

func loadOBJMesh(path string) (*Mesh3D, error) {
	b, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	m := &Mesh3D{Scale: Vec3{1, 1, 1}}
	lines := strings.Split(strings.ReplaceAll(string(b), "\r\n", "\n"), "\n")
	for lineNo, raw := range lines {
		line := strings.TrimSpace(raw)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		fields := strings.Fields(line)
		if len(fields) == 0 {
			continue
		}
		switch fields[0] {
		case "v":
			if len(fields) < 4 {
				return nil, fmt.Errorf("OBJ line %d: vertex requires x y z", lineNo+1)
			}
			x, e1 := strconv.ParseFloat(fields[1], 64)
			y, e2 := strconv.ParseFloat(fields[2], 64)
			z, e3 := strconv.ParseFloat(fields[3], 64)
			if e1 != nil || e2 != nil || e3 != nil {
				return nil, fmt.Errorf("OBJ line %d: invalid vertex", lineNo+1)
			}
			m.Vertices = append(m.Vertices, Vec3{x, y, z})
		case "f":
			if len(fields) < 4 {
				return nil, fmt.Errorf("OBJ line %d: face requires at least 3 vertices", lineNo+1)
			}
			face := make([]int, 0, len(fields)-1)
			for _, spec := range fields[1:] {
				part := strings.Split(spec, "/")[0]
				n, e := strconv.Atoi(part)
				if e != nil || n == 0 {
					return nil, fmt.Errorf("OBJ line %d: invalid face index", lineNo+1)
				}
				idx := n - 1
				if n < 0 {
					idx = len(m.Vertices) + n
				}
				if idx < 0 || idx >= len(m.Vertices) {
					return nil, fmt.Errorf("OBJ line %d: face index out of range", lineNo+1)
				}
				face = append(face, idx)
			}
			for j := 1; j+1 < len(face); j++ {
				m.Indices = append(m.Indices, face[0], face[j], face[j+1])
			}
		}
	}
	if len(m.Vertices) == 0 || len(m.Indices) == 0 {
		return nil, fmt.Errorf("OBJ contains no renderable triangles")
	}
	return m, nil
}

func (i *Interpreter) callPlatformExpansion(module, name string, args []Value, t Token) (Value, bool, error) {
	bad := func(msg string) (Value, bool, error) { return nil, true, i.rerr(t, "SAGA-R150", msg) }
	if module == "app" {
		switch name {
		case "host":
			if len(args) != 0 {
				return bad("app.host()")
			}
			return "native", true, nil
		case "capability":
			if len(args) != 1 {
				return bad("app.capability(name)")
			}
			q, ok := args[0].(string)
			if !ok {
				return bad("capability name must be text")
			}
			return containsText(sagaNativeAppCapabilities, q), true, nil
		case "capabilities":
			if len(args) != 0 {
				return bad("app.capabilities()")
			}
			out := make([]Value, len(sagaNativeAppCapabilities))
			for j, x := range sagaNativeAppCapabilities {
				out[j] = x
			}
			return out, true, nil
		case "operation_supported":
			if len(args) != 1 {
				return bad("app.operation_supported(name)")
			}
			q, ok := args[0].(string)
			if !ok {
				return bad("operation name must be text")
			}
			return containsText(sagaNativeAppOperations, q), true, nil
		case "operations":
			if len(args) != 0 {
				return bad("app.operations()")
			}
			out := make([]Value, len(sagaNativeAppOperations))
			for j, x := range sagaNativeAppOperations {
				out[j] = x
			}
			return out, true, nil
		case "invoke":
			if len(args) != 2 {
				return bad("app.invoke(operation,payload_json)")
			}
			op, ok := args[0].(string)
			payload, pok := args[1].(string)
			if !ok || !pok {
				return bad("operation/payload must be text")
			}
			v, e := nativeAppInvoke(op, payload)
			if e != nil {
				return ResultValue{OK: false, Value: e.Error()}, true, nil
			}
			return ResultValue{OK: true, Value: v}, true, nil
		case "invoke_async":
			return ResultValue{OK: false, Value: "async app host operations unavailable in native reference profile"}, true, nil
		case "cancel", "off":
			return ResultValue{OK: false, Value: "app async/event handle unavailable in native reference profile"}, true, nil
		case "on":
			return ResultValue{OK: false, Value: "app lifecycle events unavailable in native reference profile"}, true, nil
		}
	}
	if module == "web" {
		switch name {
		case "escape":
			if len(args) != 1 {
				return bad("web.escape(text)")
			}
			s, ok := args[0].(string)
			if !ok {
				return bad("text required")
			}
			return sagaHTMLEscape(s), true, nil
		case "element":
			if len(args) != 3 {
				return bad("web.element(tag,attrs,body)")
			}
			tag, tok := args[0].(string)
			attrs, aok := args[1].(MapValue)
			body, bok := args[2].(string)
			if !tok || !aok || !bok {
				return bad("tag/body text and map[text,text] attrs required")
			}
			s, e := sagaHTMLElement(tag, attrs, body)
			if e != nil {
				return bad(e.Error())
			}
			return s, true, nil
		case "document":
			if len(args) != 2 {
				return bad("web.document(title,body)")
			}
			title, tok := args[0].(string)
			body, bok := args[1].(string)
			if !tok || !bok {
				return bad("title/body text required")
			}
			return "<!doctype html><html><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>" + sagaHTMLEscape(title) + "</title></head><body>" + body + "</body></html>", true, nil
		case "route":
			if len(args) != 2 {
				return bad("web.route(pattern,path)")
			}
			p, pok := args[0].(string)
			q, qok := args[1].(string)
			if !pok || !qok {
				return bad("pattern/path text required")
			}
			m, ok := sagaRouteMatch(p, q)
			if !ok {
				return OptionValue{}, true, nil
			}
			return OptionValue{Present: true, Value: m}, true, nil
		case "query":
			if len(args) != 1 {
				return bad("web.query(query_text)")
			}
			s, ok := args[0].(string)
			if !ok {
				return bad("query text required")
			}
			vals, e := url.ParseQuery(s)
			if e != nil {
				return bad(e.Error())
			}
			m := MapValue{}
			keys := make([]string, 0, len(vals))
			for k := range vals {
				keys = append(keys, k)
			}
			sort.Strings(keys)
			for _, k := range keys {
				m = mapPut(m, k, vals.Get(k))
			}
			return m, true, nil
		case "url_encode":
			if len(args) != 1 {
				return bad("web.url_encode(text)")
			}
			s, ok := args[0].(string)
			if !ok {
				return bad("text required")
			}
			return url.QueryEscape(s), true, nil
		case "browser_available":
			if len(args) != 0 {
				return bad("web.browser_available()")
			}
			return false, true, nil
		case "capability":
			if len(args) != 1 {
				return bad("web.capability(name)")
			}
			return false, true, nil
		case "exists", "query_exists", "query_count", "title", "set_title", "set_text", "text", "set_html", "html", "append_html", "prepend_html", "create", "clear", "remove", "set_value", "value", "set_attr", "attr", "remove_attr", "set_style", "style", "add_class", "remove_class", "toggle_class", "has_class", "focus", "blur", "click", "scroll_into_view", "set_checked", "checked", "set_disabled", "disabled", "set_selected_index", "selected_index", "rect", "on_click", "on_event", "dispatch_event", "storage_set", "storage_get", "storage_remove", "storage_clear", "session_set", "session_get", "session_remove", "session_clear", "cookie_set", "cookie_get", "cookie_remove", "href", "path", "search", "hash", "set_hash", "navigate", "replace_url", "reload", "history_push", "history_replace", "history_back", "history_forward", "set_timeout", "set_interval", "animation_frame", "clear_timer", "online", "fetch", "abort_fetch", "ws_open", "ws_send", "ws_close", "ws_ready_state", "canvas_set_size", "canvas_clear", "canvas_fill_rect", "canvas_stroke_rect", "canvas_line", "canvas_circle", "canvas_text", "canvas_data_url", "media_play", "media_pause", "media_current_time", "media_set_current_time", "media_volume", "media_set_volume", "clipboard_write", "clipboard_read", "viewport_width", "viewport_height", "pixel_ratio", "language", "user_agent", "visibility", "geolocate", "request_fullscreen", "exit_fullscreen", "fullscreen_active":
			return ResultValue{OK: false, Value: "browser host unavailable in native profile"}, true, nil
		}
	}
	if module == "http" {
		switch name {
		case "listen":
			if len(args) != 2 {
				return bad("http.listen(host,port)")
			}
			host, ok := args[0].(string)
			port, e := numberToInt(args[1])
			if !ok || e != nil {
				return bad("host text and port int required")
			}
			s, e := newSagaHTTPServer(host, port)
			if e != nil {
				return ResultValue{OK: false, Value: e.Error()}, true, nil
			}
			return ResultValue{OK: true, Value: s}, true, nil
		case "server_port":
			if len(args) != 1 {
				return bad("http.server_port(server)")
			}
			s, ok := args[0].(*HTTPServerValue)
			if !ok {
				return bad("server required")
			}
			return numberFromInt64(int64(sagaServerPort(s))), true, nil
		case "accept":
			if len(args) != 1 {
				return bad("http.accept(server)")
			}
			s, ok := args[0].(*HTTPServerValue)
			if !ok {
				return bad("server required")
			}
			if s.closed.Load() {
				return ResultValue{OK: false, Value: "server is closed"}, true, nil
			}
			select {
			case req := <-s.Requests:
				return ResultValue{OK: true, Value: req}, true, nil
			case <-s.Done:
				return ResultValue{OK: false, Value: "server is closed"}, true, nil
			}
		case "request_method", "request_path", "request_body":
			if len(args) != 1 {
				return bad("http request accessor requires request")
			}
			r, ok := args[0].(*HTTPRequestValue)
			if !ok {
				return bad("request required")
			}
			if name == "request_method" {
				return r.Method, true, nil
			}
			if name == "request_path" {
				return r.Path, true, nil
			}
			return r.Body, true, nil
		case "request_header", "request_query":
			if len(args) != 2 {
				return bad("http request accessor requires request,name")
			}
			r, ok := args[0].(*HTTPRequestValue)
			key, kok := args[1].(string)
			if !ok || !kok {
				return bad("request and text name required")
			}
			var s string
			if name == "request_header" {
				s = r.Header.Get(key)
			} else {
				s = r.Query.Get(key)
			}
			if s == "" {
				return OptionValue{}, true, nil
			}
			return OptionValue{Present: true, Value: s}, true, nil
		case "respond":
			if len(args) != 4 {
				return bad("http.respond(request,status,content_type,body)")
			}
			r, ok := args[0].(*HTTPRequestValue)
			status, e := numberToInt(args[1])
			ct, cok := args[2].(string)
			body, bok := args[3].(string)
			if !ok || e != nil || !cok || !bok || status < 100 || status > 599 {
				return bad("request,status,content_type,body required")
			}
			if strings.ContainsAny(ct, "\r\n") {
				return bad("content_type must not contain CR/LF")
			}
			if !r.done.CompareAndSwap(false, true) {
				return ResultValue{OK: false, Value: "request already responded"}, true, nil
			}
			ack := make(chan error, 1)
			resp := sagaHTTPResponse{Status: status, ContentType: ct, Body: body, Ack: ack}
			select {
			case r.response <- resp:
			case <-r.ctxDone:
				return ResultValue{OK: false, Value: "request closed before response"}, true, nil
			}
			e, acknowledged := sagaAwaitHTTPResponseAck(ack, r.ctxDone)
			if !acknowledged {
				return ResultValue{OK: false, Value: "request closed while writing response"}, true, nil
			}
			if e != nil {
				return ResultValue{OK: false, Value: e.Error()}, true, nil
			}
			return ResultValue{OK: true, Value: nil}, true, nil
		case "server_close":
			if len(args) != 1 {
				return bad("http.server_close(server)")
			}
			s, ok := args[0].(*HTTPServerValue)
			if !ok {
				return bad("server required")
			}
			s.markClosed()
			e := s.Server.Close()
			if e != nil && e != http.ErrServerClosed {
				return nil, true, e
			}
			return nil, true, nil
		}
	}
	if module == "db" {
		switch name {
		case "put":
			if len(args) != 3 {
				return bad("db.put(db,key,value)")
			}
			db, ok := args[0].(*KVDBValue)
			key, kok := args[1].(string)
			if !ok || !kok {
				return bad("db and text key required")
			}
			db.Mu.Lock()
			defer db.Mu.Unlock()
			if db.Closed {
				return ResultValue{OK: false, Value: "database is closed"}, true, nil
			}
			value := snapshotValue(args[2], map[*Instance]*Instance{})
			if e := mutateKVDBLocked(db, func(current MapValue) MapValue { return mapPut(current, key, value) }); e != nil {
				return ResultValue{OK: false, Value: e.Error()}, true, nil
			}
			return ResultValue{OK: true, Value: nil}, true, nil
		case "get":
			if len(args) != 2 {
				return bad("db.get(db,key)")
			}
			db, ok := args[0].(*KVDBValue)
			key, kok := args[1].(string)
			if !ok || !kok {
				return bad("db and text key required")
			}
			db.Mu.Lock()
			defer db.Mu.Unlock()
			if db.Closed {
				return nil, true, i.rerr(t, "SAGA-R160", "database is closed")
			}
			lock := sagaDBPathLock(db.Path)
			lock.Lock()
			defer lock.Unlock()
			if e := refreshKVDBLocked(db); e != nil {
				return nil, true, i.rerr(t, "SAGA-R160", e.Error())
			}
			v, found := mapLookup(db.Data, key)
			if !found {
				return OptionValue{}, true, nil
			}
			return OptionValue{Present: true, Value: snapshotValue(v, map[*Instance]*Instance{})}, true, nil
		case "delete":
			if len(args) != 2 {
				return bad("db.delete(db,key)")
			}
			db, ok := args[0].(*KVDBValue)
			key, kok := args[1].(string)
			if !ok || !kok {
				return bad("db and text key required")
			}
			db.Mu.Lock()
			defer db.Mu.Unlock()
			if db.Closed {
				return ResultValue{OK: false, Value: "database is closed"}, true, nil
			}
			if e := mutateKVDBLocked(db, func(current MapValue) MapValue { return mapRemove(current, key) }); e != nil {
				return ResultValue{OK: false, Value: e.Error()}, true, nil
			}
			return ResultValue{OK: true, Value: nil}, true, nil
		case "keys":
			if len(args) != 1 {
				return bad("db.keys(db)")
			}
			db, ok := args[0].(*KVDBValue)
			if !ok {
				return bad("db required")
			}
			db.Mu.Lock()
			defer db.Mu.Unlock()
			if db.Closed {
				return nil, true, i.rerr(t, "SAGA-R160", "database is closed")
			}
			lock := sagaDBPathLock(db.Path)
			lock.Lock()
			defer lock.Unlock()
			if e := refreshKVDBLocked(db); e != nil {
				return nil, true, i.rerr(t, "SAGA-R160", e.Error())
			}
			ks := make([]string, 0, len(db.Data.Entries))
			for _, e := range db.Data.Entries {
				ks = append(ks, e.Key.(string))
			}
			sort.Strings(ks)
			out := make([]Value, len(ks))
			for j, k := range ks {
				out[j] = k
			}
			return out, true, nil
		case "begin":
			if len(args) != 1 {
				return bad("db.begin(db)")
			}
			db, ok := args[0].(*KVDBValue)
			if !ok {
				return bad("db required")
			}
			db.Mu.Lock()
			defer db.Mu.Unlock()
			if db.Closed {
				return ResultValue{OK: false, Value: "database is closed"}, true, nil
			}
			lock := sagaDBPathLock(db.Path)
			lock.Lock()
			defer lock.Unlock()
			if e := refreshKVDBLocked(db); e != nil {
				return ResultValue{OK: false, Value: e.Error()}, true, nil
			}
			return ResultValue{OK: true, Value: &KVTxValue{DB: db, Data: snapshotMapValue(db.Data), BaseRevision: db.Revision, Active: true}}, true, nil
		case "tx_put":
			if len(args) != 3 {
				return bad("db.tx_put(tx,key,value)")
			}
			tx, ok := args[0].(*KVTxValue)
			key, kok := args[1].(string)
			if !ok || !kok || !tx.Active {
				return bad("active transaction and text key required")
			}
			tx.Data = mapPut(tx.Data, key, snapshotValue(args[2], map[*Instance]*Instance{}))
			return nil, true, nil
		case "tx_get":
			if len(args) != 2 {
				return bad("db.tx_get(tx,key)")
			}
			tx, ok := args[0].(*KVTxValue)
			key, kok := args[1].(string)
			if !ok || !kok || !tx.Active {
				return bad("active transaction and text key required")
			}
			v, found := mapLookup(tx.Data, key)
			if !found {
				return OptionValue{}, true, nil
			}
			return OptionValue{Present: true, Value: snapshotValue(v, map[*Instance]*Instance{})}, true, nil
		case "tx_delete":
			if len(args) != 2 {
				return bad("db.tx_delete(tx,key)")
			}
			tx, ok := args[0].(*KVTxValue)
			key, kok := args[1].(string)
			if !ok || !kok || !tx.Active {
				return bad("active transaction and text key required")
			}
			tx.Data = mapRemove(tx.Data, key)
			return nil, true, nil
		case "commit":
			if len(args) != 1 {
				return bad("db.commit(tx)")
			}
			tx, ok := args[0].(*KVTxValue)
			if !ok || !tx.Active {
				return bad("active transaction required")
			}
			db := tx.DB
			db.Mu.Lock()
			defer db.Mu.Unlock()
			if db.Closed {
				return ResultValue{OK: false, Value: "database is closed"}, true, nil
			}
			lock := sagaDBPathLock(db.Path)
			lock.Lock()
			defer lock.Unlock()
			var conflict bool
			e := withKVFileLock(db.Path, true, func() error {
				current, rev, err := loadKVDataUnlocked(db.Path)
				if err != nil {
					return err
				}
				if rev != tx.BaseRevision {
					db.Data = current
					db.Revision = rev
					conflict = true
					return nil
				}
				newRev, err := persistKVDataUnlocked(db.Path, tx.Data)
				if err != nil {
					return err
				}
				db.Data = snapshotMapValue(tx.Data)
				db.Revision = newRev
				return nil
			})
			if e != nil {
				return ResultValue{OK: false, Value: e.Error()}, true, nil
			}
			if conflict {
				return ResultValue{OK: false, Value: "transaction conflict"}, true, nil
			}
			tx.Active = false
			return ResultValue{OK: true, Value: nil}, true, nil
		case "rollback":
			if len(args) != 1 {
				return bad("db.rollback(tx)")
			}
			tx, ok := args[0].(*KVTxValue)
			if !ok {
				return bad("transaction required")
			}
			tx.Active = false
			return nil, true, nil
		}
	}

	if module == "game" {
		switch name {
		case "mesh3d_cube":
			if len(args) != 1 {
				return bad("game.mesh3d_cube(size)")
			}
			s, e := floatLike(args[0])
			if e != nil || s <= 0 {
				return bad("positive size required")
			}
			return newCubeMesh(s), true, nil
		case "mesh3d":
			if len(args) != 2 {
				return bad("game.mesh3d(vertices,indices)")
			}
			vs, vok := args[0].([]Value)
			is, iok := args[1].([]Value)
			if !vok || !iok || len(vs)%3 != 0 || len(is)%3 != 0 {
				return bad("flat vertex triples and triangle indices required")
			}
			m := &Mesh3D{Scale: Vec3{1, 1, 1}}
			for j := 0; j < len(vs); j += 3 {
				x, e1 := floatLike(vs[j])
				y, e2 := floatLike(vs[j+1])
				z, e3 := floatLike(vs[j+2])
				if e1 != nil || e2 != nil || e3 != nil {
					return bad("mesh vertices must be numeric")
				}
				m.Vertices = append(m.Vertices, Vec3{x, y, z})
			}
			for _, v := range is {
				k, e := numberToInt(v)
				if e != nil || k < 0 || k >= len(m.Vertices) {
					return bad("mesh index out of range")
				}
				m.Indices = append(m.Indices, k)
			}
			return m, true, nil
		case "mesh3d_obj":
			if len(args) != 1 {
				return bad("game.mesh3d_obj(path)")
			}
			path, ok := args[0].(string)
			if !ok {
				return bad("path text required")
			}
			m, e := loadOBJMesh(path)
			if e != nil {
				return ResultValue{OK: false, Value: e.Error()}, true, nil
			}
			return ResultValue{OK: true, Value: m}, true, nil
		case "mesh3d_translate", "mesh3d_rotate", "mesh3d_scale":
			if len(args) != 4 {
				return bad("mesh transform requires mesh,x,y,z")
			}
			m, ok := args[0].(*Mesh3D)
			if !ok {
				return bad("mesh required")
			}
			x, e1 := floatLike(args[1])
			y, e2 := floatLike(args[2])
			z, e3 := floatLike(args[3])
			if e1 != nil || e2 != nil || e3 != nil {
				return bad("numeric transform required")
			}
			if name == "mesh3d_translate" {
				m.Pos = Vec3{x, y, z}
			} else if name == "mesh3d_rotate" {
				m.Rot = Vec3{x, y, z}
			} else {
				if x == 0 || y == 0 || z == 0 {
					return bad("scale components must be non-zero")
				}
				m.Scale = Vec3{x, y, z}
			}
			return nil, true, nil
		case "camera3d":
			if len(args) != 9 {
				return bad("game.camera3d(px,py,pz,tx,ty,tz,fov,near,far)")
			}
			v := make([]float64, 9)
			for j := range v {
				q, e := floatLike(args[j])
				if e != nil {
					return bad(e.Error())
				}
				v[j] = q
			}
			if v[6] <= 1 || v[6] >= 179 || v[7] <= 0 || v[8] <= v[7] {
				return bad("camera requires 1<fov<179 and 0<near<far")
			}
			return &Camera3D{Pos: Vec3{v[0], v[1], v[2]}, Target: Vec3{v[3], v[4], v[5]}, FOV: v[6], Near: v[7], Far: v[8]}, true, nil
		case "draw_mesh3d":
			if len(args) != 7 {
				return bad("game.draw_mesh3d(framebuffer,mesh,camera,r,g,b,a)")
			}
			f, fok := args[0].(*PixelBuffer)
			m, mok := args[1].(*Mesh3D)
			c, cok := args[2].(*Camera3D)
			if !fok || !mok || !cok {
				return bad("framebuffer,mesh,camera required")
			}
			r, g, b, a, e := intColor(args, 3)
			if e != nil {
				return bad(e.Error())
			}
			col := [4]byte{r, g, b, a}
			pv := make([]projected3, len(m.Vertices))
			for j, v := range m.Vertices {
				pv[j] = project3(transformMeshVertex(v, m), c, f.W, f.H)
			}
			count := 0
			for j := 0; j+2 < len(m.Indices); j += 3 {
				a0, b0, c0 := m.Indices[j], m.Indices[j+1], m.Indices[j+2]
				if renderTriangle3D(f, pv[a0], pv[b0], pv[c0], col) {
					count++
				}
			}
			return numberFromInt64(int64(count)), true, nil
		case "draw_wireframe3d":
			if len(args) != 7 {
				return bad("game.draw_wireframe3d(framebuffer,mesh,camera,r,g,b,a)")
			}
			f, fok := args[0].(*PixelBuffer)
			m, mok := args[1].(*Mesh3D)
			c, cok := args[2].(*Camera3D)
			if !fok || !mok || !cok {
				return bad("framebuffer,mesh,camera required")
			}
			r, g, b, a, e := intColor(args, 3)
			if e != nil {
				return bad(e.Error())
			}
			pv := make([]projected3, len(m.Vertices))
			for j, v := range m.Vertices {
				pv[j] = project3(transformMeshVertex(v, m), c, f.W, f.H)
			}
			count := 0
			for j := 0; j+2 < len(m.Indices); j += 3 {
				ids := []int{m.Indices[j], m.Indices[j+1], m.Indices[j+2]}
				for k := 0; k < 3; k++ {
					u, v := pv[ids[k]], pv[ids[(k+1)%3]]
					if u.ok && v.ok {
						f.line(int(math.Round(u.x)), int(math.Round(u.y)), int(math.Round(v.x)), int(math.Round(v.y)), r, g, b, a)
						count++
					}
				}
			}
			return numberFromInt64(int64(count)), true, nil
		}
	}
	return nil, false, nil
}
