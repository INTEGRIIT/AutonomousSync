from backend.fusion.engine import FusionEngine
from backend.classifier.state_machine import StateMachine
from backend.sync_engine.engine import SyncEngine

from backend.evaluator.temporal_window import TemporalWindow
from backend.sensors.water_interaction import WaterInteractionSensor
from backend.evaluator.emergency_capture import EmergencyStateCapture
from backend.evaluator.state_transitions import StateTransitionEngine

class Runtime:
    def __init__(self):
        self.fusion = FusionEngine()
        self.temporal = TemporalWindow()
        self.water = WaterInteractionSensor()
        self.emergency = EmergencyStateCapture()

        self.sm = StateMachine()
        self.sync = SyncEngine()

        self.latest = None
        self.timeline = []   # last N outputs

        self.state_transition = StateTransitionEngine()

runtime = Runtime()