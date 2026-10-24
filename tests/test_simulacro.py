"""El simulacro de combate se retira solo cuando ya gana (sin emulador)."""
import unittest
from types import SimpleNamespace

from stable_baselines3.common.logger import Logger

import src.utils.config as config
from src.agents.callbacks import SimulacroCallback


class SimulacroCallbackTests(unittest.TestCase):
    def setUp(self):
        self.llamadas = []
        self.cb = SimulacroCallback()
        entorno = SimpleNamespace(env_method=lambda *a: self.llamadas.append(a))
        self.cb.model = SimpleNamespace(logger=Logger(folder=None, output_formats=[]), get_env=lambda: entorno)

    def episodios(self, n, ganado, salida=config.SALIDA_SIMULACRO):
        combates = {"salvaje": {"ganado": int(ganado), "huido": int(not ganado), "perdido": 0}}
        for _ in range(n):
            self.cb.locals = {"infos": [{"salida": salida, "combates": combates, "splits": {}}]}
            self.assertTrue(self.cb._on_step())

    def test_stays_while_it_still_loses(self):
        self.episodios(config.SIMULACRO_VENTANA, ganado=False)
        self.episodios(config.SIMULACRO_VENTANA // 2, ganado=True)  # 50% < 80%
        self.assertEqual(self.llamadas, [])

    def test_is_retired_once_when_it_wins_enough(self):
        self.episodios(config.SIMULACRO_VENTANA, ganado=True)
        self.episodios(10, ganado=True)
        self.assertEqual(self.llamadas, [("fijar_prob_simulacro", config.PROB_SIMULACRO_DOMINADO)])

    def test_route_episodes_do_not_count(self):
        self.episodios(config.SIMULACRO_VENTANA, ganado=True, salida="inicio.state")
        self.assertEqual(self.llamadas, [])


if __name__ == "__main__":
    unittest.main()
