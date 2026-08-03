import os
from collections import defaultdict
from pyboy import PyBoy
import src.utils.config as config
from src.env.core.extractor_ram import RamExtractor


def snapshot_flags(ram):
    return {key: value for key, value in ram.get_all_flags().items() if value == 1}


def load_state_flags(pb, state_path):
    with open(state_path, "rb") as f:
        pb.load_state(f)
    return snapshot_flags(RamExtractor(pb))


def main():
    rom_path = config.ROM_PATH
    base_state = os.path.join(config.STATES_DIR, "inicio.state")
    if not os.path.exists(rom_path):
        print("ROM no encontrada", rom_path)
        return
    if not os.path.exists(base_state):
        print("Save state base no encontrada", base_state)
        return

    pb = PyBoy(rom_path, window="null")
    try:
        base_flags = load_state_flags(pb, base_state)
        state_files = []
        for name in sorted(os.listdir(config.STATES_DIR)):
            if name.endswith(".state") and name != os.path.basename(base_state):
                state_files.append(os.path.join(config.STATES_DIR, name))

        changes_by_bit = defaultdict(list)
        for state_path in state_files:
            target_flags = load_state_flags(pb, state_path)
            for key in sorted(set(target_flags) - set(base_flags)):
                changes_by_bit[key].append(os.path.basename(state_path))

        print("Flags candidatos detectados:")
        for key in sorted(changes_by_bit):
            states = ", ".join(changes_by_bit[key])
            print(f"{key[0]:#06x}:{key[1]} -> {states}")
    finally:
        pb.stop()


if __name__ == "__main__":
    main()
