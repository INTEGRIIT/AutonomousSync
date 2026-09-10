from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


# =========================================================
# CORE VECTOR TYPES
# =========================================================

class Vec3(BaseModel):
    x: float
    y: float
    z: float


# =========================================================
# TOUCH INPUT
# =========================================================

class TouchState(BaseModel):
    active: bool = False
    pressure: Optional[float] = None
    area: Optional[float] = None


# =========================================================
# MOISTURE / WATER DETECTION
# =========================================================

class MoistureState(BaseModel):
    value: Optional[float] = None   # 0.0 → 1.0 normalized
    source: Optional[str] = None    # "ble", "estimate", etc.


# =========================================================
# 🔋 BATTERY (CRITICAL — COMPLETE)
# =========================================================

class BatteryState(BaseModel):
    level: Optional[float] = None        # 0.0 → 1.0
    state: Optional[str] = None          # charging, unplugged, full
    drain_rate: Optional[float] = None   # % per minute
    low_power_mode: Optional[bool] = None


# =========================================================
# 🌐 DEVICE CONTEXT (FUTURE-PROOF)
# =========================================================

class DeviceContext(BaseModel):
    platform: Optional[str] = None       # ios, android
    model: Optional[str] = None
    os_version: Optional[str] = None
    app_version: Optional[str] = None


# =========================================================
# 📡 NETWORK STATE (FUTURE AI SIGNAL)
# =========================================================

class NetworkState(BaseModel):
    type: Optional[str] = None           # wifi, cellular
    is_connected: Optional[bool] = None
    strength: Optional[float] = None


# =========================================================
# 👤 USER PREFERENCES (🔥 NEW — CRITICAL)
# =========================================================

class UserPreferences(BaseModel):
    device_name: Optional[str] = None
    auto_backup: Optional[bool] = True
    alert_sensitivity: Optional[str] = None   # low, medium, high
    include_location: Optional[bool] = False
    include_telemetry: Optional[bool] = True
    include_battery: Optional[bool] = True


# =========================================================
# 🧠 MAIN SENSOR PACKET (GLOBAL CONTRACT)
# =========================================================

class SensorPacket(BaseModel):

    # -----------------------------------------------------
    # CORE IDENTIFIERS
    # -----------------------------------------------------

    ts: float = Field(..., description="Unix ms timestamp")
    device_uid: str = Field(..., description="Permanent device UUID")

    # -----------------------------------------------------
    # MOTION SENSORS
    # -----------------------------------------------------

    accel: Optional[Vec3] = None
    gyro: Optional[Vec3] = None
    mag: Optional[Vec3] = None

    # -----------------------------------------------------
    # INTERACTION / ENVIRONMENT
    # -----------------------------------------------------

    touch: Optional[TouchState] = None
    moisture: Optional[MoistureState] = None

    # -----------------------------------------------------
    # 🔥 CRITICAL SYSTEM SIGNALS
    # -----------------------------------------------------

    battery: Optional[BatteryState] = None

    # -----------------------------------------------------
    # 🌐 DEVICE + NETWORK CONTEXT
    # -----------------------------------------------------

    device: Optional[DeviceContext] = None
    network: Optional[NetworkState] = None

    # -----------------------------------------------------
    # 👤 USER CONTEXT (🔥 NEW — THIS WAS MISSING)
    # -----------------------------------------------------

    preferences: Optional[UserPreferences] = None

    # -----------------------------------------------------
    # RAW / CUSTOM METADATA
    # -----------------------------------------------------

    meta: Optional[Dict[str, Any]] = None

    # -----------------------------------------------------
    # VERSIONING (VERY IMPORTANT)
    # -----------------------------------------------------

    schema_version: str = "v3"