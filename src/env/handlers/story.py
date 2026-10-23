import os
import src.utils.config as config
import src.utils.constantes as c
from src.utils import rom_catalog

class StoryHandler:
    def __init__(self, rank, logger):
        self.rank = rank
        self.logger = logger
        self.hitos_nuevos = []  # hitos conseguidos en el último procesar(), para las capturas

    def procesar(self, pb, ram, rewards, active_flags, tuplas_historia, step_count):
        reward = 0.0
        self.hitos_nuevos = []
        current_flags = ram.get_all_flags()

        for f_id, val in current_flags.items():
            if val == 1 and active_flags.get(f_id, 0) == 0:
                active_flags[f_id] = 1

                if f_id in tuplas_historia:
                    # Hito del speedrun: gran premio y savestate para el curriculum
                    nombre_evento = tuplas_historia[f_id]
                    self.hitos_nuevos.append(nombre_evento)
                    bonus = rewards.calcular_bonus_prisa_flag(step_count)
                    reward += c.REWARD_FLAG_STORY + bonus
                    print(f"🌟 [Clon {self.rank}] ¡HIT HISTÓRICO! -> {nombre_evento}")
                    if self.logger:
                        self.logger.log_step({"evento": "LOGRO_HISTORIA", "flag": nombre_evento, "step": step_count})

                    ruta_estado = os.path.join(config.STATES_DIR, f"best_speedrun_{nombre_evento}.state")
                    if not os.path.exists(ruta_estado):
                        try:
                            with open(ruta_estado, "wb") as f:
                                pb.save_state(f)
                        except Exception:
                            pass

                elif rom_catalog.is_story_flag(*f_id):
                    # Evento de historia menor; los de visibilidad, entrenador y temporales no puntúan
                    nombre_evento = rom_catalog.flag_name(*f_id)
                    reward += c.REWARD_FLAG_UNKNOWN
                    print(f"🧭 [Clon {self.rank}] Evento de historia: {nombre_evento}")
                    if self.logger:
                        self.logger.log_step({"evento": "PROGRESO_HISTORIA", "flag": nombre_evento, "step": step_count})

        return reward
