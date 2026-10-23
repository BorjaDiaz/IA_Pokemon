import src.utils.constantes as c
import src.utils.config as config

class MovementHandler:
    def __init__(self, rank):
        self.rank = rank
        self.steps_sin_progreso = 0
        self.max_steps_sin_progreso = config.MAX_STEPS_SIN_PROGRESO

    def registrar_progreso(self):
        """Algo nuevo ha pasado en la partida (p. ej. un evento del juego): reinicia el contador."""
        self.steps_sin_progreso = 0

    def procesar(self, x, y, last_pos, curr_tile, visited_tiles, map_name, en_combate, en_script):
        """El contador de pasos sin progreso avanza en todos los pasos, también en diálogos y combates:
        si se pausara en ellos, repetir un diálogo sin fin evitaría el corte del episodio.
        Lo reinicia una casilla nueva o registrar_progreso() (eventos nuevos del juego)."""
        reward = 0.0
        sin_progreso = False
        self.steps_sin_progreso += 1

        # En combate o en una escena/diálogo quedarse quieto es normal: no se penaliza ni se explora
        if not (en_combate or en_script):
            if (x, y) == last_pos:
                reward += c.PENALTY_SAME_TILE

            # 🗺️ Recompensa por explorar nuevos tiles (visited_tiles se vacía en cada episodio)
            if curr_tile not in visited_tiles:
                visited_tiles.add(curr_tile)
                reward += c.REWARD_NEW_TILE
                self.steps_sin_progreso = 0
            else:
                reward += c.PENALTY_REVISIT_TILE

        # ⚠️ Alertas de atasco
        if self.steps_sin_progreso > 0 and self.steps_sin_progreso % 250 == 0:
            if config.VERBOSE: print(f"⚠️ [Clon {self.rank}] Lleva {self.steps_sin_progreso} pasos sin progreso en {map_name}...")

        # 💀 Corte del episodio si no avanza
        if self.steps_sin_progreso >= self.max_steps_sin_progreso:
            if config.VERBOSE: print(f"🛑 [Clon {self.rank}] SIN PROGRESO en {map_name}. Reiniciando...")
            sin_progreso = True
            reward += c.PENALTY_NO_PROGRESS

        return reward, sin_progreso
