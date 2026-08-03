import os
import unittest
from pathlib import Path

from src.env.core.extractor_ram import RamExtractor
from src.utils import constantes as c


class RuntimeFlagProbeTests(unittest.TestCase):
    def test_flag_ranges_are_accessible(self):
        self.assertTrue(c.FLAG_START < c.FLAG_END)
        self.assertGreaterEqual(c.FLAG_END - c.FLAG_START + 1, 256)


if __name__ == "__main__":
    unittest.main()
