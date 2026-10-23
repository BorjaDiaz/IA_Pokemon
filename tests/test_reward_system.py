import unittest

from src.env.handlers.reward_system import RewardSystem
import src.utils.constantes as c


class RewardSystemTests(unittest.TestCase):
    def test_speed_bonus_is_capped_by_story_reward(self):
        rewards = RewardSystem(rank=0)
        self.assertEqual(rewards.calcular_bonus_prisa_flag(0), c.REWARD_FLAG_STORY)

    def test_speed_bonus_decreases_with_steps(self):
        rewards = RewardSystem(rank=0)
        early = rewards.calcular_bonus_prisa_flag(100)
        late = rewards.calcular_bonus_prisa_flag(c.MAX_STEPS_PER_EPISODE // 2)
        self.assertGreater(early, late)
        self.assertEqual(rewards.calcular_bonus_prisa_flag(c.MAX_STEPS_PER_EPISODE * 2), 0.0)


if __name__ == "__main__":
    unittest.main()
