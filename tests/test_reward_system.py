import unittest

from src.env.handlers.reward_system import RewardSystem


class RewardSystemTests(unittest.TestCase):
    def test_transition_reward_is_positive_for_map_change(self):
        rewards = RewardSystem(rank=0)
        bonus = rewards.calcular_bonus_transicion((1, 1), (2, 2), (5, 5), (6, 6))
        self.assertGreater(bonus, 0.0)

    def test_transition_reward_is_zero_for_same_map(self):
        rewards = RewardSystem(rank=0)
        bonus = rewards.calcular_bonus_transicion((1, 1), (1, 1), (5, 5), (6, 6))
        self.assertEqual(bonus, 0.0)


if __name__ == "__main__":
    unittest.main()
