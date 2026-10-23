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
    def test_route_milestones_go_between_the_starter_and_the_mystery_egg(self):
        i = c.HITOS.index("EVENT_GOT_A_POKEMON_FROM_ELM")
        self.assertEqual(c.HITOS[i + 1:i + 4], ["LLEGADA_CHERRYGROVE_CITY", "LLEGADA_ROUTE_30", "LLEGADA_MR_POKEMONS_HOUSE"])
        self.assertEqual(c.HITOS[i + 4], "EVENT_GOT_MYSTERY_EGG_FROM_MR_POKEMON")
        self.assertEqual(c.MAP_NAMES[c.HITOS_MAPA["LLEGADA_CHERRYGROVE_CITY"]], "CHERRYGROVE_CITY")

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
