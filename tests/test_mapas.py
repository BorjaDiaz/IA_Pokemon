"""Geometría de los mapas extraída de la ROM (tools/build_mapas.py), contrastada con pret y con el juego."""
import os
import random
import unittest

from src.utils import config

MAPAS_JSON = os.path.join(config.BASE_DIR, "data", "mapas.json")
ESTADO_CEREZO = os.path.join(config.STATES_DIR, "best_speedrun_LLEGADA_CHERRYGROVE_CITY.state")


@unittest.skipUnless(os.path.exists(MAPAS_JSON), "Falta data/mapas.json (tools/build_mapas.py)")
class MapasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from src.utils import mapas
        cls.mapas = mapas

    def test_new_bark_town_matches_the_disassembly(self):
        # maps/NewBarkTown.asm de pret: warp_event x, y, destino
        pueblo = self.mapas.POR_NOMBRE["NEW_BARK_TOWN"]
        self.assertEqual((pueblo.ancho, pueblo.alto), (20, 18))
        destinos = [(w["x"], w["y"], self.mapas.MAPAS[w["mapa"]].nombre) for w in pueblo.warps]
        self.assertEqual(destinos, [(6, 3, "ELMS_LAB"), (13, 5, "PLAYERS_HOUSE_1F"),
                                    (3, 11, "PLAYERS_NEIGHBORS_HOUSE"), (11, 13, "ELMS_HOUSE")])
        self.assertEqual(self.mapas.MAPAS[pueblo.conexiones["oeste"]["mapa"]].nombre, "ROUTE_29")
        self.assertEqual([o["evento"] for o in pueblo.objetos][-1], "EVENT_RIVAL_NEW_BARK_TOWN")

    def test_doors_are_walkable_and_walls_are_not(self):
        pueblo = self.mapas.POR_NOMBRE["NEW_BARK_TOWN"]
        self.assertEqual(self.mapas.NOMBRES_COLISION[pueblo.colision_en(6, 3)], "DOOR")  # laboratorio de Elm
        self.assertTrue(pueblo.andable(6, 4))
        self.assertFalse(pueblo.andable(0, 0))
        self.assertEqual(pueblo.permiso(19, 6), "WATER")
        self.assertEqual(pueblo.permiso(-1, 0), "WALL")  # fuera del mapa

    def test_every_warp_leads_to_an_existing_warp(self):
        for mapa in self.mapas.MAPAS.values():
            for w in mapa.warps:
                if w["mapa"] == (0, 0) or w["warp"] in (0, 255):  # sin destino fijo: vuelve por donde se entró
                    continue
                destino = self.mapas.MAPAS.get(w["mapa"])
                self.assertIsNotNone(destino, (mapa.nombre, w))
                self.assertLessEqual(w["warp"], len(destino.warps), (mapa.nombre, w))

    def test_almost_every_warp_sits_on_a_door_stairs_or_carpet_tile(self):
        total = en_su_sitio = 0
        for mapa in self.mapas.MAPAS.values():
            for w in mapa.warps:
                total += 1
                c = mapa.colision_en(w["x"], w["y"])
                en_su_sitio += c is not None and 0x60 <= c <= 0x7F
        self.assertGreater(en_su_sitio / total, 0.95)


@unittest.skipUnless(os.path.exists(MAPAS_JSON) and os.path.exists(config.ROM_PATH) and os.path.exists(ESTADO_CEREZO),
                     "Faltan data/mapas.json, la ROM o el savestate de Cerezo")
class MapasEnElJuegoTests(unittest.TestCase):
    """Lo extraído coincide con lo que el juego carga y con dónde deja andar al personaje."""

    @classmethod
    def setUpClass(cls):
        from pyboy import PyBoy
        from src.utils import mapas
        cls.mapas = mapas
        cls.pb = PyBoy(config.ROM_PATH, window="null", sound_emulated=False)
        with open(config.ROM_PATH, "rb") as f:
            cls.rom = f.read()

    @classmethod
    def tearDownClass(cls):
        cls.pb.stop(save=False)

    def setUp(self):
        with open(ESTADO_CEREZO, "rb") as f:
            self.pb.load_state(f)
        self.pb.tick(4, False)

    def test_the_tileset_table_is_where_the_game_reads_it(self):
        # wMapTileset (D082) y la copia en WRAM de su entrada de 15 bytes (wTilesetBank, D0C2)
        tileset = self.pb.memory[1, 0xD082]
        cargado = bytes(self.pb.memory[1, 0xD0C2 + i] for i in range(15))
        tabla = 0x05 * 0x4000 + (0x56D3 - 0x4000) + 15 * tileset
        self.assertEqual(self.rom[tabla:tabla + 15], cargado)

    def test_the_player_only_ever_stands_on_walkable_tiles(self):
        from pyboy.utils import WindowEvent as W
        botones = [(W.PRESS_ARROW_UP, W.RELEASE_ARROW_UP), (W.PRESS_ARROW_DOWN, W.RELEASE_ARROW_DOWN),
                   (W.PRESS_ARROW_LEFT, W.RELEASE_ARROW_LEFT), (W.PRESS_ARROW_RIGHT, W.RELEASE_ARROW_RIGHT)]
        rng, total, malas = random.Random(0), 0, 0
        for _ in range(400):
            pulsar, soltar = rng.choice(botones)
            self.pb.send_input(pulsar); self.pb.tick(8, False)
            self.pb.send_input(soltar); self.pb.tick(8, False)
            if self.pb.memory[1, 0xD116] or self.pb.memory[1, 0xD15F]:  # combate o escena
                continue
            x, y = self.pb.memory[1, 0xDA03], self.pb.memory[1, 0xDA02]
            mapa = self.mapas.MAPAS.get((self.pb.memory[1, 0xDA00], self.pb.memory[1, 0xDA01]))
            if mapa is None or 255 in (x, y):
                continue
            total += 1
            malas += mapa.permiso(x, y) == "WALL"
        self.assertGreater(total, 200)
        self.assertLessEqual(malas, total * 0.01)  # como mucho, lecturas en el fotograma de cambiar de mapa


if __name__ == "__main__":
    unittest.main()
