import os
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv
from stable_baselines3.common.monitor import Monitor
from gymnasium.wrappers import RecordVideo
import sys
from pathlib import Path

# Ensure project root is on sys.path so local modules like `config` can be imported
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import src.utils.config as config
from src.env.pokemon_env import PokemonGoldEnv

def make_env(rank):
    def _init():
        return Monitor(PokemonGoldEnv(rank=rank))
    return _init

if __name__ == "__main__":
    os.makedirs(config.IA_DIR, exist_ok=True)
    
    if config.NUM_CLONES == 1:
        env = DummyVecEnv([make_env(0)])
    else:
        env = SubprocVecEnv([make_env(i) for i in range(config.NUM_CLONES)])

    model_path = os.path.join(config.IA_DIR, "modelo_speedrunner.zip")
    
    if os.path.exists(model_path):
        print("\n🧠 Cargando cerebro existente...")
        model = PPO.load(model_path, env=env, learning_rate=0.0001, batch_size=128)
    else:
        print("\n👶 Creando cerebro neuronal desde cero...")
        # Se añade entropy coefficient para forzar que explore más y no caiga en bucles
        model = PPO("CnnPolicy", env, verbose=1, ent_coef=0.1, learning_rate=0.0003)

    print("\n🔥 ¡Entrenando! Pulsa Ctrl+C en esta consola para guardar y salir.")

    try:
        model.learn(total_timesteps=5_000_000)
    except KeyboardInterrupt:
        print("\n🛑 Entrenamiento detenido. Guardando progreso...")
    finally:
        model.save(model_path)
        print("💾 Cerebro guardado correctamente.")
        env.close() 