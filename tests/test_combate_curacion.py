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
        gestor = SimpleNamespace(leer_vida_enemigo=lambda: 0, leer_vida_max_enemigo=lambda: 20)
        ram = SimpleNamespace(leer_max_vida_total_equipo=lambda: 20)
        reward, _ = h.procesar(None, ram, RewardSystem(), gestor, True, 20, 20, 1, "ROUTE_29")
        return reward

    def test_knockouts_are_worth_more_while_below_the_target_level(self):
        # El último golpe quita 5 de 20 PS: por debajo vale su fracción, por encima el multiplicador bajo
        golpe = c.REWARD_DAMAGE_FRAC_BAJO_OBJETIVO * 5 / 20 - 5 * c.REWARD_DAMAGE_MULT
        extra = c.REWARD_KO_BAJO_OBJETIVO - c.REWARD_KO_SOBRE_OBJETIVO
        self.assertAlmostEqual(self.ko(True) - self.ko(False), extra + golpe)

    def test_each_hit_below_target_is_worth_its_share_of_the_rival_hp(self):
        r = RewardSystem()
        self.assertAlmostEqual(r.calcular_premio_danio(10, 40, bajo_objetivo=True), c.REWARD_DAMAGE_FRAC_BAJO_OBJETIVO / 4)
        self.assertAlmostEqual(r.calcular_premio_danio(99, 40, bajo_objetivo=True), c.REWARD_DAMAGE_FRAC_BAJO_OBJETIVO)
        self.assertAlmostEqual(r.calcular_premio_danio(10, 40, bajo_objetivo=False), 10 * c.REWARD_DAMAGE_MULT)

    def test_a_knockout_below_target_is_flagged_as_progress(self):
        h = CombatHandler(rank=0, logger=None)
        for bajo in (True, False):
            h.bajo_objetivo, h.vida_enemigo_anterior = bajo, 5
            h.procesar(None, SimpleNamespace(leer_max_vida_total_equipo=lambda: 20), RewardSystem(),
                       SimpleNamespace(leer_vida_enemigo=lambda: 0, leer_vida_max_enemigo=lambda: 20), True, 20, 20, 1, "ROUTE_29")
            self.assertEqual(h.ko_bajo_objetivo, bajo)


class HuidaTests(unittest.TestCase):
    """Huir solo se penaliza si hacía falta entrenar y el combate era razonable."""

    def setUp(self):
        from src.env.pokemon_env import PokemonGoldEnv, nuevas_estadisticas_combate
        self.env = PokemonGoldEnv.__new__(PokemonGoldEnv)
        self.env.combates = nuevas_estadisticas_combate()
        self.env.logger, self.env.steps_count = None, 100
        self.env.h_combat = SimpleNamespace(bajo_objetivo=True)
        self.env.nivel_max_previo, self.env.fraccion_vida = 5, 1.0

    def huir(self, nivel_rival=3, tipo="salvaje"):
        self.env.combate_actual = {"tipo": tipo, "inicio": 40, "rival": 16, "nivel_rival": nivel_rival, "mapa": "ROUTE_29"}
        return self.env._cerrar_combate("huido")

    def test_fleeing_an_easy_battle_while_under_level_is_penalized(self):
        self.assertEqual(self.huir(), c.PENALTY_HUIR_BAJO_OBJETIVO)
        self.assertEqual(self.env.combates["huidas_penalizadas"], 1)

    def test_fleeing_is_free_otherwise(self):
        self.assertEqual(self.huir(nivel_rival=6), 0.0)              # el salvaje es más fuerte
        self.env.fraccion_vida = 0.4
        self.assertEqual(self.huir(), 0.0)                           # con la vida baja
        self.env.fraccion_vida, self.env.h_combat.bajo_objetivo = 1.0, False
        self.assertEqual(self.huir(), 0.0)                           # ya tiene nivel suficiente
        self.assertEqual(self.env.combates["huidas_penalizadas"], 0)


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
