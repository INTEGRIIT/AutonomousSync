from dataclasses import dataclass
from typing import Optional, Dict, Any
from backend.utils.time import now_ms

@dataclass
class Transition:
    from_state: str
    to_state: str
    ts: int

class StateTransitionEngine:
    def __init__(self):
        self.prev_state: Optional[str] = None

    def update(self, current_state: str) -> Optional[Dict[str, Any]]:
        if self.prev_state is None:
            self.prev_state = current_state
            return None

        if self.prev_state != current_state:
            event = {
                "type": "STATE_TRANSITION",
                "from": self.prev_state,
                "to": current_state,
                "ts": now_ms(),
            }
            self.prev_state = current_state
            return event

        return None