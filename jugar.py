"""Juega la partida con el piloto (opción híbrida): navegación y diálogos programados, combates con una política.

Uso (desde la carpeta "Pokemon"):
    .venv\\Scripts\\python.exe jugar.py                  # sin ventana, lo más rápido posible
    .venv\\Scripts\\python.exe jugar.py --ventana        # para verlo jugar (velocidad real)
    .venv\\Scripts\\python.exe jugar.py --ventana --velocidad 4
Empieza en state/inicio.state y va consiguiendo los objetivos de src/piloto/objetivos.py. Al conseguir cada uno
guarda la partida en state/piloto/ (para continuar o depurar desde ahí con --desde).
"""
import argparse
import os
import sys
import time

from src.piloto.juego import FPS, Juego
from src.piloto.objetivos import OBJETIVOS
from src.piloto.piloto import Piloto
from src.utils import config

PILOTO_DIR = os.path.join(config.STATES_DIR, "piloto")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ventana", action="store_true", help="ver el juego en una ventana")
    parser.add_argument("--velocidad", type=int, help="con ventana: 1 = tiempo real (por defecto), 0 = sin límite")
    parser.add_argument("--desde", help="savestate desde el que empezar (por defecto, state/inicio.state)")
    parser.add_argument("--max-decisiones", type=int, default=100_000, help="tope por objetivo, por si se atasca")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # la consola de Windows no siempre es UTF-8

    juego = Juego(ventana=args.ventana, velocidad=args.velocidad)
    juego.cargar(args.desde or os.path.join(config.STATES_DIR, "inicio.state"))
    piloto = Piloto(juego)
    os.makedirs(PILOTO_DIR, exist_ok=True)
    inicio_real, inicio_frames = time.time(), juego.frames
    try:
        for i, objetivo in enumerate(OBJETIVOS, 1):
            if objetivo.hecho(juego):
                continue
            print(f"▶ {objetivo.nombre}")
            conseguido = piloto.conseguir(objetivo, args.max_decisiones)
            minutos = (juego.frames - inicio_frames) / FPS / 60
            if not conseguido:
                print(f"✋ Atascado en «{objetivo.nombre}» tras {args.max_decisiones:,} decisiones ({minutos:.1f} min de juego)")
                juego.guardar(os.path.join(PILOTO_DIR, "atascado.state"))
                break
            print(f"✅ {objetivo.nombre} · {minutos:.1f} min de juego · nivel {juego.nivel()} · "
                  f"combates: {piloto.combates['ganados']} ganados, {piloto.combates['perdidos']} perdidos")
            juego.guardar(os.path.join(PILOTO_DIR, f"{i:02d}.state"))
        else:
            print(f"🏁 Objetivos conseguidos: {len(OBJETIVOS)} · {time.time() - inicio_real:.0f} s reales")
    except KeyboardInterrupt:
        print("\n🛑 Parado")
    finally:
        juego.cerrar()


if __name__ == "__main__":
    main()
