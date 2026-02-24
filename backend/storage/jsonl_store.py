import os
from backend.utils.jsonx import dumps

class JSONLStore:
    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def append(self, record: dict):
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(dumps(record) + "\n")