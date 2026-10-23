import os
import tempfile
import unittest
from unittest import mock

import numpy as np

from src.utils import frame_capturer
from src.utils.frame_capturer import FrameCapturer, inicio_de_ejecucion

PANTALLA = np.zeros((144, 160, 3), dtype=np.uint8)


class FrameCapturerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.capturas = os.path.join(self.tmp.name, "runs", "2026-10-23_120000", "capturas")

    def tearDown(self):
        self.tmp.cleanup()

    def test_run_start_comes_from_folder_name(self):
        from datetime import datetime
        self.assertEqual(inicio_de_ejecucion(self.capturas), datetime(2026, 10, 23, 12, 0, 0).timestamp())

    def test_each_clone_has_its_own_folder_in_time_order(self):
        cap = FrameCapturer(rank=3, output_dir=self.capturas, max_episodios=2)
        inicio = cap.inicio
        archivos = []
        for i, segundos in enumerate([65, 3725, 7300]):
            with mock.patch.object(frame_capturer.time, "time", return_value=inicio + segundos):
                cap.milestone(PANTALLA, i + 1, "EVENT_X", "ELMS_LAB", (4, 3), 100, 300.0)
                cap.episode_end(PANTALLA, i + 1, "no_progress", "ELMS_LAB", (4, 3), 900, -1.0, 400.0)

        archivos = sorted(os.listdir(os.path.join(self.capturas, "clon_03")))
        self.assertEqual(archivos[0], "T00h01m05s_ep0001_HITO_EVENT_X.png")
        # Solo los 2 últimos finales de episodio; los hitos se conservan todos
        finales = [a for a in archivos if "_FIN_" in a]
        self.assertEqual(finales, ["T01h02m05s_ep0002_FIN_no_progress.png", "T02h01m40s_ep0003_FIN_no_progress.png"])
        self.assertEqual(len([a for a in archivos if "_HITO_" in a]), 3)


if __name__ == "__main__":
    unittest.main()
