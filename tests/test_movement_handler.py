import unittest

from src.env.handlers.movement import MovementHandler
import src.utils.constantes as c


def paso(handler, visited, pos=(1, 1), last_pos=(1, 1), en_combate=False, en_script=False, explorable=True):
    return handler.procesar(pos[0], pos[1], last_pos, (24, 7) + pos, visited, "PLAYERS_HOUSE_2F", en_combate, en_script,
                            explorable=explorable)


class MovementHandlerTests(unittest.TestCase):
    def test_new_tile_is_rewarded_once(self):
        handler, visited = MovementHandler(rank=0), set()
        reward, _ = paso(handler, visited, pos=(2, 1))
        self.assertEqual(reward, c.REWARD_NEW_TILE)
        reward, _ = paso(handler, visited, pos=(2, 1), last_pos=(1, 1))
        self.assertLess(reward, 0)

    def test_dialogue_and_battle_are_not_penalized_but_count_as_no_progress(self):
        # Repetir un diálogo sin fin no debe evitar el corte del episodio
        handler, visited = MovementHandler(rank=0), {(24, 7, 1, 1)}
        for i in range(handler.max_steps_sin_progreso - 1):
            self.assertEqual(paso(handler, visited, en_script=i % 2 == 0, en_combate=i % 2 == 1), (0.0, False))
        reward, sin_progreso = paso(handler, visited, en_script=True)
        self.assertTrue(sin_progreso)
        self.assertEqual(reward, c.PENALTY_NO_PROGRESS)

    def test_maps_before_the_start_milestone_are_not_explorable(self):
        # Empezando en un hito, volver a casa no da recompensa de exploración ni reinicia el contador
        handler, visited = MovementHandler(rank=0), set()
        handler.steps_sin_progreso = 10
        reward, _ = paso(handler, visited, pos=(2, 1), explorable=False)
        self.assertLess(reward, 0)
        self.assertEqual(visited, set())
        self.assertEqual(handler.steps_sin_progreso, 11)

    def test_game_events_reset_no_progress_counter(self):
        handler, visited = MovementHandler(rank=0), {(24, 7, 1, 1)}
        for _ in range(500):
            paso(handler, visited, en_script=True)
        handler.registrar_progreso()
        self.assertEqual(handler.steps_sin_progreso, 0)

    def test_episode_ends_without_progress(self):
        handler, visited = MovementHandler(rank=0), {(24, 7, 1, 1)}
        for _ in range(handler.max_steps_sin_progreso - 1):
            _, sin_progreso = paso(handler, visited)
            self.assertFalse(sin_progreso)
        reward, sin_progreso = paso(handler, visited)
        self.assertTrue(sin_progreso)
        self.assertLessEqual(reward, c.PENALTY_NO_PROGRESS)

    def test_new_tile_resets_no_progress_counter(self):
        handler, visited = MovementHandler(rank=0), {(24, 7, 1, 1)}
        for _ in range(10):
            paso(handler, visited)
        paso(handler, visited, pos=(3, 3))
        self.assertEqual(handler.steps_sin_progreso, 0)


if __name__ == "__main__":
    unittest.main()
