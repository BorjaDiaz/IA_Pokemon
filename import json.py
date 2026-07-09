import json
import os
import config

class PathMemory:
    def __init__(self):
        self.memory = {}
        self.load()

    def load(self):
        if os.path.exists(config.PATH_MEMORY_FILE):
            with open(config.PATH_MEMORY_FILE, "r") as f:
                self.memory = json.load(f)

    def save(self):
        with open(config.PATH_MEMORY_FILE, "w") as f:
            json.dump(self.memory, f)

    def get_key(self, grp, mid, x, y):
        return f"{grp}_{mid}_{x}_{y}"

    def get_best_action(self, grp, mid, x, y):
        return self.memory.get(self.get_key(grp, mid, x, y))

    def update(self, grp, mid, x, y, action):
        key = self.get_key(grp, mid, x, y)
        self.memory[key] = action