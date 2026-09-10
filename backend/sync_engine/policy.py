from dataclasses import dataclass

@dataclass
class SyncPolicy:
    cooldown_ms: int = 2500
    require_stable_ms: int = 1500
    unstable_blocks_sync: bool = True
    
    # Upper bound on episode identity. Without this, a device that
    # settles, synchronizes, and stays settled never synchronizes
    # again: _graceful_fired persists for the life of the episode and
    # the episode has no end. Measured consequence was a median
    # 29-minute data-at-risk window on stationary, connected devices,
    # with a maximum of five days.
    episode_max_ms: int = 300_000   # 5 minutes

    emergency_cooldown_ms: int = 2_000 # NEW (short, prevents spam)