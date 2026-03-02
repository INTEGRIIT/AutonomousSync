backend/contracts/mobile_protocol.md

--------------------------------------------------
# Autonomous Sync – Mobile Integration Protocol
--------------------------------------------------

This document defines the official contract between all mobile clients
(React Native, Android Native, iOS Native) and the Autonomous Sync backend.

All clients MUST follow this specification exactly.

The backend is platform-agnostic and accepts JSON over WebSocket and HTTP.

--------------------------------------------------
# Core System Principle
--------------------------------------------------

# **Notification == Confirmed Backup**

A user notification MUST only be sent when the backend has successfully:
1) decided a sync is required, AND  
2) created/persisted the backup/snapshot artifact.

If backup persistence fails, the backend must NOT send a notification claiming a backup happened.

--------------------------------------------------
# 1 WebSocket Telemetry Stream
--------------------------------------------------

Endpoint:
    wss://api.autonomous-sync.com/ws/stream

Purpose:
    Continuous telemetry streaming for:
    - Motion classification
    - Impact detection
    - Water detection
    - Stability tracking
    - Sync decision logic

Required JSON Packet Schema:
{
  "device_uid": "string",
  "ts": 1234567890,
  "accel": { "x": 0.0, "y": 0.0, "z": 0.0 },
  "gyro": { "x": 0.0, "y": 0.0, "z": 0.0 },
  "touch": { "active": false },
  "moisture": { "value": null }
}

Field Definitions:

device_uid: Unique per-device identifier (string)

ts: Unix timestamp in milliseconds

accel: Accelerometer vector (required)

gyro: Gyroscope vector (required)

touch.active: Boolean user interaction state

moisture.value: Optional water sensor value (nullable)

Backend Response:

Server returns structured state output including:

{
  "ts": 1234567890,
  "device_uid": "string",
  "device_name": "string|null",
  "platform": "ios|android|null",

  "state": "STILL|MOVING|UNSTABLE|WATER_INTERACTION|USER_INTERACTION|...",
  "transition": "string",

  "decision": {
    "sync": true,
    "reason": "impact|water_detected|stable_window|...",
    "type": "GRACEFUL|EMERGENCY",
    "priority": "HIGH|LOW",
    "notify": true
  },

  "action": {},
  "features": {},
  "temporal": {},
  "water": {},
  "emergency": {},

  "push": { "sent": true }
}

Important Notes:

WebSocket is best-effort real-time, but NOT guaranteed when the app is backgrounded or terminated.

iOS will often close sockets when the app goes to background.

Therefore, emergency detection must exist on-device for real safety guarantees.

--------------------------------------------------
# 2 HTTP Health + Debug Endpoints
--------------------------------------------------

GET /health

Purpose:

Simple liveness check

Response:

{ "ok": true }

GET /state/latest

Purpose:

Get latest runtime output

Response:

{ "state": "STILL", "...": "..." }

GET /state/timeline?n=120

Purpose:

Get last N runtime outputs

Response:

{ "items": [ ... ] }

GET /logs/recent?n=50

Purpose:

Unified tail log (all devices)

Response:

{ "items": [ ... ] }

GET /logs/device/{device_uid}?n=200

Purpose:

Per-device log tail

Response:

{ "device_uid": "string", "items": [ ... ] }

--------------------------------------------------
# 3 Push Registration (All Clients)
--------------------------------------------------

POST /push/register

Purpose:

Register the device push token with backend.

Request Schema:

{
  "device_uid": "string",
  "device_name": "string",
  "platform": "ios|android",
  "push_token": "string"
}

Response:

{
  "ok": true,
  "device_uid": "string",
  "device_name": "string"
}

Notes:

iOS uses APNs token (hex string)

Android uses FCM token (future support)

Clients MUST re-register token when:

App reinstall happens

Token rotates

OS updates change token

User disables/re-enables notifications

--------------------------------------------------
# 4 Push Test Endpoint (Backend Debug Only)
--------------------------------------------------

POST /push/test

Purpose:

Confirm backend push delivery logic + APNs connectivity works.

Request:

{ "device_uid": "string" }

Response:

{ "ok": true, "device_uid": "string" }

Notes:

This is a debug endpoint.

It is NOT part of the safety system itself.

If /push/test works but “real” notifications don’t, the issue is usually:

sync decision never fires (sync=false)

notify is false

backup fails before notify

app logic never triggers emergency on device

--------------------------------------------------
# 5 Emergency Trigger (Device → Backend)
--------------------------------------------------

POST /emergency

Purpose:

Device-side emergency signal that does NOT rely on WebSocket.

Used for battery critical, failsafe triggers, and device-only sensors.

Request Schema:

{
  "device_uid": "string",
  "reason": "battery_critical|manual|impact|water|fallback",
  "priority": "HIGH|LOW"
}

Response:

{
  "ok": true,
  "device_uid": "string",
  "reason": "battery_critical",
  "queued": true
}

Backend Responsibilities:

Call SyncEngine.decide(...) with emergency override

Persist snapshot via BackupService

Send push notification if and only if snapshot succeeded

--------------------------------------------------
# 6 Snapshot / Backup Artifact Contract
--------------------------------------------------

A “backup” event must produce a durable artifact.

Minimum Snapshot Schema:

{
  "snapshot_id": "uuid",
  "device_uid": "string",
  "timestamp": 1234567890,

  "reason": "impact|water_detected|battery_critical|stable_window|manual",
  "priority": "HIGH|LOW",
  "type": "EMERGENCY|GRACEFUL",

  "state": "string",
  "decision": {},

  "features": {},
  "temporal": {},
  "water": {},
  "emergency": {},

  "battery": {
    "level": 0.80,
    "charging": false
  },

  "connectivity": {
    "ws_connected": true,
    "network": "wifi|cellular|unknown"
  }
}

Rules:

Snapshot MUST be written before push “backup created” notification.

Snapshot ID must be unique.

Snapshot must be durable (disk now, cloud later).

--------------------------------------------------
# 7 Client Runtime Responsibilities (Device Engines)
--------------------------------------------------

Device engines exist because the OS can stop background networking.

Minimum device engines:

EmergencyDetectionEngine

Detect impact/free-fall/water locally

Trigger POST /emergency immediately (does not depend on WebSocket)

BatteryProtectionEngine

Detect low battery threshold locally

Trigger POST /emergency with reason=battery_critical

Prevent shutdown data loss

PowerManager

Optimize sampling + send intervals

Preserve battery without reducing emergency detection reliability

ConnectivityEngine

Track ws connectivity state

Retry strategy + last successful send

Optional: queue emergency signals for HTTP retry

Important:

Device engines detect and trigger.

Backend engines decide, persist, and notify.

--------------------------------------------------
# 8 Backend Responsibilities (Decision + Alert Authority)
--------------------------------------------------

Backend engines are authoritative:
Feature extraction
Temporal inference
State machine classification
Sync decision policy
Snapshot persistence
Push delivery
Backend is the only layer that sends notifications.

--------------------------------------------------
# 9 Why WebSockets Close in Background (iOS Reality)
--------------------------------------------------

iOS aggressively suspends background apps and will:
pause JS execution
suspend network
close WebSockets
throttle timers

Therefore:
You cannot rely on background WebSocket streaming for safety.
Emergency detection must run locally and send HTTP triggers.
This is expected OS behavior, not a bug.

--------------------------------------------------
# 10 Versioning
--------------------------------------------------

Future production structure:

/api/v1/ws/stream
/api/v1/push/register
/api/v1/push/test
/api/v1/emergency
/api/v1/logs/recent
/api/v1/state/latest

This allows clean upgrades without breaking older clients.

--------------------------------------------------
# 11 Platform-Specific Notes
--------------------------------------------------

iOS:
WebSocket will close when app goes background.
APNs tokens differ by environment (sandbox vs production).
Background processing requires iOS background modes (not guaranteed for continuous streaming).

Android:
WebSockets can persist longer, but still not guaranteed.
FCM integration required for push (backend extension).
Background services exist but must respect OS power limits.

--------------------------------------------------
# 12 Compliance Rules
--------------------------------------------------

Clients MUST send packets matching schema.
Clients MUST implement emergency detection locally.
Clients MUST use POST /emergency for critical triggers.
Backend MUST persist snapshot before push notification.
Backend is the only alert authority.
