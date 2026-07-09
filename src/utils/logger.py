import json
import numpy as np
import os

class Logger:
    def __init__(self, rank, log_dir):
        self.rank = rank
        os.makedirs(log_dir, exist_ok=True)
        self.filepath = os.path.join(log_dir, f"log_clon_{rank}.jsonl")
        self.actions = []

    def _convert(self, obj):
        if isinstance(obj, np.integer): return int(obj)
        elif isinstance(obj, np.floating): return float(obj)
        elif isinstance(obj, np.ndarray): return obj.tolist()
        elif isinstance(obj, dict): return {k: self._convert(v) for k, v in obj.items()}
        elif isinstance(obj, list): return [self._convert(v) for v in obj]
        elif isinstance(obj, tuple): return [self._convert(v) for v in obj]
        else: return obj

    def log_step(self, data):
        try:
            clean_data = self._convert(data)
            with open(self.filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(clean_data) + "\n")
            if "action" in clean_data:
                self.actions.append(clean_data["action"])
        except Exception:
            pass

    def close(self):
        pass


