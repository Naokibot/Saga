package main

import (
	"bytes"
	"encoding/binary"
	"fmt"
	"image"
	"image/jpeg"
	"image/png"
	"math"
	"math/big"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
)

const (
	gameMaxTextureBytes     int64 = 128 << 20
	gameMaxTextureDimension       = 16384
	gameMaxTexturePixels          = 64 * 1024 * 1024
	gameMaxAudioBytes       int64 = 256 << 20
)

func readGameAssetLimited(path string, maxBytes int64) ([]byte, error) {
	info, err := os.Stat(path)
	if err != nil {
		return nil, err
	}
	if info.Size() < 0 || info.Size() > maxBytes {
		return nil, fmt.Errorf("asset exceeds implementation limit (%d bytes)", maxBytes)
	}
	b, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	if int64(len(b)) > maxBytes {
		return nil, fmt.Errorf("asset exceeds implementation limit (%d bytes)", maxBytes)
	}
	return b, nil
}

// PixelBuffer is the canonical Saga Game RGBA8 framebuffer.
// Pixels are stored row-major, top-left origin, straight alpha, sRGB byte values.
type PixelBuffer struct {
	W, H  int
	Pix   []byte
	Depth []float64
}

func newPixelBuffer(w, h int) (*PixelBuffer, error) {
	if w <= 0 || h <= 0 {
		return nil, fmt.Errorf("framebuffer width/height must be positive")
	}
	if w > (int(^uint(0)>>1)/4)/h {
		return nil, fmt.Errorf("framebuffer dimensions overflow host address space")
	}
	f := &PixelBuffer{W: w, H: h, Pix: make([]byte, w*h*4), Depth: make([]float64, w*h)}
	f.resetDepth()
	return f, nil
}

func clampByte(v int) byte {
	if v < 0 {
		return 0
	}
	if v > 255 {
		return 255
	}
	return byte(v)
}

func (f *PixelBuffer) offset(x, y int) int {
	if x < 0 || y < 0 || x >= f.W || y >= f.H {
		return -1
	}
	return (y*f.W + x) * 4
}

func (f *PixelBuffer) setPixel(x, y int, r, g, b, a byte) {
	off := f.offset(x, y)
	if off < 0 {
		return
	}
	if a == 255 {
		f.Pix[off+0], f.Pix[off+1], f.Pix[off+2], f.Pix[off+3] = r, g, b, a
		return
	}
	if a == 0 {
		return
	}
	// Straight-alpha source-over, rounded deterministically in integer space.
	da := int(f.Pix[off+3])
	sa := int(a)
	outA := sa + (da*(255-sa)+127)/255
	if outA == 0 {
		f.Pix[off+0], f.Pix[off+1], f.Pix[off+2], f.Pix[off+3] = 0, 0, 0, 0
		return
	}
	blend := func(sc byte, dc byte) byte {
		num := int(sc)*sa*255 + int(dc)*da*(255-sa)
		den := outA * 255
		return byte((num + den/2) / den)
	}
	f.Pix[off+0] = blend(r, f.Pix[off+0])
	f.Pix[off+1] = blend(g, f.Pix[off+1])
	f.Pix[off+2] = blend(b, f.Pix[off+2])
	f.Pix[off+3] = byte(outA)
}

func (f *PixelBuffer) resetDepth() {
	if len(f.Depth) != f.W*f.H {
		f.Depth = make([]float64, f.W*f.H)
	}
	for j := range f.Depth {
		f.Depth[j] = math.Inf(1)
	}
}

func (f *PixelBuffer) clearRGBA(r, g, b, a byte) {
	for p := 0; p < len(f.Pix); p += 4 {
		f.Pix[p+0], f.Pix[p+1], f.Pix[p+2], f.Pix[p+3] = r, g, b, a
	}
	f.resetDepth()
}

func (f *PixelBuffer) fillRect(x, y, w, h int, r, g, b, a byte) {
	if w <= 0 || h <= 0 {
		return
	}
	for yy := y; yy < y+h; yy++ {
		for xx := x; xx < x+w; xx++ {
			f.setPixel(xx, yy, r, g, b, a)
		}
	}
}

func (f *PixelBuffer) line(x0, y0, x1, y1 int, r, g, b, a byte) {
	dx := absInt(x1 - x0)
	sx := -1
	if x0 < x1 {
		sx = 1
	}
	dy := -absInt(y1 - y0)
	sy := -1
	if y0 < y1 {
		sy = 1
	}
	err := dx + dy
	for {
		f.setPixel(x0, y0, r, g, b, a)
		if x0 == x1 && y0 == y1 {
			break
		}
		e2 := 2 * err
		if e2 >= dy {
			err += dy
			x0 += sx
		}
		if e2 <= dx {
			err += dx
			y0 += sy
		}
	}
}

func (f *PixelBuffer) circle(cx, cy, radius int, r, g, b, a byte) {
	if radius < 0 {
		return
	}
	x, y := radius, 0
	err := 1 - x
	for x >= y {
		pts := [][2]int{{cx + x, cy + y}, {cx + y, cy + x}, {cx - y, cy + x}, {cx - x, cy + y}, {cx - x, cy - y}, {cx - y, cy - x}, {cx + y, cy - x}, {cx + x, cy - y}}
		for _, p := range pts {
			f.setPixel(p[0], p[1], r, g, b, a)
		}
		y++
		if err < 0 {
			err += 2*y + 1
		} else {
			x--
			err += 2*(y-x) + 1
		}
	}
}

type GameTexture struct {
	W, H   int
	Pix    []byte
	Source string
}

func textureFromImage(img image.Image, source string) *GameTexture {
	b := img.Bounds()
	w, h := b.Dx(), b.Dy()
	pix := make([]byte, w*h*4)
	p := 0
	for y := b.Min.Y; y < b.Max.Y; y++ {
		for x := b.Min.X; x < b.Max.X; x++ {
			rr, gg, bb, aa := img.At(x, y).RGBA()
			pix[p+0], pix[p+1], pix[p+2], pix[p+3] = byte(rr>>8), byte(gg>>8), byte(bb>>8), byte(aa>>8)
			p += 4
		}
	}
	return &GameTexture{W: w, H: h, Pix: pix, Source: source}
}

func loadGameTexture(path string) (*GameTexture, error) {
	b, err := readGameAssetLimited(path, gameMaxTextureBytes)
	if err != nil {
		return nil, err
	}
	ext := strings.ToLower(filepath.Ext(path))
	var cfg image.Config
	switch ext {
	case ".png":
		cfg, err = png.DecodeConfig(bytes.NewReader(b))
	case ".jpg", ".jpeg":
		cfg, err = jpeg.DecodeConfig(bytes.NewReader(b))
	default:
		return nil, fmt.Errorf("unsupported texture format %q; PNG or JPEG required", ext)
	}
	if err != nil {
		return nil, fmt.Errorf("decode texture header: %w", err)
	}
	if cfg.Width <= 0 || cfg.Height <= 0 || cfg.Width > gameMaxTextureDimension || cfg.Height > gameMaxTextureDimension || cfg.Width > gameMaxTexturePixels/cfg.Height {
		return nil, fmt.Errorf("texture dimensions exceed implementation limit")
	}
	var img image.Image
	switch ext {
	case ".png":
		img, err = png.Decode(bytes.NewReader(b))
	case ".jpg", ".jpeg":
		img, err = jpeg.Decode(bytes.NewReader(b))
	}
	if err != nil {
		return nil, fmt.Errorf("decode texture: %w", err)
	}
	return textureFromImage(img, path), nil
}

func drawTexture(dst *PixelBuffer, tex *GameTexture, sx, sy, sw, sh, dx, dy, dw, dh int) {
	if tex == nil || dst == nil || sw <= 0 || sh <= 0 || dw <= 0 || dh <= 0 {
		return
	}
	for yy := 0; yy < dh; yy++ {
		ty := sy + (yy*sh)/dh
		if ty < 0 || ty >= tex.H {
			continue
		}
		for xx := 0; xx < dw; xx++ {
			tx := sx + (xx*sw)/dw
			if tx < 0 || tx >= tex.W {
				continue
			}
			so := (ty*tex.W + tx) * 4
			dst.setPixel(dx+xx, dy+yy, tex.Pix[so], tex.Pix[so+1], tex.Pix[so+2], tex.Pix[so+3])
		}
	}
}

type SpriteAnimation struct {
	Texture                *GameTexture
	FrameW, FrameH, Frames int
	FPS                    float64
}

func (a *SpriteAnimation) frameIndex(elapsedMS int64) int {
	if a == nil || a.Frames <= 0 || a.FPS <= 0 {
		return 0
	}
	n := int(math.Floor(float64(elapsedMS) * a.FPS / 1000.0))
	if n < 0 {
		n = 0
	}
	return n % a.Frames
}

type GameCamera struct{ X, Y, Zoom float64 }

type GameTilemap struct {
	W, H, TileW, TileH int
	Tiles              []int
}

func newTilemap(w, h, tw, th int) (*GameTilemap, error) {
	if w <= 0 || h <= 0 || tw <= 0 || th <= 0 {
		return nil, fmt.Errorf("tilemap dimensions must be positive")
	}
	if w > int(^uint(0)>>1)/h {
		return nil, fmt.Errorf("tilemap dimensions overflow")
	}
	return &GameTilemap{W: w, H: h, TileW: tw, TileH: th, Tiles: make([]int, w*h)}, nil
}
func (m *GameTilemap) set(x, y, v int) {
	if x >= 0 && y >= 0 && x < m.W && y < m.H {
		m.Tiles[y*m.W+x] = v
	}
}
func (m *GameTilemap) get(x, y int) (int, bool) {
	if x < 0 || y < 0 || x >= m.W || y >= m.H {
		return 0, false
	}
	return m.Tiles[y*m.W+x], true
}
func drawTilemap(dst *PixelBuffer, m *GameTilemap, atlas *GameTexture, cam *GameCamera, columns int) {
	if dst == nil || m == nil || atlas == nil || columns <= 0 {
		return
	}
	zoom := 1.0
	cx, cy := 0.0, 0.0
	if cam != nil {
		zoom = cam.Zoom
		cx = cam.X
		cy = cam.Y
	}
	if zoom <= 0 {
		return
	}
	dw := int(math.Round(float64(m.TileW) * zoom))
	dh := int(math.Round(float64(m.TileH) * zoom))
	if dw <= 0 || dh <= 0 {
		return
	}
	for y := 0; y < m.H; y++ {
		for x := 0; x < m.W; x++ {
			id := m.Tiles[y*m.W+x]
			if id < 0 {
				continue
			}
			sx := (id % columns) * m.TileW
			sy := (id / columns) * m.TileH
			dx := int(math.Round((float64(x*m.TileW) - cx) * zoom))
			dy := int(math.Round((float64(y*m.TileH) - cy) * zoom))
			drawTexture(dst, atlas, sx, sy, m.TileW, m.TileH, dx, dy, dw, dh)
		}
	}
}

type GameParticle struct {
	X, Y, VX, VY, Life float64
	R, G, B, A         byte
	Size               int
}
type ParticleSystem struct{ Particles []GameParticle }

func (p *ParticleSystem) emit(x, y, vx, vy, life float64, r, g, b, a byte, size int) {
	if life > 0 && size > 0 {
		p.Particles = append(p.Particles, GameParticle{X: x, Y: y, VX: vx, VY: vy, Life: life, R: r, G: g, B: b, A: a, Size: size})
	}
}
func (p *ParticleSystem) update(dt, gravityY float64) {
	if dt < 0 {
		return
	}
	out := p.Particles[:0]
	for _, q := range p.Particles {
		q.VY += gravityY * dt
		q.X += q.VX * dt
		q.Y += q.VY * dt
		q.Life -= dt
		if q.Life > 0 {
			out = append(out, q)
		}
	}
	p.Particles = out
}
func (p *ParticleSystem) draw(dst *PixelBuffer, cam *GameCamera) {
	zoom := 1.0
	cx, cy := 0.0, 0.0
	if cam != nil {
		zoom = cam.Zoom
		cx = cam.X
		cy = cam.Y
	}
	if zoom <= 0 {
		return
	}
	for _, q := range p.Particles {
		x := int(math.Round((q.X - cx) * zoom))
		y := int(math.Round((q.Y - cy) * zoom))
		s := int(math.Max(1, math.Round(float64(q.Size)*zoom)))
		dst.fillRect(x, y, s, s, q.R, q.G, q.B, q.A)
	}
}

type PhysicsBody struct {
	X, Y, W, H, VX, VY, FX, FY, Mass, Restitution float64
	Dynamic                                       bool
}
type PhysicsWorld struct {
	GravityX, GravityY float64
	Bodies             []*PhysicsBody
}

func (w *PhysicsWorld) addBody(x, y, bw, bh, mass float64, dynamic bool) (*PhysicsBody, error) {
	if bw <= 0 || bh <= 0 {
		return nil, fmt.Errorf("body dimensions must be positive")
	}
	if mass <= 0 {
		mass = 1
	}
	b := &PhysicsBody{X: x, Y: y, W: bw, H: bh, Mass: mass, Restitution: 0, Dynamic: dynamic}
	w.Bodies = append(w.Bodies, b)
	return b, nil
}
func overlapF(a, b *PhysicsBody) bool {
	return a.X < b.X+b.W && b.X < a.X+a.W && a.Y < b.Y+b.H && b.Y < a.Y+a.H
}
func bodyInvMass(b *PhysicsBody) float64 {
	if b == nil || !b.Dynamic || b.Mass <= 0 {
		return 0
	}
	return 1 / b.Mass
}
func resolveAABB(a, b *PhysicsBody) {
	if !overlapF(a, b) {
		return
	}
	acx, acy := a.X+a.W/2, a.Y+a.H/2
	bcx, bcy := b.X+b.W/2, b.Y+b.H/2
	overlapX := math.Min(a.X+a.W, b.X+b.W) - math.Max(a.X, b.X)
	overlapY := math.Min(a.Y+a.H, b.Y+b.H) - math.Max(a.Y, b.Y)
	nx, ny, penetration := 0.0, 0.0, overlapX
	if overlapX < overlapY {
		if acx < bcx {
			nx = 1
		} else {
			nx = -1
		}
	} else {
		penetration = overlapY
		if acy < bcy {
			ny = 1
		} else {
			ny = -1
		}
	}
	invA, invB := bodyInvMass(a), bodyInvMass(b)
	invSum := invA + invB
	if invSum == 0 {
		return
	}
	// Positional correction prevents persistent sinking while retaining a tiny slop.
	const slop = 0.0005
	const percent = 0.85
	corr := math.Max(penetration-slop, 0) * percent / invSum
	a.X -= nx * corr * invA
	a.Y -= ny * corr * invA
	b.X += nx * corr * invB
	b.Y += ny * corr * invB
	// Normal impulse with coefficient of restitution.
	rvx, rvy := b.VX-a.VX, b.VY-a.VY
	velNormal := rvx*nx + rvy*ny
	if velNormal > 0 {
		return
	}
	e := math.Min(a.Restitution, b.Restitution)
	if e < 0 {
		e = 0
	}
	if e > 1 {
		e = 1
	}
	j := -(1 + e) * velNormal / invSum
	ix, iy := j*nx, j*ny
	if a.Dynamic {
		a.VX -= ix * invA
		a.VY -= iy * invA
	}
	if b.Dynamic {
		b.VX += ix * invB
		b.VY += iy * invB
	}
}
func (w *PhysicsWorld) step(dt float64) {
	if dt <= 0 {
		return
	}
	if dt > 0.25 {
		dt = 0.25
	}
	for _, b := range w.Bodies {
		if b.Dynamic {
			inv := bodyInvMass(b)
			b.VX += (w.GravityX + b.FX*inv) * dt
			b.VY += (w.GravityY + b.FY*inv) * dt
			b.X += b.VX * dt
			b.Y += b.VY * dt
			b.FX, b.FY = 0, 0
		}
	}
	// A small fixed iteration count improves stacking without nondeterministic convergence tests.
	for iter := 0; iter < 4; iter++ {
		for x := 0; x < len(w.Bodies); x++ {
			for y := x + 1; y < len(w.Bodies); y++ {
				resolveAABB(w.Bodies[x], w.Bodies[y])
			}
		}
	}
}

type AudioClip struct {
	SampleRate, Channels int
	PCM16                []byte
	Source               string
}

func loadWAV(path string) (*AudioClip, error) {
	b, err := readGameAssetLimited(path, gameMaxAudioBytes)
	if err != nil {
		return nil, err
	}
	return decodeWAV(b, path)
}
func decodeWAV(b []byte, source string) (*AudioClip, error) {
	if len(b) < 12 || string(b[:4]) != "RIFF" || string(b[8:12]) != "WAVE" {
		return nil, fmt.Errorf("not a RIFF/WAVE file")
	}
	var format, channels, bits int
	var rate int
	var data []byte
	for off := 12; off+8 <= len(b); {
		id := string(b[off : off+4])
		n := int(binary.LittleEndian.Uint32(b[off+4 : off+8]))
		off += 8
		if n < 0 || off+n > len(b) {
			return nil, fmt.Errorf("truncated WAV chunk")
		}
		chunk := b[off : off+n]
		if id == "fmt " {
			if len(chunk) < 16 {
				return nil, fmt.Errorf("short WAV fmt")
			}
			format = int(binary.LittleEndian.Uint16(chunk[0:2]))
			channels = int(binary.LittleEndian.Uint16(chunk[2:4]))
			rate = int(binary.LittleEndian.Uint32(chunk[4:8]))
			bits = int(binary.LittleEndian.Uint16(chunk[14:16]))
		}
		if id == "data" {
			data = append([]byte(nil), chunk...)
		}
		off += n
		if n&1 == 1 {
			off++
		}
	}
	if format != 1 {
		return nil, fmt.Errorf("WAV encoding %d unsupported; PCM required", format)
	}
	if channels < 1 || channels > 2 {
		return nil, fmt.Errorf("WAV channels must be 1 or 2")
	}
	if rate <= 0 {
		return nil, fmt.Errorf("invalid WAV sample rate")
	}
	if len(data) == 0 {
		return nil, fmt.Errorf("WAV has no data")
	}
	pcm := make([]byte, 0, len(data)*2)
	switch bits {
	case 16:
		pcm = append(pcm, data...)
	case 8:
		pcm = make([]byte, len(data)*2)
		for i, v := range data {
			s := int16((int(v) - 128) << 8)
			binary.LittleEndian.PutUint16(pcm[i*2:], uint16(s))
		}
	default:
		return nil, fmt.Errorf("WAV bits per sample %d unsupported; 8 or 16 required", bits)
	}
	return &AudioClip{SampleRate: rate, Channels: channels, PCM16: pcm, Source: source}, nil
}

type AssetManager struct {
	mu       sync.RWMutex
	Textures map[string]*GameTexture
	Audio    map[string]*AudioClip
}

func newAssetManager() *AssetManager {
	return &AssetManager{Textures: map[string]*GameTexture{}, Audio: map[string]*AudioClip{}}
}
func (a *AssetManager) texture(path string) (*GameTexture, error) {
	a.mu.RLock()
	t := a.Textures[path]
	a.mu.RUnlock()
	if t != nil {
		return t, nil
	}
	q, e := loadGameTexture(path)
	if e != nil {
		return nil, e
	}
	a.mu.Lock()
	if old := a.Textures[path]; old != nil {
		q = old
	} else {
		a.Textures[path] = q
	}
	a.mu.Unlock()
	return q, nil
}
func (a *AssetManager) audio(path string) (*AudioClip, error) {
	a.mu.RLock()
	t := a.Audio[path]
	a.mu.RUnlock()
	if t != nil {
		return t, nil
	}
	q, e := loadWAV(path)
	if e != nil {
		return nil, e
	}
	a.mu.Lock()
	if old := a.Audio[path]; old != nil {
		q = old
	} else {
		a.Audio[path] = q
	}
	a.mu.Unlock()
	return q, nil
}

type GameWindow struct {
	Handle      uintptr
	W, H        int
	Closed      bool
	ShouldClose bool
	Title       string
	Renderer    *GameRenderer
}
type GameRenderer struct {
	Handle uintptr
	Window *GameWindow
	Info   string
	Kind   string
}
type GameShader struct {
	Handle   uintptr
	Renderer *GameRenderer
}
type GamepadHandle struct {
	Handle uintptr
	Index  int
}

func intColor(args []Value, start int) (byte, byte, byte, byte, error) {
	vals := [4]int{0, 0, 0, 255}
	for j := 0; j < 4; j++ {
		q, e := numberToInt(args[start+j])
		if e != nil {
			return 0, 0, 0, 0, e
		}
		if q < 0 || q > 255 {
			return 0, 0, 0, 0, fmt.Errorf("RGBA channel must be 0..255")
		}
		vals[j] = q
	}
	return byte(vals[0]), byte(vals[1]), byte(vals[2]), byte(vals[3]), nil
}

func numberToF(v Value) (float64, error) { return numberToFloat(v) }
func numberFromFloat64(v float64) Number {
	s := strconv.FormatFloat(v, 'g', -1, 64)
	n, err := newNumber(s, "decimal")
	if err != nil {
		return Number{R: new(big.Rat), Kind: "decimal"}
	}
	return n
}
