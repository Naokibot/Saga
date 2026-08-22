package main

import (
	"fmt"
	"strings"
)

func sagaResultOK(v Value) ResultValue    { return ResultValue{OK: true, Value: v} }
func sagaResultErr(err error) ResultValue { return ResultValue{OK: false, Value: err.Error()} }

func intArgs(args []Value, start, count int) ([]int, error) {
	if start+count > len(args) {
		return nil, fmt.Errorf("not enough integer arguments")
	}
	out := make([]int, count)
	for j := 0; j < count; j++ {
		v, e := numberToInt(args[start+j])
		if e != nil {
			return nil, e
		}
		out[j] = v
	}
	return out, nil
}
func floatArg(v Value) (float64, error) { return numberToFloat(v) }

func destroyGameRenderer(r *GameRenderer) {
	if r == nil || r.Handle == 0 {
		return
	}
	if r.Kind == "sdl2d" {
		desktopRenderer2DDestroy(r.Handle)
	} else if r.Kind == "vulkan" {
		desktopVulkanRendererDestroy(r.Handle)
	} else {
		desktopRendererDestroy(r.Handle)
	}
	r.Handle = 0
}
func presentGameRenderer(r *GameRenderer, f *PixelBuffer, shader uintptr) error {
	if r == nil || r.Handle == 0 || f == nil {
		return fmt.Errorf("renderer and framebuffer required")
	}
	if r.Kind == "sdl2d" {
		if shader != 0 {
			return fmt.Errorf("SDL2D renderer does not expose programmable shaders; use SIR1 with a programmable backend")
		}
		return desktopRenderer2DPresent(r.Handle, f.Pix, f.W, f.H)
	}
	if r.Kind == "vulkan" {
		if shader != 0 {
			return fmt.Errorf("Vulkan framebuffer-transfer backend does not yet accept backend-native shader handles; compile SIR1 to glsl450/SPIR-V in the Vulkan shader profile")
		}
		return desktopVulkanRendererPresent(r.Handle, f.Pix, f.W, f.H)
	}
	return desktopRendererPresent(r.Handle, f.Pix, f.W, f.H, shader)
}

func (i *Interpreter) callGameExtended(name string, args []Value, t Token) (Value, bool, error) {
	bad := func(msg string) (Value, bool, error) { return nil, true, i.rerr(t, "SAGA-R150", msg) }
	switch name {
	case "framebuffer":
		if len(args) != 2 {
			return bad("game.framebuffer(width,height)")
		}
		v, e := intArgs(args, 0, 2)
		if e != nil {
			return bad(e.Error())
		}
		f, e := newPixelBuffer(v[0], v[1])
		if e != nil {
			return nil, true, i.rerr(t, "SAGA-R170", e.Error())
		}
		return f, true, nil
	case "fb_clear":
		if len(args) != 5 {
			return bad("game.fb_clear(framebuffer,r,g,b,a)")
		}
		f, ok := args[0].(*PixelBuffer)
		if !ok {
			return bad("framebuffer required")
		}
		r, g, b, a, e := intColor(args, 1)
		if e != nil {
			return bad(e.Error())
		}
		f.clearRGBA(r, g, b, a)
		return nil, true, nil
	case "fb_pixel":
		if len(args) != 7 {
			return bad("game.fb_pixel(framebuffer,x,y,r,g,b,a)")
		}
		f, ok := args[0].(*PixelBuffer)
		if !ok {
			return bad("framebuffer required")
		}
		v, e := intArgs(args, 1, 2)
		if e != nil {
			return bad(e.Error())
		}
		r, g, b, a, e := intColor(args, 3)
		if e != nil {
			return bad(e.Error())
		}
		f.setPixel(v[0], v[1], r, g, b, a)
		return nil, true, nil
	case "fb_rect":
		if len(args) != 9 {
			return bad("game.fb_rect(framebuffer,x,y,w,h,r,g,b,a)")
		}
		f, ok := args[0].(*PixelBuffer)
		if !ok {
			return bad("framebuffer required")
		}
		v, e := intArgs(args, 1, 4)
		if e != nil {
			return bad(e.Error())
		}
		r, g, b, a, e := intColor(args, 5)
		if e != nil {
			return bad(e.Error())
		}
		f.fillRect(v[0], v[1], v[2], v[3], r, g, b, a)
		return nil, true, nil
	case "fb_line":
		if len(args) != 9 {
			return bad("game.fb_line(framebuffer,x0,y0,x1,y1,r,g,b,a)")
		}
		f, ok := args[0].(*PixelBuffer)
		if !ok {
			return bad("framebuffer required")
		}
		v, e := intArgs(args, 1, 4)
		if e != nil {
			return bad(e.Error())
		}
		r, g, b, a, e := intColor(args, 5)
		if e != nil {
			return bad(e.Error())
		}
		f.line(v[0], v[1], v[2], v[3], r, g, b, a)
		return nil, true, nil
	case "fb_circle":
		if len(args) != 8 {
			return bad("game.fb_circle(framebuffer,cx,cy,radius,r,g,b,a)")
		}
		f, ok := args[0].(*PixelBuffer)
		if !ok {
			return bad("framebuffer required")
		}
		v, e := intArgs(args, 1, 3)
		if e != nil || v[2] < 0 {
			return bad("circle coordinates/radius must be valid")
		}
		r, g, b, a, e := intColor(args, 4)
		if e != nil {
			return bad(e.Error())
		}
		f.circle(v[0], v[1], v[2], r, g, b, a)
		return nil, true, nil
	case "fb_width", "fb_height":
		if len(args) != 1 {
			return bad("framebuffer required")
		}
		f, ok := args[0].(*PixelBuffer)
		if !ok {
			return bad("framebuffer required")
		}
		if name == "fb_width" {
			return numberFromInt64(int64(f.W)), true, nil
		}
		return numberFromInt64(int64(f.H)), true, nil
	case "texture_load":
		if len(args) != 1 {
			return bad("game.texture_load(path)")
		}
		p, ok := args[0].(string)
		if !ok {
			return bad("path text required")
		}
		tex, e := loadGameTexture(p)
		if e != nil {
			return sagaResultErr(e), true, nil
		}
		return sagaResultOK(tex), true, nil
	case "texture_width", "texture_height":
		if len(args) != 1 {
			return bad("texture required")
		}
		tex, ok := args[0].(*GameTexture)
		if !ok {
			return bad("texture required")
		}
		if name == "texture_width" {
			return numberFromInt64(int64(tex.W)), true, nil
		}
		return numberFromInt64(int64(tex.H)), true, nil
	case "draw_texture":
		if len(args) != 4 {
			return bad("game.draw_texture(framebuffer,texture,x,y)")
		}
		f, fok := args[0].(*PixelBuffer)
		tex, tok := args[1].(*GameTexture)
		if !fok || !tok {
			return bad("framebuffer and texture required")
		}
		v, e := intArgs(args, 2, 2)
		if e != nil {
			return bad(e.Error())
		}
		drawTexture(f, tex, 0, 0, tex.W, tex.H, v[0], v[1], tex.W, tex.H)
		return nil, true, nil
	case "draw_texture_region":
		if len(args) != 10 {
			return bad("game.draw_texture_region(framebuffer,texture,sx,sy,sw,sh,dx,dy,dw,dh)")
		}
		f, fok := args[0].(*PixelBuffer)
		tex, tok := args[1].(*GameTexture)
		if !fok || !tok {
			return bad("framebuffer and texture required")
		}
		v, e := intArgs(args, 2, 8)
		if e != nil {
			return bad(e.Error())
		}
		drawTexture(f, tex, v[0], v[1], v[2], v[3], v[4], v[5], v[6], v[7])
		return nil, true, nil
	case "animation":
		if len(args) != 5 {
			return bad("game.animation(texture,frame_w,frame_h,frames,fps)")
		}
		tex, ok := args[0].(*GameTexture)
		if !ok {
			return bad("texture required")
		}
		v, e := intArgs(args, 1, 3)
		if e != nil || v[0] <= 0 || v[1] <= 0 || v[2] <= 0 {
			return bad("positive frame dimensions/count required")
		}
		fps, e := floatArg(args[4])
		if e != nil || fps <= 0 {
			return bad("positive fps required")
		}
		return &SpriteAnimation{Texture: tex, FrameW: v[0], FrameH: v[1], Frames: v[2], FPS: fps}, true, nil
	case "animation_frame":
		if len(args) != 2 {
			return bad("game.animation_frame(animation,elapsed_ms)")
		}
		a, ok := args[0].(*SpriteAnimation)
		if !ok {
			return bad("animation required")
		}
		ms, e := numberToInt(args[1])
		if e != nil {
			return bad(e.Error())
		}
		return numberFromInt64(int64(a.frameIndex(int64(ms)))), true, nil
	case "draw_animation":
		if len(args) != 6 {
			return bad("game.draw_animation(framebuffer,animation,elapsed_ms,x,y,scale)")
		}
		f, fok := args[0].(*PixelBuffer)
		a, aok := args[1].(*SpriteAnimation)
		if !fok || !aok {
			return bad("framebuffer and animation required")
		}
		v, e := intArgs(args, 2, 4)
		if e != nil || v[3] <= 0 {
			return bad("elapsed/x/y and positive scale required")
		}
		idx := a.frameIndex(int64(v[0]))
		cols := a.Texture.W / a.FrameW
		if cols <= 0 {
			return bad("animation frame wider than texture")
		}
		sx := (idx % cols) * a.FrameW
		sy := (idx / cols) * a.FrameH
		drawTexture(f, a.Texture, sx, sy, a.FrameW, a.FrameH, v[1], v[2], a.FrameW*v[3], a.FrameH*v[3])
		return nil, true, nil
	case "camera":
		if len(args) != 3 {
			return bad("game.camera(x,y,zoom)")
		}
		x, e := floatArg(args[0])
		if e != nil {
			return bad(e.Error())
		}
		y, e := floatArg(args[1])
		if e != nil {
			return bad(e.Error())
		}
		z, e := floatArg(args[2])
		if e != nil || z <= 0 {
			return bad("positive camera zoom required")
		}
		return &GameCamera{X: x, Y: y, Zoom: z}, true, nil
	case "camera_set":
		if len(args) != 4 {
			return bad("game.camera_set(camera,x,y,zoom)")
		}
		c, ok := args[0].(*GameCamera)
		if !ok {
			return bad("camera required")
		}
		x, e := floatArg(args[1])
		if e != nil {
			return bad(e.Error())
		}
		y, e := floatArg(args[2])
		if e != nil {
			return bad(e.Error())
		}
		z, e := floatArg(args[3])
		if e != nil || z <= 0 {
			return bad("positive camera zoom required")
		}
		c.X, c.Y, c.Zoom = x, y, z
		return nil, true, nil
	case "tilemap":
		if len(args) != 4 {
			return bad("game.tilemap(width,height,tile_w,tile_h)")
		}
		v, e := intArgs(args, 0, 4)
		if e != nil {
			return bad(e.Error())
		}
		m, e := newTilemap(v[0], v[1], v[2], v[3])
		if e != nil {
			return bad(e.Error())
		}
		return m, true, nil
	case "tile_set":
		if len(args) != 4 {
			return bad("game.tile_set(tilemap,x,y,id)")
		}
		m, ok := args[0].(*GameTilemap)
		if !ok {
			return bad("tilemap required")
		}
		v, e := intArgs(args, 1, 3)
		if e != nil {
			return bad(e.Error())
		}
		m.set(v[0], v[1], v[2])
		return nil, true, nil
	case "tile_get":
		if len(args) != 3 {
			return bad("game.tile_get(tilemap,x,y)")
		}
		m, ok := args[0].(*GameTilemap)
		if !ok {
			return bad("tilemap required")
		}
		v, e := intArgs(args, 1, 2)
		if e != nil {
			return bad(e.Error())
		}
		q, p := m.get(v[0], v[1])
		if !p {
			return OptionValue{Present: false}, true, nil
		}
		return OptionValue{Present: true, Value: numberFromInt64(int64(q))}, true, nil
	case "tile_draw":
		if len(args) != 5 {
			return bad("game.tile_draw(framebuffer,tilemap,atlas,camera,columns)")
		}
		f, fok := args[0].(*PixelBuffer)
		m, mok := args[1].(*GameTilemap)
		tex, tok := args[2].(*GameTexture)
		c, cok := args[3].(*GameCamera)
		cols, e := numberToInt(args[4])
		if !fok || !mok || !tok || !cok || e != nil || cols <= 0 {
			return bad("framebuffer/tilemap/texture/camera and positive columns required")
		}
		drawTilemap(f, m, tex, c, cols)
		return nil, true, nil
	case "particles":
		if len(args) != 0 {
			return bad("game.particles()")
		}
		return &ParticleSystem{}, true, nil
	case "particle_emit":
		if len(args) != 11 {
			return bad("game.particle_emit(system,x,y,vx,vy,life,r,g,b,a,size)")
		}
		p, ok := args[0].(*ParticleSystem)
		if !ok {
			return bad("particle system required")
		}
		fv := make([]float64, 5)
		for j := 0; j < 5; j++ {
			q, e := floatArg(args[1+j])
			if e != nil {
				return bad(e.Error())
			}
			fv[j] = q
		}
		r, g, b, a, e := intColor(args, 6)
		if e != nil {
			return bad(e.Error())
		}
		size, e := numberToInt(args[10])
		if e != nil || size <= 0 {
			return bad("positive particle size required")
		}
		p.emit(fv[0], fv[1], fv[2], fv[3], fv[4], r, g, b, a, size)
		return nil, true, nil
	case "particles_update":
		if len(args) != 3 {
			return bad("game.particles_update(system,dt,gravity_y)")
		}
		p, ok := args[0].(*ParticleSystem)
		if !ok {
			return bad("particle system required")
		}
		dt, e := floatArg(args[1])
		if e != nil || dt < 0 {
			return bad("non-negative dt required")
		}
		g, e := floatArg(args[2])
		if e != nil {
			return bad(e.Error())
		}
		p.update(dt, g)
		return nil, true, nil
	case "particles_draw":
		if len(args) != 3 {
			return bad("game.particles_draw(framebuffer,system,camera)")
		}
		f, fok := args[0].(*PixelBuffer)
		p, pok := args[1].(*ParticleSystem)
		c, cok := args[2].(*GameCamera)
		if !fok || !pok || !cok {
			return bad("framebuffer, particle system and camera required")
		}
		p.draw(f, c)
		return nil, true, nil
	case "particle_count":
		if len(args) != 1 {
			return bad("game.particle_count(system)")
		}
		p, ok := args[0].(*ParticleSystem)
		if !ok {
			return bad("particle system required")
		}
		return numberFromInt64(int64(len(p.Particles))), true, nil
	case "physics_world":
		if len(args) != 2 {
			return bad("game.physics_world(gravity_x,gravity_y)")
		}
		gx, e := floatArg(args[0])
		if e != nil {
			return bad(e.Error())
		}
		gy, e := floatArg(args[1])
		if e != nil {
			return bad(e.Error())
		}
		return &PhysicsWorld{GravityX: gx, GravityY: gy}, true, nil
	case "physics_body":
		if len(args) != 7 {
			return bad("game.physics_body(world,x,y,w,h,mass,dynamic)")
		}
		w, ok := args[0].(*PhysicsWorld)
		if !ok {
			return bad("physics world required")
		}
		fv := make([]float64, 5)
		for j := 0; j < 5; j++ {
			q, e := floatArg(args[1+j])
			if e != nil {
				return bad(e.Error())
			}
			fv[j] = q
		}
		dyn, ok := args[6].(bool)
		if !ok {
			return bad("dynamic bool required")
		}
		b, e := w.addBody(fv[0], fv[1], fv[2], fv[3], fv[4], dyn)
		if e != nil {
			return bad(e.Error())
		}
		return b, true, nil
	case "body_velocity":
		if len(args) != 3 {
			return bad("game.body_velocity(body,vx,vy)")
		}
		b, ok := args[0].(*PhysicsBody)
		if !ok {
			return bad("physics body required")
		}
		vx, e := floatArg(args[1])
		if e != nil {
			return bad(e.Error())
		}
		vy, e := floatArg(args[2])
		if e != nil {
			return bad(e.Error())
		}
		b.VX, b.VY = vx, vy
		return nil, true, nil
	case "body_position":
		if len(args) != 3 {
			return bad("game.body_position(body,x,y)")
		}
		b, ok := args[0].(*PhysicsBody)
		if !ok {
			return bad("physics body required")
		}
		x, e := floatArg(args[1])
		if e != nil {
			return bad(e.Error())
		}
		y, e := floatArg(args[2])
		if e != nil {
			return bad(e.Error())
		}
		b.X, b.Y = x, y
		return nil, true, nil
	case "body_force":
		if len(args) != 3 {
			return bad("game.body_force(body,fx,fy)")
		}
		b, ok := args[0].(*PhysicsBody)
		if !ok {
			return bad("physics body required")
		}
		fx, e := floatArg(args[1])
		if e != nil {
			return bad(e.Error())
		}
		fy, e := floatArg(args[2])
		if e != nil {
			return bad(e.Error())
		}
		if b.Dynamic {
			b.FX += fx
			b.FY += fy
		}
		return nil, true, nil
	case "body_impulse":
		if len(args) != 3 {
			return bad("game.body_impulse(body,ix,iy)")
		}
		b, ok := args[0].(*PhysicsBody)
		if !ok {
			return bad("physics body required")
		}
		ix, e := floatArg(args[1])
		if e != nil {
			return bad(e.Error())
		}
		iy, e := floatArg(args[2])
		if e != nil {
			return bad(e.Error())
		}
		if b.Dynamic {
			inv := bodyInvMass(b)
			b.VX += ix * inv
			b.VY += iy * inv
		}
		return nil, true, nil
	case "body_restitution":
		if len(args) != 2 {
			return bad("game.body_restitution(body,value)")
		}
		b, ok := args[0].(*PhysicsBody)
		if !ok {
			return bad("physics body required")
		}
		q, e := floatArg(args[1])
		if e != nil || q < 0 || q > 1 {
			return bad("restitution must be 0..1")
		}
		b.Restitution = q
		return nil, true, nil
	case "physics_step":
		if len(args) != 2 {
			return bad("game.physics_step(world,dt)")
		}
		w, ok := args[0].(*PhysicsWorld)
		if !ok {
			return bad("physics world required")
		}
		dt, e := floatArg(args[1])
		if e != nil || dt < 0 {
			return bad("non-negative dt required")
		}
		w.step(dt)
		return nil, true, nil
	case "body_x", "body_y", "body_vx", "body_vy":
		if len(args) != 1 {
			return bad("physics body required")
		}
		b, ok := args[0].(*PhysicsBody)
		if !ok {
			return bad("physics body required")
		}
		q := b.X
		if name == "body_y" {
			q = b.Y
		} else if name == "body_vx" {
			q = b.VX
		} else if name == "body_vy" {
			q = b.VY
		}
		return numberFromFloat64(q), true, nil
	case "body_overlaps":
		if len(args) != 2 {
			return bad("game.body_overlaps(a,b)")
		}
		a, aok := args[0].(*PhysicsBody)
		b, bok := args[1].(*PhysicsBody)
		if !aok || !bok {
			return bad("physics bodies required")
		}
		return overlapF(a, b), true, nil
	case "audio_load":
		if len(args) != 1 {
			return bad("game.audio_load(path)")
		}
		p, ok := args[0].(string)
		if !ok {
			return bad("path text required")
		}
		clip, e := loadWAV(p)
		if e != nil {
			return sagaResultErr(e), true, nil
		}
		return sagaResultOK(clip), true, nil
	case "audio_play":
		if len(args) != 1 {
			return bad("game.audio_play(clip)")
		}
		clip, ok := args[0].(*AudioClip)
		if !ok {
			return bad("audio clip required")
		}
		if e := desktopAudioPlay(clip.PCM16, clip.SampleRate, clip.Channels); e != nil {
			return sagaResultErr(e), true, nil
		}
		return sagaResultOK(nil), true, nil
	case "asset_manager":
		if len(args) != 0 {
			return bad("game.asset_manager()")
		}
		return newAssetManager(), true, nil
	case "asset_texture":
		if len(args) != 2 {
			return bad("game.asset_texture(manager,path)")
		}
		a, ok := args[0].(*AssetManager)
		p, pok := args[1].(string)
		if !ok || !pok {
			return bad("asset manager and path required")
		}
		tex, e := a.texture(p)
		if e != nil {
			return sagaResultErr(e), true, nil
		}
		return sagaResultOK(tex), true, nil
	case "asset_audio":
		if len(args) != 2 {
			return bad("game.asset_audio(manager,path)")
		}
		a, ok := args[0].(*AssetManager)
		p, pok := args[1].(string)
		if !ok || !pok {
			return bad("asset manager and path required")
		}
		clip, e := a.audio(p)
		if e != nil {
			return sagaResultErr(e), true, nil
		}
		return sagaResultOK(clip), true, nil
	case "desktop_available":
		if len(args) != 0 {
			return bad("game.desktop_available()")
		}
		return desktopAvailable(), true, nil
	case "desktop_backend":
		if len(args) != 0 {
			return bad("game.desktop_backend()")
		}
		return desktopBackendName(), true, nil
	case "graphics_backends":
		if len(args) != 0 {
			return bad("game.graphics_backends()")
		}
		items := []Value{"opengl"}
		if desktopVulkanRendererCompiled() {
			items = append(items, "vulkan")
		}
		for _, q := range strings.Split(desktopRendererDrivers(), ",") {
			if strings.TrimSpace(q) != "" {
				items = append(items, strings.TrimSpace(q))
			}
		}
		return items, true, nil
	case "window_open":
		if len(args) != 3 {
			return bad("game.window_open(title,width,height)")
		}
		title, ok := args[0].(string)
		if !ok {
			return bad("window title text required")
		}
		v, e := intArgs(args, 1, 2)
		if e != nil || v[0] <= 0 || v[1] <= 0 {
			return bad("positive window dimensions required")
		}
		h, e := desktopOpenWindow(title, v[0], v[1])
		if e != nil {
			return sagaResultErr(e), true, nil
		}
		return sagaResultOK(&GameWindow{Handle: h, W: v[0], H: v[1], Title: title}), true, nil
	case "window_close":
		if len(args) != 1 {
			return bad("game.window_close(window)")
		}
		w, ok := args[0].(*GameWindow)
		if !ok {
			return bad("window required")
		}
		if w.Renderer != nil && w.Renderer.Handle != 0 {
			destroyGameRenderer(w.Renderer)
			w.Renderer = nil
		}
		if w.Handle != 0 {
			desktopCloseWindow(w.Handle)
			w.Handle = 0
		}
		w.Closed = true
		w.ShouldClose = true
		return nil, true, nil
	case "window_poll":
		if len(args) != 1 {
			return bad("game.window_poll(window)")
		}
		w, ok := args[0].(*GameWindow)
		if !ok || w.Closed {
			return bad("open window required")
		}
		q, e := desktopPoll(w.Handle)
		if e != nil {
			return nil, true, i.rerr(t, "SAGA-R170", e.Error())
		}
		if q {
			w.ShouldClose = true
		}
		return w.ShouldClose, true, nil
	case "key_down":
		if len(args) != 2 {
			return bad("game.key_down(window,key)")
		}
		w, ok := args[0].(*GameWindow)
		key, kok := args[1].(string)
		if !ok || !kok || w.Closed {
			return bad("open window and key text required")
		}
		q, e := desktopKeyDown(w.Handle, key)
		if e != nil {
			return nil, true, i.rerr(t, "SAGA-R170", e.Error())
		}
		return q, true, nil
	case "mouse_x", "mouse_y":
		if len(args) != 1 {
			return bad("game.mouse_x/window or mouse_y(window)")
		}
		w, ok := args[0].(*GameWindow)
		if !ok || w.Closed {
			return bad("open window required")
		}
		x, y, _, e := desktopMouse(w.Handle)
		if e != nil {
			return nil, true, i.rerr(t, "SAGA-R170", e.Error())
		}
		if name == "mouse_x" {
			return numberFromInt64(int64(x)), true, nil
		}
		return numberFromInt64(int64(y)), true, nil
	case "mouse_button":
		if len(args) != 2 {
			return bad("game.mouse_button(window,name)")
		}
		w, ok := args[0].(*GameWindow)
		bn, bok := args[1].(string)
		if !ok || !bok || w.Closed {
			return bad("open window and button name required")
		}
		_, _, mask, e := desktopMouse(w.Handle)
		if e != nil {
			return nil, true, i.rerr(t, "SAGA-R170", e.Error())
		}
		bit := uint32(0)
		switch strings.ToLower(bn) {
		case "left":
			bit = 1
		case "middle":
			bit = 2
		case "right":
			bit = 4
		case "x1":
			bit = 8
		case "x2":
			bit = 16
		default:
			return bad("mouse button must be left/middle/right/x1/x2")
		}
		return mask&bit != 0, true, nil
	case "gamepad_count":
		if len(args) != 0 {
			return bad("game.gamepad_count()")
		}
		return numberFromInt64(int64(desktopGamepadCount())), true, nil
	case "gamepad_open":
		if len(args) != 1 {
			return bad("game.gamepad_open(index)")
		}
		idx, e := numberToInt(args[0])
		if e != nil || idx < 0 {
			return bad("non-negative gamepad index required")
		}
		h, e := desktopOpenGamepad(idx)
		if e != nil {
			return sagaResultErr(e), true, nil
		}
		return sagaResultOK(&GamepadHandle{Handle: h, Index: idx}), true, nil
	case "gamepad_close":
		if len(args) != 1 {
			return bad("game.gamepad_close(gamepad)")
		}
		g, ok := args[0].(*GamepadHandle)
		if !ok {
			return bad("gamepad required")
		}
		desktopCloseGamepad(g.Handle)
		g.Handle = 0
		return nil, true, nil
	case "gamepad_button":
		if len(args) != 2 {
			return bad("game.gamepad_button(gamepad,button)")
		}
		g, ok := args[0].(*GamepadHandle)
		bn, bok := args[1].(string)
		if !ok || !bok || g.Handle == 0 {
			return bad("open gamepad and button required")
		}
		q, e := desktopGamepadButton(g.Handle, bn)
		if e != nil {
			return nil, true, i.rerr(t, "SAGA-R170", e.Error())
		}
		return q, true, nil
	case "gamepad_axis":
		if len(args) != 2 {
			return bad("game.gamepad_axis(gamepad,axis)")
		}
		g, ok := args[0].(*GamepadHandle)
		an, aok := args[1].(string)
		if !ok || !aok || g.Handle == 0 {
			return bad("open gamepad and axis required")
		}
		q, e := desktopGamepadAxis(g.Handle, an)
		if e != nil {
			return nil, true, i.rerr(t, "SAGA-R170", e.Error())
		}
		return numberFromFloat64(q), true, nil
	case "renderer":
		if len(args) != 1 {
			return bad("game.renderer(window)")
		}
		w, ok := args[0].(*GameWindow)
		if !ok || w.Closed {
			return bad("open window required")
		}
		if w.Renderer != nil && w.Renderer.Handle != 0 {
			return sagaResultErr(fmt.Errorf("window already has a renderer")), true, nil
		}
		h, info, e := desktopRendererCreate(w.Handle)
		if e != nil {
			return sagaResultErr(e), true, nil
		}
		r := &GameRenderer{Handle: h, Window: w, Info: info, Kind: "opengl"}
		w.Renderer = r
		return sagaResultOK(r), true, nil
	case "vulkan_probe":
		if len(args) != 0 {
			return bad("game.vulkan_probe()")
		}
		ok, info := desktopVulkanProbe()
		if !ok {
			return sagaResultErr(fmt.Errorf("%s", info)), true, nil
		}
		return sagaResultOK(info), true, nil
	case "renderer_backend":
		if len(args) != 2 {
			return bad("game.renderer_backend(window,backend)")
		}
		w, ok := args[0].(*GameWindow)
		backend, bok := args[1].(string)
		if !ok || !bok || w.Closed {
			return bad("open window and backend text required")
		}
		if w.Renderer != nil && w.Renderer.Handle != 0 {
			return sagaResultErr(fmt.Errorf("window already has a renderer")), true, nil
		}
		backend = strings.ToLower(strings.TrimSpace(backend))
		if backend == "opengl" || backend == "gl" {
			h, info, e := desktopRendererCreate(w.Handle)
			if e != nil {
				return sagaResultErr(e), true, nil
			}
			r := &GameRenderer{Handle: h, Window: w, Info: info, Kind: "opengl"}
			w.Renderer = r
			return sagaResultOK(r), true, nil
		}
		if backend == "vulkan" {
			h, newWindow, info, e := desktopVulkanRendererCreate(w.Handle, w.Title, w.W, w.H)
			if e != nil {
				return sagaResultErr(e), true, nil
			}
			w.Handle = newWindow
			r := &GameRenderer{Handle: h, Window: w, Info: info, Kind: "vulkan"}
			w.Renderer = r
			return sagaResultOK(r), true, nil
		}
		h, info, e := desktopRenderer2DCreate(w.Handle, backend)
		if e != nil {
			return sagaResultErr(e), true, nil
		}
		r := &GameRenderer{Handle: h, Window: w, Info: info, Kind: "sdl2d"}
		w.Renderer = r
		return sagaResultOK(r), true, nil
	case "renderer_info":
		if len(args) != 1 {
			return bad("game.renderer_info(renderer)")
		}
		r, ok := args[0].(*GameRenderer)
		if !ok || r.Handle == 0 {
			return bad("renderer required")
		}
		return r.Info, true, nil
	case "renderer_close":
		if len(args) != 1 {
			return bad("game.renderer_close(renderer)")
		}
		r, ok := args[0].(*GameRenderer)
		if !ok {
			return bad("renderer required")
		}
		if r.Handle != 0 {
			destroyGameRenderer(r)
		}
		if r.Window != nil && r.Window.Renderer == r {
			r.Window.Renderer = nil
		}
		return nil, true, nil
	case "shader":
		if len(args) != 2 {
			return bad("game.shader(renderer,fragment_source)")
		}
		r, ok := args[0].(*GameRenderer)
		src, sok := args[1].(string)
		if !ok || !sok || r.Handle == 0 || r.Kind != "opengl" {
			return bad("OpenGL renderer and GLSL fragment source required")
		}
		h, e := desktopShaderCreate(r.Handle, src)
		if e != nil {
			return sagaResultErr(e), true, nil
		}
		return sagaResultOK(&GameShader{Handle: h, Renderer: r}), true, nil
	case "shader_program":
		if len(args) != 3 {
			return bad("game.shader_program(renderer,vertex_source,fragment_source)")
		}
		r, ok := args[0].(*GameRenderer)
		vs, vok := args[1].(string)
		fs, fok := args[2].(string)
		if !ok || !vok || !fok || r.Handle == 0 || r.Kind != "opengl" {
			return bad("OpenGL renderer and GLSL vertex/fragment source required")
		}
		h, e := desktopShaderProgramCreate(r.Handle, vs, fs)
		if e != nil {
			return sagaResultErr(e), true, nil
		}
		return sagaResultOK(&GameShader{Handle: h, Renderer: r}), true, nil
	case "shader_ir_validate":
		if len(args) != 1 {
			return bad("game.shader_ir_validate(source)")
		}
		src, ok := args[0].(string)
		if !ok {
			return bad("SIR1 source text required")
		}
		if _, e := parseShaderIR(src); e != nil {
			return sagaResultErr(e), true, nil
		}
		return sagaResultOK(nil), true, nil
	case "shader_ir_compile":
		if len(args) != 2 {
			return bad("game.shader_ir_compile(source,target)")
		}
		src, sok := args[0].(string)
		target, tok := args[1].(string)
		if !sok || !tok {
			return bad("SIR1 source and target text required")
		}
		out, e := compileShaderIR(src, target)
		if e != nil {
			return sagaResultErr(e), true, nil
		}
		return sagaResultOK(out), true, nil
	case "shader_ir_compute_reference":
		if len(args) != 2 {
			return bad("game.shader_ir_compute_reference(source,values)")
		}
		src, sok := args[0].(string)
		vals, vok := args[1].([]Value)
		if !sok || !vok {
			return bad("compute SIR1 source and list[float64] required")
		}
		in := make([]float64, len(vals))
		for j, v := range vals {
			f, ok := v.(FloatValue)
			if !ok {
				return bad("compute reference values must be float32/float64")
			}
			in[j] = f.V
		}
		out, e := executeComputeShaderIRReference(src, in)
		if e != nil {
			return sagaResultErr(e), true, nil
		}
		result := make([]Value, len(out))
		for j, v := range out {
			result[j] = FloatValue{V: v, Bits: 64}
		}
		return sagaResultOK(result), true, nil
	case "shader_ir":
		if len(args) != 2 {
			return bad("game.shader_ir(renderer,source)")
		}
		r, rok := args[0].(*GameRenderer)
		src, sok := args[1].(string)
		if !rok || !sok || r.Handle == 0 || r.Kind != "opengl" {
			return bad("OpenGL renderer and SIR1 source required")
		}
		glsl, e := compileShaderIR(src, "glsl120")
		if e != nil {
			return sagaResultErr(e), true, nil
		}
		h, e := desktopShaderCreate(r.Handle, glsl)
		if e != nil {
			return sagaResultErr(e), true, nil
		}
		return sagaResultOK(&GameShader{Handle: h, Renderer: r}), true, nil
	case "shader_close":
		if len(args) != 1 {
			return bad("game.shader_close(shader)")
		}
		s, ok := args[0].(*GameShader)
		if !ok {
			return bad("shader required")
		}
		if s.Handle != 0 && s.Renderer != nil {
			desktopShaderDestroy(s.Renderer.Handle, s.Handle)
			s.Handle = 0
		}
		return nil, true, nil
	case "present_rgba", "present_shader":
		need := 2
		if name == "present_shader" {
			need = 3
		}
		if len(args) != need {
			return bad("game.present_rgba(renderer,framebuffer) / game.present_shader(renderer,framebuffer,shader)")
		}
		r, rok := args[0].(*GameRenderer)
		f, fok := args[1].(*PixelBuffer)
		if !rok || !fok || r.Handle == 0 {
			return bad("renderer and framebuffer required")
		}
		sh := uintptr(0)
		if name == "present_shader" {
			s, ok := args[2].(*GameShader)
			if !ok || s.Handle == 0 || s.Renderer != r {
				return bad("shader from the same renderer required")
			}
			sh = s.Handle
		}
		if e := presentGameRenderer(r, f, sh); e != nil {
			return sagaResultErr(e), true, nil
		}
		return sagaResultOK(nil), true, nil
	}
	return nil, false, nil
}
