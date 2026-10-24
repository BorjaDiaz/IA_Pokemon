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

    def procesar(self, x, y, last_pos, curr_tile, visited_tiles, map_name, en_combate, en_script,
                 explorable=True, cuenta_progreso=True):
        """El contador de pasos sin progreso avanza en todos los pasos, también en diálogos y combates:
        si se pausara en ellos, repetir un diálogo sin fin evitaría el corte del episodio.
        Lo reinicia una casilla nueva (si cuenta_progreso) o registrar_progreso() (eventos nuevos del juego).
        explorable=False: la casilla nueva no da recompensa (mapa ya recorrido antes del hito de salida,
        o interior).
        cuenta_progreso=False (interiores: casas, Centros Pokémon, tiendas): la casilla nueva tampoco
        reinicia el contador; si no, los interiores eran un refugio donde el episodio no se cortaba. En
        exteriores ya recorridos sí lo reinicia: hace falta para atravesarlos (p. ej. la vuelta a Elm)
        sin que el episodio se corte antes de llegar a donde hay recompensa."""
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
                reward += c.REWARD_NEW_TILE if explorable else c.PENALTY_REVISIT_TILE
                if cuenta_progreso:
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
