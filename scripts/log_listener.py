import asyncio
import websockets
import sys
import signal

# ===============================
# CONFIG
# ===============================

EC2_IP = "YOUR_EC2_PUBLIC_IP"
PORT = 8765

# ===============================
# ARGUMENT PARSING
# ===============================

mode = "live"
limit = None

if len(sys.argv) > 1:
    mode = sys.argv[1]

if len(sys.argv) > 2:
    limit = sys.argv[2]

query = f"?mode={mode}"

if limit:
    query += f"&limit={limit}"

EC2_WS = f"ws://{EC2_IP}:{PORT}{query}"

# ===============================
# LISTENER
# ===============================

async def listen():
    print(f"🔌 Connecting to {EC2_WS}")

    try:
        async with websockets.connect(EC2_WS) as ws:
            print(f"🟢 Connected in {mode.upper()} mode\n")

            async for message in ws:
                print(message)

    except Exception as e:
        print("❌ Connection error:", e)


# ===============================
# GRACEFUL SHUTDOWN
# ===============================

def shutdown_handler(sig, frame):
    print("\n🛑 Listener stopped")
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown_handler)

# ===============================
# RUN
# ===============================

if __name__ == "__main__":
    asyncio.run(listen())