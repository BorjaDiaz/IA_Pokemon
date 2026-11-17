"""Piloto híbrido: buscador de caminos, política de combate y los primeros objetivos en el emulador."""
import os
import unittest

from src.utils import config

MAPAS_JSON = os.path.join(config.BASE_DIR, "data", "mapas.json")
INICIO = os.path.join(config.STATES_DIR, "inicio.state")


@unittest.skipUnless(os.path.exists(MAPAS_JSON), "Falta data/mapas.json (tools/build_mapas.py)")
class RutasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from src.piloto import rutas
        from src.utils import mapas
        cls.rutas, cls.mapas = rutas, mapas

    def vecinos(self, nombre, x, y):
        clave = self.mapas.POR_NOMBRE[nombre].clave
        return {d: (self.mapas.MAPAS[n[0]].nombre, n[1], n[2]) for d, n, _ in self.rutas.vecinos((clave, x, y))}

    def test_a_ledge_tile_is_walked_onto_and_hopped_from(self):
        # Ruta 30, comprobado en el emulador: (4, 24) es bordillo; se entra de lado y, empujando hacia abajo,
        # se salta el escalón (4, 25) y se cae en (4, 26)
        self.assertEqual(self.vecinos("ROUTE_30", 5, 24)["left"], ("ROUTE_30", 4, 24))
        self.assertEqual(self.vecinos("ROUTE_30", 4, 24)["down"], ("ROUTE_30", 4, 26))
        self.assertNotIn("up", self.vecinos("ROUTE_30", 4, 26))  # el escalón no se sube

    def test_stepping_on_a_door_leads_inside_and_the_carpet_leads_back(self):
        self.assertEqual(self.vecinos("NEW_BARK_TOWN", 6, 4)["up"], ("ELMS_LAB", 4, 11))
        self.assertEqual(self.vecinos("ELMS_LAB", 4, 11)["down"], ("NEW_BARK_TOWN", 6, 3))

    def test_walking_off_the_edge_enters_the_connected_map(self):
        self.assertEqual(self.vecinos("NEW_BARK_TOWN", 0, 8)["left"], ("ROUTE_29", 59, 8))

    def test_finds_the_way_across_several_maps(self):
        origen = (self.mapas.POR_NOMBRE["PLAYERS_HOUSE_2F"].clave, 3, 3)
        destino = self.mapas.POR_NOMBRE["VIOLET_CITY"].clave
        pasos = self.rutas.ruta(origen, lambda n: n[0] == destino)
        recorridos = [self.mapas.MAPAS[n[0]].nombre for _, n in pasos]
        for nombre in ("NEW_BARK_TOWN", "ROUTE_29", "CHERRYGROVE_CITY", "ROUTE_30", "ROUTE_31", "VIOLET_CITY"):
            self.assertIn(nombre, recorridos)

    def test_goes_around_a_blocked_tile(self):
        clave = self.mapas.POR_NOMBRE["ROUTE_30"].clave
        libre = self.rutas.ruta((clave, 5, 26), lambda n: n == (clave, 5, 22))
        rodeo = self.rutas.ruta((clave, 5, 26), lambda n: n == (clave, 5, 22), bloqueadas={(clave, 5, 23)})
        self.assertIsNotNone(libre)
        self.assertTrue(rodeo is None or len(rodeo) > len(libre))

    def test_talking_across_a_counter(self):
        from src.piloto.piloto import casillas_para_hablar
        centro = self.mapas.POR_NOMBRE["CHERRYGROVE_POKECENTER_1F"]
        enfermera = centro.objetos[0]
        opciones = casillas_para_hablar(centro, enfermera["x"], enfermera["y"])
        self.assertIn((enfermera["x"], enfermera["y"] + 2), opciones)
        self.assertEqual(opciones[(enfermera["x"], enfermera["y"] + 2)], "up")


class JuegoFalso:
    """Lo mínimo de Juego para probar una política de combate sin emulador."""

    def __init__(self, ataques, pp, filas, columnas, cursor_y, cursor_x=1):
        from src.piloto import combate as c
        self.c, self.pulsados = c, []
        self.memoria = {c.ADDR_MENU_ROWS: filas, c.ADDR_MENU_COLS: columnas, c.ADDR_MENU_CURSOR_Y: cursor_y,
                        c.ADDR_MENU_CURSOR_X: cursor_x}
        for i in range(4):
            self.memoria[c.ADDR_BATTLE_MON_MOVES + i] = ataques[i] if i < len(ataques) else 0
            self.memoria[c.ADDR_BATTLE_MON_PP + i] = pp[i] if i < len(pp) else 0
        self.pb = type("PB", (), {"memory": self.memoria})()

    def pulsar(self, boton, *_):
        self.pulsados.append(boton)
        if boton == "down":  # el cursor del menú de ataques baja (y da la vuelta)
            filas = self.memoria[self.c.ADDR_MENU_ROWS]
            self.memoria[self.c.ADDR_MENU_CURSOR_Y] = self.memoria[self.c.ADDR_MENU_CURSOR_Y] % filas + 1


class CombateTests(unittest.TestCase):
    PLACAJE, MALICIOSO, PANTALLAHUMO, ASCUAS = 33, 43, 108, 52

    def setUp(self):
        from src.piloto import combate
        self.combate = combate

    def test_moves_the_cursor_to_the_strongest_move_with_pp(self):
        juego = JuegoFalso([self.PLACAJE, self.MALICIOSO, self.PANTALLAHUMO, self.ASCUAS], [35, 30, 20, 25], 4, 1, 1)
        for _ in range(4):
            self.combate.mejor_ataque(juego)
        self.assertEqual(juego.pulsados, ["down", "down", "down", "a"])  # Ascuas (40) antes que Placaje (35)

    def test_skips_a_move_without_pp(self):
        # Sin esto se quedaba para siempre eligiendo Placaje con 0 PP ("¡No quedan PP!")
        juego = JuegoFalso([self.PLACAJE, self.MALICIOSO, self.PANTALLAHUMO, self.ASCUAS], [35, 30, 20, 0], 4, 1, 4)
        self.combate.mejor_ataque(juego)
        self.assertEqual(juego.pulsados, ["down"])
        self.assertEqual(juego.memoria[self.combate.ADDR_MENU_CURSOR_Y], 1)

    def test_goes_back_to_fight_in_the_main_menu(self):
        juego = JuegoFalso([self.PLACAJE, self.MALICIOSO], [35, 30], 2, 2, 2)  # cursor en MOCHILA
        self.combate.mejor_ataque(juego)
        self.assertEqual(juego.pulsados, ["up"])

    def test_presses_a_when_there_is_text_instead_of_the_move_menu(self):
        juego = JuegoFalso([self.PLACAJE, self.MALICIOSO, self.PANTALLAHUMO, self.ASCUAS], [35, 30, 20, 25], 4, 1, 1)
        juego.pulsar = lambda boton, *_: juego.pulsados.append(boton)  # el cursor no responde: hay un texto
        self.combate.mejor_ataque(juego)
        self.assertEqual(juego.pulsados, ["down", "a"])


@unittest.skipUnless(os.path.exists(MAPAS_JSON) and os.path.exists(config.ROM_PATH) and os.path.exists(INICIO),
                     "Faltan data/mapas.json, la ROM o state/inicio.state")
class PilotoEnElJuegoTests(unittest.TestCase):
    def test_gets_the_starter_from_the_bedroom(self):
        from src.piloto.juego import Juego
        from src.piloto.objetivos import OBJETIVOS
        from src.piloto.piloto import Piloto
        juego = Juego()
        try:
            juego.cargar(INICIO)
            piloto = Piloto(juego, registro=lambda _: None)
            self.assertTrue(piloto.conseguir(OBJETIVOS[0], max_decisiones=1500))
            self.assertEqual((juego.equipo(), juego.nivel()), (1, 5))
            self.assertLess(juego.frames / 59.73, 180)  # ~2 min de juego (la IA anterior: 118 s de récord)
        finally:
            juego.cerrar()


if __name__ == "__main__":
    unittest.main()
