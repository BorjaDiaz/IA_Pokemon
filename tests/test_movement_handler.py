import unittest

from src.env.handlers.movement import MovementHandler
import src.utils.constantes as c


class MovementHandlerTests(unittest.TestCase):
    def test_house_exit_movement_gets_extra_reward(self):
        handler = MovementHandler(rank=0)
        reward, done = handler.procesar(
            1,
            1,
            (0, 0),
            (1, 1, 1, 1),
            set(),
            "Tu Casa (Planta Baja)",
            False,
        )

        self.assertFalse(done)
        self.assertGreater(reward, 0.1)

    def test_stuck_threshold_is_more_forgiving(self):
        handler = MovementHandler(rank=0)
        self.assertGreaterEqual(handler.max_steps_estancado, 600)


if __name__ == "__main__":
    unittest.main()
