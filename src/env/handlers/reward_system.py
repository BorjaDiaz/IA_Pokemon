import src.utils.constantes as c

class RewardSystem:
    def __init__(self, rank=0):
        self.rank = rank

    def calcular_premio_curacion(self, curacion, max_vida_equipo):
        """Calcula el premio por curarse. Modificado para evitar granjeo."""
        if max_vida_equipo <= 0 or curacion <= 0:
            return 0.0
            
        # 🛑 Reducimos drásticamente el peso de la curación. 
        # Es una pequeña ayuda para no morir, no un farmeo.
        porcentaje_curado = curacion / max_vida_equipo
        return porcentaje_curado * (c.REWARD_HEAL * 0.2)

    def calcular_premio_danio(self, danio_causado):
        """Calcula el premio por golpear al rival."""
        if danio_causado <= 0:
            return 0.0
        # Multiplicador bajo para que no prefiera quedarse pegando eternamente
        return danio_causado * c.REWARD_DAMAGE_MULT

    def calcular_penalizacion_danio_recibido(self, danio_recibido):
        """Calcula una penalización proporcional por recibir daño."""
        if danio_recibido <= 0:
            return 0.0
        return c.PENALTY_COMBAT_DAMAGE_RECEIVED

    def calcular_bonus_prisa_flag(self, steps_actuales):
        """Bonus por conseguir un hito rápido: hasta REWARD_FLAG_STORY si es al principio del episodio."""
        fraccion_restante = max(0, c.MAX_STEPS_PER_EPISODE - steps_actuales) / c.MAX_STEPS_PER_EPISODE
        return c.REWARD_FLAG_STORY * fraccion_restante