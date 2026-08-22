package main

import (
	"bytes"
	"encoding/binary"
	"image"
	"image/color"
	"image/jpeg"
	"image/png"
	"os"
	"path/filepath"
	"testing"
)

func TestRGBAFramebufferAndTexturePipeline(t *testing.T) {
	f, err := newPixelBuffer(8, 8)
	if err != nil {
		t.Fatal(err)
	}
	f.clearRGBA(0, 0, 0, 255)
	f.fillRect(1, 1, 3, 2, 255, 0, 0, 255)
	f.line(0, 7, 7, 0, 0, 255, 0, 255)
	f.circle(4, 4, 2, 0, 0, 255, 255)
	if len(f.Pix) != 8*8*4 {
		t.Fatal("bad framebuffer size")
	}
	// Alpha blend must modify both color and alpha deterministically.
	f.setPixel(0, 0, 255, 255, 255, 128)
	if f.Pix[0] == 0 || f.Pix[3] != 255 {
		t.Fatalf("blend failed: %v", f.Pix[:4])
	}

	dir := t.TempDir()
	img := image.NewRGBA(image.Rect(0, 0, 2, 2))
	img.Set(0, 0, color.RGBA{255, 0, 0, 255})
	img.Set(1, 0, color.RGBA{0, 255, 0, 255})
	img.Set(0, 1, color.RGBA{0, 0, 255, 255})
	img.Set(1, 1, color.RGBA{255, 255, 0, 128})
	pp := filepath.Join(dir, "tex.png")
	pf, _ := os.Create(pp)
	if err := png.Encode(pf, img); err != nil {
		t.Fatal(err)
	}
	pf.Close()
	jp := filepath.Join(dir, "tex.jpg")
	jf, _ := os.Create(jp)
	if err := jpeg.Encode(jf, img, &jpeg.Options{Quality: 90}); err != nil {
		t.Fatal(err)
	}
	jf.Close()
	ptex, err := loadGameTexture(pp)
	if err != nil {
		t.Fatal(err)
	}
	if ptex.W != 2 || ptex.H != 2 {
		t.Fatal("png dimensions")
	}
	jtex, err := loadGameTexture(jp)
	if err != nil {
		t.Fatal(err)
	}
	if jtex.W != 2 || jtex.H != 2 {
		t.Fatal("jpeg dimensions")
	}
	drawTexture(f, ptex, 0, 0, 2, 2, 3, 3, 4, 4)
}

func TestAnimationTilemapParticlesPhysicsAndAssets(t *testing.T) {
	tex := &GameTexture{W: 4, H: 2, Pix: make([]byte, 4*2*4)}
	for i := 3; i < len(tex.Pix); i += 4 {
		tex.Pix[i] = 255
	}
	a := &SpriteAnimation{Texture: tex, FrameW: 2, FrameH: 2, Frames: 2, FPS: 10}
	if got := a.frameIndex(150); got != 1 {
		t.Fatalf("animation frame=%d", got)
	}
	if got := a.frameIndex(250); got != 0 {
		t.Fatalf("animation loop=%d", got)
	}
	m, err := newTilemap(3, 2, 2, 2)
	if err != nil {
		t.Fatal(err)
	}
	m.set(1, 1, 3)
	if v, ok := m.get(1, 1); !ok || v != 3 {
		t.Fatal("tile set/get")
	}
	fb, _ := newPixelBuffer(12, 8)
	cam := &GameCamera{Zoom: 1}
	drawTilemap(fb, m, tex, cam, 2)
	ps := &ParticleSystem{}
	ps.emit(1, 1, 2, 0, 1, 255, 255, 255, 255, 1)
	ps.update(0.25, 4)
	if len(ps.Particles) != 1 || ps.Particles[0].X <= 1 {
		t.Fatal("particle update")
	}
	ps.draw(fb, cam)
	w := &PhysicsWorld{GravityY: 10}
	floor, _ := w.addBody(0, 5, 10, 2, 1, false)
	_ = floor
	b, _ := w.addBody(1, 0, 2, 2, 1, true)
	b.Restitution = 0
	b.FX = 2
	b.VY -= 1
	for n := 0; n < 60; n++ {
		w.step(1.0 / 60.0)
	}
	if b.Y+b.H > 5.001 {
		t.Fatalf("body penetrated floor: y=%f", b.Y)
	}
}

func wavBytes() []byte {
	data := make([]byte, 400)
	for i := 0; i < len(data); i += 2 {
		binary.LittleEndian.PutUint16(data[i:], uint16(int16((i%40-20)*500)))
	}
	var b bytes.Buffer
	b.WriteString("RIFF")
	binary.Write(&b, binary.LittleEndian, uint32(36+len(data)))
	b.WriteString("WAVEfmt ")
	binary.Write(&b, binary.LittleEndian, uint32(16))
	binary.Write(&b, binary.LittleEndian, uint16(1))
	binary.Write(&b, binary.LittleEndian, uint16(1))
	binary.Write(&b, binary.LittleEndian, uint32(8000))
	binary.Write(&b, binary.LittleEndian, uint32(16000))
	binary.Write(&b, binary.LittleEndian, uint16(2))
	binary.Write(&b, binary.LittleEndian, uint16(16))
	b.WriteString("data")
	binary.Write(&b, binary.LittleEndian, uint32(len(data)))
	b.Write(data)
	return b.Bytes()
}
func TestWAVAndAssetManager(t *testing.T) {
	clip, err := decodeWAV(wavBytes(), "memory.wav")
	if err != nil {
		t.Fatal(err)
	}
	if clip.SampleRate != 8000 || clip.Channels != 1 || len(clip.PCM16) == 0 {
		t.Fatal("wav parse")
	}
	dir := t.TempDir()
	wp := filepath.Join(dir, "tone.wav")
	if err := os.WriteFile(wp, wavBytes(), 0644); err != nil {
		t.Fatal(err)
	}
	img := image.NewRGBA(image.Rect(0, 0, 1, 1))
	img.Set(0, 0, color.White)
	pp := filepath.Join(dir, "a.png")
	f, _ := os.Create(pp)
	png.Encode(f, img)
	f.Close()
	a := newAssetManager()
	t1, err := a.texture(pp)
	if err != nil {
		t.Fatal(err)
	}
	t2, err := a.texture(pp)
	if err != nil || t1 != t2 {
		t.Fatal("texture cache")
	}
	c1, err := a.audio(wp)
	if err != nil {
		t.Fatal(err)
	}
	c2, err := a.audio(wp)
	if err != nil || c1 != c2 {
		t.Fatal("audio cache")
	}
}

func TestExpandedGameAPIChecks(t *testing.T) {
	src := `use game
let fb=game.framebuffer(64,48)
game.fb_clear(fb,0,0,0,255)
game.fb_rect(fb,2,2,10,10,255,0,0,255)
game.fb_line(fb,0,0,20,20,0,255,0,255)
game.fb_circle(fb,20,20,5,0,0,255,255)
let cam=game.camera(0,0,1)
let tm=game.tilemap(4,4,8,8)
game.tile_set(tm,1,1,2)
let ps=game.particles()
game.particle_emit(ps,1,1,2,3,1,255,255,255,255,1)
game.particles_update(ps,0.016,9.8)
game.particles_draw(fb,ps,cam)
let pw=game.physics_world(0,9.8)
let body=game.physics_body(pw,0,0,8,8,1,true)
game.body_velocity(body,2,0)
game.physics_step(pw,0.016)
print(game.fb_width(fb))
print(game.body_x(body))
print(game.desktop_available())`
	got, err := runSagaForTest(t, src)
	if err != nil {
		t.Fatal(err)
	}
	if got == "" {
		t.Fatal("no output")
	}
}
