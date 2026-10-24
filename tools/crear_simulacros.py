"""Crea savestates al empezar combates salvajes para el simulacro de combate.

Desde el savestate de un hito, camina al azar por la hierba hasta que salta un combate salvaje y
guarda el estado en state/combates/combate_<HITO>_NN.state. Busca rivales distintos (especie y nivel)
para que la IA aprenda a combatir en general, no a memorizar un combate concreto.

No usa el entorno: no escribe récords, capturas ni datos de ninguna ejecución.

Uso:
    python tools/crear_simulacros.py                          # 8 combates desde LLEGADA_ROUTE_30
    python tools/crear_simulacros.py --hito LLEGADA_ROUTE_30 --n 12
"""
import argparse
import io
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyboy import PyBoy
from pyboy.utils import WindowEvent

import src.utils.config as config
import src.utils.constantes as c

DIRECCIONES = [WindowEvent.PRESS_ARROW_UP, WindowEvent.PRESS_ARROW_DOWN,
               WindowEvent.PRESS_ARROW_LEFT, WindowEvent.PRESS_ARROW_RIGHT]
SOLTAR = {WindowEvent.PRESS_ARROW_UP: WindowEvent.RELEASE_ARROW_UP,
          WindowEvent.PRESS_ARROW_DOWN: WindowEvent.RELEASE_ARROW_DOWN,
          WindowEvent.PRESS_ARROW_LEFT: WindowEvent.RELEASE_ARROW_LEFT,
          WindowEvent.PRESS_ARROW_RIGHT: WindowEvent.RELEASE_ARROW_RIGHT,
          WindowEvent.PRESS_BUTTON_B: WindowEvent.RELEASE_BUTTON_B}
MAX_PASOS_BUSQUEDA = 3000


def leer(pb, addr):
    return pb.memory[c.WRAM_BANK, addr]


def pulsar(pb, boton):
    pb.send_input(boton)
    pb.tick(config.FRAMES_PULSACION, False)
    pb.send_input(SOLTAR[boton])
    pb.tick(config.FRAMES_POR_ACCION - config.FRAMES_PULSACION, False)


def buscar_combate(pb, estado, rng):
    """Carga el estado y camina al azar hasta un combate salvaje. Devuelve (especie, nivel) o None."""
    estado.seek(0)
    pb.load_state(estado)
    for _ in range(MAX_PASOS_BUSQUEDA):
        # De vez en cuando B, para cerrar carteles o diálogos que bloqueen el paso
        pulsar(pb, WindowEvent.PRESS_BUTTON_B if rng.random() < 0.1 else rng.choice(DIRECCIONES))
        modo = leer(pb, c.ADDR_BATTLE_MODE)
        if modo == 2:
            return None  # entrenador: no sirve para el simulacro
        if modo == 1:
            pb.tick(60, False)  # que se carguen los datos del rival
            return leer(pb, c.ADDR_RIVAL_ESPECIE), leer(pb, c.ADDR_RIVAL_NIVEL)
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--hito", default="LLEGADA_ROUTE_30")
    parser.add_argument("--n", type=int, default=8, help="cuántos combates distintos guardar")
    parser.add_argument("--semilla", type=int, default=0)
    args = parser.parse_args()

    origen = os.path.join(config.STATES_DIR, f"best_speedrun_{args.hito}.state")
    if not os.path.exists(origen):
        raise SystemExit(f"No existe {origen}")
    destino = os.path.join(config.STATES_DIR, config.SIMULACRO_DIR)
    os.makedirs(destino, exist_ok=True)

    pb = PyBoy(config.ROM_PATH, window="null", sound_emulated=False)
    pb.set_emulation_speed(0)
    pb.rtc_lock_experimental(True)
    with open(origen, "rb") as f:
        estado = io.BytesIO(f.read())

    rng = random.Random(args.semilla)
    vistos, guardados = set(), 0
    for intento in range(args.n * 20):
        if guardados >= args.n:
            break
        rival = buscar_combate(pb, estado, rng)
        # Rivales repetidos solo si ya no salen nuevos (la Ruta 30 tiene pocas especies)
        if rival is None or (rival in vistos and intento < args.n * 10):
            continue
        vistos.add(rival)
        guardados += 1
        ruta = os.path.join(destino, f"combate_{args.hito}_{guardados:02d}.state")
        with open(ruta, "wb") as f:
            pb.save_state(f)
        print(f"💾 {ruta}: especie {rival[0]}, nivel {rival[1]}")
    pb.stop(save=False)
    print(f"✅ {guardados} combates guardados en {destino}")


if __name__ == "__main__":
    main()
