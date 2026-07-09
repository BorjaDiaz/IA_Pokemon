import src.utils.constantes as c
import src.utils.config as config

class MovementHandler:
    def __init__(self, rank):
        self.rank = rank
        self.steps_estancado = 0
        self.max_steps_estancado = getattr(config, 'MAX_STEPS_STUCK', 300)

    def procesar(self, x, y, last_pos, curr_tile, visited_tiles, map_name, en_combate):
        reward = 0.0
        done_atasco = False

        if en_combate:
            self.steps_estancado = 0
            return 0.0, False

        # 🚶‍♂️ Lógica de movimiento normal
        if (x, y) == last_pos:
            self.steps_estancado += 1
            # 📉 PENALIZACIÓN POR INACTIVIDAD: Cada paso que pasa quieto, pierde un poco.
            # Esto la obliga a pulsar flechas y moverse.
            reward -= 0.01 
        else:
            self.steps_estancado = 0

        # 🗺️ Recompensa por explorar nuevos tiles (No es granjeable porque es un SET)
        if curr_tile not in visited_tiles:
            visited_tiles.add(curr_tile)
            recompensa_tile = getattr(c, 'REWARD_NEW_TILE', 0.1)
            reward += recompensa_tile
        else:
            # 📉 PENALIZACIÓN POR REPETICIÓN: Si pisa una baldosa por la que ya pasó,
            # no gana nada o incluso podemos ponerle una micro-penalización (-0.001) para que busque lo nuevo.
            reward -= 0.001

        # ⚠️ Alertas de atasco
        if self.steps_estancado > 0 and self.steps_estancado % 50 == 0:
            print(f"⚠️ [Clon {self.rank}] Lleva {self.steps_estancado} pasos en la misma baldosa...")

        # 💀 Penalización masiva por atasco definitivo
        if self.steps_estancado >= self.max_steps_estancado:
            print(f"🛑 [Clon {self.rank}] ATASCADO DEFINITIVAMENTE en {map_name}. Reiniciando...")
            done_atasco = True
            # Castigo severo por quedarse atascada
            reward -= 10.0 

        return reward, done_atasco