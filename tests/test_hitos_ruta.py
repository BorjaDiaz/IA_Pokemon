"""Hitos intermedios de ruta (llegadas a mapas) y filtro de coordenadas de los mapas de calor."""
import json
import os
import tempfile
import unittest
from types import SimpleNamespace

import numpy as np

import src.utils.config as config
import src.utils.constantes as c
from src.env.handlers.reward_system import RewardSystem
from src.env.handlers.story import StoryHandler


class HitosRutaTests(unittest.TestCase):
    def test_route_milestones_order(self):
        i = c.HITOS.index("EVENT_GOT_A_POKEMON_FROM_ELM")
        self.assertEqual(c.HITOS[i:i + 14], [
            "EVENT_GOT_A_POKEMON_FROM_ELM",
            "LLEGADA_CHERRYGROVE_CITY", "LLEGADA_ROUTE_30", "LLEGADA_MR_POKEMONS_HOUSE",
            "EVENT_GOT_MYSTERY_EGG_FROM_MR_POKEMON",
            "VUELTA_CHERRYGROVE_CITY", "RIVAL_CHERRYGROVE_SUPERADO", "VUELTA_ROUTE_29", "VUELTA_NEW_BARK_TOWN",
            "VUELTA_ELMS_LAB",
            "EVENT_GAVE_MYSTERY_EGG_TO_ELM",
            "LLEGADA_ROUTE_31", "LLEGADA_VIOLET_CITY", "LLEGADA_VIOLET_GYM",
        ])
        self.assertEqual(c.HITOS[i + 14], "EVENT_BEAT_FALKNER")
        mapa, requisito, _ = c.HITOS_MAPA["VUELTA_ROUTE_29"]
        self.assertEqual((c.MAP_NAMES[mapa], requisito), ("ROUTE_29", "EVENT_GOT_MYSTERY_EGG_FROM_MR_POKEMON"))

    def test_reaching_a_route_milestone_rewards_and_saves_a_record(self):
        tmp = tempfile.TemporaryDirectory()
        originales = (config.STATES_DIR, config.RECORDS_PATH)
        config.STATES_DIR, config.RECORDS_PATH = tmp.name, os.path.join(tmp.name, "records.json")
        try:
            handler = StoryHandler(rank=1, logger=None)
            handler.mapas_episodio = {(24, 3), (26, 3)}
            pb = SimpleNamespace(save_state=lambda f: f.write(b"estado"))
            ram = SimpleNamespace(leer_tiempo_juego=lambda: 400.0)
            reward = handler.conseguir_hito(pb, ram, RewardSystem(), "LLEGADA_CHERRYGROVE_CITY", step_count=0)
            self.assertEqual(reward, 2 * c.REWARD_FLAG_STORY)  # premio + bonus de rapidez máximo
            self.assertEqual(handler.hitos_nuevos, ["LLEGADA_CHERRYGROVE_CITY"])
            self.assertTrue(os.path.exists(os.path.join(tmp.name, "best_speedrun_LLEGADA_CHERRYGROVE_CITY.state")))
            with open(config.RECORDS_PATH, encoding="utf-8") as f:
                record = json.load(f)["LLEGADA_CHERRYGROVE_CITY"]
            # El propio mapa del hito queda como ya visitado para los episodios que empiecen ahí
            self.assertIn([26, 3], record["mapas_previos"])
        finally:
            config.STATES_DIR, config.RECORDS_PATH = originales
            tmp.cleanup()


class HitosConRequisitoTests(unittest.TestCase):
    """Lógica de hitos del entorno sin emulador: un PokemonGoldEnv sin __init__ con lo justo."""

    def setUp(self):
        from src.env.handlers.movement import MovementHandler
        from src.env.pokemon_env import PokemonGoldEnv
        from src.utils import rom_catalog
        self.env = PokemonGoldEnv.__new__(PokemonGoldEnv)
        self.env.hitos_por_mapa = {}
        for hito, (mapa, requisito, prohibido) in c.HITOS_MAPA.items():
            self.env.hitos_por_mapa.setdefault(mapa, []).append((hito, requisito, prohibido))
        self.env.splits, self.env.hitos_previos, self.env.steps_count = {}, set(), 50
        self.env.h_movement = MovementHandler(rank=0)
        self.conseguidos = []
        self.env.h_story = SimpleNamespace(conseguir_hito=lambda pb, ram, rw, hito, paso: self.conseguidos.append(hito) or 10.0)
        self.env.pb = self.env.rewards = None
        self.flags = set()
        self.env.ram = SimpleNamespace(leer=lambda addr: sum(1 << b for a, b in self.flags if a == addr))
        self.huevo = rom_catalog.EVENT_FLAGS["EVENT_GOT_MYSTERY_EGG_FROM_MR_POKEMON"]
        self.mapa = {n: m for m, n in c.MAP_NAMES.items()}

    def test_return_milestones_need_the_egg(self):
        self.assertEqual(self.env._comprobar_hitos_mapa(self.mapa["ROUTE_29"]), 0.0)  # ida: sin huevo, nada
        self.flags.add(self.huevo)
        self.assertEqual(self.env._comprobar_hitos_mapa(self.mapa["ROUTE_29"]), 10.0)
        self.assertEqual(self.conseguidos, ["VUELTA_ROUTE_29"])
        self.assertEqual(self.env._comprobar_hitos_mapa(self.mapa["ROUTE_29"]), 0.0)  # una vez por episodio

    def test_cherrygrove_gives_arrival_first_and_return_later(self):
        self.env._comprobar_hitos_mapa(self.mapa["CHERRYGROVE_CITY"])
        self.flags.add(self.huevo)
        self.env._comprobar_hitos_mapa(self.mapa["CHERRYGROVE_CITY"])
        self.assertEqual(self.conseguidos, ["LLEGADA_CHERRYGROVE_CITY", "VUELTA_CHERRYGROVE_CITY"])

    def test_after_delivering_the_egg_going_back_gives_nothing(self):
        from src.utils import rom_catalog
        self.flags.update({self.huevo, rom_catalog.EVENT_FLAGS["EVENT_GAVE_MYSTERY_EGG_TO_ELM"]})
        for mapa in ("ELMS_LAB", "NEW_BARK_TOWN", "ROUTE_29", "CHERRYGROVE_CITY", "ROUTE_30"):
            self.assertEqual(self.env._comprobar_hitos_mapa(self.mapa[mapa]), 0.0, mapa)
        self.assertEqual(self.env._comprobar_hitos_mapa(self.mapa["ROUTE_31"]), 10.0)  # solo avanzar da puntos
        self.assertEqual(self.conseguidos, ["LLEGADA_ROUTE_31"])

    def test_detours_give_no_minor_reward(self):
        self.assertTrue(c.es_desvio("EVENT_TALKED_TO_MOM_AFTER_MYSTERY_EGG_QUEST"))
        self.assertTrue(c.es_desvio("EVENT_ROUTE_30_HIDDEN_POTION"))
        self.assertFalse(c.es_desvio("EVENT_GOT_CYNDAQUIL_FROM_ELM"))

    def test_milestones_before_the_start_are_not_rewarded_again(self):
        self.flags.add(self.huevo)
        self.env.hitos_previos = set(c.HITOS[:c.HITOS.index("VUELTA_ROUTE_29") + 1])
        self.assertEqual(self.env._comprobar_hitos_mapa(self.mapa["CHERRYGROVE_CITY"]), 0.0)  # volver atrás no
        self.assertEqual(self.env._comprobar_hitos_mapa(self.mapa["NEW_BARK_TOWN"]), 10.0)    # seguir sí
        self.assertEqual(self.conseguidos, ["VUELTA_NEW_BARK_TOWN"])

    def test_beating_the_rival_in_cherrygrove(self):
        self.env.combates = {"entrenador": {"ganado": 0, "huido": 0, "perdido": 0}, "pasos_en_combate": 0}
        self.env.logger = None
        for resultado, mapa, esperado in [("perdido", "CHERRYGROVE_CITY", 0.0), ("ganado", "ROUTE_30", 0.0),
                                          ("ganado", "CHERRYGROVE_CITY", 10.0)]:
            self.env.combate_actual = {"tipo": "entrenador", "inicio": 40, "rival": 158, "nivel_rival": 5, "mapa": mapa}
            self.assertEqual(self.env._cerrar_combate(resultado), esperado)
        self.assertEqual(self.conseguidos, ["RIVAL_CHERRYGROVE_SUPERADO"])


class FiltroCoordenadasTests(unittest.TestCase):
    def test_points_far_from_the_known_map_are_dropped(self):
        import visualizador
        known = np.zeros((5, 10), dtype=bool)
        known[1:4, 2:8] = True  # casillas x 12..17, y 21..23 con origen (10, 20)
        limites = visualizador.limites_conocidos({(24, 3): {"origin": (10, 20), "known": known}})
        self.assertTrue(visualizador.dentro_del_mapa(limites, (24, 3), 15, 22))
        self.assertTrue(visualizador.dentro_del_mapa(limites, (24, 3), 12 - visualizador.MARGEN_MAPA, 22))
        self.assertFalse(visualizador.dentro_del_mapa(limites, (24, 3), 250, 22))
        self.assertTrue(visualizador.dentro_del_mapa(limites, (1, 1), 250, 22))  # mapa sin atlas: no se filtra


if __name__ == "__main__":
    unittest.main()
