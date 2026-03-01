#!/usr/bin/env python3
import asyncio
import os
import signal
import argparse
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import websockets


def _get_path(websocket, maybe_path):
    """
    websockets library changed handler signatures across versions:
      - some call handler(websocket)
      - older call handler(websocket, path)

    This makes us compatible with both.
    """
    if maybe_path:
        return maybe_path

    # Try common attributes across versions
    for attr in ("path",):
        v = getattr(websocket, attr, None)
        if isinstance(v, str) and v:
            return v

    # Newer versions may store request info differently
    req = getattr(websocket, "request", None)
    if req is not None:
        p = getattr(req, "path", None)
        if isinstance(p, str) and p:
            return p

    return "/"


async def _send_file_history(ws, file_path: str):
    name = Path(file_path).name
    try:
        # stream file contents line by line (safe for large files)
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.rstrip("\n")
                if line:
                    await ws.send(f"[{name}] {line}")
    except Exception as e:
        await ws.send(f"[{name}] ERROR reading history: {e}")


async def _tail_file(ws, file_path: str):
    """
    tails a file and streams new lines as they arrive.
    """
    name = Path(file_path).name

    # -n 0 => start at end (live only)
    # -F => follow name (handles rotate)
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
    # ✅ signature-safe
    path = _get_path(websocket, path)

    parsed = urlparse(path)
    params = parse_qs(parsed.query)
    mode = (params.get("mode", ["live"])[0] or "live").lower()  # default live

    # Gather all log files from folder
    files = sorted(
        str(Path(log_dir) / f)
        for f in os.listdir(log_dir)
        if os.path.isfile(os.path.join(log_dir, f))
    )

    await websocket.send(f"✅ Connected. mode={mode}. files={len(files)}")
    if not files:
        await websocket.send("⚠️ No log files found in devices folder.")
        return

    # 🥈 Mode 2: dump history then stream
    if mode == "full":
        await websocket.send("📦 MODE=full: dumping existing logs first...")
        for fp in files:
            await _send_file_history(websocket, fp)
        await websocket.send("------ LIVE STREAM STARTED ------")

    # 🥇 Mode 1: live only
    tails = []
    try:
        for fp in files:
            tails.append(asyncio.create_task(_tail_file(websocket, fp)))

        # wait until client disconnects or task errors
        done, pending = await asyncio.wait(
            tails,
            return_when=asyncio.FIRST_EXCEPTION,
        )
        for t in done:
            exc = t.exception()
            if exc:
                raise exc
    finally:
        for t in tails:
            t.cancel()


async def main(host: str, port: int, log_dir: str):
    async def handler(websocket, path=None):
        return await stream_logs(websocket, path, log_dir=log_dir)

    print(f"🟢 Device log streaming server starting on {host}:{port}")
    print(f"📁 Log dir: {log_dir}")

    async with websockets.serve(handler, host, port):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--log-dir", default="/AutonomousSync/logs/devices")
    args = parser.parse_args()

    # nicer shutdown
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: (_ for _ in ()).throw(SystemExit))

    asyncio.run(main(args.host, args.port, args.log_dir))