"""
Capturas por eventos durante el entrenamiento.

- Fin de episodio: una tira con las últimas pantallas (una cada `intervalo` pasos)
  y un encabezado con clon, episodio, motivo, mapa, posición y recompensa.
- Hito del speedrun: la pantalla en el momento de conseguirlo.

Cada clon guarda sus archivos como capturas/clon<N>_... y conserva solo los
últimos `max_episodios` finales de episodio (los hitos se conservan todos).
"""
import glob
import os
from collections import deque

import numpy as np
from PIL import Image, ImageDraw

ALTO_TEXTO = 18


class FrameCapturer:
    def __init__(self, rank, output_dir="capturas", intervalo=25, n_frames=8, max_episodios=20):
        self.rank = rank
        self.output_dir = output_dir
        self.intervalo = intervalo
        self.max_episodios = max_episodios
        self.frames = deque(maxlen=n_frames)  # (paso, pantalla)

        # Cada clon borra solo sus capturas de entrenamientos anteriores
        os.makedirs(output_dir, exist_ok=True)
        for viejo in glob.glob(os.path.join(output_dir, f"clon{rank}_*.png")):
            os.remove(viejo)

    def record(self, screen, paso):
        """Guarda en memoria una pantalla cada `intervalo` pasos."""
        if paso % self.intervalo == 0:
            self.frames.append((paso, screen.copy()))

    def new_episode(self):
        self.frames.clear()

    def episode_end(self, screen, episodio, motivo, mapa, pos, paso, recompensa):
        if not self.frames or self.frames[-1][0] != paso:
            self.frames.append((paso, screen.copy()))
        titulo = (f"Clon {self.rank} | Episodio {episodio} | {motivo.upper()} | {mapa} {pos} | "
                  f"paso {paso} | recompensa {recompensa:.2f}")
        img = _tira(list(self.frames), titulo)
        img.save(os.path.join(self.output_dir, f"clon{self.rank}_ep{episodio:04d}_{motivo}.png"))
        self._recortar()

    def milestone(self, screen, episodio, hito, mapa, pos, paso):
        titulo = f"Clon {self.rank} | Episodio {episodio} | {hito} | {mapa} {pos} | paso {paso}"
        img = _tira([(paso, screen)], titulo)
        img.save(os.path.join(self.output_dir, f"clon{self.rank}_ep{episodio:04d}_paso{paso:06d}_{hito}.png"))

    def _recortar(self):
        finales = sorted(f for f in glob.glob(os.path.join(self.output_dir, f"clon{self.rank}_ep*.png"))
                         if "_paso" not in os.path.basename(f))
        for viejo in finales[:-self.max_episodios]:
            os.remove(viejo)


def _tira(frames, titulo):
    """Pantallas en fila, con el paso de cada una debajo y un título arriba."""
    h, w = frames[0][1].shape[:2]
    ancho = max(w * len(frames), 8 * len(titulo))
    img = Image.new("RGB", (ancho, h + 2 * ALTO_TEXTO), (25, 25, 25))
    draw = ImageDraw.Draw(img)
    draw.text((4, 3), titulo, fill=(255, 255, 255))
    for i, (paso, pantalla) in enumerate(frames):
        img.paste(Image.fromarray(np.asarray(pantalla, dtype=np.uint8)), (i * w, ALTO_TEXTO))
        draw.text((i * w + 4, h + ALTO_TEXTO + 3), f"paso {paso}", fill=(200, 200, 200))
    return img
