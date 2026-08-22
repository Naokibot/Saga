package main

import (
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"math"
	"strings"
)

const machineSqrt3 = 1.7320508075688772935

type MachineFOCCurrent struct {
	KpD, KiD, KpQ, KiQ                     float64
	Resistance, Ld, Lq, Flux               float64
	CurrentLimit, VoltageLimit, Antiwindup float64
	IntegralD, IntegralQ                   float64
	MeasuredD, MeasuredQ                   float64
	VoltageD, VoltageQ                     float64
	DutyA, DutyB, DutyC                    float64
}

func newMachineFOCCurrent(v []float64) (*MachineFOCCurrent, error) {
	if len(v) != 11 {
		return nil, fmt.Errorf("FOC current loop requires 11 parameters")
	}
	for _, q := range v {
		if !finiteFloat(q) {
			return nil, fmt.Errorf("FOC parameters must be finite")
		}
	}
	if v[4] < 0 || v[5] <= 0 || v[6] <= 0 || v[7] < 0 {
		return nil, fmt.Errorf("FOC motor parameters require R>=0, Ld/Lq>0 and flux>=0")
	}
	if v[8] <= 0 || v[9] <= 0 || v[10] < 0 {
		return nil, fmt.Errorf("FOC limits must be >0 and antiwindup_gain >=0")
	}
	return &MachineFOCCurrent{KpD: v[0], KiD: v[1], KpQ: v[2], KiQ: v[3], Resistance: v[4], Ld: v[5], Lq: v[6], Flux: v[7], CurrentLimit: v[8], VoltageLimit: v[9], Antiwindup: v[10], DutyA: .5, DutyB: .5, DutyC: .5}, nil
}
func (c *MachineFOCCurrent) reset() {
	c.IntegralD = 0
	c.IntegralQ = 0
	c.MeasuredD = 0
	c.MeasuredQ = 0
	c.VoltageD = 0
	c.VoltageQ = 0
	c.DutyA = .5
	c.DutyB = .5
	c.DutyC = .5
}
func (c *MachineFOCCurrent) step(idRef, iqRef, ia, ib, ic, theta, omega, vbus, dt float64) error {
	vals := []float64{idRef, iqRef, ia, ib, ic, theta, omega, vbus, dt}
	for _, v := range vals {
		if !finiteFloat(v) {
			return fmt.Errorf("FOC arguments must be finite")
		}
	}
	if vbus <= 0 || dt <= 0 {
		return fmt.Errorf("FOC bus_voltage and dt_seconds must be > 0")
	}
	idRef = clampFloat(idRef, -c.CurrentLimit, c.CurrentLimit)
	iqRef = clampFloat(iqRef, -c.CurrentLimit, c.CurrentLimit)
	alpha := (2.0 / 3.0) * (ia - ib/2.0 - ic/2.0)
	beta := (machineSqrt3 / 3.0) * (ib - ic)
	s, co := math.Sin(theta), math.Cos(theta)
	c.MeasuredD = alpha*co + beta*s
	c.MeasuredQ = -alpha*s + beta*co
	ed, eq := idRef-c.MeasuredD, iqRef-c.MeasuredQ
	candD := c.IntegralD + c.KiD*ed*dt
	candQ := c.IntegralQ + c.KiQ*eq*dt
	vdFF := c.Resistance*idRef - omega*c.Lq*c.MeasuredQ
	vqFF := c.Resistance*iqRef + omega*(c.Ld*c.MeasuredD+c.Flux)
	vd := c.KpD*ed + candD + vdFF
	vq := c.KpQ*eq + candQ + vqFF
	limit := math.Min(c.VoltageLimit, vbus/machineSqrt3)
	mag := math.Hypot(vd, vq)
	scale := 1.0
	if mag > limit && mag > 0 {
		scale = limit / mag
	}
	satD, satQ := vd*scale, vq*scale
	c.IntegralD = clampFloat(candD+c.Antiwindup*(satD-vd)*dt, -c.VoltageLimit, c.VoltageLimit)
	c.IntegralQ = clampFloat(candQ+c.Antiwindup*(satQ-vq)*dt, -c.VoltageLimit, c.VoltageLimit)
	c.VoltageD, c.VoltageQ = satD, satQ
	av := satD*co - satQ*s
	bv := satD*s + satQ*co
	va := av
	vb := -av/2 + machineSqrt3*bv/2
	vc := -av/2 - machineSqrt3*bv/2
	off := (math.Max(va, math.Max(vb, vc)) + math.Min(va, math.Min(vb, vc))) / 2
	c.DutyA = clampFloat(.5+(va-off)/vbus, 0, 1)
	c.DutyB = clampFloat(.5+(vb-off)/vbus, 0, 1)
	c.DutyC = clampFloat(.5+(vc-off)/vbus, 0, 1)
	return nil
}

type MachineUnifiedEncoder struct {
	CPR           int
	Gear          float64
	Modulus       int
	Direction     int
	VelocityAlpha float64
	Zero          float64
	Raw           int
	Unwrapped     int64
	Position      float64
	Velocity      float64
	lastRaw       int
	hasLast       bool
	lastPosition  float64
	lastTimestamp int64
}

func newMachineUnifiedEncoder(cpr int, gear float64, modulus, direction int, alpha float64) (*MachineUnifiedEncoder, error) {
	if cpr <= 0 || !finiteFloat(gear) || gear <= 0 {
		return nil, fmt.Errorf("encoder counts_per_revolution and gear_ratio must be > 0")
	}
	if modulus < 0 || modulus == 1 {
		return nil, fmt.Errorf("encoder modulus must be 0 or > 1")
	}
	if direction != -1 && direction != 1 {
		return nil, fmt.Errorf("encoder direction must be -1 or 1")
	}
	if !finiteFloat(alpha) || alpha <= 0 || alpha > 1 {
		return nil, fmt.Errorf("encoder velocity_alpha must be in (0,1]")
	}
	return &MachineUnifiedEncoder{CPR: cpr, Gear: gear, Modulus: modulus, Direction: direction, VelocityAlpha: alpha}, nil
}
func (e *MachineUnifiedEncoder) sample(raw int, ts int64) error {
	if ts < 0 {
		return fmt.Errorf("encoder timestamp_ns must be >= 0")
	}
	if e.Modulus > 0 {
		raw = ((raw % e.Modulus) + e.Modulus) % e.Modulus
	}
	if !e.hasLast {
		e.Unwrapped = int64(raw)
	} else {
		delta := raw - e.lastRaw
		if e.Modulus > 0 {
			half := e.Modulus / 2
			if delta > half {
				delta -= e.Modulus
			} else if delta < -half {
				delta += e.Modulus
			}
		}
		if e.Modulus > 0 {
			e.Unwrapped += int64(delta)
		} else {
			e.Unwrapped += int64(raw - e.lastRaw)
		}
	}
	effective := float64(e.CPR) * e.Gear
	pos := float64(e.Direction)*float64(e.Unwrapped)*360/effective + e.Zero
	if e.hasLast {
		dt := ts - e.lastTimestamp
		if dt <= 0 {
			return fmt.Errorf("encoder timestamps must increase")
		}
		rawVel := (pos - e.lastPosition) * 1e9 / float64(dt)
		e.Velocity += e.VelocityAlpha * (rawVel - e.Velocity)
	}
	e.Raw = raw
	e.Position = pos
	e.lastRaw = raw
	e.lastPosition = pos
	e.lastTimestamp = ts
	e.hasLast = true
	return nil
}
func (e *MachineUnifiedEncoder) align(raw int, mechanical float64) error {
	if !finiteFloat(mechanical) {
		return fmt.Errorf("mechanical_degrees must be finite")
	}
	if e.Modulus > 0 {
		raw = ((raw % e.Modulus) + e.Modulus) % e.Modulus
	}
	base := float64(e.Direction*raw) * 360 / (float64(e.CPR) * e.Gear)
	e.Zero = mechanical - base
	e.hasLast = false
	e.lastTimestamp = 0
	return nil
}

type MachineRLS2 struct{ Lambda, P00, P01, P10, P11, Theta0, Theta1, LastError float64 }

func newMachineRLS2(lambda, cov float64) (*MachineRLS2, error) {
	if !finiteFloat(lambda) || lambda <= 0 || lambda > 1 {
		return nil, fmt.Errorf("RLS forgetting_factor must be in (0,1]")
	}
	if !finiteFloat(cov) || cov <= 0 {
		return nil, fmt.Errorf("RLS covariance must be > 0")
	}
	return &MachineRLS2{Lambda: lambda, P00: cov, P11: cov}, nil
}
func (r *MachineRLS2) update(x0, x1, y float64) error {
	for _, v := range []float64{x0, x1, y} {
		if !finiteFloat(v) {
			return fmt.Errorf("RLS values must be finite")
		}
	}
	px0 := r.P00*x0 + r.P01*x1
	px1 := r.P10*x0 + r.P11*x1
	den := r.Lambda + x0*px0 + x1*px1
	if den <= 0 {
		return fmt.Errorf("RLS covariance lost positive denominator")
	}
	k0, k1 := px0/den, px1/den
	r.LastError = y - (r.Theta0*x0 + r.Theta1*x1)
	r.Theta0 += k0 * r.LastError
	r.Theta1 += k1 * r.LastError
	row0x0 := x0*r.P00 + x1*r.P10
	row0x1 := x0*r.P01 + x1*r.P11
	r.P00 = (r.P00 - k0*row0x0) / r.Lambda
	r.P01 = (r.P01 - k0*row0x1) / r.Lambda
	r.P10 = (r.P10 - k1*row0x0) / r.Lambda
	r.P11 = (r.P11 - k1*row0x1) / r.Lambda
	return nil
}

type machineMat2 [4]float64

func mat2mul(a, b machineMat2) machineMat2 {
	return machineMat2{a[0]*b[0] + a[1]*b[2], a[0]*b[1] + a[1]*b[3], a[2]*b[0] + a[3]*b[2], a[2]*b[1] + a[3]*b[3]}
}

type machineVec2 struct{ x, y float64 }
type MachineMPC2 struct {
	A          machineMat2
	B          machineVec2
	Q0, Q1, R  float64
	Horizon    int
	UMin, UMax float64
	Iterations int
	H          [][]float64
	Influence  [][]machineVec2
	APowers    []machineMat2
	U          []float64
	Step       float64
}

func newMachineMPC2(v []float64, horizon int) (*MachineMPC2, error) {
	if len(v) != 11 {
		return nil, fmt.Errorf("MPC requires 11 numeric parameters")
	}
	for _, q := range v {
		if !finiteFloat(q) {
			return nil, fmt.Errorf("MPC parameters must be finite")
		}
	}
	if v[6] < 0 || v[7] < 0 || v[8] <= 0 {
		return nil, fmt.Errorf("MPC requires q0/q1>=0 and r>0")
	}
	if horizon < 1 || horizon > 32 {
		return nil, fmt.Errorf("MPC horizon must be in 1..32")
	}
	if v[9] >= v[10] {
		return nil, fmt.Errorf("MPC u_min must be smaller than u_max")
	}
	m := &MachineMPC2{A: machineMat2{v[0], v[1], v[2], v[3]}, B: machineVec2{v[4], v[5]}, Q0: v[6], Q1: v[7], R: v[8], Horizon: horizon, UMin: v[9], UMax: v[10], Iterations: 12}
	m.precompute()
	return m, nil
}
func (m *MachineMPC2) precompute() {
	n := m.Horizon
	m.APowers = make([]machineMat2, n+1)
	m.APowers[0] = machineMat2{1, 0, 0, 1}
	for i := 0; i < n; i++ {
		m.APowers[i+1] = mat2mul(m.APowers[i], m.A)
	}
	m.Influence = make([][]machineVec2, n)
	for k := 0; k < n; k++ {
		m.Influence[k] = make([]machineVec2, n)
		for j := 0; j <= k; j++ {
			p := m.APowers[k-j]
			m.Influence[k][j] = machineVec2{p[0]*m.B.x + p[1]*m.B.y, p[2]*m.B.x + p[3]*m.B.y}
		}
	}
	m.H = make([][]float64, n)
	maxRow := 0.0
	for i := 0; i < n; i++ {
		m.H[i] = make([]float64, n)
		row := 0.0
		for j := 0; j < n; j++ {
			total := 0.0
			if i == j {
				total = m.R
			}
			start := i
			if j > start {
				start = j
			}
			for k := start; k < n; k++ {
				ci, cj := m.Influence[k][i], m.Influence[k][j]
				total += m.Q0*ci.x*cj.x + m.Q1*ci.y*cj.y
			}
			m.H[i][j] = total
			row += math.Abs(total)
		}
		if row > maxRow {
			maxRow = row
		}
	}
	if maxRow > 0 {
		m.Step = 1 / (2 * maxRow)
	} else {
		m.Step = 1
	}
	m.U = make([]float64, n)
}
func (m *MachineMPC2) reset() {
	for i := range m.U {
		m.U[i] = 0
	}
}
func (m *MachineMPC2) step(x0, x1, r0, r1 float64) (float64, error) {
	for _, v := range []float64{x0, x1, r0, r1} {
		if !finiteFloat(v) {
			return 0, fmt.Errorf("MPC state/reference must be finite")
		}
	}
	n := m.Horizon
	g := make([]float64, n)
	for i := 0; i < n; i++ {
		total := 0.0
		for k := i; k < n; k++ {
			p := m.APowers[k+1]
			f0 := p[0]*x0 + p[1]*x1 - r0
			f1 := p[2]*x0 + p[3]*x1 - r1
			c := m.Influence[k][i]
			total += m.Q0*c.x*f0 + m.Q1*c.y*f1
		}
		g[i] = total
	}
	for iter := 0; iter < m.Iterations; iter++ {
		for i := 0; i < n; i++ {
			hu := 0.0
			for j := 0; j < n; j++ {
				hu += m.H[i][j] * m.U[j]
			}
			grad := 2 * (hu + g[i])
			m.U[i] = clampFloat(m.U[i]-m.Step*grad, m.UMin, m.UMax)
		}
	}
	cmd := m.U[0]
	for i := 0; i < n-1; i++ {
		m.U[i] = m.U[i+1]
	}
	if n > 1 {
		m.U[n-1] = m.U[n-2]
	} else {
		m.U[0] = cmd
	}
	return cmd, nil
}

type MachineDOB struct {
	InputGain, Damping, Bandwidth, Estimate, PreviousVelocity float64
	HasPrevious                                               bool
}

func newMachineDOB(gain, damping, bw float64) (*MachineDOB, error) {
	for _, v := range []float64{gain, damping, bw} {
		if !finiteFloat(v) {
			return nil, fmt.Errorf("disturbance observer parameters must be finite")
		}
	}
	if bw <= 0 {
		return nil, fmt.Errorf("disturbance observer bandwidth_hz must be > 0")
	}
	return &MachineDOB{InputGain: gain, Damping: damping, Bandwidth: bw}, nil
}
func (d *MachineDOB) reset(estimate float64) error {
	if !finiteFloat(estimate) {
		return fmt.Errorf("estimate must be finite")
	}
	d.Estimate = estimate
	d.HasPrevious = false
	return nil
}
func (d *MachineDOB) step(command, velocity, dt float64) (float64, error) {
	for _, v := range []float64{command, velocity, dt} {
		if !finiteFloat(v) {
			return 0, fmt.Errorf("disturbance observer values must be finite")
		}
	}
	if dt <= 0 {
		return 0, fmt.Errorf("dt_seconds must be > 0")
	}
	if !d.HasPrevious {
		d.PreviousVelocity = velocity
		d.HasPrevious = true
		return d.Estimate, nil
	}
	acc := (velocity - d.PreviousVelocity) / dt
	nom := d.InputGain*command - d.Damping*velocity
	raw := acc - nom
	alpha := 1 - math.Exp(-2*math.Pi*d.Bandwidth*dt)
	d.Estimate += alpha * (raw - d.Estimate)
	d.PreviousVelocity = velocity
	return d.Estimate, nil
}

func machineFrictionCompensation(coulomb, viscous, static, stribeck, velocity, smoothing float64) (float64, error) {
	for _, v := range []float64{coulomb, viscous, static, stribeck, velocity, smoothing} {
		if !finiteFloat(v) {
			return 0, fmt.Errorf("friction parameters must be finite")
		}
	}
	if coulomb < 0 || viscous < 0 || static < coulomb || stribeck <= 0 || smoothing <= 0 {
		return 0, fmt.Errorf("friction requires coulomb/viscous>=0, static>=coulomb, positive velocities")
	}
	ratio := math.Abs(velocity) / stribeck
	mag := coulomb + (static-coulomb)*math.Exp(-(ratio*ratio))
	return mag*math.Tanh(velocity/smoothing) + viscous*velocity, nil
}

type MachineAxisSync struct {
	AxisCount                            int
	Kp, MaxCorrection, SkewLimit, Master float64
	Ratios, Offsets, Errors              []float64
	Healthy                              bool
}

func newMachineAxisSync(count int, kp, maxCorrection, skew float64) (*MachineAxisSync, error) {
	if count < 1 || count > 32 {
		return nil, fmt.Errorf("axis_sync axis_count must be in 1..32")
	}
	if !finiteFloat(kp) || !finiteFloat(maxCorrection) || !finiteFloat(skew) || maxCorrection <= 0 || skew <= 0 {
		return nil, fmt.Errorf("axis_sync limits must be finite and > 0")
	}
	s := &MachineAxisSync{AxisCount: count, Kp: kp, MaxCorrection: maxCorrection, SkewLimit: skew, Healthy: true, Ratios: make([]float64, count), Offsets: make([]float64, count), Errors: make([]float64, count)}
	for i := range s.Ratios {
		s.Ratios[i] = 1
	}
	return s, nil
}
func (s *MachineAxisSync) configure(axis int, ratio, offset float64) error {
	if axis < 0 || axis >= s.AxisCount {
		return fmt.Errorf("axis_sync axis index out of range")
	}
	if !finiteFloat(ratio) || !finiteFloat(offset) {
		return fmt.Errorf("axis_sync ratio/offset must be finite")
	}
	s.Ratios[axis] = ratio
	s.Offsets[axis] = offset
	return nil
}
func (s *MachineAxisSync) begin(master float64) error {
	if !finiteFloat(master) {
		return fmt.Errorf("master_position must be finite")
	}
	s.Master = master
	s.Healthy = true
	return nil
}
func (s *MachineAxisSync) correction(axis int, actual float64) (float64, error) {
	if axis < 0 || axis >= s.AxisCount {
		return 0, fmt.Errorf("axis_sync axis index out of range")
	}
	if !finiteFloat(actual) {
		return 0, fmt.Errorf("actual_position must be finite")
	}
	expected := s.Master*s.Ratios[axis] + s.Offsets[axis]
	errv := expected - actual
	s.Errors[axis] = errv
	if math.Abs(errv) > s.SkewLimit {
		s.Healthy = false
	}
	return clampFloat(s.Kp*errv, -s.MaxCorrection, s.MaxCorrection), nil
}

var machineEtherCATCommands = map[string]byte{"NOP": 0x00, "APRD": 0x01, "APWR": 0x02, "APRW": 0x03, "FPRD": 0x04, "FPWR": 0x05, "FPRW": 0x06, "BRD": 0x07, "BWR": 0x08, "BRW": 0x09, "LRD": 0x0a, "LWR": 0x0b, "LRW": 0x0c, "ARMW": 0x0d, "FRMW": 0x0e}

func machineEtherCATDatagram(command string, index, address, offset int, data []byte, irq int, more bool) ([]byte, error) {
	cmd, ok := machineEtherCATCommands[strings.ToUpper(command)]
	if !ok {
		return nil, fmt.Errorf("unsupported EtherCAT command")
	}
	if index < 0 || index > 255 || address < 0 || address > 65535 || offset < 0 || offset > 65535 || irq < 0 || irq > 65535 {
		return nil, fmt.Errorf("EtherCAT header field out of range")
	}
	if len(data) > 0x7ff {
		return nil, fmt.Errorf("EtherCAT datagram payload exceeds 2047 bytes")
	}
	out := make([]byte, 10+len(data)+2)
	out[0] = cmd
	out[1] = byte(index)
	binary.LittleEndian.PutUint16(out[2:4], uint16(address))
	binary.LittleEndian.PutUint16(out[4:6], uint16(offset))
	lf := uint16(len(data))
	if more {
		lf |= 0x8000
	}
	binary.LittleEndian.PutUint16(out[6:8], lf)
	binary.LittleEndian.PutUint16(out[8:10], uint16(irq))
	copy(out[10:], data)
	return out, nil
}
func machineEtherCATFrame(datagrams []byte) ([]byte, error) {
	if len(datagrams) > 0x7ff {
		return nil, fmt.Errorf("EtherCAT frame payload exceeds 2047 bytes")
	}
	out := make([]byte, 2+len(datagrams))
	binary.LittleEndian.PutUint16(out[:2], uint16(len(datagrams))|(1<<12))
	copy(out[2:], datagrams)
	return out, nil
}
func machineEtherCATLRW(index int, address int64, data []byte) ([]byte, error) {
	if address < 0 || address > 0xffffffff {
		return nil, fmt.Errorf("EtherCAT logical address must be 0..0xffffffff")
	}
	dg, e := machineEtherCATDatagram("LRW", index, int(address&0xffff), int((address>>16)&0xffff), data, 0, false)
	if e != nil {
		return nil, e
	}
	return machineEtherCATFrame(dg)
}
func machineEtherCATFirstDatagramJSON(frame []byte) (string, error) {
	if len(frame) < 14 {
		return "", fmt.Errorf("EtherCAT frame is too short")
	}
	h := binary.LittleEndian.Uint16(frame[:2])
	length := int(h & 0x7ff)
	typ := (h >> 12) & 0xf
	if typ != 1 || length+2 > len(frame) {
		return "", fmt.Errorf("invalid EtherCAT frame header")
	}
	cmd := frame[2]
	index := int(frame[3])
	address := int(binary.LittleEndian.Uint16(frame[4:6]))
	offset := int(binary.LittleEndian.Uint16(frame[6:8]))
	lf := binary.LittleEndian.Uint16(frame[8:10])
	irq := int(binary.LittleEndian.Uint16(frame[10:12]))
	dataLen := int(lf & 0x7ff)
	end := 12 + dataLen
	if end+2 > len(frame) {
		return "", fmt.Errorf("truncated EtherCAT datagram")
	}
	name := fmt.Sprintf("0x%02x", cmd)
	for k, v := range machineEtherCATCommands {
		if v == cmd {
			name = k
			break
		}
	}
	b, _ := json.Marshal(map[string]any{"command": name, "index": index, "address": address, "offset": offset, "length": dataLen, "more": lf&0x8000 != 0, "irq": irq, "data_hex": hex.EncodeToString(frame[12:end]), "working_counter": int(binary.LittleEndian.Uint16(frame[end : end+2]))})
	return string(b), nil
}

func machineAllocationFreeProfileJSON() string {
	return `{"profile":"mcu-control-0.47","saga_visible_heap_allocation_in_tick":"forbidden","preallocate_state_before_tick":true,"bounded_loops_required":true,"blocking_io_in_tick":"forbidden","async_in_tick":"forbidden","host_reference_runtime_hard_realtime":false,"target_backend_must_prove_no_allocator_calls":true}`
}
