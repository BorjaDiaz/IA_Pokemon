import src.utils.constantes as c

class RewardSystem:
    def __init__(self, rank=0):
        self.rank = rank

    def calcular_premio_curacion(self, curacion, max_vida_equipo):
        """Premio proporcional a la fracción de PS del equipo recuperada (Centro Pokémon, pociones...).
        Es algo menor que la penalización por perder esos PS, así que no compensa hacerse daño para curarse."""
        if max_vida_equipo <= 0 or curacion <= 0:
            return 0.0
        return c.REWARD_HEAL_FRAC * min(1.0, curacion / max_vida_equipo)

    def calcular_premio_danio(self, danio_causado, vida_max_rival=0, bajo_objetivo=False):
        """Premio por golpear al rival: por debajo del nivel objetivo, proporcional a la fracción de sus PS
        máximos quitada; por encima, bajo, para que no prefiera quedarse pegando eternamente."""
        if danio_causado <= 0:
            return 0.0
        if bajo_objetivo and vida_max_rival > 0:
            return c.REWARD_DAMAGE_FRAC_BAJO_OBJETIVO * min(1.0, danio_causado / vida_max_rival)
        return danio_causado * c.REWARD_DAMAGE_MULT

    def calcular_penalizacion_danio_recibido(self, danio_recibido, max_vida_equipo):
        """Penalización proporcional a la fracción de PS del equipo perdida."""
        if danio_recibido <= 0 or max_vida_equipo <= 0:
            return 0.0
        return c.PENALTY_DAMAGE_FRAC * min(1.0, danio_recibido / max_vida_equipo)

    def calcular_bonus_prisa_flag(self, steps_actuales):
        """Bonus por conseguir un hito rápido: hasta REWARD_FLAG_STORY si es al principio del episodio."""
        fraccion_restante = max(0, c.MAX_STEPS_PER_EPISODE - steps_actuales) / c.MAX_STEPS_PER_EPISODE
        return c.REWARD_FLAG_STORY * fraccion_restante