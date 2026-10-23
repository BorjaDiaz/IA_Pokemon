import os
import unittest
from types import SimpleNamespace

from stable_baselines3.common.logger import Logger

from src.agents.callbacks import SplitsCallback


class SplitsCallbackTests(unittest.TestCase):
    def setUp(self):
        self.callback = SplitsCallback()
        self.callback.model = SimpleNamespace(logger=Logger(folder=None, output_formats=[]))

    def step(self, *infos):
        self.callback.locals = {"infos": list(infos)}
        self.callback._on_step()
        return self.callback.model.logger.name_to_value

    def test_logs_mean_steps_and_success_rate_per_milestone(self):
        hito = "EVENT_GOT_A_POKEMON_FROM_ELM"
        valores = self.step(
            {"splits": {"PLAYERS_HOUSE_1F": 120, hito: 1000}},
            {"splits": {"PLAYERS_HOUSE_1F": 90, hito: 600}},
            {"splits": {"PLAYERS_HOUSE_1F": 150}},
            {},  # paso intermedio sin fin de episodio
        )
        self.assertEqual(valores[f"splits/{hito}"], 800)
        self.assertAlmostEqual(valores[f"exito/{hito}"], 2 / 3)

    def test_logs_battle_results_per_episode(self):
        combates = {"salvaje": {"ganado": 2, "huido": 1, "perdido": 0},
                    "entrenador": {"ganado": 0, "huido": 0, "perdido": 1}, "pasos_en_combate": 120}
        valores = self.step({"splits": {}, "combates": combates})
        self.assertEqual(valores["combate/salvaje_ganado"], 2)
        self.assertEqual(valores["combate/entrenador_perdido"], 1)
        self.assertEqual(valores["combate/pasos_en_combate"], 120)

    def test_episodes_from_a_milestone_are_logged_apart(self):
        hito = "EVENT_GOT_A_POKEMON_FROM_ELM"
        valores = self.step(
            {"splits": {hito: 500}, "salida": "inicio.state"},
            {"splits": {"ROUTE_29": 80}, "salida": f"best_speedrun_{hito}.state"},
        )
        self.assertEqual(valores[f"splits/{hito}"], 500)
        self.assertEqual(valores[f"exito/{hito}"], 1.0)  # solo cuenta el episodio que empezó en el inicio
        self.assertEqual(valores[f"desde_{hito}/exito/{hito}"], 0.0)
        self.assertEqual(valores["salidas/desde_base"], 0.5)

    def test_maps_are_not_sent_to_tensorboard(self):
        valores = self.step({"splits": {"PLAYERS_HOUSE_1F": 120}})
        self.assertFalse(any("PLAYERS_HOUSE_1F" in k for k in valores))


class StopFileCallbackTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        from unittest import mock
        from src.agents import callbacks
        self.tmp = tempfile.TemporaryDirectory()
        self.parar = os.path.join(self.tmp.name, "PARAR")
        self.patch = mock.patch.object(callbacks, "STOP_FILE", self.parar)
        self.patch.start()
        self.callback = callbacks.StopFileCallback()
        self.callback.n_calls = 100

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def test_stops_with_a_parar_file(self):
        open(self.parar, "w").close()
        self.assertFalse(self.callback._on_step())
        self.assertFalse(os.path.exists(self.parar))

    def test_stops_with_a_parar_folder(self):
        # Crear una carpeta desde el explorador es lo más rápido; antes os.remove fallaba con "Acceso denegado"
        os.makedirs(self.parar)
        self.assertFalse(self.callback._on_step())
        self.assertFalse(os.path.exists(self.parar))

    def test_keeps_training_without_parar(self):
        self.assertTrue(self.callback._on_step())


if __name__ == "__main__":
    unittest.main()
