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

HITOS = list(c.FLAGS)


class SalidasTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.originales = (config.STATES_DIR, config.SALIDAS_MEZCLADAS, config.PROB_SALIDA_INICIO,
                           config.PROB_HITO_MAS_AVANZADO, config.CURRENT_STAGE)
        config.STATES_DIR = self.tmp.name
        config.SALIDAS_MEZCLADAS, config.PROB_SALIDA_INICIO, config.PROB_HITO_MAS_AVANZADO = True, 0.5, 0.6
        config.CURRENT_STAGE = 0
        # _elegir_salida solo usa self.rng: no hace falta arrancar el emulador
        self.env = SimpleNamespace(rng=random.Random(0))

    def tearDown(self):
        (config.STATES_DIR, config.SALIDAS_MEZCLADAS, config.PROB_SALIDA_INICIO,
         config.PROB_HITO_MAS_AVANZADO, config.CURRENT_STAGE) = self.originales
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

    def test_most_advanced_milestone_is_preferred(self):
        for hito in HITOS[:3]:
            self.crear_hito(hito)
        salidas = self.elegir()
        mas_avanzado = salidas[f"best_speedrun_{HITOS[2]}.state"] / 4000
        # Mitad desde hitos; de esa mitad, el 60% desde el más avanzado y el resto entre los anteriores
        self.assertAlmostEqual(mas_avanzado, 0.5 * 0.6, delta=0.04)
        for anterior in HITOS[:2]:
            self.assertAlmostEqual(salidas[f"best_speedrun_{anterior}.state"] / 4000, 0.5 * 0.4 / 2, delta=0.04)

    def test_disabled_uses_curriculum_stage(self):
        self.crear_hito(HITOS[0])
        config.SALIDAS_MEZCLADAS = False
        self.assertEqual(self.elegir(50), Counter({"inicio.state": 50}))


if __name__ == "__main__":
    unittest.main()
