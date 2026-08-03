import os
import sys
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
        print(f"Estado base cargado desde {base_state}")
        print(f"Bits activos al inicio: {len(base_flags)}")

        state_files = []
        for name in sorted(os.listdir(config.STATES_DIR)):
            if name.endswith(".state") and name != os.path.basename(base_state):
                state_files.append(os.path.join(config.STATES_DIR, name))

        if not state_files:
            print("No hay otros save states para comparar.")
            return

        for state_path in state_files:
            print(f"\nComparando con {os.path.basename(state_path)}")
            target_flags = load_state_flags(pb, state_path)
            new_flags = sorted(set(target_flags) - set(base_flags))
            if new_flags:
                print(f"Nuevos bits activos ({len(new_flags)}):")
                for key in new_flags:
                    print(f"0x{key[0]:X}:{key[1]}")
            else:
                print("No hay bits nuevos respecto al estado base.")
    finally:
        pb.stop()


if __name__ == "__main__":
    main()
