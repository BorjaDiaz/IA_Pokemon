import os
import pickle

class PathMemory:
    def __init__(self, file_name="paths.pkl"):
        self.file_name = file_name
        self.memory = {}

        if os.path.exists(self.file_name):
            try:
                with open(self.file_name, "rb") as f:
                    self.memory = pickle.load(f)
            except:
                self.memory = {}

    def get_best_action(self, grp, mid, x, y):
        data = self.memory.get((grp, mid, x, y))
        if data is not None:
            if isinstance(data, tuple):
                return data[0]
            else:
                return data
        return None

    def update(self, grp, mid, x, y, action, current_step):
        key = (grp, mid, x, y)
        if key not in self.memory:
            self.memory[key] = (action, current_step)
        else:
            data = self.memory[key]
            if isinstance(data, tuple):
                if current_step < data[1]:
                    self.memory[key] = (action, current_step)
            else:
                self.memory[key] = (action, current_step)

    def save(self):
        try:
            with open(self.file_name, "wb") as f:
                pickle.dump(self.memory, f)
        except Exception as e:
            print(f"❌ Error guardando PathMemory: {e}")