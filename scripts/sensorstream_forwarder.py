#!/usr/bin/env python3
import asyncio
import os
import signal
import argparse
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import websockets


def _get_path(websocket, maybe_path):
    if maybe_path:
        return maybe_path

    v = getattr(websocket, "path", None)
    if isinstance(v, str) and v:
        return v

    req = getattr(websocket, "request", None)
    if req is not None:
        p = getattr(req, "path", None)
        if isinstance(p, str) and p:
            return p

    return "/"


async def _send_file_history(ws, file_path: str):
    name = Path(file_path).name
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.rstrip("\n")
                if line:
                    await ws.send(f"[{name}] {line}")
    except Exception as e:
        await ws.send(f"[{name}] ERROR reading history: {e}")


async def _tail_file(ws, file_path: str):
    name = Path(file_path).name

    proc = await asyncio.create_subprocess_exec(
        "tail", "-n", "0", "-F", file_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        while True:
            line = await proc.stdout.readline()
            if not line:
                await asyncio.sleep(0.05)
                continue
            text = line.decode("utf-8", errors="replace").rstrip("\n")
            if text:
                await ws.send(f"[{name}] {text}")
    finally:
        try:
            proc.terminate()
        except Exception:
            pass
        try:
            await proc.wait()
        except Exception:
            pass


async def stream_logs(websocket, path=None, *, log_dir: str):
    path = _get_path(websocket, path)

    parsed = urlparse(path)
    params = parse_qs(parsed.query)

    mode = (params.get("mode", ["live"])[0] or "live").lower()
    device_filter = params.get("device", [None])[0]

    await websocket.send(f"✅ Connected. mode={mode}. device_filter={device_filter}")

    active_tails = {}
    known_files = set()

    async def scan_and_tail():
        files = sorted(
            str(Path(log_dir) / f)
            for f in os.listdir(log_dir)
            if os.path.isfile(os.path.join(log_dir, f))
        )

        for fp in files:
            name = Path(fp).name

            if device_filter and device_filter not in name:
                continue

            if fp not in known_files:
                known_files.add(fp)

                if mode == "full":
                    await _send_file_history(websocket, fp)

                task = asyncio.create_task(_tail_file(websocket, fp))
                active_tails[fp] = task
                await websocket.send(f"📡 Now streaming: {name}")

    try:
        while True:
            await scan_and_tail()
            await asyncio.sleep(1)
    finally:
        for task in active_tails.values():
            task.cancel()


async def main(host: str, port: int, log_dir: str):
    async def handler(websocket, path=None):
        return await stream_logs(websocket, path, log_dir=log_dir)

    print(f"🟢 Device log streaming server starting on {host}:{port}")
    print(f"📁 Log dir: {log_dir}")

    async with websockets.serve(handler, host, port):
        await asyncio.Future()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--log-dir", default="/home/ubuntu/AutonomousSync/logs/devices")
    args = parser.parse_args()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: (_ for _ in ()).throw(SystemExit))

    asyncio.run(main(args.host, args.port, args.log_dir))