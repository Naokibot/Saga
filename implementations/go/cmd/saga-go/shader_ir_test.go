package main

import (
	"strings"
	"testing"
)

func TestShaderIRPortableTargets(t *testing.T) {
	src := "SIR1\nstage fragment\nsample\ngrayscale\nmul 1 0.8 0.6 1\nalpha 0.5\n"
	for _, target := range []string{"glsl120", "glsl450", "hlsl5", "msl2", "wgsl"} {
		out, err := compileShaderIR(src, target)
		if err != nil {
			t.Fatalf("%s: %v", target, err)
		}
		if !strings.Contains(out, "saga") && target != "glsl120" && target != "glsl450" {
			t.Fatalf("%s missing generated entry point", target)
		}
	}
	if _, err := compileShaderIR("SIR1\nstage fragment\ninvert\n", "glsl120"); err == nil {
		t.Fatal("accepted transform before sample")
	}
}

func TestShaderIRCanonicalAndDigest(t *testing.T) {
	a := "SIR1\r\nstage fragment\r\nsample\r\nmul 1 0.8 0.60 1\r\n"
	b := "  SIR1\nstage fragment\nsample\nmul 1.000000 0.800000 0.600000 1.0\n"
	ca, err := compileShaderIR(a, "sir1")
	if err != nil {
		t.Fatal(err)
	}
	cb, err := compileShaderIR(b, "canonical")
	if err != nil {
		t.Fatal(err)
	}
	if ca != cb {
		t.Fatalf("canonical forms differ:\n%s\n---\n%s", ca, cb)
	}
	da, err := compileShaderIR(a, "sir1-sha256")
	if err != nil {
		t.Fatal(err)
	}
	db, err := compileShaderIR(b, "digest")
	if err != nil {
		t.Fatal(err)
	}
	if da != db || len(da) != 64 {
		t.Fatalf("digest mismatch: %q %q", da, db)
	}
}

func TestSIR1ComputeTargetsAndReferenceSemantics(t *testing.T) {
	src := "SIR1\nstage compute\nscale 2\nadd -1\nclamp 0 10\n"
	for _, target := range []string{"glsl450", "hlsl5", "msl2", "wgsl"} {
		out, err := compileShaderIR(src, target)
		if err != nil || len(out) == 0 {
			t.Fatalf("compute target %s failed: %v", target, err)
		}
	}
	if _, err := compileShaderIR(src, "glsl120"); err == nil {
		t.Fatal("GLSL120 compute must be rejected")
	}
	out, err := executeComputeShaderIRReference(src, []float64{-2, 1, 8})
	if err != nil {
		t.Fatal(err)
	}
	want := []float64{0, 1, 10}
	for i := range want {
		if out[i] != want[i] {
			t.Fatalf("compute reference mismatch: got=%v want=%v", out, want)
		}
	}
	a, _ := compileShaderIR(src, "sir1-sha256")
	b, _ := compileShaderIR("  SIR1\r\nstage compute\r\nscale 2.0\r\nadd -1.000\r\nclamp 0.0 10.000\r\n", "digest")
	if a != b {
		t.Fatalf("compute canonical digest differs: %s %s", a, b)
	}
}
