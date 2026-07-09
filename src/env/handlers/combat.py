import src.utils.constantes as c

class CombatHandler:
    def __init__(self, rank, logger):
        self.rank = rank
        self.logger = logger
        self.vida_enemigo_anterior = 999

    def procesar(self, pb, ram, rewards, gestor, en_combate, vida_actual_equipo, vida_equipo_anterior, step_count, map_name):
        reward = 0.0
        vida_enemigo_out = self.vida_enemigo_anterior

        if not en_combate:
            return reward, 999 # Reset de vida enemiga si no hay combate

        vida_actual_enemigo = gestor.leer_vida_enemigo()
        
        # --- Daño causado al enemigo ---
        if vida_actual_enemigo > 0 and (self.vida_enemigo_anterior == 999 or vida_actual_enemigo > self.vida_enemigo_anterior):
            vida_enemigo_out = vida_actual_enemigo
            
        elif 0 <= vida_actual_enemigo < self.vida_enemigo_anterior and self.vida_enemigo_anterior != 999:
            daño = self.vida_enemigo_anterior - vida_actual_enemigo
            if 0 < daño < 500:
                premio_daño = rewards.calcular_premio_danio(daño)
                reward += premio_daño
                print(f"🗡️ [Clon {self.rank}] ¡Ataque! {daño} HP. Premio: +{round(premio_daño, 2)}")
                if self.logger: self.logger.log_step({"evento": "DAÑO_CAUSADO", "daño": daño, "hp_enemigo": vida_actual_enemigo, "step": step_count})
            
            if vida_actual_enemigo == 0:
                reward += c.REWARD_COMBAT_ENEMY_FAINTED
                print(f"🏆 [Clon {self.rank}] ¡Rival Debilitado!")
                vida_enemigo_out = 999
            else:
                vida_enemigo_out = vida_actual_enemigo

        # --- Daño y curación del equipo en combate ---
        if 0 <= vida_actual_equipo < vida_equipo_anterior and vida_equipo_anterior != 999:
            daño_recibido = vida_equipo_anterior - vida_actual_equipo
            if 0 < daño_recibido < 500:
                castigo = rewards.calcular_penalizacion_danio_recibido(daño_recibido)
                reward += castigo 
                print(f"💥 [Clon {self.rank}] ¡Recibes daño! (-{daño_recibido} HP).")
            
        elif vida_actual_equipo > vida_equipo_anterior and vida_equipo_anterior != 999:
            curacion = vida_actual_equipo - vida_equipo_anterior
            if 0 < curacion < 500:
                premio = rewards.calcular_premio_curacion(curacion, ram.leer_max_vida_total_equipo())
                reward += premio
                print(f"💚 [Clon {self.rank}] ¡Curación en combate! (+{curacion} HP).")

        reward += c.PENALTY_COMBAT_STEP 
        
        self.vida_enemigo_anterior = vida_enemigo_out
        return reward, vida_enemigo_out