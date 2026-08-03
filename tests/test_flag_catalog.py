import os
import unittest

from src.utils.flag_catalog import build_flag_change_catalog, format_flag_catalog


class FlagCatalogTests(unittest.TestCase):
    def test_build_flag_change_catalog_groups_states(self):
        base_flags = {(0xD87F, 0): 1}
        state_flags_by_name = {
            "a.state": {(0xD87F, 0): 1, (0xD87F, 1): 1},
            "b.state": {(0xD87F, 0): 1, (0xD87F, 2): 1},
        }

        catalog = build_flag_change_catalog(base_flags, state_flags_by_name)

        self.assertEqual(catalog[(0xD87F, 1)], ["a.state"])
        self.assertEqual(catalog[(0xD87F, 2)], ["b.state"])

    def test_format_flag_catalog_is_stable(self):
        catalog = {(0xD87F, 1): ["a.state", "b.state"]}
        rendered = format_flag_catalog(catalog)
        self.assertIn("0xd87f:1 -> a.state, b.state", rendered)


if __name__ == "__main__":
    unittest.main()
