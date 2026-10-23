import os
import time
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback
import src.utils.config as config

class AgentManager:
    def __init__(self, env):
        self.env = env
        self.model_path = os.path.join(config.IA_DIR, "modelo_speedrunner.zip")
        os.makedirs(config.IA_DIR, exist_ok=True)

    def _hiperparametros(self):
        return dict(
            learning_rate=config.PPO_LEARNING_RATE,
            gamma=config.PPO_GAMMA,
            ent_coef=config.PPO_ENT_COEF,
            n_steps=config.PPO_N_STEPS,
            batch_size=config.PPO_BATCH_SIZE,
            tensorboard_log=config.TENSORBOARD_DIR,
        )

    def load_or_create_model(self):
        """Carga el modelo guardado (aplicando los hiperparámetros actuales de config.py) o crea uno nuevo.
        Si el guardado no es compatible (p. ej. cambió la observación), se aparta con otro nombre."""
        model = None
        self.cargado = False  # True si se continúa un modelo guardado
        if os.path.exists(self.model_path):
            print("\n🧠 [AgentManager] Cargando cerebro existente...")
            try:
                model = PPO.load(self.model_path, env=self.env, **self._hiperparametros())
                self.cargado = True
            except ValueError as e:
                apartado = self.model_path.replace(".zip", f"_incompatible_{time.strftime('%Y%m%d_%H%M%S')}.zip")
                os.replace(self.model_path, apartado)
                print(f"⚠️ [AgentManager] El modelo guardado no es compatible con el entorno actual ({e}).")
                print(f"   Se ha apartado como {os.path.basename(apartado)} y se empieza uno nuevo.")
        if model is None:
            print("\n👶 [AgentManager] Creando cerebro neuronal desde cero...")
            model = PPO("CnnPolicy", self.env, verbose=1, **self._hiperparametros())
        print(f"🖥️ [AgentManager] Entrenando en: {model.device}")
        return model

    def checkpoint_callback(self):
        """Guarda una copia del modelo cada CHECKPOINT_FREQ pasos totales (entre todos los clones)."""
        return CheckpointCallback(
            save_freq=max(1, config.CHECKPOINT_FREQ // self.env.num_envs),
            save_path=config.CHECKPOINT_DIR,
            name_prefix="speedrunner",
        )

    def save_model(self, model):
        """Guarda el modelo de forma segura."""
        model.save(self.model_path)
        print("💾 [AgentManager] Cerebro guardado correctamente en:", self.model_path)
