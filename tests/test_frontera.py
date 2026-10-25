"""Savestates de frontera: cuándo se guardan y cómo se nombran (sin emulador)."""
import os
import tempfile
import unittest
from types import SimpleNamespace

import src.utils.config as config
import src.utils.constantes as c
from src.env.pokemon_env import PokemonGoldEnv
from src.utils import rom_catalog

RUTA_29 = next(m for m, n in rom_catalog.MAPS.items() if n == "ROUTE_29")
CASA = next(m for m, n in rom_catalog.MAPS.items() if n == "PLAYERS_HOUSE_1F")


class FronteraTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.originales = (config.STATES_DIR, config.GUARDAR_RECORDS)
        config.STATES_DIR, config.GUARDAR_RECORDS = self.tmp.name, True
        e = PokemonGoldEnv.__new__(PokemonGoldEnv)
        e.rank, e.simulacro, e.fraccion_vida, e.fraccion_pp = 0, False, 1.0, 1.0
        e.splits, e.hitos_previos = {"EVENT_GOT_A_POKEMON_FROM_ELM": 1}, set()
        e.ram = SimpleNamespace(leer=lambda addr: 0)
        e.pb = SimpleNamespace(save_state=lambda f: f.write(b"partida"))
        e.frontera_conocida = set()
        self.env = e

    def tearDown(self):
        config.STATES_DIR, config.GUARDAR_RECORDS = self.originales
        self.tmp.cleanup()

    def guardadas(self):
        carpeta = os.path.join(self.tmp.name, config.FRONTERA_DIR)
        return sorted(os.listdir(carpeta)) if os.path.isdir(carpeta) else []

    def test_first_visit_to_a_zone_is_saved_once_with_the_current_mission(self):
        self.env._guardar_frontera(RUTA_29, 50, 7, False, False)
        self.env._guardar_frontera(RUTA_29, 51, 6, False, False)  # misma zona de 8x8: no se repite
        self.assertEqual(self.guardadas(), [f"m01_{RUTA_29[0]}_{RUTA_29[1]}_6_0.state"])
        self.assertEqual(c.HITOS[1], "LLEGADA_CHERRYGROVE_CITY")  # m01 = misión "llegar a Cerezo"

    def test_not_saved_indoors_in_battle_or_when_weak(self):
        self.env._guardar_frontera(CASA, 3, 3, False, False)        # interior
        self.env._guardar_frontera(RUTA_29, 50, 7, True, False)     # en combate
        self.env.fraccion_pp = 0.2                                  # sin PP: sería una trampa
        self.env._guardar_frontera(RUTA_29, 30, 7, False, False)
        self.assertEqual(self.guardadas(), [])

    def test_tests_and_ver_ia_do_not_save(self):
        config.GUARDAR_RECORDS = False
        self.env._guardar_frontera(RUTA_29, 50, 7, False, False)
        self.assertEqual(self.guardadas(), [])


if __name__ == "__main__":
    unittest.main()
