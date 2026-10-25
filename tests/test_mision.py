"""Misión en curso: el primer hito sin conseguir, y va en la observación en binario (sin emulador)."""
import unittest
from types import SimpleNamespace

import src.utils.constantes as c
from src.env.pokemon_env import BITS_MISION, PokemonGoldEnv


class MisionTests(unittest.TestCase):
    def env(self, splits=(), previos=()):
        e = PokemonGoldEnv.__new__(PokemonGoldEnv)
        e.splits, e.hitos_previos = dict.fromkeys(splits, 1), set(previos)
        e.ram = SimpleNamespace(leer=lambda addr: 0)  # ningún evento activo en la RAM
        return e

    def test_mission_is_the_first_milestone_not_reached(self):
        self.assertEqual(self.env()._mision_actual(), 0)
        self.assertEqual(self.env(splits=c.HITOS[:3])._mision_actual(), 3)
        huevo = c.HITOS.index("EVENT_GOT_MYSTERY_EGG_FROM_MR_POKEMON")
        self.assertEqual(c.HITOS[self.env(previos=c.HITOS[:huevo + 1])._mision_actual()], "VUELTA_CHERRYGROVE_CITY")

    def test_mission_is_encoded_in_binary_in_the_observation(self):
        self.assertGreaterEqual(2 ** BITS_MISION, len(c.HITOS) + 1)
        e = self.env()
        e.mision, e.fraccion_vida, e.fraccion_nivel = 5, 1.0, 0.5   # 5 = 0b101
        e.episode_tiles = set()
        e.ram = SimpleNamespace(leer=lambda addr: 1 if addr == c.ADDR_BATTLE_MODE else 0)
        import numpy as np
        e.pb = SimpleNamespace(screen=SimpleNamespace(ndarray=np.zeros((144, 160, 4), dtype=np.uint8)))
        franja = e._get_obs()[1][4:6]
        encendidos = [bool(franja[:, b * 10:(b + 1) * 10].all()) for b in range(BITS_MISION)]
        self.assertEqual(encendidos, [True, False, True] + [False] * (BITS_MISION - 3))


if __name__ == "__main__":
    unittest.main()
