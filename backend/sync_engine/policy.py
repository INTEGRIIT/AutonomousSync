from dataclasses import dataclass

@dataclass
class SyncPolicy:
    cooldown_ms: int = 2500
    require_stable_ms: int = 1500
    unstable_blocks_sync: bool = True
    
    emergency_cooldown_ms: int = 2_000 # NEW (short, prevents spam)