"""El vigilante para el entrenamiento solo y guarda el mejor modelo (sin emulador)."""
import time
import unittest
from types import SimpleNamespace

from stable_baselines3.common.logger import Logger

import src.utils.config as config
from src.agents.callbacks import VigilanteCallback

HITO = "EVENT_GOT_A_POKEMON_FROM_ELM"


class VigilanteTests(unittest.TestCase):
    def setUp(self):
        self.originales = (config.MAX_MINUTOS, config.VIGILAR_VENTANA, config.VIGILAR_RONDAS_ESTANCADO)
        config.MAX_MINUTOS, config.VIGILAR_VENTANA, config.VIGILAR_RONDAS_ESTANCADO = 180, 10, None
        self.guardados = []
        self.v = VigilanteCallback()
        self.v.model = SimpleNamespace(logger=Logger(folder=None, output_formats=[]),
                                       save=lambda path: self.guardados.append(path))
        self.v.ultimo_reloj = time.time()

    def tearDown(self):
        config.MAX_MINUTOS, config.VIGILAR_VENTANA, config.VIGILAR_RONDAS_ESTANCADO = self.originales

    def episodios(self, n, con_hito):
        splits = {HITO: 400, "ROUTE_29": 700} if con_hito else {"NEW_BARK_TOWN": 200}
        for _ in range(n):
            self.v.locals = {"infos": [{"splits": splits, "salida": "inicio.state"}]}
            self.v.n_calls += 1
            self.assertTrue(self.v._on_step())

    def ronda(self, kl=0.01, ev=0.9):
        self.v.model.logger.name_to_value.update({"train/approx_kl": kl, "train/explained_variance": ev})
        self.v._on_rollout_start()
        self.v._on_rollout_end()
        self.v.locals = {"infos": []}
        self.v.n_calls += 1
        return self.v._on_step()

    def test_keeps_training_while_things_go_well_and_saves_the_best_model(self):
        self.episodios(10, con_hito=True)
        self.assertTrue(self.ronda())
        self.assertEqual(self.guardados, [config.MODELO_MEJOR])
        self.assertIsNone(self.v.motivo)

    def test_stops_after_the_time_limit(self):
        self.v.segundos_activo = 181 * 60
        self.v.n_calls = 100  # comprueba el tiempo cada 100 pasos (SB3 incrementa n_calls antes de _on_step)
        self.v.locals = {"infos": []}
        self.assertFalse(self.v._on_step())
        self.assertIn("tiempo máximo", self.v.motivo)
        self.assertFalse(self.v.degradado)

    def test_time_while_the_pc_sleeps_does_not_count(self):
        self.v.ultimo_reloj = time.time() - 4 * 3600  # 4 h hibernando
        self.v.n_calls = 100
        self.v.locals = {"infos": []}
        self.assertTrue(self.v._on_step())
        self.assertLess(self.v.segundos_activo, 1)
        self.v.ultimo_reloj = time.time() - 30        # 30 s entrenando sí cuentan
        self.v.n_calls = 200
        self.assertTrue(self.v._on_step())
        self.assertAlmostEqual(self.v.segundos_activo, 30, delta=1)

    def test_stops_when_the_mastered_milestone_gets_worse(self):
        self.episodios(10, con_hito=True)
        self.ronda()
        self.episodios(8, con_hito=False)  # en la ventana de 10 solo quedan 2 con el hito: 20% < 80%
        self.assertFalse(self.ronda())
        self.assertIn(HITO, self.v.motivo)
        self.assertTrue(self.v.degradado)

    def test_a_fresh_ai_that_has_not_mastered_the_milestone_is_not_stopped(self):
        self.episodios(10, con_hito=False)  # 0%: nunca lo ha dominado, no es empeorar
        self.assertTrue(self.ronda())
        self.assertIsNone(self.v.motivo)

    def test_stops_when_learning_is_unstable_for_several_rounds(self):
        for _ in range(config.VIGILAR_RONDAS_INESTABLE - 1):
            self.assertTrue(self.ronda(kl=0.2))
        self.assertTrue(self.ronda(kl=0.01))  # una ronda buena reinicia la cuenta
        for _ in range(config.VIGILAR_RONDAS_INESTABLE - 1):
            self.assertTrue(self.ronda(ev=0.1))
        self.assertFalse(self.ronda(ev=0.1))
        self.assertIn("inestable", self.v.motivo)
        self.assertTrue(self.v.degradado)


if __name__ == "__main__":
    unittest.main()
