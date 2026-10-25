"""Elección de la salida de cada episodio (salidas mezcladas), sin emulador."""
import os
import random
import tempfile
import unittest
from collections import Counter
from types import SimpleNamespace

import src.utils.config as config
import src.utils.constantes as c
from src.env.pokemon_env import PokemonGoldEnv

HITOS = list(c.HITOS)


class SalidasTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.originales = (config.STATES_DIR, config.SALIDAS_MEZCLADAS, config.PROB_SALIDA_INICIO, config.CURRENT_STAGE)
        config.STATES_DIR = self.tmp.name
        config.SALIDAS_MEZCLADAS, config.PROB_SALIDA_INICIO = True, 0.5
        config.CURRENT_STAGE = 0
        # _elegir_salida solo usa self.rng: no hace falta arrancar el emulador
        self.env = SimpleNamespace(rng=random.Random(0), salida_fija=None)

    def tearDown(self):
        config.STATES_DIR, config.SALIDAS_MEZCLADAS, config.PROB_SALIDA_INICIO, config.CURRENT_STAGE = self.originales
        self.tmp.cleanup()

    def crear_hito(self, hito):
        open(os.path.join(self.tmp.name, f"best_speedrun_{hito}.state"), "wb").close()

    def elegir(self, n=4000):
        return Counter(PokemonGoldEnv._elegir_salida(self.env) for _ in range(n))

    def test_without_milestones_always_starts_at_base(self):
        self.assertEqual(self.elegir(100), Counter({"inicio.state": 100}))

    def test_half_from_base_half_from_milestone(self):
        self.crear_hito(HITOS[0])
        salidas = self.elegir()
        self.assertAlmostEqual(salidas["inicio.state"] / 4000, 0.5, delta=0.04)
        self.assertAlmostEqual(salidas[f"best_speedrun_{HITOS[0]}.state"] / 4000, 0.5, delta=0.04)

    def test_milestones_share_the_other_half_equally(self):
        for hito in HITOS[:3]:
            self.crear_hito(hito)
        salidas = self.elegir()
        # Un tramo bloqueado (p. ej. el rival desde el huevo) no se lleva más episodios que los demás
        for hito in HITOS[:3]:
            self.assertAlmostEqual(salidas[f"best_speedrun_{hito}.state"] / 4000, 0.5 / 3, delta=0.04)

    def test_a_quarter_of_episodes_are_battle_drills_when_there_are_battle_states(self):
        self.crear_hito(HITOS[0])
        os.makedirs(os.path.join(self.tmp.name, config.SIMULACRO_DIR))
        for n in (1, 2):
            open(os.path.join(self.tmp.name, config.SIMULACRO_DIR, f"combate_{HITOS[0]}_0{n}.state"), "wb").close()
        salidas = self.elegir()
        simulacros = sum(v for k, v in salidas.items() if os.path.dirname(k) == config.SIMULACRO_DIR)
        self.assertAlmostEqual(simulacros / 4000, config.PROB_SIMULACRO_COMBATE, delta=0.04)
        self.assertEqual(len([k for k in salidas if os.path.dirname(k) == config.SIMULACRO_DIR]), 2)  # usa todos
        self.assertAlmostEqual(salidas["inicio.state"] / 4000, (1 - config.PROB_SIMULACRO_COMBATE) * 0.5, delta=0.04)

    def test_frontier_states_are_used_and_the_least_chosen_weigh_more(self):
        self.crear_hito(HITOS[0])
        os.makedirs(os.path.join(self.tmp.name, config.FRONTERA_DIR))
        for nombre in ("m01_24_3_1_0.state", "m01_24_3_2_0.state"):
            open(os.path.join(self.tmp.name, config.FRONTERA_DIR, nombre), "wb").close()
        salidas = self.elegir()
        frontera = {k: v for k, v in salidas.items() if os.path.dirname(k) == config.FRONTERA_DIR}
        self.assertAlmostEqual(sum(frontera.values()) / 4000, config.PROB_FRONTERA, delta=0.04)
        self.assertEqual(len(frontera), 2)
        a, b = frontera.values()
        self.assertLess(abs(a - b) / (a + b), 0.15)  # se reparten: la menos elegida pasa a pesar más

    def test_disabled_uses_curriculum_stage(self):
        self.crear_hito(HITOS[0])
        config.SALIDAS_MEZCLADAS = False
        self.assertEqual(self.elegir(50), Counter({"inicio.state": 50}))


if __name__ == "__main__":
    unittest.main()
