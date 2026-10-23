import src.utils.constantes as c
import src.utils.config as config

class MovementHandler:
    def __init__(self, rank):
        self.rank = rank
        self.steps_sin_progreso = 0
        self.max_steps_sin_progreso = config.MAX_STEPS_SIN_PROGRESO

    def procesar(self, x, y, last_pos, curr_tile, visited_tiles, map_name, en_combate, en_script):
        reward = 0.0
        sin_progreso = False

        # En combate o en una escena/diálogo quedarse quieto es normal: ni penaliza ni cuenta
        if en_combate or en_script:
            return 0.0, False

        if (x, y) == last_pos:
            reward += c.PENALTY_SAME_TILE

        # 🗺️ Recompensa por explorar nuevos tiles (visited_tiles se vacía en cada episodio)
        if curr_tile not in visited_tiles:
            visited_tiles.add(curr_tile)
            reward += c.REWARD_NEW_TILE
            self.steps_sin_progreso = 0
        else:
            reward += c.PENALTY_REVISIT_TILE
            self.steps_sin_progreso += 1

        # ⚠️ Alertas de atasco
        if self.steps_sin_progreso > 0 and self.steps_sin_progreso % 250 == 0:
            print(f"⚠️ [Clon {self.rank}] Lleva {self.steps_sin_progreso} pasos sin pisar baldosas nuevas en {map_name}...")

        # 💀 Corte del episodio si no avanza
        if self.steps_sin_progreso >= self.max_steps_sin_progreso:
            print(f"🛑 [Clon {self.rank}] SIN PROGRESO en {map_name}. Reiniciando...")
            sin_progreso = True
            reward += c.PENALTY_NO_PROGRESS

        return reward, sin_progreso
