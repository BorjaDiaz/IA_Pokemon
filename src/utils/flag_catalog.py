import os
from collections import defaultdict

from pyboy import PyBoy

import src.utils.config as config
import src.utils.constantes as c
from src.env.core.extractor_ram import RamExtractor


def snapshot_flags(ram):
    return {key: value for key, value in ram.get_all_flags().items() if value == 1}


def load_state_flags(pb, state_path, extractor_cls=None):
    with open(state_path, "rb") as handle:
        pb.load_state(handle)
    extractor = extractor_cls or RamExtractor
    return snapshot_flags(extractor(pb))


def build_flag_change_catalog(base_flags, state_flags_by_name):
    changes_by_bit = defaultdict(list)
    for state_name, target_flags in sorted(state_flags_by_name.items()):
        for flag_id in sorted(set(target_flags) - set(base_flags)):
            changes_by_bit[flag_id].append(state_name)
    return dict(changes_by_bit)


def discover_flag_catalog(rom_path=None, state_dir=None, base_state_name="inicio.state"):
    rom_path = rom_path or config.ROM_PATH
    state_dir = state_dir or config.STATES_DIR
    base_state_path = os.path.join(state_dir, base_state_name)

    if not os.path.exists(rom_path):
        raise FileNotFoundError(f"ROM no encontrada: {rom_path}")
    if not os.path.exists(base_state_path):
        raise FileNotFoundError(f"Save state base no encontrada: {base_state_path}")

    pb = PyBoy(rom_path, window="null")
    try:
        base_flags = load_state_flags(pb, base_state_path)
        state_paths = []
        for filename in sorted(os.listdir(state_dir)):
            if not filename.endswith(".state"):
                continue
            if filename == os.path.basename(base_state_path):
                continue
            state_paths.append(os.path.join(state_dir, filename))

        state_flags_by_name = {}
        for state_path in state_paths:
            state_flags_by_name[os.path.basename(state_path)] = load_state_flags(pb, state_path)

        return build_flag_change_catalog(base_flags, state_flags_by_name)
    finally:
        pb.stop()


def format_flag_catalog(changes_by_bit):
    lines = []
    for flag_id in sorted(changes_by_bit):
        state_names = ", ".join(changes_by_bit[flag_id])
        lines.append(f"{flag_id[0]:#06x}:{flag_id[1]} -> {state_names}")
    return "\n".join(lines)
