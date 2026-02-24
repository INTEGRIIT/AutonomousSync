import numpy as np

def norm3(v) -> float:
    return float(np.linalg.norm(v))

def vec3_to_np(vec):
    return np.array([vec.x, vec.y, vec.z], dtype=float)