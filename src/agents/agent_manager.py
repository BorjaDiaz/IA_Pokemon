import os
from stable_baselines3 import PPO
import src.utils.config as config

class AgentManager:
    def __init__(self, env):
        self.env = env
        self.model_path = os.path.join(config.IA_DIR, "modelo_speedrunner.zip")
        os.makedirs(config.IA_DIR, exist_ok=True)

    def load_or_create_model(self):
        """Carga un modelo existente o crea uno nuevo con los hiperparámetros base."""
        if os.path.exists(self.model_path):
            print("\n🧠 [AgentManager] Cargando cerebro existente...")
            # Si cargas un modelo, le bajamos un poco el learning rate para afinar
            model = PPO.load(self.model_path, env=self.env, learning_rate=0.0001, batch_size=128)
        else:
            print("\n👶 [AgentManager] Creando cerebro neuronal desde cero...")
            # ent_coef=0.1 fuerza a la IA a explorar mucho al principio
            model = PPO("CnnPolicy", self.env, verbose=1, ent_coef=0.1, learning_rate=0.0003)
        
        return model

    def save_model(self, model):
        """Guarda el modelo de forma segura."""
        model.save(self.model_path)
        print("💾 [AgentManager] Cerebro guardado correctamente en:", self.model_path)