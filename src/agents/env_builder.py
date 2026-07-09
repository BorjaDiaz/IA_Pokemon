from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv
from stable_baselines3.common.monitor import Monitor
from src.env.pokemon_env import PokemonGoldEnv
import src.utils.config as config

def make_env(rank):
    """Función constructora para cada clon individual."""
    def _init():
        return Monitor(PokemonGoldEnv(rank=rank))
    return _init

def build_vectorized_env():
    """Crea los entornos en paralelo según la configuración."""
    if config.NUM_CLONES == 1:
        print("🌍 [EnvBuilder] Inicializando 1 entorno en modo Dummy (Ideal para debug)...")
        return DummyVecEnv([make_env(0)])
    else:
        print(f"🌍 [EnvBuilder] Inicializando {config.NUM_CLONES} entornos en paralelo (Subproc)...")
        return SubprocVecEnv([make_env(i) for i in range(config.NUM_CLONES)])