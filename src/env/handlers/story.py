import os
import src.utils.config as config
import src.utils.constantes as c

class StoryHandler:
    def __init__(self, rank, logger):
        self.rank = rank
        self.logger = logger

    def procesar(self, pb, ram, rewards, active_flags, tuplas_historia, step_count):
        reward = 0.0
        current_flags = ram.get_all_flags()

        for f_id, val in current_flags.items():
            if val == 1 and active_flags.get(f_id, 0) == 0:
                active_flags[f_id] = 1
                
                if f_id in tuplas_historia:
                    nombre_evento = tuplas_historia[f_id]
                    bonus = rewards.calcular_bonus_prisa_flag(step_count)
                    reward += c.REWARD_FLAG_STORY + bonus 
                    nombre_archivo = f"best_speedrun_{nombre_evento}.state"
                    print(f"🌟 [Clon {self.rank}] ¡HIT HISTÓRICO! -> {nombre_evento}")
                    if self.logger: self.logger.log_step({"evento": "LOGRO_HISTORIA", "flag": nombre_evento, "step": step_count})
                else:
                    reward += c.REWARD_FLAG_UNKNOWN 
                    nombre_archivo = f"best_speedrun_0x{f_id[0]:X}_{f_id[1]}.state"

                # Guardado de Savestate
                ruta_estado = os.path.join(config.STATES_DIR, nombre_archivo)
                if not os.path.exists(ruta_estado):
                    try:
                        with open(ruta_estado, "wb") as f: pb.save_state(f)
                    except Exception: pass
                    
        return reward