"""Recompensas de combate y curación: proporcionales a los PS y con nivel objetivo por tramo."""
import unittest
from types import SimpleNamespace

import src.utils.constantes as c
from src.env.handlers.combat import CombatHandler
from src.env.handlers.reward_system import RewardSystem


class CuracionTests(unittest.TestCase):
    def test_damage_and_heal_are_proportional_and_heal_does_not_pay_for_damage(self):
        r = RewardSystem()
        dano = r.calcular_penalizacion_danio_recibido(20, 40)   # pierde la mitad de los PS
        cura = r.calcular_premio_curacion(20, 40)                # recupera esa misma mitad
        self.assertAlmostEqual(dano, c.PENALTY_DAMAGE_FRAC / 2)
        self.assertAlmostEqual(cura, c.REWARD_HEAL_FRAC / 2)
        self.assertLess(dano + cura, 0)  # hacerse daño y curarse nunca sale a cuenta
        self.assertGreater(r.calcular_premio_curacion(35, 40), r.calcular_premio_curacion(5, 40))  # más baja, más vale


class KOTests(unittest.TestCase):
    def ko(self, bajo_objetivo):
        h = CombatHandler(rank=0, logger=None)
        h.bajo_objetivo = bajo_objetivo
        h.vida_enemigo_anterior = 5
        gestor = SimpleNamespace(leer_vida_enemigo=lambda: 0)
        ram = SimpleNamespace(leer_max_vida_total_equipo=lambda: 20)
        reward, _ = h.procesar(None, ram, RewardSystem(), gestor, True, 20, 20, 1, "ROUTE_29")
        return reward

    def test_knockouts_are_worth_more_while_below_the_target_level(self):
        extra = c.REWARD_COMBAT_ENEMY_FAINTED * (c.MULT_KO_BAJO_OBJETIVO - 1)
        self.assertAlmostEqual(self.ko(True) - self.ko(False), extra)


class NivelObjetivoTests(unittest.TestCase):
    def env(self, splits=(), previos=()):
        from src.env.pokemon_env import PokemonGoldEnv
        e = PokemonGoldEnv.__new__(PokemonGoldEnv)
        e.splits, e.hitos_previos = dict.fromkeys(splits, 1), set(previos)
        e.ram = SimpleNamespace(leer=lambda addr: 0)  # ningún evento activo en la RAM
        return e

    def test_target_level_advances_with_milestones(self):
        self.assertEqual(self.env()._nivel_objetivo(), 8)
        self.assertEqual(self.env(splits=["RIVAL_CHERRYGROVE_SUPERADO"])._nivel_objetivo(), 12)
        self.assertEqual(self.env(previos=["RIVAL_CHERRYGROVE_SUPERADO", "EVENT_BEAT_FALKNER"])._nivel_objetivo(), 17)


if __name__ == "__main__":
    unittest.main()
