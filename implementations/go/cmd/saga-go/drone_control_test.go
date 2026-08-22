package main

import (
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"math"
	"testing"
)

func droneDecimal(t *testing.T, s string) Value {
	t.Helper()
	v, err := newNumber(s, "decimal")
	if err != nil {
		t.Fatal(err)
	}
	return v
}

func TestDroneMAVLinkSignedRoundTrip(t *testing.T) {
	key := make([]byte, 32)
	for i := range key {
		key[i] = byte(i)
	}
	frame, err := mavlinkEncodeSigned(200, 33, []byte("abc"), 9, 42, 10, key, 3, 123456)
	if err != nil {
		t.Fatal(err)
	}
	info, err := mavlinkVerify(frame, 33, key, 123456)
	if err != nil {
		t.Fatal(err)
	}
	if info["message_id"].(int) != 200 || info["link_id"].(int) != 3 {
		t.Fatalf("unexpected info: %#v", info)
	}
	bad := append([]byte{}, frame...)
	bad[len(bad)-1] ^= 1
	if _, err := mavlinkVerify(bad, 33, key, 0); err == nil {
		t.Fatal("expected signature rejection")
	}
}

func TestDroneHeartbeatCRCRejectsMutation(t *testing.T) {
	frame, err := mavlinkHeartbeat(7, 1, 1, 2, 3, 0x81, 0, 4)
	if err != nil {
		t.Fatal(err)
	}
	info, err := mavlinkDecode(frame, 50)
	if err != nil {
		t.Fatal(err)
	}
	if info["message_id"].(int) != 0 {
		t.Fatalf("wrong heartbeat info: %#v", info)
	}
	frame[10] ^= 1
	if _, err := mavlinkDecode(frame, 50); err == nil {
		t.Fatal("expected CRC rejection")
	}
}

func TestDroneFlightManagerAndMixer(t *testing.T) {
	s := &MachineSafety{}
	f, err := newDroneFlightManager(s, 0.2)
	if err != nil {
		t.Fatal(err)
	}
	f.EstimatorHealthy, f.PositionHealthy, f.HomeSet = true, true, true
	f.BatteryFraction, f.RCLink, f.DataLink = 0.8, true, true
	if err := f.arm(true); err != nil {
		t.Fatal(err)
	}
	if !f.allowed() {
		t.Fatal("flight should be allowed")
	}
	f.EstimatorHealthy = false
	f.PositionHealthy = false
	f.BatteryFraction = 0.01
	f.RCLink, f.DataLink = false, false
	if !f.allowed() || f.State != "ARMED" || f.Mode != "ATTITUDE" {
		t.Fatalf("health telemetry must not trigger an automatic transition: %#v", f)
	}
	if err := f.setMode("RTL"); err != nil {
		t.Fatal(err)
	}
	if f.Mode != "RTL" {
		t.Fatalf("explicit mode change failed: %#v", f)
	}
	m := &droneMixer{Idle: 0.05, Maximum: 1}
	o, err := m.mix(0.7, 0.4, 0.3, 0.2)
	if err != nil {
		t.Fatal(err)
	}
	if len(o) != 4 {
		t.Fatalf("wrong motor count: %v", o)
	}
	for _, v := range o {
		if v < 0.05 || v > 1 {
			t.Fatalf("out of range motor output %v", o)
		}
	}
}

func TestDroneInterpreterSurface(t *testing.T) {
	src := `
use machine
use drone
let safety = machine.safety_latch()
let flight = drone.flight_manager(safety, 0.2)
drone.health_update(flight, true, true, 0.8, true, true, true)
drone.arm(flight, true)
print(drone.flight_allowed(flight))
let mixer = drone.quad_x_mixer(0.05, 1.0)
print(len(drone.mix_quad_x(mixer, 0.5, 0.0, 0.0, 0.0)))
let fence = drone.geofence(35.0, 139.0, 100.0, 0.0, 120.0)
print(drone.geofence_contains(fence, 35.0, 139.0, 10.0))
let hb = drone.mavlink_heartbeat(1, 1, 1, 2, 3, 0, 0, 4)
print(len(hb) > 12)
`
	out, err := runSagaForTest(t, src)
	if err != nil {
		t.Fatal(err)
	}
	if got, want := out, "true\n4\ntrue\ntrue"; got != want {
		t.Fatalf("got %q want %q", got, want)
	}
}

func TestDroneJSONState(t *testing.T) {
	s := &MachineSafety{}
	f, _ := newDroneFlightManager(s, 0.2)
	b, _ := json.Marshal(map[string]any{"state": f.State, "flight_allowed": f.allowed()})
	var got map[string]any
	if err := json.Unmarshal(b, &got); err != nil {
		t.Fatal(err)
	}
	if got["state"] != "DISARMED" {
		t.Fatalf("%v", got)
	}
}

func TestDroneExplicitRTLAndDroneCAN(t *testing.T) {
	s := &MachineSafety{}
	f, err := newDroneFlightManager(s, 0.2)
	if err != nil {
		t.Fatal(err)
	}
	f.EstimatorHealthy, f.PositionHealthy, f.HomeSet = true, true, true
	f.BatteryFraction, f.RCLink, f.DataLink = 0.8, false, false
	f.State = "ARMED"
	if err := f.setMode("RTL"); err != nil {
		t.Fatal(err)
	}
	if f.State != "ARMED" || f.Mode != "RTL" {
		t.Fatalf("explicit RTL mode failed: %#v", f)
	}

	r := &droneRTLPlanner{HomeLat: 35, HomeLon: 139, HomeAlt: 5, ReturnAlt: 30, Acceptance: 2}
	j, err := r.targetJSON(35.001, 139, 10)
	if err != nil {
		t.Fatal(err)
	}
	var target map[string]any
	if err := json.Unmarshal([]byte(j), &target); err != nil {
		t.Fatal(err)
	}
	if target["phase"] != "CLIMB" {
		t.Fatalf("unexpected target: %v", target)
	}

	if got := droneCANCRC16([]byte("123456789")); got != 0x29b1 {
		t.Fatalf("CRC got %#x", got)
	}
	enc, err := droneCANSingleFrame(16, 341, 42, 7, []byte("abc"))
	if err != nil {
		t.Fatal(err)
	}
	if enc["can_id"].(int) != (16<<24)|(341<<8)|42 {
		t.Fatalf("bad CAN ID: %v", enc)
	}
	data, _ := hex.DecodeString(enc["data_hex"].(string))
	dec, err := droneCANSingleFrameDecode(enc["can_id"].(int), data)
	if err != nil {
		t.Fatal(err)
	}
	if dec["payload_hex"] != "616263" || dec["transfer_id"].(int) != 7 {
		t.Fatalf("bad decode: %v", dec)
	}
}

func TestDroneQuaternionController(t *testing.T) {
	ctl := &droneQuaternionController{KpRoll: 4, KpPitch: 4, KpYaw: 2, MaxRate: 3}
	target, err := droneQuaternionFromRPY(0.2, -0.1, 0.3)
	if err != nil {
		t.Fatal(err)
	}
	current, _ := droneQuaternionFromRPY(0, 0, 0)
	rates, err := ctl.step(target, current)
	if err != nil {
		t.Fatal(err)
	}
	for _, v := range rates {
		if math.Abs(v) > 3 {
			t.Fatalf("rate out of range: %v", rates)
		}
	}
	for j := range target {
		target[j] = -target[j]
	}
	rates2, err := ctl.step(target, current)
	if err != nil {
		t.Fatal(err)
	}
	for j := 0; j < 3; j++ {
		if math.Abs(rates[j]-rates2[j]) > 1e-12 {
			t.Fatalf("quaternion sign changed result: %v vs %v", rates, rates2)
		}
	}
}

func TestDroneCANMultiFrame(t *testing.T) {
	sig, _ := hex.DecodeString("8877665544332211")
	payload := []byte("0123456789abcdef")
	frames, err := droneCANMultiFrame(8, 20000, 10, 5, sig, payload)
	if err != nil {
		t.Fatal(err)
	}
	if len(frames) < 2 {
		t.Fatalf("expected multiframe: %v", frames)
	}
	var stream []byte
	for j, f := range frames {
		data, _ := hex.DecodeString(f["data_hex"].(string))
		tail := data[len(data)-1]
		if j == 0 && tail&0x80 == 0 {
			t.Fatal("first frame missing SOT")
		}
		if j == len(frames)-1 && tail&0x40 == 0 {
			t.Fatal("last frame missing EOT")
		}
		if ((tail & 0x20) != 0) != (j%2 == 1) {
			t.Fatalf("bad toggle at %d", j)
		}
		stream = append(stream, data[:len(data)-1]...)
	}
	crc := droneCANCRC16(append(append([]byte{}, sig...), payload...))
	if len(stream) < 2 || binary.LittleEndian.Uint16(stream[:2]) != crc || string(stream[2:]) != string(payload) {
		t.Fatalf("bad transfer stream %x", stream)
	}
}

func TestDroneMAVLinkOffboardBuildersAndStream(t *testing.T) {
	q := [4]float64{1, 0, 0, 0}
	rates := [3]float64{0.1, -0.2, 0.3}
	att, err := mavlinkSetAttitudeTarget(7, 245, 190, 1, 1, 0, q, rates, 0.55, 1234)
	if err != nil {
		t.Fatal(err)
	}
	info, err := mavlinkCommonDecode(att)
	if err != nil {
		t.Fatal(err)
	}
	if info["message_id"].(int) != 82 || len(att) != 51 {
		t.Fatalf("bad attitude target: %v len=%d", info, len(att))
	}

	pos, err := mavlinkSetPositionTargetLocalNED(8, 245, 190, 1, 1, 1, 0, [3]float64{1, 2, -3}, [3]float64{0.1, 0.2, 0.3}, [3]float64{}, 0.4, 0, 2000)
	if err != nil {
		t.Fatal(err)
	}
	if len(pos) != 65 {
		t.Fatalf("bad position target length %d", len(pos))
	}

	params := [7]float64{1, 2, 3, 4, 5, 6, 7}
	cmd, err := mavlinkCommandLong(9, 245, 190, 1, 1, 400, 0, params)
	if err != nil {
		t.Fatal(err)
	}
	if len(cmd) != 45 {
		t.Fatalf("bad command length %d", len(cmd))
	}

	stream := &droneMavlinkStream{}
	if got := stream.feed(att[:9]); len(got) != 0 {
		t.Fatalf("partial frame emitted: %v", got)
	}
	got := stream.feed(append(att[9:], pos...))
	if len(got) != 2 || got[0]["message_id"].(int) != 82 || got[1]["message_id"].(int) != 84 {
		t.Fatalf("bad stream output: %v", got)
	}
}

func TestDroneDShotAndPWMHelpers(t *testing.T) {
	word, err := droneDShotFrame(0.5, false)
	if err != nil {
		t.Fatal(err)
	}
	packet := word >> 4
	data := packet
	checksum := 0
	for j := 0; j < 3; j++ {
		checksum ^= data
		data >>= 4
	}
	if word&0xf != checksum&0xf {
		t.Fatalf("DShot checksum mismatch %#x", word)
	}
	duty, err := dronePWMESCDuty(0.5, 1000, 2000, 20000)
	if err != nil {
		t.Fatal(err)
	}
	if math.Abs(duty-0.075) > 1e-12 {
		t.Fatalf("PWM duty %v", duty)
	}
}
