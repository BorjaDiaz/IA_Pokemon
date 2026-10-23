"""Verifica contra la ROM real que las direcciones de RAM y los event flags son correctos.

Necesita roms/Pokemon_Oro.gbc y los savestates de state/; si faltan, se saltan.
"""
import os
import random
import unittest

import src.utils.config as config
from src.utils import rom_catalog

RAM = rom_catalog.RAM
ROM_AVAILABLE = os.path.exists(config.ROM_PATH)
EVENT_FLAG_ACTION = 0x2F53

ROUTE_29_WILD = {16, 19, 161, 163}  # Pidgey, Rattata, Sentret, Hoothoot
CYNDAQUIL = 155


@unittest.skipUnless(ROM_AVAILABLE, "ROM no disponible")
class RomAddressTests(unittest.TestCase):
    def setUp(self):
        from pyboy import PyBoy
        self.pb = PyBoy(config.ROM_PATH, window="null", sound_emulated=False)
        self.pb.set_emulation_speed(0)
        # Sin congelar el reloj del cartucho el juego no es determinista (hora, día, RNG)
        self.pb.rtc_lock_experimental(True)

    def tearDown(self):
        self.pb.stop()

    def load(self, state_name):
        with open(os.path.join(config.STATES_DIR, state_name), "rb") as f:
            self.pb.load_state(f)

    def mem(self, name, offset=0):
        return self.pb.memory[1, RAM[name] + offset]

    def mem16(self, name):
        return self.mem(name) << 8 | self.mem(name, 1)

    def walk(self, direction, times=1):
        for _ in range(times):
            self.pb.button(direction, 10)
            self.pb.tick(30)

    def flag(self, event_name):
        addr, bit = rom_catalog.EVENT_FLAGS[event_name]
        return self.pb.memory[1, addr] >> bit & 1

    # --- Cabecera y código ---

    def test_rom_is_spanish_gold(self):
        header = bytes(self.pb.memory[0, 0x134 + i] for i in range(15))
        self.assertEqual(header, b"POKEMON_GLDAAUS")

    def test_event_flag_action_uses_event_flags_base(self):
        # ld hl, wEventFlags / call FlagAction / ret
        code = bytes(self.pb.memory[0, EVENT_FLAG_ACTION + i] for i in range(7))
        base = RAM["wEventFlags"]
        self.assertEqual(code, bytes([0x21, base & 0xFF, base >> 8, 0xCD, 0x5A, 0x2F, 0xC9]))

    # --- Coordenadas y mapas ---

    def test_walking_changes_only_the_expected_coordinate(self):
        self.load("inicio.state")
        self.assertEqual(rom_catalog.map_name(self.mem("wMapGroup"), self.mem("wMapNumber")), "PLAYERS_HOUSE_2F")
        x, y = self.mem("wXCoord"), self.mem("wYCoord")

        self.walk("right")
        self.assertEqual((self.mem("wXCoord"), self.mem("wYCoord")), (x + 1, y))
        self.walk("up")
        self.assertEqual((self.mem("wXCoord"), self.mem("wYCoord")), (x + 1, y - 1))

    def test_player_sprite_coords_are_map_coords_plus_4(self):
        for state in ("inicio.state", "ruta_29.state", "best_speedrun_got_cyndaquil.state"):
            self.load(state)
            self.assertEqual(self.mem("wPlayerMapX"), self.mem("wXCoord") + 4, state)
            self.assertEqual(self.mem("wPlayerMapY"), self.mem("wYCoord") + 4, state)

    def test_stairs_warp_to_players_house_1f(self):
        # La escalera de la habitación (7,0) lleva a la de la planta baja (9,0) según pret;
        # al llegar, el juego baja al jugador un paso automáticamente
        self.load("inicio.state")
        self.walk("right", 4)
        self.walk("up", 3)
        self.pb.tick(60)
        self.assertEqual(rom_catalog.map_name(self.mem("wMapGroup"), self.mem("wMapNumber")), "PLAYERS_HOUSE_1F")
        self.assertEqual((self.mem("wXCoord"), self.mem("wYCoord")), (9, 1))

    def test_savestate_maps_match_catalog(self):
        expected = {
            "inicio.state": "PLAYERS_HOUSE_2F",
            "best_speedrun_got_pokegear_1.state": "PLAYERS_HOUSE_1F",
            "best_speedrun_got_cyndaquil.state": "ELMS_LAB",
            "ruta_29.state": "ROUTE_29",
        }
        for state, map_const in expected.items():
            self.load(state)
            self.assertEqual(rom_catalog.map_name(self.mem("wMapGroup"), self.mem("wMapNumber")), map_const, state)

    # --- Equipo y objetos clave ---

    def test_party_structs(self):
        self.load("inicio.state")
        self.assertEqual(self.mem("wPartyCount"), 0)

        self.load("ruta_29.state")
        self.assertEqual(self.mem("wPartyCount"), 1)
        self.assertEqual(self.mem("wPartyCount", 1), CYNDAQUIL)  # wPartySpecies
        self.assertEqual(self.mem("wPartyMons"), CYNDAQUIL)
        level = self.mem("wPartyMons", 0x1F)
        hp = self.mem("wPartyMons", 0x22) << 8 | self.mem("wPartyMons", 0x23)
        max_hp = self.mem("wPartyMons", 0x24) << 8 | self.mem("wPartyMons", 0x25)
        self.assertTrue(1 <= level <= 100)
        self.assertTrue(0 < hp <= max_hp)

    def test_pokegear_flag(self):
        self.load("inicio.state")
        self.assertFalse(self.mem("wPokegearFlags") >> 7 & 1)
        self.load("best_speedrun_got_pokegear_1.state")
        self.assertTrue(self.mem("wPokegearFlags") >> 7 & 1)

    # --- Combate ---

    def test_wild_battle_on_route_29(self):
        self.load("ruta_29.state")
        self.assertEqual(self.mem("wBattleMode"), 0)
        rng = random.Random(1)
        for _ in range(3000):
            if self.mem("wBattleMode"):
                break
            self.walk(rng.choice(["up", "down", "left", "right"]))
        else:
            self.fail("No hubo encuentro salvaje")

        self.pb.tick(400)
        self.assertEqual(self.mem("wBattleMode"), 1)  # salvaje
        self.assertIn(self.mem("wEnemyMonSpecies"), ROUTE_29_WILD)
        self.assertTrue(2 <= self.mem("wEnemyMonLevel") <= 5)
        hp, max_hp = self.mem16("wEnemyMonHP"), self.mem16("wEnemyMonMaxHP")
        self.assertTrue(0 < hp <= max_hp)

    # --- Event flags ---

    def test_savestate_story_flags(self):
        self.load("inicio.state")
        self.assertFalse(self.flag("EVENT_GOT_A_POKEMON_FROM_ELM"))
        self.load("best_speedrun_got_cyndaquil.state")
        self.assertTrue(self.flag("EVENT_GOT_CYNDAQUIL_FROM_ELM"))
        self.assertFalse(self.flag("EVENT_GOT_TOTODILE_FROM_ELM"))
        self.assertFalse(self.flag("EVENT_GOT_CHIKORITA_FROM_ELM"))

    def test_game_sets_got_cyndaquil_flag_through_event_flag_action(self):
        """El propio juego activa el flag nº 27 (EVENT_GOT_CYNDAQUIL_FROM_ELM) al elegir a Cyndaquil."""
        self.load("best_speedrun_got_pokegear_1.state")
        calls = []
        self.pb.hook_register(0, EVENT_FLAG_ACTION,
                              lambda _: calls.append((self.pb.register_file.B, self.pb.register_file.D << 8 | self.pb.register_file.E)), None)

        # Botones al azar con semilla fija; con el reloj congelado llega a Cyndaquil hacia el frame 30775
        rng = random.Random(4)
        buttons = ["up", "down", "left", "right", "a", "a", "b"]
        for frame in range(45000):
            if frame % 16 == 0:
                self.pb.button(rng.choice(buttons), 8)
            self.pb.tick()
            if (1, 27) in calls:
                break

        self.assertIn((1, 27), calls)
        self.assertEqual(rom_catalog.EVENT_FLAG_NAMES[(RAM["wEventFlags"] + 27 // 8, 27 % 8)], "EVENT_GOT_CYNDAQUIL_FROM_ELM")
        self.assertTrue(self.flag("EVENT_GOT_CYNDAQUIL_FROM_ELM"))


if __name__ == "__main__":
    unittest.main()
