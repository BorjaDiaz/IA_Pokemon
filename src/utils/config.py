import os

BASE_DIR = r"C:\Users\borja\Desktop\IA"
ROM_PATH = os.path.join(BASE_DIR, "roms", "Pokemon_Oro.gbc")

# El estado desde el que empezará la IA al abrir el programa
STATE_PATH = os.path.join(BASE_DIR, "state", "inicio.state")

# Aquí se guardarán los logros automáticos de la IA
STATES_DIR = os.path.join(BASE_DIR, "state")
LOG_DIR = os.path.join(BASE_DIR, "logs")
IA_DIR = os.path.join(BASE_DIR, "ia")

NUM_CLONES = 6          
SPEEDRUN_MODE = True
ENABLE_LOGS = True        
MAX_STEPS_PER_EPISODE = 500000


USE_CURRICULUM = True
CURRICULUM_STATES = [
    "inicio.state",                     
    "best_speedrun_got_cyndaquil.state", 
    "ruta_29.state",
]


CURRENT_STAGE = 2

TIME_PENALTY = 0.01
STUCK_PENALTY = 0.5
MAX_STUCK = 25

PATH_MEMORY_FILE = "best_path.json"