"""Traza en vivo los event flags que activa el juego, sacados de su propio código.

Pone un hook de PyBoy en EventFlagAction (00:2F53 en la ROM española), la
rutina por la que pasa todo setevent/clearevent de los scripts. En ese momento
el registro DE lleva el número de flag y B la acción (0 borrar, 1 activar,
2 comprobar). Después de cada frame se compara la RAM de wEventFlags para
confirmar que el bit que cambia es justo 0xD7B7 + n/8, bit n%8.

Uso:
    python tools/trace_events.py                     # juegas tú en la ventana
    python tools/trace_events.py --state ruta_29.state
    python tools/trace_events.py --headless --random --frames 200000
"""
import argparse
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyboy import PyBoy

import src.utils.config as config
from src.utils import rom_catalog

EVENT_FLAG_ACTION = 0x2F53  # banco 0; en la ROM US es 0x2F2F
FLAGS_BASE = rom_catalog.RAM["wEventFlags"]
FLAGS_SIZE = 256
ACTIONS = {0: "BORRAR", 1: "ACTIVAR"}
RANDOM_BUTTONS = ["up", "down", "left", "right", "a", "a", "b"]


def read_flags(pb):
    return bytes(pb.memory[1, FLAGS_BASE + i] for i in range(FLAGS_SIZE))


def changed_bits(before, after):
    for i, (old, new) in enumerate(zip(before, after)):
        diff = old ^ new
        for bit in range(8):
            if diff >> bit & 1:
                yield i * 8 + bit, new >> bit & 1


def describe(index):
    addr, bit = FLAGS_BASE + index // 8, index % 8
    name = rom_catalog.flag_name(addr, bit) or "(hueco sin nombre)"
    kind = rom_catalog.EVENT_FLAG_KIND.get(name, "?")
    return addr, bit, name, kind


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--state", default="inicio.state", help="savestate de la carpeta state/ desde el que empezar")
    parser.add_argument("--headless", action="store_true", help="sin ventana (para pruebas automáticas)")
    parser.add_argument("--random", action="store_true", help="pulsa botones al azar")
    parser.add_argument("--frames", type=int, default=0, help="parar tras N frames (0 = hasta cerrar la ventana)")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--log", default=os.path.join(config.LOG_DIR, "event_trace.jsonl"))
    args = parser.parse_args()

    pb = PyBoy(config.ROM_PATH, window="null" if args.headless else "SDL2", sound_emulated=False)
    pb.set_emulation_speed(0 if args.headless else 1)
    with open(os.path.join(config.STATES_DIR, args.state), "rb") as f:
        pb.load_state(f)

    calls = []  # llamadas a EventFlagAction durante el frame actual

    def on_event_flag_action(_):
        regs = pb.register_file
        if regs.B in ACTIONS:
            calls.append((regs.B, regs.D << 8 | regs.E))

    pb.hook_register(0, EVENT_FLAG_ACTION, on_event_flag_action, None)

    os.makedirs(os.path.dirname(args.log), exist_ok=True)
    log = open(args.log, "a", encoding="utf-8")
    rng = random.Random(args.seed)
    stats = {"verificados": 0, "ya_estaban": 0, "fallos": 0, "sin_atribuir": 0}
    flags = read_flags(pb)
    frame = 0
    print(f"Trazando event flags desde {args.state}. Cierra la ventana o pulsa Ctrl+C para terminar.\n")

    try:
        while args.frames == 0 or frame < args.frames:
            if args.random and frame % 16 == 0:
                pb.button(rng.choice(RANDOM_BUTTONS), 8)
            if not pb.tick():
                break
            frame += 1

            new_flags = read_flags(pb)
            changes = dict(changed_bits(flags, new_flags))
            mapa = rom_catalog.map_name(pb.memory[1, rom_catalog.RAM["wMapGroup"]], pb.memory[1, rom_catalog.RAM["wMapNumber"]])

            for action, index in calls:
                addr, bit, name, kind = describe(index)
                expected = 1 if action == 1 else 0
                if changes.pop(index, None) == expected:
                    estado = "OK"
                    stats["verificados"] += 1
                elif new_flags[index // 8] >> bit & 1 == expected:
                    estado = "ya estaba"
                    stats["ya_estaban"] += 1
                else:
                    estado = "FALLO: la RAM no cambió como se esperaba"
                    stats["fallos"] += 1
                if estado != "ya estaba":
                    print(f"[frame {frame:7d}] {ACTIONS[action]:7s} #{index:4d} 0x{addr:04X}:{bit}  {name:50s} {kind:11s} en {mapa}  -> {estado}")
                log.write(json.dumps({"frame": frame, "accion": ACTIONS[action], "indice": index, "addr": f"0x{addr:04X}",
                                      "bit": bit, "nombre": name, "tipo": kind, "mapa": mapa, "estado": estado}) + "\n")

            # Bits cambiados sin pasar por EventFlagAction (p. ej. reset de flags temporales al cambiar de mapa)
            for index, value in changes.items():
                addr, bit, name, kind = describe(index)
                if kind != "temporal":
                    stats["sin_atribuir"] += 1
                    print(f"[frame {frame:7d}] DIRECTO={value} #{index:4d} 0x{addr:04X}:{bit}  {name:50s} {kind:11s} en {mapa}")

            calls.clear()
            flags = new_flags
    except KeyboardInterrupt:
        pass
    finally:
        log.close()
        pb.stop()

    print(f"\n{frame} frames. Verificados: {stats['verificados']} | ya activos: {stats['ya_estaban']} | "
          f"fallos: {stats['fallos']} | cambios sin atribuir: {stats['sin_atribuir']}")


if __name__ == "__main__":
    main()
