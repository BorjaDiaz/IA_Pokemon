"""Pruebas del entorno con la ROM real (se saltan si no está). Se ejecutan en una carpeta temporal."""
import os
import tempfile
import unittest

import src.utils.config as config
import src.utils.constantes as c

ROM_AVAILABLE = os.path.exists(config.ROM_PATH)
DERECHA, B = 3, 5


@unittest.skipUnless(ROM_AVAILABLE, "ROM no disponible")
class PokemonGoldEnvTests(unittest.TestCase):
    def setUp(self):
        self.cwd = os.getcwd()
        self.tmp = tempfile.TemporaryDirectory()
        os.chdir(self.tmp.name)
        self.enable_logs, self.stage = config.ENABLE_LOGS, config.CURRENT_STAGE
        config.ENABLE_LOGS, config.CURRENT_STAGE = False, 0  # inicio.state: habitación

        from src.env.pokemon_env import PokemonGoldEnv
        self.env = PokemonGoldEnv(rank=0)
        self.env.metrics_path = os.path.join(self.tmp.name, "metrics.jsonl")
        self.obs, _ = self.env.reset()

    def tearDown(self):
        self.env.close()
        config.ENABLE_LOGS, config.CURRENT_STAGE = self.enable_logs, self.stage
        os.chdir(self.cwd)
        self.tmp.cleanup()

    def pos(self):
        return self.env.ram.leer(c.ADDR_PLAYER_X), self.env.ram.leer(c.ADDR_PLAYER_Y)

    def test_observation_shape(self):
        self.assertEqual(self.obs.shape, (2, 72, 80))
        self.assertEqual(self.obs.dtype, "uint8")
        self.assertTrue(self.env.observation_space.contains(self.obs))

    def test_exploration_channel_marks_visited_tiles(self):
        obs, *_ = self.env.step(B)
        # La casilla del jugador (columna 4, fila 4 de la pantalla) ocupa los píxeles [32:40, 32:40]
        self.assertTrue((obs[1, 32:40, 32:40] == 255).all())
        self.assertEqual(int((obs[1] == 255).sum()), 64)  # solo esa casilla

    def test_each_direction_action_moves_one_tile(self):
        # Un toque corto en una dirección distinta a la que mira el jugador solo lo gira (como en el juego);
        # a partir de ahí, cada acción en la misma dirección avanza exactamente una casilla
        self.env.step(DERECHA)
        x, y = self.pos()
        for i in range(1, 5):
            self.env.step(DERECHA)
            self.assertEqual(self.pos(), (x + i, y))

    def test_exploration_channel_is_empty_in_battle(self):
        import random
        config.CURRENT_STAGE = 2  # ruta_29.state: hierba alta
        self.env.reset()
        rng = random.Random(1)
        for _ in range(3000):
            obs, *_ = self.env.step(rng.choice([0, 1, 2, DERECHA]))
            if self.env.ram.leer(c.ADDR_BATTLE_MODE):
                break
        else:
            self.fail("No hubo encuentro salvaje")
        self.assertFalse(obs[1].any())

    def test_no_progress_terminates_episode(self):
        self.env.h_movement.max_steps_sin_progreso = 3
        resultados = [self.env.step(B) for _ in range(4)]
        _, _, terminated, truncated, info = resultados[-1]
        self.assertTrue(terminated)
        self.assertFalse(truncated)
        self.assertIn("splits", info)


if __name__ == "__main__":
    unittest.main()
