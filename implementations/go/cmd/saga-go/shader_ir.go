package main

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"math"
	"strconv"
	"strings"
)

type ShaderIROp struct {
	Name string
	Args [4]float64
	N    int
}

type ShaderIRProgram struct {
	Stage string
	Ops   []ShaderIROp
}

func shaderIRNumber(fields []string, idx, lineNo int, min, max float64) (float64, error) {
	v, e := strconv.ParseFloat(fields[idx], 64)
	if e != nil || math.IsNaN(v) || math.IsInf(v, 0) || v < min || v > max {
		return 0, fmt.Errorf("line %d: numeric argument %q must be finite and in %g..%g", lineNo+1, fields[idx], min, max)
	}
	return v, nil
}

func parseShaderIR(source string) (ShaderIRProgram, error) {
	var p ShaderIRProgram
	lines := strings.Split(strings.ReplaceAll(source, "\r\n", "\n"), "\n")
	seenHeader := false
	seenStage := false
	seenSample := false
	for lineNo, raw := range lines {
		line := strings.TrimSpace(raw)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		fields := strings.Fields(line)
		if !seenHeader {
			if len(fields) != 1 || strings.ToLower(fields[0]) != "sir1" {
				return p, fmt.Errorf("line %d: expected SIR1 header", lineNo+1)
			}
			seenHeader = true
			continue
		}
		if !seenStage {
			if len(fields) != 2 || strings.ToLower(fields[0]) != "stage" {
				return p, fmt.Errorf("line %d: expected 'stage fragment' or 'stage compute'", lineNo+1)
			}
			p.Stage = strings.ToLower(fields[1])
			if p.Stage != "fragment" && p.Stage != "compute" {
				return p, fmt.Errorf("line %d: unsupported SIR1 stage %q", lineNo+1, fields[1])
			}
			seenStage = true
			continue
		}
		name := strings.ToLower(fields[0])
		if p.Stage == "compute" {
			switch name {
			case "scale", "add":
				if len(fields) != 2 {
					return p, fmt.Errorf("line %d: %s requires one numeric argument", lineNo+1, name)
				}
				v, e := shaderIRNumber(fields, 1, lineNo, -1_000_000, 1_000_000)
				if e != nil {
					return p, e
				}
				p.Ops = append(p.Ops, ShaderIROp{Name: name, N: 1, Args: [4]float64{v}})
			case "clamp":
				if len(fields) != 3 {
					return p, fmt.Errorf("line %d: clamp requires min and max", lineNo+1)
				}
				lo, e := shaderIRNumber(fields, 1, lineNo, -1_000_000, 1_000_000)
				if e != nil {
					return p, e
				}
				hi, e := shaderIRNumber(fields, 2, lineNo, -1_000_000, 1_000_000)
				if e != nil {
					return p, e
				}
				if lo > hi {
					return p, fmt.Errorf("line %d: clamp min exceeds max", lineNo+1)
				}
				p.Ops = append(p.Ops, ShaderIROp{Name: name, N: 2, Args: [4]float64{lo, hi}})
			default:
				return p, fmt.Errorf("line %d: unknown compute SIR1 operation %q", lineNo+1, fields[0])
			}
			continue
		}
		// Fragment stage.
		switch name {
		case "sample":
			if len(fields) != 1 {
				return p, fmt.Errorf("line %d: sample takes no arguments", lineNo+1)
			}
			if seenSample {
				return p, fmt.Errorf("line %d: sample may appear only once", lineNo+1)
			}
			seenSample = true
			p.Ops = append(p.Ops, ShaderIROp{Name: name})
		case "invert", "grayscale":
			if len(fields) != 1 {
				return p, fmt.Errorf("line %d: %s takes no arguments", lineNo+1, name)
			}
			if !seenSample {
				return p, fmt.Errorf("line %d: %s requires sample first", lineNo+1, name)
			}
			p.Ops = append(p.Ops, ShaderIROp{Name: name})
		case "mul", "bias":
			if len(fields) != 5 {
				return p, fmt.Errorf("line %d: %s requires four numeric arguments", lineNo+1, name)
			}
			if !seenSample {
				return p, fmt.Errorf("line %d: %s requires sample first", lineNo+1, name)
			}
			op := ShaderIROp{Name: name, N: 4}
			for j := 0; j < 4; j++ {
				v, e := shaderIRNumber(fields, j+1, lineNo, -16, 16)
				if e != nil {
					return p, e
				}
				op.Args[j] = v
			}
			p.Ops = append(p.Ops, op)
		case "alpha":
			if len(fields) != 2 {
				return p, fmt.Errorf("line %d: alpha requires one numeric argument", lineNo+1)
			}
			if !seenSample {
				return p, fmt.Errorf("line %d: alpha requires sample first", lineNo+1)
			}
			v, e := shaderIRNumber(fields, 1, lineNo, 0, 1)
			if e != nil {
				return p, e
			}
			p.Ops = append(p.Ops, ShaderIROp{Name: name, N: 1, Args: [4]float64{v}})
		default:
			return p, fmt.Errorf("line %d: unknown SIR1 operation %q", lineNo+1, fields[0])
		}
	}
	if !seenHeader || !seenStage {
		return p, fmt.Errorf("incomplete SIR1 program")
	}
	if p.Stage == "fragment" && !seenSample {
		return p, fmt.Errorf("fragment SIR1 requires sample")
	}
	if p.Stage == "compute" && len(p.Ops) == 0 {
		return p, fmt.Errorf("compute SIR1 requires at least one operation")
	}
	if len(p.Ops) > 64 {
		return p, fmt.Errorf("SIR1 operation limit exceeded")
	}
	return p, nil
}

func shaderF(v float64) string { return strconv.FormatFloat(v, 'f', 6, 64) }

func canonicalShaderIR(p ShaderIRProgram) string {
	var b strings.Builder
	b.WriteString("SIR1\nstage " + p.Stage + "\n")
	for _, op := range p.Ops {
		b.WriteString(op.Name)
		for i := 0; i < op.N; i++ {
			b.WriteByte(' ')
			b.WriteString(strconv.FormatFloat(op.Args[i], 'f', 6, 64))
		}
		b.WriteByte('\n')
	}
	return b.String()
}

func compileComputeShaderIR(p ShaderIRProgram, target string) (string, error) {
	var b strings.Builder
	switch target {
	case "glsl120":
		return "", fmt.Errorf("GLSL 1.20 has no standardized compute shader stage; use glsl450, hlsl5, msl2 or wgsl")
	case "glsl450", "vulkan-glsl":
		b.WriteString("#version 450\nlayout(local_size_x=64) in;\nlayout(set=0,binding=0) buffer SagaData { float data[]; };\nvoid main(){ uint i=gl_GlobalInvocationID.x; float x=data[i];\n")
		for _, op := range p.Ops {
			writeComputeShaderOp(&b, op, "glsl")
		}
		b.WriteString("  data[i]=x;\n}\n")
	case "hlsl5", "direct3d11", "direct3d12":
		b.WriteString("RWStructuredBuffer<float> data : register(u0);\n[numthreads(64,1,1)] void main(uint3 id : SV_DispatchThreadID){ uint i=id.x; float x=data[i];\n")
		for _, op := range p.Ops {
			writeComputeShaderOp(&b, op, "hlsl")
		}
		b.WriteString("  data[i]=x;\n}\n")
	case "msl2", "metal":
		b.WriteString("#include <metal_stdlib>\nusing namespace metal;\nkernel void saga_compute(device float* data [[buffer(0)]], uint i [[thread_position_in_grid]]) { float x=data[i];\n")
		for _, op := range p.Ops {
			writeComputeShaderOp(&b, op, "msl")
		}
		b.WriteString("  data[i]=x;\n}\n")
	case "wgsl":
		b.WriteString("@group(0) @binding(0) var<storage, read_write> data: array<f32>;\n@compute @workgroup_size(64) fn saga_compute(@builtin(global_invocation_id) id: vec3<u32>) { let i=id.x; var x=data[i];\n")
		for _, op := range p.Ops {
			writeComputeShaderOp(&b, op, "wgsl")
		}
		b.WriteString("  data[i]=x;\n}\n")
	default:
		return "", fmt.Errorf("unknown SIR1 target %q", target)
	}
	return b.String(), nil
}
func writeComputeShaderOp(b *strings.Builder, op ShaderIROp, lang string) {
	_ = lang
	switch op.Name {
	case "scale":
		b.WriteString("  x = x * " + shaderF(op.Args[0]) + ";\n")
	case "add":
		b.WriteString("  x = x + " + shaderF(op.Args[0]) + ";\n")
	case "clamp":
		b.WriteString("  x = clamp(x, " + shaderF(op.Args[0]) + ", " + shaderF(op.Args[1]) + ");\n")
	}
}
func executeComputeShaderIRReference(source string, values []float64) ([]float64, error) {
	p, e := parseShaderIR(source)
	if e != nil {
		return nil, e
	}
	if p.Stage != "compute" {
		return nil, fmt.Errorf("compute SIR1 required")
	}
	out := append([]float64{}, values...)
	for i, x := range out {
		for _, op := range p.Ops {
			switch op.Name {
			case "scale":
				x *= op.Args[0]
			case "add":
				x += op.Args[0]
			case "clamp":
				x = math.Max(op.Args[0], math.Min(op.Args[1], x))
			}
		}
		out[i] = x
	}
	return out, nil
}

func compileShaderIR(source, target string) (string, error) {
	p, e := parseShaderIR(source)
	if e != nil {
		return "", e
	}
	target = strings.ToLower(strings.TrimSpace(target))
	if target == "sir1" || target == "canonical" {
		return canonicalShaderIR(p), nil
	}
	if target == "sir1-sha256" || target == "digest" {
		sum := sha256.Sum256([]byte(canonicalShaderIR(p)))
		return hex.EncodeToString(sum[:]), nil
	}
	if p.Stage == "compute" {
		return compileComputeShaderIR(p, target)
	}
	var b strings.Builder
	switch target {
	case "glsl120":
		b.WriteString("#version 120\nuniform sampler2D u_tex;\nvarying vec2 v_uv;\nvoid main(){\n  vec4 c = texture2D(u_tex, v_uv);\n")
		for _, op := range p.Ops[1:] {
			writeShaderOp(&b, op, "glsl")
		}
		b.WriteString("  gl_FragColor = c;\n}\n")
	case "glsl450", "vulkan-glsl":
		b.WriteString("#version 450\nlayout(set=0,binding=0) uniform sampler2D u_tex;\nlayout(location=0) in vec2 v_uv;\nlayout(location=0) out vec4 out_color;\nvoid main(){\n  vec4 c = texture(u_tex, v_uv);\n")
		for _, op := range p.Ops[1:] {
			writeShaderOp(&b, op, "glsl")
		}
		b.WriteString("  out_color = c;\n}\n")
	case "hlsl5", "direct3d11", "direct3d12":
		b.WriteString("Texture2D u_tex : register(t0);\nSamplerState u_sampler : register(s0);\nstruct PSIn { float4 pos : SV_POSITION; float2 uv : TEXCOORD0; };\nfloat4 main(PSIn input) : SV_TARGET {\n  float4 c = u_tex.Sample(u_sampler, input.uv);\n")
		for _, op := range p.Ops[1:] {
			writeShaderOp(&b, op, "hlsl")
		}
		b.WriteString("  return c;\n}\n")
	case "msl2", "metal":
		b.WriteString("#include <metal_stdlib>\nusing namespace metal;\nstruct FSIn { float4 position [[position]]; float2 uv; };\nfragment float4 saga_fragment(FSIn input [[stage_in]], texture2d<float> u_tex [[texture(0)]], sampler u_sampler [[sampler(0)]]) {\n  float4 c = u_tex.sample(u_sampler, input.uv);\n")
		for _, op := range p.Ops[1:] {
			writeShaderOp(&b, op, "msl")
		}
		b.WriteString("  return c;\n}\n")
	case "wgsl":
		b.WriteString("@group(0) @binding(0) var u_tex: texture_2d<f32>;\n@group(0) @binding(1) var u_sampler: sampler;\n@fragment fn saga_fragment(@location(0) uv: vec2<f32>) -> @location(0) vec4<f32> {\n  var c = textureSample(u_tex, u_sampler, uv);\n")
		for _, op := range p.Ops[1:] {
			writeShaderOp(&b, op, "wgsl")
		}
		b.WriteString("  return c;\n}\n")
	default:
		return "", fmt.Errorf("unknown SIR1 target %q; use sir1, sir1-sha256, glsl120, glsl450, hlsl5, msl2, or wgsl", target)
	}
	return b.String(), nil
}

func writeShaderOp(b *strings.Builder, op ShaderIROp, lang string) {
	vec4 := func(a [4]float64) string {
		prefix := "vec4"
		if lang == "hlsl" || lang == "msl" {
			prefix = "float4"
		}
		if lang == "wgsl" {
			prefix = "vec4<f32>"
		}
		return fmt.Sprintf("%s(%s, %s, %s, %s)", prefix, shaderF(a[0]), shaderF(a[1]), shaderF(a[2]), shaderF(a[3]))
	}
	switch op.Name {
	case "invert":
		b.WriteString("  c.rgb = " + func() string {
			if lang == "hlsl" || lang == "msl" || lang == "wgsl" {
				return "1.0 - c.rgb"
			}
			return "vec3(1.0) - c.rgb"
		}() + ";\n")
	case "grayscale":
		if lang == "wgsl" {
			b.WriteString("  let saga_luma = dot(c.rgb, vec3<f32>(0.212600, 0.715200, 0.072200));\n  c = vec4<f32>(saga_luma, saga_luma, saga_luma, c.a);\n")
		} else if lang == "hlsl" || lang == "msl" {
			b.WriteString("  float saga_luma = dot(c.rgb, float3(0.212600, 0.715200, 0.072200));\n  c = float4(saga_luma, saga_luma, saga_luma, c.a);\n")
		} else {
			b.WriteString("  float saga_luma = dot(c.rgb, vec3(0.212600, 0.715200, 0.072200));\n  c = vec4(saga_luma, saga_luma, saga_luma, c.a);\n")
		}
	case "mul":
		b.WriteString("  c = c * " + vec4(op.Args) + ";\n")
	case "bias":
		b.WriteString("  c = c + " + vec4(op.Args) + ";\n")
	case "alpha":
		b.WriteString("  c.a = c.a * " + shaderF(op.Args[0]) + ";\n")
	}
}
