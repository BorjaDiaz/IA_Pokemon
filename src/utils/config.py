import os

BASE_DIR = r"C:\Users\borja\Desktop\IA"
ROM_PATH = os.path.join(BASE_DIR, "roms", "Pokemon_Oro.gbc")

# Aquí se guardarán los logros automáticos de la IA
STATES_DIR = os.path.join(BASE_DIR, "state")
LOG_DIR = os.path.join(BASE_DIR, "logs")
IA_DIR = os.path.join(BASE_DIR, "ia")

NUM_CLONES = 6          
SPEEDRUN_MODE = True
ENABLE_LOGS = True        
MAX_STEPS_PER_EPISODE = 20480       # múltiplo de 2048 (n_steps de PPO)
MAX_STEPS_SIN_PROGRESO = 1000       # pasos sin pisar baldosa nueva (fuera de combate y escenas) antes de cortar


USE_CURRICULUM = True
CURRICULUM_STATES = [
    "inicio.state",
    "best_speedrun_got_cyndaquil.state",
    "ruta_29.state",
]

CURRENT_STAGE = 0

# ==========================================
# ENTRENAMIENTO (PPO)
# ==========================================
TOTAL_TIMESTEPS = 5_000_000
PPO_LEARNING_RATE = 0.0003
PPO_GAMMA = 0.998          # horizonte largo: los hitos están a miles de pasos
PPO_ENT_COEF = 0.01        # exploración sin volver la política casi aleatoria
PPO_BATCH_SIZE = 256       # 12288 pasos por rollout (2048 x 6 clones) / 256 = 48 minibatches
FRAME_STACK = 3            # frames apilados en la observación (da sensación de movimiento)
CHECKPOINT_FREQ = 100_000  # pasos totales entre copias de seguridad del modelo
CHECKPOINT_DIR = os.path.join(IA_DIR, "checkpoints")
TENSORBOARD_DIR = os.path.join(LOG_DIR, "tensorboard")
