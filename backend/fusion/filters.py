import numpy as np

class LowPass:
    def __init__(self, alpha: float = 0.85):
        self.alpha = alpha
        self.prev = None

    def update(self, x: np.ndarray) -> np.ndarray:
        if self.prev is None:
            self.prev = x
        else:
            self.prev = self.alpha * self.prev + (1 - self.alpha) * x
        return self.prev