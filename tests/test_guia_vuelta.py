"""Guía de la vuelta a Elm con el huevo: premia acercarse a la salida, solo superando la mejor marca."""
import unittest
from types import SimpleNamespace

import src.utils.constantes as c
from src.env.pokemon_env import PokemonGoldEnv
from src.utils import rom_catalog

RUTA_30 = next(m for m, n in rom_catalog.MAPS.items() if n == "ROUTE_30")
CEREZO = next(m for m, n in rom_catalog.MAPS.items() if n == "CHERRYGROVE_CITY")


class GuiaVueltaTests(unittest.TestCase):
    def env(self, huevo=True, entregado=False):
        activos = {rom_catalog.EVENT_FLAGS[n] for n, on in ((c.VUELTA_REQUISITO, huevo), (c.VUELTA_PROHIBIDO, entregado)) if on}
        e = PokemonGoldEnv.__new__(PokemonGoldEnv)
        e.ram = SimpleNamespace(leer=lambda addr: sum(1 << b for a, b in activos if a == addr))
        e.mejor_vuelta = {}
        return e

    def test_each_tile_closer_to_the_exit_than_ever_is_rewarded_once(self):
        e = self.env()
        self.assertEqual(e._guia_vuelta(RUTA_30, 17, 6), 0.0)                       # fija la marca
        self.assertAlmostEqual(e._guia_vuelta(RUTA_30, 17, 7), c.REWARD_VUELTA_AVANCE)  # hacia el sur
        self.assertEqual(e._guia_vuelta(RUTA_30, 17, 6), 0.0)                       # volver atrás no paga
        self.assertEqual(e._guia_vuelta(RUTA_30, 17, 7), 0.0)                       # ni repetir la marca
        self.assertAlmostEqual(e._guia_vuelta(RUTA_30, 3, 8), c.REWARD_VUELTA_AVANCE)   # x no cuenta en la Ruta 30

    def test_each_map_has_its_own_direction(self):
        e = self.env()
        e._guia_vuelta(CEREZO, 17, 0)
        self.assertAlmostEqual(e._guia_vuelta(CEREZO, 18, 0), c.REWARD_VUELTA_AVANCE)   # Cerezo: hacia el este...
        self.assertAlmostEqual(e._guia_vuelta(CEREZO, 18, 1), c.REWARD_VUELTA_AVANCE)   # ...y bajando a la fila 6
        self.assertEqual(e._guia_vuelta(CEREZO, 17, 1), 0.0)                            # (donde salta el rival)

    def test_only_while_carrying_the_egg(self):
        for e in (self.env(huevo=False), self.env(entregado=True)):
            e._guia_vuelta(RUTA_30, 17, 6)
            self.assertEqual(e._guia_vuelta(RUTA_30, 17, 7), 0.0)

    def test_odd_readings_do_not_pay(self):
        e = self.env()
        e._guia_vuelta(RUTA_30, 17, 6)
        self.assertEqual(e._guia_vuelta(RUTA_30, 17, 255), 0.0)    # transición entre mapas
        self.assertEqual(e._guia_vuelta(RUTA_30, 17, 20), 0.0)     # salto de warp: fija sin premiar
        self.assertAlmostEqual(e._guia_vuelta(RUTA_30, 17, 21), c.REWARD_VUELTA_AVANCE)


if __name__ == "__main__":
    unittest.main()
