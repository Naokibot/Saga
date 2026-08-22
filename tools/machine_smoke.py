from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
SAGA = [sys.executable, str(ROOT / "saga.py")]


def run(file: Path, *args: str, input_text: str | None = None) -> str:
    result = subprocess.run(
        [*SAGA, "run", str(file), *args],
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
        cwd=ROOT,
    )
    return result.stdout.strip()


def write_program(root: Path, name: str, source: str) -> Path:
    path = root / name
    path.write_text(source, encoding="utf-8")
    return path


def tcp_echo_server() -> tuple[int, threading.Thread]:
    ready = threading.Event(); holder: list[int] = []
    def worker():
        with socket.socket() as server:
            server.bind(("127.0.0.1", 0)); server.listen(1)
            holder.append(server.getsockname()[1]); ready.set()
            conn, _ = server.accept()
            with conn: conn.sendall(conn.recv(1024))
    thread = threading.Thread(target=worker, daemon=True); thread.start(); ready.wait(5)
    return holder[0], thread


def udp_echo_server() -> tuple[int, threading.Thread]:
    ready = threading.Event(); holder: list[int] = []
    def worker():
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server:
            server.bind(("127.0.0.1", 0)); holder.append(server.getsockname()[1]); ready.set()
            data, address = server.recvfrom(1024); server.sendto(data, address)
    thread = threading.Thread(target=worker, daemon=True); thread.start(); ready.wait(5)
    return holder[0], thread


def main() -> int:
    results: dict[str, object] = {
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "tests": {},
    }
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()

        basic = write_program(root, "basic.saga", 'print(0.1 + 0.2 == 0.3, 1 / 3 + 1 / 6)')
        results["tests"]["exact_numbers"] = run(basic)

        io_db = write_program(root, "io_db.saga", f'''
use io
use db
io.write_text("{root / 'note.txt'}", "Saga")
let conn = db.open("{root / 'smoke.db'}")
db.execute(conn, "create table values_table(value text)", [])
db.execute(conn, "insert into values_table(value) values (?)", [io.read_text("{root / 'note.txt'}")])
db.commit(conn)
print(map_get(db.query(conn, "select value from values_table", [])[0], "value", ""))
db.close(conn)
''')
        results["tests"]["file_sqlite"] = run(
            io_db, "--allow-read", str(root), "--allow-write", str(root), "--allow-db", str(root)
        )

        tcp_port, tcp_thread = tcp_echo_server()
        tcp = write_program(root, "tcp.saga", f'''
use net
use io
let connection = net.tcp_connect("127.0.0.1", {tcp_port})
net.send(connection, io.encode("TCP_OK"))
print(io.decode(net.receive(connection, 64)))
net.close(connection)
''')
        results["tests"]["tcp"] = run(tcp, "--allow-net", f"127.0.0.1:{tcp_port}")
        tcp_thread.join(5)

        udp_port, udp_thread = udp_echo_server()
        udp = write_program(root, "udp.saga", f'''
use net
use io
let connection = net.udp()
net.udp_send(connection, io.encode("UDP_OK"), "127.0.0.1", {udp_port})
print(io.decode(net.udp_receive(connection, 64)))
net.close(connection)
''')
        results["tests"]["udp"] = run(udp, "--allow-net", f"127.0.0.1:{udp_port}")
        udp_thread.join(5)

        crypto = write_program(root, "crypto.saga", '''
use crypto
use io
let key = crypto.random(32)
let encrypted = crypto.aes_encrypt(key, io.encode("AES_OK"))
print(io.decode(crypto.aes_decrypt(key, encrypted)))
''')
        results["tests"]["aes_gcm"] = run(crypto)

        process_program = write_program(root, "process.saga", f'''
use process
let result = process.run("{sys.executable}", ["-c", "print(40 + 2)"], 10)
print(map_get(result, "code", -1))
print(map_get(result, "stdout", ""))
''')
        results["tests"]["process"] = run(process_program, "--allow-process").replace("\n\n", "\n")

        try:
            from websockets.sync.server import serve

            def echo(websocket):
                websocket.send(websocket.recv())

            server = serve(echo, "127.0.0.1", 0)
            ws_port = server.socket.getsockname()[1]
            ws_thread = threading.Thread(target=server.serve_forever, daemon=True)
            ws_thread.start()
            ws_program = write_program(root, "websocket.saga", f'''
use websocket
let connection = websocket.connect("ws://127.0.0.1:{ws_port}")
websocket.send(connection, "WS_OK")
print(websocket.receive(connection))
websocket.close(connection)
''')
            results["tests"]["websocket"] = run(ws_program, "--allow-net", f"127.0.0.1:{ws_port}")
            server.shutdown(); ws_thread.join(5)
        except Exception as exc:
            results["tests"]["websocket"] = f"SKIP: {exc}"

        media_available = {}
        try:
            from PIL import Image
            image_path = root / "source.png"; Image.new("RGB", (8, 6), (20, 40, 60)).save(image_path)
            image_program = write_program(root, "image.saga", f'''
use image
let source = image.open("{image_path}")
let small = image.resize(source, 4, 3)
image.save(small, "{root / 'small.png'}")
print(image.width(small), image.height(small))
''')
            media_available["image"] = run(image_program, "--allow-read", str(root), "--allow-write", str(root))
        except Exception as exc:
            media_available["image"] = f"SKIP: {exc}"

        try:
            import cv2
            import numpy as np
            video_path = root / "source.avi"
            writer = cv2.VideoWriter(str(video_path), cv2.VideoWriter_fourcc(*"MJPG"), 5.0, (16, 16))
            for value in (0, 80, 160): writer.write(np.full((16, 16, 3), value, dtype=np.uint8))
            writer.release()
            video_program = write_program(root, "video.saga", f'''
use video
let source = video.open("{video_path}")
print(video.frame_count(source))
video.close(source)
''')
            media_available["video"] = run(video_program, "--allow-read", str(root))
        except Exception as exc:
            media_available["video"] = f"SKIP: {exc}"
        results["tests"]["media"] = media_available

        results["tests"]["othello"] = run(ROOT / "examples" / "othello" / "othello_selfplay.saga")

    out = ROOT / "validation" / "machine-smoke-0.38.0.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
