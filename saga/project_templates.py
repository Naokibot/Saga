from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectTemplate:
    description: str
    files: dict[str, str]


TEMPLATES: dict[str, ProjectTemplate] = {
    "basic": ProjectTemplate(
        "基本的なコンソールアプリ",
        {"main.saga": 'let name = "Saga"\nprint("Hello from", name)\n'},
    ),
    "web": ProjectTemplate(
        "REST API / HTTPサーバー",
        {
            "main.saga": '''use http
use json

fn handle(request: http_request) -> http_response {
    if http.request_path(request) == "/health" {
        return http.response(200, json.encode(map_of("status", "ok")), "application/json; charset=utf-8")
    }
    return http.response(404, "Not Found", "text/plain; charset=utf-8")
}

let server = http.serve("127.0.0.1", 8080, handle)
print("http://127.0.0.1:8080")
http.wait(server)
''',
            "README.md": "Run: saga run main.saga --allow-net 127.0.0.1\n",
        },
    ),
    "desktop": ProjectTemplate(
        "イベント駆動のデスクトップGUI",
        {
            "main.saga": '''use ui

let window = ui.window("Saga Desktop", 480, 260)
let message = ui.label(window, "Hello, Saga")
let input = ui.input(window, "名前")

fn clicked() -> unit {
    ui.set(message, "Hello, " + ui.get(input))
}

ui.button(window, "表示", clicked)
ui.run(window)
''',
            "README.md": "Run: saga run main.saga --allow-ui\n",
        },
    ),
    "microservice": ProjectTemplate(
        "HTTP・SQLite・JSONを使うマイクロサービス",
        {
            "main.saga": '''use http
use json
use db

let database = db.open("service.db")
db.execute(database, "CREATE TABLE IF NOT EXISTS notes(id INTEGER PRIMARY KEY, body TEXT NOT NULL)", [])

fn handle(request: http_request) -> http_response {
    if http.request_path(request) == "/notes" {
        let rows = db.query(database, "SELECT id, body FROM notes ORDER BY id", [])
        return http.response(200, json.encode(rows), "application/json; charset=utf-8")
    }
    return http.response(404, "Not Found", "text/plain; charset=utf-8")
}

let server = http.serve("127.0.0.1", 8080, handle)
http.wait(server)
''',
            "README.md": "Run: saga run main.saga --allow-net 127.0.0.1 --allow-db .\n",
        },
    ),
    "batch": ProjectTemplate(
        "CSV・DB・例外処理を使うバッチ",
        {
            "main.saga": '''use data
use io

try {
    let rows = data.csv_read("input.csv")
    io.write_text("count.txt", text(len(rows)))
    print("processed", len(rows), "rows")
} catch error {
    print("batch failed:", error.message)
}
''',
            "README.md": "Run: saga run main.saga --allow-read . --allow-write .\n",
        },
    ),
    "science": ProjectTemplate(
        "高精度計算・数値解析",
        {"main.saga": '''use science
precision(100)
let xs = science.linspace(0.0, 1.0, 11)
print(xs)
print("sqrt(2) =", sqrt(2))
'''},
    ),
    "game": ProjectTemplate(
        "Pygameアダプターを使うゲームプロジェクト",
        {
            "main.saga": '''use game
if game.available() {
    game.run_demo("Saga Game", 800, 450)
} else {
    print("pip install 'saga-language[game]' を実行してください")
}
''',
            "README.md": "Install extras: pip install 'saga-language[game]'\nRun: saga run main.saga --allow-ui\n",
        },
    ),
    "iot": ProjectTemplate(
        "Raspberry Pi / GPIO制御",
        {
            "main.saga": '''use gpio
use time
let led = gpio.output(17)
gpio.on(led)
time.sleep(1.0)
gpio.off(led)
gpio.close(led)
''',
            "README.md": "Install extras: pip install 'saga-language[iot]'\n",
        },
    ),
    "machine": ProjectTemplate(
        "安全ラッチ・軸制御・Modbusを使う機械制御プロジェクト",
        {
            "main.saga": '''use machine

let safety = machine.safety_latch()
let axis = machine.axis(0.0, -180.0, 180.0, 90.0, 180.0, 0.8, 0.05, 0.01, 20.0, safety)
machine.axis_target(axis, 90.0)

var measured = 0.0
var i = 0
while i < 200 and not machine.axis_done(axis, measured) {
    let command = machine.axis_step(axis, measured, 0.01)
    // Safe simulation: a real system should replace this with an encoder read
    // and send command to a drive/PLC through a guarded hardware adapter.
    measured = machine.axis_planned_position(axis)
    print(measured, command)
    i = i + 1
}

print("safe=", not machine.safety_tripped(safety))
''',
            "README.md": """# Saga machine-control starter\n\nRun the simulation first: `saga run main.saga`.\n\nPhysical adapters are deny-by-default. Use `--allow-device` only after wiring an independent E-stop/interlock chain. Modbus TCP additionally requires an explicit `--allow-net host:port` grant in the Python hosted runtime. Saga 0.40 is hosted soft real-time; hard real-time current/position loops belong on an MCU, RTOS, servo drive, or safety PLC.\n""",
        },
    ),
    "drone": ProjectTemplate(
        "SITL-firstのドローン飛行制御・MAVLink/DroneCANプロジェクト",
        {
            "main.saga": r'''use machine
use drone

// Safe starter: no physical actuator is opened. Validate the controller in SITL
// before attaching ESCs, motors, propellers, or a real aircraft.
let safety = machine.safety_latch()
let flight = drone.flight_manager(safety, 0.25)
drone.health_update(flight, true, true, 1.0, true, true, true)
drone.arm(flight, true)
drone.set_mode(flight, "ATTITUDE")

let attitude = drone.quaternion_controller(4.0, 4.0, 2.0, 3.0)
let rates = drone.rate_controller(0.5, 0.08, 0.01, 0.35)
let mixer = drone.quad_x_mixer(0.05, 1.0)
let desired = drone.quaternion_from_rpy(0.0, 0.0, 0.0)
let current = drone.quaternion_from_rpy(0.0, 0.0, 0.0)
let desired_rates = drone.quaternion_step(attitude, desired, current)
let torque = drone.rate_step(rates, desired_rates, [0.0, 0.0, 0.0], 0.01)
print(drone.mix_quad_x(mixer, 0.5, torque[0], torque[1], torque[2]))

let fence = drone.geofence(35.0, 139.0, 120.0, 0.0, 120.0)
print("inside geofence=", drone.geofence_contains(fence, 35.0, 139.0, 10.0))

let rtl = drone.rtl(35.0, 139.0, 5.0, 30.0, 2.0)
print(drone.rtl_target_json(rtl, 35.001, 139.0, 10.0))

let heartbeat = drone.mavlink_heartbeat(0, 245, 190, 18, 8, 0, 0, 3)
print("MAVLink heartbeat bytes=", len(heartbeat))

// Practical companion/offboard output. This only builds the standard MAVLink
// frame; send it through net.udp_* or machine.uart_* after configuring a real autopilot.
let setpoint = drone.mavlink_set_attitude_target(1, 245, 190, 1, 1, 7, [1.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0], 0.5, 0)
print("SET_ATTITUDE_TARGET bytes=", len(setpoint))

let node_status_payload = machine.bytes_from_hex("00000000000000")
print(drone.dronecan_single_frame_json(16, 341, 42, 0, node_status_payload))
''',
            "README.md": """# Saga drone-control starter

Start with `saga run main.saga`. This starter deliberately performs no physical motor/ESC output.

The `drone` standard module provides attitude/rate/position control, jerk-limited 3D trajectories, Quad-X/general allocation, link-quality monitoring, mission/geofence and explicit RTL/landing helpers, MAVLink 2 common offboard messages/framing/signing/stream parsing, and DroneCAN transport helpers. The `vision` module adds NMS/tracking/camera geometry plus optional OpenCV-backed ArUco/ONNX processing. It does not automatically select RTL, LAND, or DISARM from link, battery, estimator, geofence, or vision state.

For practical flight use, prefer Saga as a companion/offboard controller connected to PX4 or ArduPilot over MAVLink. Direct ESC/motor stabilization from the hosted runtime is not qualified because Saga is soft real-time and does not provide a production EKF or hardware-timed DShot waveform backend. Connect real sensors/ESCs only through guarded `machine` adapters after SITL/HIL testing.
""",
        },
    ),
    "android": ProjectTemplate(
        "Briefcase/TogaホストでSagaをAndroidへ同梱するプロジェクト",
        {
            "app/main.saga": 'print("Hello from Saga on Android")\n',
            "app/app.py": '''from pathlib import Path
import toga
from saga import run_source


class SagaAndroidApp(toga.App):
    def startup(self):
        output = []
        source = (Path(__file__).with_name("main.saga")).read_text(encoding="utf-8")
        run_source(source, filename="main.saga", output=output.append)
        box = toga.Box(children=[toga.Label("\\n".join(output))])
        self.main_window = toga.MainWindow(title=self.formal_name)
        self.main_window.content = box
        self.main_window.show()


def main():
    return SagaAndroidApp("Saga Android", "dev.saga.android")
''',
            "pyproject.toml": '''[build-system]
requires = ["briefcase"]
build-backend = "briefcase"

[tool.briefcase]
project_name = "Saga Android"
bundle = "dev.saga"
version = "0.1.0"

[tool.briefcase.app.sagaandroid]
formal_name = "Saga Android"
description = "Saga language Android host"
sources = ["app"]
requires = ["saga-language==0.50.0", "toga-android"]
''',
            "README.md": "Install Briefcase, then run: briefcase create android && briefcase build android && briefcase run android\nAndroid SDK/Java tooling is required.\n",
        },
    ),
}
