"""PP de los ataques que hacen daño: lectura de la RAM, barra y premio por recuperarlos (sin emulador)."""
import unittest
from types import SimpleNamespace

import src.utils.constantes as c
from src.env.core.extractor_ram import RamExtractor
from src.env.pokemon_env import PokemonGoldEnv

PLACAJE, MALICIOSO, ASCUAS = 33, 43, 52   # potencia 35, 0 y 40; PP 35, 30 y 25


def ram_con(ataques, pps):
    """RAM de un equipo de 1 Pokémon con esos ataques y bytes de PP."""
    mem = {c.ADDR_PARTY_COUNT: 1}
    for slot, (ataque, pp) in enumerate(zip(ataques, pps)):
        mem[0xDA2A + 0x02 + slot] = ataque
        mem[0xDA2A + 0x17 + slot] = pp
    ram = RamExtractor.__new__(RamExtractor)
    ram.leer = lambda addr: mem.get(addr, 0)
    return ram


class LecturaPPTests(unittest.TestCase):
    def test_only_damaging_moves_count(self):
        # Placaje a 0 PP y Malicioso lleno: como el savestate de la vuelta a Cerezo, no puede hacer daño
        self.assertEqual(ram_con([PLACAJE, MALICIOSO], [0, 29]).leer_pp_ataques(), (0, 35))

    def test_pp_ups_raise_the_maximum(self):
        # 2 Más PP usados (bits altos = 2): Ascuas pasa de 25 a 25 + 2 * 5
        self.assertEqual(ram_con([ASCUAS], [(2 << 6) | 30]).leer_pp_ataques(), (30, 35))


class PremioPPTests(unittest.TestCase):
    def env(self, fraccion, maximos=35):
        e = PokemonGoldEnv.__new__(PokemonGoldEnv)
        e.rank, e.fraccion_pp, e.pp_maximos = 0, fraccion, maximos
        return e

    def recuperar(self, e, actuales, maximos=35, en_combate=False):
        e.ram = SimpleNamespace(leer_pp_ataques=lambda: (actuales, maximos))
        return e._premio_pp(en_combate)

    def test_restoring_from_empty_pays_up_to_the_threshold(self):
        self.assertAlmostEqual(self.recuperar(self.env(0.0), 35), c.REWARD_PP_FRAC * c.PP_UMBRAL)

    def test_restoring_when_it_was_not_needed_pays_nothing(self):
        self.assertEqual(self.recuperar(self.env(0.8), 35), 0.0)

    def test_new_move_or_battle_is_not_a_restore(self):
        self.assertEqual(self.recuperar(self.env(0.0), 60, maximos=60), 0.0)   # ataque nuevo: nueva referencia
        self.assertEqual(self.recuperar(self.env(0.0), 35, en_combate=True), 0.0)


if __name__ == "__main__":
    unittest.main()
