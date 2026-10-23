import json
import os
import tempfile
import unittest
from types import SimpleNamespace

import src.utils.config as config
from src.env.handlers.story import StoryHandler

HITO = "EVENT_GOT_A_POKEMON_FROM_ELM"


class FakePyBoy:
    def __init__(self):
        self.contenido = b""

    def save_state(self, f):
        f.write(self.contenido)


class RecordsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.originales = (config.STATES_DIR, config.RECORDS_PATH)
        config.STATES_DIR = self.tmp.name
        config.RECORDS_PATH = os.path.join(self.tmp.name, "records.json")
        self.handler = StoryHandler(rank=3, logger=None)
        self.pb = FakePyBoy()

    def tearDown(self):
        config.STATES_DIR, config.RECORDS_PATH = self.originales
        self.tmp.cleanup()

    def conseguir(self, tiempo, contenido):
        self.pb.contenido = contenido
        ram = SimpleNamespace(leer_tiempo_juego=lambda: tiempo)
        self.handler._guardar_si_es_record(self.pb, ram, HITO, step_count=100)

    def guardado(self):
        with open(os.path.join(self.tmp.name, f"best_speedrun_{HITO}.state"), "rb") as f:
            return f.read()

    def record(self):
        with open(config.RECORDS_PATH, encoding="utf-8") as f:
            return json.load(f)[HITO]

    def test_first_time_is_saved(self):
        self.conseguir(300.0, b"primero")
        self.assertEqual(self.guardado(), b"primero")
        self.assertEqual(self.record()["tiempo_juego_s"], 300.0)
        self.assertEqual(self.record()["clon"], 3)

    def test_slower_time_does_not_replace_record(self):
        self.conseguir(300.0, b"rapido")
        self.conseguir(450.0, b"lento")
        self.assertEqual(self.guardado(), b"rapido")
        self.assertEqual(self.record()["tiempo_juego_s"], 300.0)

    def test_faster_time_replaces_record(self):
        self.conseguir(300.0, b"antes")
        self.conseguir(250.5, b"mejor")
        self.assertEqual(self.guardado(), b"mejor")
        self.assertEqual(self.record()["tiempo_juego_s"], 250.5)


if __name__ == "__main__":
    unittest.main()
