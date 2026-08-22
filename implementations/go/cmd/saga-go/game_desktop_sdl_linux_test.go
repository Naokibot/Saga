//go:build linux && sagadesktop

package main

import (
	"os"
	"strings"
	"testing"
)

func TestDesktopSDLWindowOpenGLShaderAndAudio(t *testing.T) {
	if os.Getenv("SAGA_DESKTOP_INTEGRATION") != "1" {
		t.Skip("set SAGA_DESKTOP_INTEGRATION=1 under a display server")
	}
	if !desktopAvailable() {
		t.Fatal("desktop backend false")
	}
	w, err := desktopOpenWindow("Saga desktop validation", 160, 120)
	if err != nil {
		t.Fatal(err)
	}
	defer desktopCloseWindow(w)
	r, info, err := desktopRendererCreate(w)
	if err != nil {
		t.Fatal(err)
	}
	defer desktopRendererDestroy(r)
	if info == "" {
		t.Fatal("missing renderer info")
	}
	fb, _ := newPixelBuffer(64, 48)
	fb.clearRGBA(20, 30, 40, 255)
	fb.fillRect(4, 4, 20, 10, 255, 0, 0, 255)
	if err := desktopRendererPresent(r, fb.Pix, fb.W, fb.H, 0); err != nil {
		t.Fatal(err)
	}
	frag := `#version 120
uniform sampler2D u_tex;
varying vec2 v_uv;
void main(){ vec4 c=texture2D(u_tex,v_uv); gl_FragColor=vec4(1.0-c.rgb,c.a); }`
	s, err := desktopShaderCreate(r, frag)
	if err != nil {
		t.Fatal(err)
	}
	defer desktopShaderDestroy(r, s)
	if err := desktopRendererPresent(r, fb.Pix, fb.W, fb.H, s); err != nil {
		t.Fatal(err)
	}
	vertex := `#version 120
varying vec2 v_uv;
void main(){ gl_Position=gl_Vertex; v_uv=gl_MultiTexCoord0.xy; }`
	program, err := desktopShaderProgramCreate(r, vertex, frag)
	if err != nil {
		t.Fatal(err)
	}
	defer desktopShaderDestroy(r, program)
	if err := desktopRendererPresent(r, fb.Pix, fb.W, fb.H, program); err != nil {
		t.Fatal(err)
	}
	if count := desktopGamepadCount(); count < 0 {
		t.Fatalf("invalid gamepad count %d", count)
	}
	if _, err := desktopKeyDown(w, "Space"); err != nil {
		t.Fatal(err)
	}
	if _, _, _, err := desktopMouse(w); err != nil {
		t.Fatal(err)
	}
	if _, err := desktopPoll(w); err != nil {
		t.Fatal(err)
	}
	clip, err := decodeWAV(wavBytes(), "memory.wav")
	if err != nil {
		t.Fatal(err)
	}
	if err := desktopAudioPlay(clip.PCM16, clip.SampleRate, clip.Channels); err != nil {
		t.Fatal(err)
	}
}

func TestDesktopSDL2DSecondRenderer(t *testing.T) {
	w, err := desktopOpenWindow("Saga SDL2D", 96, 64)
	if err != nil {
		t.Fatal(err)
	}
	defer desktopCloseWindow(w)
	r, info, err := desktopRenderer2DCreate(w, "native2")
	if err != nil {
		t.Fatal(err)
	}
	defer desktopRenderer2DDestroy(r)
	if info == "" {
		t.Fatal("missing SDL2D renderer info")
	}
	fb, err := newPixelBuffer(32, 24)
	if err != nil {
		t.Fatal(err)
	}
	fb.clearRGBA(15, 30, 60, 255)
	fb.fillRect(4, 4, 12, 8, 240, 100, 20, 255)
	if err := desktopRenderer2DPresent(r, fb.Pix, fb.W, fb.H); err != nil {
		t.Fatal(err)
	}
	if desktopRendererDrivers() == "" {
		t.Fatal("no SDL renderer drivers reported")
	}
	t.Log(info)
}

func TestDesktopVulkanProbe(t *testing.T) {
	if os.Getenv("SAGA_DESKTOP_INTEGRATION") != "1" {
		t.Skip("set SAGA_DESKTOP_INTEGRATION=1 to run native desktop integration")
	}
	ok, info := desktopVulkanProbe()
	if strings.TrimSpace(info) == "" {
		t.Fatal("Vulkan probe returned no evidence")
	}
	if ok {
		t.Log("Vulkan device probe available:", info)
	} else {
		t.Log("Vulkan loader/device gate not available on this host:", info)
	}
}

func TestDesktopVirtualGamepadEndToEnd(t *testing.T) {
	idx, err := desktopTestVirtualGamepadAttach()
	if err != nil {
		t.Fatal(err)
	}
	defer desktopTestVirtualGamepadDetach(idx)
	if count := desktopGamepadCount(); count < 1 {
		t.Fatalf("virtual gamepad did not enumerate: count=%d", count)
	}
	pad, err := desktopOpenGamepad(idx)
	if err != nil {
		t.Fatal(err)
	}
	defer desktopCloseGamepad(pad)
	if err := desktopTestVirtualGamepadButton(pad, 0, true); err != nil {
		t.Fatal(err)
	}
	pressed, err := desktopGamepadButton(pad, "a")
	if err != nil || !pressed {
		t.Fatalf("A button path failed: pressed=%v err=%v", pressed, err)
	}
	if err := desktopTestVirtualGamepadAxis(pad, 0, 16384); err != nil {
		t.Fatal(err)
	}
	axis, err := desktopGamepadAxis(pad, "leftx")
	if err != nil || axis < 0.49 || axis > 0.51 {
		t.Fatalf("axis path failed: axis=%f err=%v", axis, err)
	}
}
