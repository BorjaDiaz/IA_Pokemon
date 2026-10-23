import os
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback
import src.utils.config as config

class AgentManager:
    def __init__(self, env):
        self.env = env
        self.model_path = os.path.join(config.IA_DIR, "modelo_speedrunner.zip")
        os.makedirs(config.IA_DIR, exist_ok=True)

    def load_or_create_model(self):
        """Carga un modelo existente o crea uno nuevo con los hiperparámetros de config.py."""
        if os.path.exists(self.model_path):
            print("\n🧠 [AgentManager] Cargando cerebro existente...")
            # Si cargas un modelo, le bajamos un poco el learning rate para afinar
            model = PPO.load(self.model_path, env=self.env, learning_rate=0.0001,
                             tensorboard_log=config.TENSORBOARD_DIR)
        else:
            print("\n👶 [AgentManager] Creando cerebro neuronal desde cero...")
            model = PPO(
                "CnnPolicy", self.env, verbose=1,
                learning_rate=config.PPO_LEARNING_RATE,
                gamma=config.PPO_GAMMA,
                ent_coef=config.PPO_ENT_COEF,
                batch_size=config.PPO_BATCH_SIZE,
                tensorboard_log=config.TENSORBOARD_DIR,
            )
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
