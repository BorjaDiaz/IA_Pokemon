"""
Capturas por eventos durante el entrenamiento.

- Fin de episodio: una tira con las últimas pantallas (una cada `intervalo` pasos)
  y un encabezado con clon, episodio, motivo, mapa, posición, tiempo de partida y recompensa.
- Hito del speedrun: la pantalla en el momento de conseguirlo.

Cada clon guarda sus capturas en <output_dir>/clon_NN/ con nombres que empiezan por el tiempo
transcurrido desde el inicio de la ejecución (T00h05m12s_...), así que ordenadas por nombre
quedan en orden cronológico. Se conservan los últimos `max_episodios` finales de episodio
(los hitos se conservan todos).
"""
import glob
import os
import time
from collections import deque
from datetime import datetime

import numpy as np
from PIL import Image, ImageDraw

ALTO_TEXTO = 18


def inicio_de_ejecucion(output_dir):
    """Hora de inicio de la ejecución, sacada del nombre de su carpeta (runs/AAAA-MM-DD_HHMMSS/...)."""
    for parte in os.path.normpath(os.path.abspath(output_dir)).split(os.sep):
        try:
            return datetime.strptime(parte, "%Y-%m-%d_%H%M%S").timestamp()
        except ValueError:
            continue
    return time.time()


class FrameCapturer:
    def __init__(self, rank, output_dir="capturas", intervalo=25, n_frames=8, max_episodios=20):
        self.rank = rank
        self.output_dir = os.path.join(output_dir, f"clon_{rank:02d}")
        self.intervalo = intervalo
        self.max_episodios = max_episodios
        self.frames = deque(maxlen=n_frames)  # (paso, pantalla)
        self.inicio = inicio_de_ejecucion(output_dir)

        # Cada clon borra solo sus capturas de entrenamientos anteriores en esta carpeta
        os.makedirs(self.output_dir, exist_ok=True)
        for viejo in glob.glob(os.path.join(self.output_dir, "*.png")):
            os.remove(viejo)

    def _marca_tiempo(self):
        s = int(time.time() - self.inicio)
        return f"T{s // 3600:02d}h{s % 3600 // 60:02d}m{s % 60:02d}s"

    def record(self, screen, paso):
        """Guarda en memoria una pantalla cada `intervalo` pasos."""
        if paso % self.intervalo == 0:
            self.frames.append((paso, screen.copy()))

    def new_episode(self):
        self.frames.clear()

    def episode_end(self, screen, episodio, motivo, mapa, pos, paso, recompensa, tiempo_juego):
        if not self.frames or self.frames[-1][0] != paso:
            self.frames.append((paso, screen.copy()))
        titulo = (f"Clon {self.rank} | Episodio {episodio} | {motivo.upper()} | {mapa} {pos} | "
                  f"paso {paso} | partida {_mmss(tiempo_juego)} | recompensa {recompensa:.2f}")
        img = _tira(list(self.frames), titulo)
        img.save(os.path.join(self.output_dir, f"{self._marca_tiempo()}_ep{episodio:04d}_FIN_{motivo}.png"))
        self._recortar()

    def milestone(self, screen, episodio, hito, mapa, pos, paso, tiempo_juego):
        titulo = f"Clon {self.rank} | Episodio {episodio} | {hito} | {mapa} {pos} | paso {paso} | partida {_mmss(tiempo_juego)}"
        img = _tira([(paso, screen)], titulo)
        img.save(os.path.join(self.output_dir, f"{self._marca_tiempo()}_ep{episodio:04d}_HITO_{hito}.png"))

    def _recortar(self):
        finales = sorted(glob.glob(os.path.join(self.output_dir, "*_FIN_*.png")))
        for viejo in finales[:-self.max_episodios]:
            os.remove(viejo)


def _mmss(segundos):
    return f"{int(segundos) // 60}:{int(segundos) % 60:02d}"


def _tira(frames, titulo):
    """Pantallas en fila, con el paso de cada una debajo y un título arriba."""
    h, w = frames[0][1].shape[:2]
    ancho = max(w * len(frames), 7 * len(titulo))
    img = Image.new("RGB", (ancho, h + 2 * ALTO_TEXTO), (25, 25, 25))
    draw = ImageDraw.Draw(img)
    draw.text((4, 3), titulo, fill=(255, 255, 255))
    for i, (paso, pantalla) in enumerate(frames):
        img.paste(Image.fromarray(np.asarray(pantalla, dtype=np.uint8)), (i * w, ALTO_TEXTO))
        draw.text((i * w + 4, h + ALTO_TEXTO + 3), f"paso {paso}", fill=(200, 200, 200))
    return img
