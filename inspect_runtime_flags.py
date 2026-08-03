import os
import sys
from pyboy import PyBoy
import src.utils.config as config
import src.utils.constantes as c
from src.env.core.extractor_ram import RamExtractor


def main():
    rom_path = config.ROM_PATH
    state_path = os.path.join(config.STATES_DIR, "inicio.state")
    if not os.path.exists(rom_path):
        print("ROM no encontrada", rom_path)
        return
    if not os.path.exists(state_path):
        print("Save state no encontrada", state_path)
        return

    pb = PyBoy(rom_path, window="null")
    with open(state_path, "rb") as f:
        pb.load_state(f)

    ram = RamExtractor(pb)
    flags = ram.get_all_flags()
    print("Flags activos desde inicio.state:")
    for key, value in sorted(flags.items()):
        if value:
            label = c.RUNTIME_PROGRESS_FLAGS.get(key, None)
            if label:
                print(f"0x{key[0]:X}:{key[1]} -> 1 [{label}]")
            else:
                print(f"0x{key[0]:X}:{key[1]} -> 1")

    pb.stop()


if __name__ == "__main__":
    main()
