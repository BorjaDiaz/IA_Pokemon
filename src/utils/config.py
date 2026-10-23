import os

BASE_DIR = r"C:\Users\borja\Desktop\IA"
ROM_PATH = os.path.join(BASE_DIR, "roms", "Pokemon_Oro.gbc")

# Aquí se guardarán los logros automáticos de la IA
STATES_DIR = os.path.join(BASE_DIR, "state")
LOG_DIR = os.path.join(BASE_DIR, "logs")
IA_DIR = os.path.join(BASE_DIR, "ia")

# Cada lanzamiento de train.py guarda sus recorridos, capturas, métricas y logs en runs/<fecha_hora>/.
# train.py lo comunica a los clones con la variable de entorno POKEMON_RUN_DIR; sin ella (tests,
# herramientas sueltas) se usa la carpeta actual.
RUNS_DIR = os.path.join(BASE_DIR, "runs")
RUN_DIR = os.environ.get("POKEMON_RUN_DIR", ".")
# Mejor tiempo de partida conseguido para cada hito (lo usan los savestates best_speedrun_*)
RECORDS_PATH = os.path.join(STATES_DIR, "records.json")

NUM_CLONES = 12           # medido con GPU: 8 = 495 pasos/s, 12 = 581 (9,8 GB RAM), 16 = 593. Baja a 8 si el PC va lento
SPEEDRUN_MODE = True
VERBOSE = False           # True: imprime cada golpe, curación, mapa nuevo... (útil para depurar con 1 clon)
FRAMES_POR_ACCION = 16    # una casilla andando = 16 frames: cada acción de dirección mueve exactamente 1 casilla
FRAMES_PULSACION = 8      # frames que se mantiene pulsado el botón dentro de cada acción
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

# Salidas mezcladas: en cada episodio, con probabilidad PROB_SALIDA_INICIO se empieza en
# CURRICULUM_STATES[CURRENT_STAGE]; si no, desde el savestate best_speedrun_<hito>.state del hito más
# avanzado conseguido (o, a veces, de uno anterior). Practica lo nuevo sin olvidar el principio.
SALIDAS_MEZCLADAS = True
PROB_SALIDA_INICIO = 0.5
PROB_HITO_MAS_AVANZADO = 0.6   # entre las salidas desde hitos, cuántas desde el más avanzado

# ==========================================
# ENTRENAMIENTO (PPO)
# ==========================================
TOTAL_TIMESTEPS = 5_000_000
PPO_LEARNING_RATE = 0.0001   # con 0.0003 approx_kl ~0.035 y clip_fraction ~0.25: actualizaciones demasiado bruscas
PPO_TARGET_KL = 0.02         # corta las vueltas de una actualización si la política ya cambió bastante
PPO_GAMMA = 0.998          # horizonte largo: los hitos están a miles de pasos
PPO_ENT_COEF = 0.01        # exploración sin volver la política casi aleatoria
PPO_N_STEPS = 2048         # pasos que juega cada clon antes de cada actualización de la red
PPO_BATCH_SIZE = 256       # tamaño de cada minibatch al actualizar la red
FRAME_STACK = 3            # frames apilados en la observación (da sensación de movimiento)
CHECKPOINT_FREQ = 100_000  # pasos totales entre copias de seguridad del modelo
CHECKPOINT_DIR = os.path.join(IA_DIR, "checkpoints")
TENSORBOARD_DIR = os.path.join(LOG_DIR, "tensorboard")
