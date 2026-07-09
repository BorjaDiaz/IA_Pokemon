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
            
        if hasattr(c, 'PENALTY_DAMAGE_MULT'):
            return danio_recibido * c.PENALTY_DAMAGE_MULT
            
        return c.PENALTY_COMBAT_DAMAGE_RECEIVED

    def calcular_bonus_prisa_flag(self, steps_actuales):
        """Calcula el bonus por conseguir un objetivo de la historia rápidamente."""
        distancia_al_limite = max(0, c.MAX_STEPS_PER_EPISODE - steps_actuales)
        # Cuanto más rápido lo haga, más de este colchón se lleva
        return distancia_al_limite / 1000.0