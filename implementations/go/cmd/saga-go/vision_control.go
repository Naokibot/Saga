package main

import (
	"encoding/json"
	"fmt"
	"math"
	"sort"
)

type visionDetection struct {
	ClassID    int       `json:"class_id"`
	Label      string    `json:"label,omitempty"`
	Confidence float64   `json:"confidence"`
	Box        []float64 `json:"box"`
}

func visionIoU(a, b visionDetection) float64 {
	if len(a.Box) != 4 || len(b.Box) != 4 {
		return 0
	}
	x1 := math.Max(a.Box[0], b.Box[0])
	y1 := math.Max(a.Box[1], b.Box[1])
	x2 := math.Min(a.Box[2], b.Box[2])
	y2 := math.Min(a.Box[3], b.Box[3])
	iw := math.Max(0, x2-x1)
	ih := math.Max(0, y2-y1)
	inter := iw * ih
	aa := math.Max(0, a.Box[2]-a.Box[0]) * math.Max(0, a.Box[3]-a.Box[1])
	bb := math.Max(0, b.Box[2]-b.Box[0]) * math.Max(0, b.Box[3]-b.Box[1])
	u := aa + bb - inter
	if u <= 0 {
		return 0
	}
	return inter / u
}

func visionNMS(items []visionDetection, threshold float64) ([]visionDetection, error) {
	if threshold < 0 || threshold > 1 || math.IsNaN(threshold) {
		return nil, fmt.Errorf("iou_threshold must be in 0..1")
	}
	sort.SliceStable(items, func(i, j int) bool { return items[i].Confidence > items[j].Confidence })
	out := []visionDetection{}
	for len(items) > 0 {
		best := items[0]
		items = items[1:]
		out = append(out, best)
		next := items[:0]
		for _, d := range items {
			if d.ClassID != best.ClassID || visionIoU(best, d) <= threshold {
				next = append(next, d)
			}
		}
		items = next
	}
	return out, nil
}

type visionTrack struct {
	X, Y        float64
	Age, Missed int
}
type visionTracker struct {
	MaxDistance       float64
	MaxMissed, NextID int
	Tracks            map[int]visionTrack
}

func (t *visionTracker) update(ds []visionDetection) []map[string]any {
	type pair struct {
		dist    float64
		tid, di int
	}
	centers := make([][2]float64, len(ds))
	for i, d := range ds {
		if len(d.Box) == 4 {
			centers[i] = [2]float64{(d.Box[0] + d.Box[2]) / 2, (d.Box[1] + d.Box[3]) / 2}
		}
	}
	candidates := []pair{}
	for tid, tr := range t.Tracks {
		for di, c := range centers {
			dd := math.Hypot(c[0]-tr.X, c[1]-tr.Y)
			if dd <= t.MaxDistance {
				candidates = append(candidates, pair{dd, tid, di})
			}
		}
	}
	sort.Slice(candidates, func(i, j int) bool { return candidates[i].dist < candidates[j].dist })
	ut := map[int]bool{}
	ud := map[int]bool{}
	for tid := range t.Tracks {
		ut[tid] = true
	}
	for di := range ds {
		ud[di] = true
	}
	assigned := [][2]int{}
	for _, p := range candidates {
		if ut[p.tid] && ud[p.di] {
			delete(ut, p.tid)
			delete(ud, p.di)
			assigned = append(assigned, [2]int{p.tid, p.di})
			tr := t.Tracks[p.tid]
			tr.X = centers[p.di][0]
			tr.Y = centers[p.di][1]
			tr.Age++
			tr.Missed = 0
			t.Tracks[p.tid] = tr
		}
	}
	for tid := range ut {
		tr := t.Tracks[tid]
		tr.Missed++
		if tr.Missed > t.MaxMissed {
			delete(t.Tracks, tid)
		} else {
			t.Tracks[tid] = tr
		}
	}
	for di := range ud {
		tid := t.NextID
		t.NextID++
		c := centers[di]
		t.Tracks[tid] = visionTrack{c[0], c[1], 1, 0}
		assigned = append(assigned, [2]int{tid, di})
	}
	out := []map[string]any{}
	for _, a := range assigned {
		tid, di := a[0], a[1]
		tr := t.Tracks[tid]
		d := ds[di]
		out = append(out, map[string]any{"track_id": tid, "class_id": d.ClassID, "label": d.Label, "confidence": d.Confidence, "center_x": tr.X, "center_y": tr.Y, "age": tr.Age, "missed": tr.Missed, "box": d.Box})
	}
	return out
}

type visionCamera struct{ Fx, Fy, Cx, Cy float64 }

func (c *visionCamera) bearing(u, v float64) ([3]float64, error) {
	if c.Fx <= 0 || c.Fy <= 0 {
		return [3]float64{}, fmt.Errorf("invalid camera intrinsics")
	}
	x := (u - c.Cx) / c.Fx
	y := (v - c.Cy) / c.Fy
	n := math.Sqrt(x*x + y*y + 1)
	return [3]float64{x / n, y / n, 1 / n}, nil
}

func (i *Interpreter) callVisionNative(name string, args []Value, t Token) (Value, error) {
	fail := func(e error) (Value, error) {
		return nil, diag("SAGA-R001", "SAGA-R197", "vision."+name+": "+e.Error(), t)
	}
	switch name {
	case "nms_json":
		if len(args) != 2 {
			return fail(fmt.Errorf("requires 2 arguments"))
		}
		text, ok := args[0].(string)
		if !ok {
			return fail(fmt.Errorf("detections must be JSON text"))
		}
		th, e := machineNumber(args[1], "iou threshold")
		if e != nil {
			return fail(e)
		}
		var ds []visionDetection
		if e = json.Unmarshal([]byte(text), &ds); e != nil {
			return fail(e)
		}
		out, e := visionNMS(ds, th)
		if e != nil {
			return fail(e)
		}
		b, _ := json.Marshal(out)
		return string(b), nil
	case "tracker":
		if len(args) != 2 {
			return fail(fmt.Errorf("requires 2 arguments"))
		}
		d, e := machineNumber(args[0], "max distance")
		if e != nil || d <= 0 {
			return fail(fmt.Errorf("max distance must be > 0"))
		}
		m, e := machineInt(args[1], "max missed")
		if e != nil || m < 0 {
			return fail(fmt.Errorf("max missed must be >=0"))
		}
		return &visionTracker{d, m, 1, map[int]visionTrack{}}, nil
	case "track_json":
		tr, ok := args[0].(*visionTracker)
		if !ok {
			return fail(fmt.Errorf("invalid tracker"))
		}
		text, ok := args[1].(string)
		if !ok {
			return fail(fmt.Errorf("detections must be JSON text"))
		}
		var ds []visionDetection
		if e := json.Unmarshal([]byte(text), &ds); e != nil {
			return fail(e)
		}
		b, _ := json.Marshal(tr.update(ds))
		return string(b), nil
	case "camera":
		if len(args) != 4 {
			return fail(fmt.Errorf("requires 4 arguments"))
		}
		v := make([]float64, 4)
		for j := range v {
			q, e := machineNumber(args[j], "camera parameter")
			if e != nil {
				return fail(e)
			}
			v[j] = q
		}
		if v[0] <= 0 || v[1] <= 0 {
			return fail(fmt.Errorf("fx/fy must be >0"))
		}
		return &visionCamera{v[0], v[1], v[2], v[3]}, nil
	case "pixel_to_bearing":
		c, ok := args[0].(*visionCamera)
		if !ok {
			return fail(fmt.Errorf("invalid camera"))
		}
		u, e := machineNumber(args[1], "u")
		if e != nil {
			return fail(e)
		}
		v, e := machineNumber(args[2], "v")
		if e != nil {
			return fail(e)
		}
		b, e := c.bearing(u, v)
		if e != nil {
			return fail(e)
		}
		return droneValues3(b), nil
	}
	return fail(fmt.Errorf("unknown function"))
}
