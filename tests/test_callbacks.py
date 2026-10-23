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


if __name__ == "__main__":
    unittest.main()
