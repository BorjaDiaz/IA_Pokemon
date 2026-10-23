import unittest

from src.env.handlers.movement import MovementHandler
import src.utils.constantes as c


def paso(handler, visited, pos=(1, 1), last_pos=(1, 1), en_combate=False, en_script=False):
    return handler.procesar(pos[0], pos[1], last_pos, (24, 7) + pos, visited, "PLAYERS_HOUSE_2F", en_combate, en_script)


class MovementHandlerTests(unittest.TestCase):
    def test_new_tile_is_rewarded_once(self):
        handler, visited = MovementHandler(rank=0), set()
        reward, _ = paso(handler, visited, pos=(2, 1))
        self.assertEqual(reward, c.REWARD_NEW_TILE)
        reward, _ = paso(handler, visited, pos=(2, 1), last_pos=(1, 1))
        self.assertLess(reward, 0)

    def test_dialogue_and_battle_do_not_count_as_stuck(self):
        handler, visited = MovementHandler(rank=0), {(24, 7, 1, 1)}
        for _ in range(handler.max_steps_sin_progreso * 2):
            self.assertEqual(paso(handler, visited, en_script=True), (0.0, False))
            self.assertEqual(paso(handler, visited, en_combate=True), (0.0, False))
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
