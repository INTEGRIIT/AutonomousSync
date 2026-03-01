from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class Vec3(BaseModel):
    x: float
    y: float
    z: float

class TouchState(BaseModel):
    active: bool = False
    pressure: Optional[float] = None  # optional if you later add
    area: Optional[float] = None

class MoistureState(BaseModel):
    value: Optional[float] = None     # 0..1 normalized (placeholder)
    source: Optional[str] = None      # "ble", "estimate", etc.

class SensorPacket(BaseModel):
    ts: float = Field(..., description="Unix ms timestamp")
    device_uid: str = Field(..., description="Permanent device UUID")
    accel: Optional[Vec3] = None
    gyro: Optional[Vec3] = None
    mag: Optional[Vec3] = None
    touch: Optional[TouchState] = None
    moisture: Optional[MoistureState] = None
    meta: Optional[Dict[str, Any]] = None