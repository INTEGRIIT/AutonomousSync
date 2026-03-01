import asyncio
import websockets
import subprocess
import os
from urllib.parse import urlparse, parse_qs
from pathlib import Path

LOG_DIR = "/AutonomousSync/logs/devices"

async def stream_logs(websocket, path):
    parsed = urlparse(path)
    params = parse_qs(parsed.query)

    mode = params.get("mode", ["live"])[0]  # default = live

    files = [
        os.path.join(LOG_DIR, f)
        for f in os.listdir(LOG_DIR)
        if os.path.isfile(os.path.join(LOG_DIR, f))
    ]

    # 🟡 MODE 2: Dump history first
    if mode == "full":
        for file_path in files:
            try:
                with open(file_path, "r") as f:
                    for line in f:
                        await websocket.send(
                            f"[{Path(file_path).name}] {line.strip()}"
                        )
            except Exception as e:
                await websocket.send(f"Error reading {file_path}: {e}")

        await websocket.send("----- LIVE STREAM STARTED -----")

    # 🟢 MODE 1: Live stream only (default)
    processes = []

    for file_path in files:
        process = subprocess.Popen(
            ["tail", "-F", file_path],
            stdout=subprocess.PIPE,
            text=True,
        )
        processes.append((process, file_path))

    try:
        while True:
            for process, file_path in processes:
                line = process.stdout.readline()
                if line:
                    await websocket.send(
                        f"[{Path(file_path).name}] {line.strip()}"
                    )
            await asyncio.sleep(0.05)
    finally:
        for process, _ in processes:
            process.kill()

async def main():
    async with websockets.serve(stream_logs, "0.0.0.0", 8766):
        print("🟢 Device log server running on port 8766")
        await asyncio.Future()

asyncio.run(main())