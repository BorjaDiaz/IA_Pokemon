"""Ver jugar al modelo entrenado en ventanas del emulador (no entrena ni cambia el modelo).

Uso:
    python tools/ver_ia.py                         # 1 ventana, salidas mezcladas, tiempo real
    python tools/ver_ia.py --clones 4              # 4 ventanas a la vez
    python tools/ver_ia.py --salida inicio         # siempre desde la habitación
    python tools/ver_ia.py --salida hito           # siempre desde el hito más avanzado (junto a Elm...)
    python tools/ver_ia.py --velocidad 3           # 3 veces más rápido que el juego real
    python tools/ver_ia.py --determinista          # siempre la acción más probable (sin azar)

Cierra cualquier ventana o pulsa Ctrl+C para terminar. En la consola sale cada episodio:
desde dónde empezó, hasta dónde llegó y por qué terminó.
"""
import argparse
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Los datos de esta sesión (coordenadas, capturas...) van a una carpeta temporal, no a runs/.
# Se fija antes de importar config para que también lo vean los clones en procesos aparte.
os.environ["POKEMON_RUN_DIR"] = tempfile.mkdtemp(prefix="ver_ia_")
os.environ["POKEMON_SIN_RECORDS"] = "1"  # mirar no debe cambiar los récords ni los savestates del curriculum

from stable_baselines3 import PPO
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv, VecFrameStack

import src.utils.config as config
import src.utils.constantes as c
from src.env.pokemon_env import PokemonGoldEnv

RANK_BASE = 100  # ranks distintos a los del entrenamiento (sus archivos del atlas no se mezclan)


def salida_de(opcion):
    if opcion == "inicio":
        return config.CURRICULUM_STATES[config.CURRENT_STAGE]
    if opcion == "hito":
        hitos = [f"best_speedrun_{h}.state" for h in c.HITOS
                 if os.path.exists(os.path.join(config.STATES_DIR, f"best_speedrun_{h}.state"))]
        if not hitos:
            raise SystemExit("Aún no hay ningún savestate de hito; usa --salida inicio.")
        return hitos[-1]
    return None  # salidas mezcladas, como en el entrenamiento


def crear(rank, ventana, velocidad, salida):
    def _init():
        return Monitor(PokemonGoldEnv(rank=rank, ventana=ventana, velocidad=velocidad, salida_fija=salida))
    return _init


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--clones", type=int, default=1, choices=range(1, 5), help="ventanas a la vez (1-4)")
    parser.add_argument("--salida", choices=["mezcla", "inicio", "hito"], default="mezcla")
    parser.add_argument("--velocidad", type=float, default=1, help="1 = tiempo real; 0 = sin límite")
    parser.add_argument("--determinista", action="store_true", help="elegir siempre la acción más probable")
    parser.add_argument("--episodios", type=int, default=0, help="parar tras N episodios (0 = hasta cerrar)")
    parser.add_argument("--sin-ventana", action="store_true", help=argparse.SUPPRESS)  # para pruebas automáticas
    args = parser.parse_args()

    modelo = os.path.join(config.IA_DIR, "modelo_speedrunner.zip")
    if not os.path.exists(modelo):
        raise SystemExit(f"No hay modelo entrenado en {modelo}")
    salida = salida_de(args.salida)
    fabricas = [crear(RANK_BASE + i, not args.sin_ventana, args.velocidad, salida) for i in range(args.clones)]
    # En paralelo para que todas las ventanas vayan a la vez
    env = DummyVecEnv(fabricas) if args.clones == 1 else SubprocVecEnv(fabricas)
    env = VecFrameStack(env, n_stack=config.FRAME_STACK, channels_order="first")
    model = PPO.load(modelo, env=env)

    print(f"\n👀 Viendo el modelo ({model.num_timesteps:,} pasos de entrenamiento) en {args.clones} ventana(s)."
          f" Salida: {salida or 'mezclada'}. Cierra una ventana o pulsa Ctrl+C para terminar.\n")
    obs = env.reset()
    terminados = 0
    try:
        while args.episodios == 0 or terminados < args.episodios:
            acciones, _ = model.predict(obs, deterministic=args.determinista)
            obs, _, dones, infos = env.step(acciones)
            for i, (fin, info) in enumerate(zip(dones, infos)):
                if fin:
                    terminados += 1
                    mapas = [k for k in info.get("splits", {}) if k not in c.HITOS]
                    hitos = [f"{k} @ {v}" for k, v in info.get("splits", {}).items() if k in c.HITOS]
                    inicio = info.get("salida", "?").replace("best_speedrun_", "hito ").replace(".state", "")
                    print(f"🎮 Ventana {i + 1} · episodio de {info['episode']['l']} pasos desde {inicio}\n"
                          f"     mapas nuevos: {' → '.join(mapas) or 'ninguno'}"
                          + (f"\n     hitos: {', '.join(hitos)}" if hitos else ""))
    except (KeyboardInterrupt, EOFError, BrokenPipeError, ConnectionResetError):
        print("\n👋 Fin.")
    finally:
        try:
            env.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
