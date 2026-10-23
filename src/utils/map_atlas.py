"""Atlas de mapas: reconstruye la imagen de cada mapa con las pantallas que ven los clones.

En el mundo exterior el jugador siempre está en la casilla (4, 4) de la pantalla
(10 x 9 casillas de 16 px), así que una pantalla alineada a la cuadrícula cubre
las casillas (x-4 .. x+5, y-4 .. y+4) del mapa. Cada casilla se guarda la primera
vez que se ve; la del jugador y la de encima (su cabeza) se omiten.
"""
import os

import numpy as np

TILE = 16
SCREEN_COLS, SCREEN_ROWS = 10, 9
PLAYER_COL, PLAYER_ROW = 4, 4
ATLAS_DIR = os.path.join("visualizaciones", "atlas")
FRAMES_ESTABLES = 3  # pasos seguidos sin combate/escena/cambio de mapa antes de capturar (evita fundidos)

REG_SCY, REG_SCX, REG_LCDC, REG_WY = 0xFF42, 0xFF43, 0xFF40, 0xFF4A


class MapAtlas:
    def __init__(self, rank):
        self.path = os.path.join(ATLAS_DIR, f"clon{rank}.npz")
        self.maps = load_atlas(self.path)
        self.pasos_estables = 0
        self.ultimo_mapa = None
        self.cambios = False

    def capture(self, pb, grp, mid, x, y, en_combate, en_script):
        """Pega la pantalla actual en el mapa (grp, mid) si es una vista limpia del mundo."""
        mapa = (grp, mid)
        if en_combate or en_script or mapa != self.ultimo_mapa:
            self.pasos_estables = 0
            self.ultimo_mapa = mapa
            return
        self.pasos_estables += 1
        if self.pasos_estables < FRAMES_ESTABLES:
            return

        # Pantalla alineada a la cuadrícula (no a mitad de paso) y sin ventana de texto/menú encima
        if pb.memory[REG_SCX] % TILE or pb.memory[REG_SCY] % TILE:
            return
        if pb.memory[REG_LCDC] & 0x20 and pb.memory[REG_WY] < 144:
            return

        tx0, ty0 = x - PLAYER_COL, y - PLAYER_ROW
        if mapa not in self.maps:
            self.maps[mapa] = new_entry(tx0, ty0, SCREEN_COLS, SCREEN_ROWS)
        entry = ensure_region(self.maps, mapa, tx0, ty0, SCREEN_COLS, SCREEN_ROWS)

        ox, oy = entry["origin"]
        known = entry["known"][ty0 - oy: ty0 - oy + SCREEN_ROWS, tx0 - ox: tx0 - ox + SCREEN_COLS]
        if known.all():
            return

        screen = pb.screen.ndarray[:, :, :3]
        for row in range(SCREEN_ROWS):
            for col in range(SCREEN_COLS):
                if col == PLAYER_COL and row in (PLAYER_ROW, PLAYER_ROW - 1):
                    continue
                if known[row, col]:
                    continue
                cy, cx = (ty0 - oy + row) * TILE, (tx0 - ox + col) * TILE
                entry["img"][cy:cy + TILE, cx:cx + TILE] = screen[row * TILE:(row + 1) * TILE, col * TILE:(col + 1) * TILE]
                known[row, col] = True
                self.cambios = True

    def save(self):
        if self.cambios:
            save_atlas(self.path, self.maps)
            self.cambios = False


def new_entry(tx0, ty0, cols, rows):
    return {
        "origin": (tx0, ty0),
        "img": np.zeros((rows * TILE, cols * TILE, 3), dtype=np.uint8),
        "known": np.zeros((rows, cols), dtype=bool),
    }


def ensure_region(maps, mapa, tx0, ty0, cols, rows):
    """Amplía el lienzo del mapa para que cubra las casillas (tx0..tx0+cols-1, ty0..ty0+rows-1)."""
    entry = maps[mapa]
    ox, oy = entry["origin"]
    h, w = entry["known"].shape
    nx0, ny0 = min(ox, tx0), min(oy, ty0)
    nx1, ny1 = max(ox + w, tx0 + cols), max(oy + h, ty0 + rows)
    if (nx0, ny0, nx1, ny1) == (ox, oy, ox + w, oy + h):
        return entry
    grown = new_entry(nx0, ny0, nx1 - nx0, ny1 - ny0)
    dy, dx = oy - ny0, ox - nx0
    grown["known"][dy:dy + h, dx:dx + w] = entry["known"]
    grown["img"][dy * TILE:(dy + h) * TILE, dx * TILE:(dx + w) * TILE] = entry["img"]
    maps[mapa] = grown
    return grown


def save_atlas(path, maps):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {}
    for (grp, mid), entry in maps.items():
        key = f"{grp}_{mid}"
        data[f"{key}_img"] = entry["img"]
        data[f"{key}_known"] = entry["known"]
        data[f"{key}_origin"] = np.array(entry["origin"])
    tmp = path + ".tmp.npz"
    np.savez_compressed(tmp, **data)
    os.replace(tmp, path)


def load_atlas(path):
    maps = {}
    if not os.path.exists(path):
        return maps
    try:
        with np.load(path) as data:
            for name in data.files:
                if name.endswith("_img"):
                    key = name[:-4]
                    grp, mid = (int(v) for v in key.split("_"))
                    maps[(grp, mid)] = {
                        "origin": tuple(int(v) for v in data[f"{key}_origin"]),
                        "img": data[name],
                        "known": data[f"{key}_known"],
                    }
    except Exception:
        return {}
    return maps


def merge_atlases(paths):
    """Une los atlas de varios clones: cada casilla se toma del primero que la tenga."""
    merged = {}
    for path in paths:
        for mapa, entry in load_atlas(path).items():
            ox, oy = entry["origin"]
            h, w = entry["known"].shape
            if mapa not in merged:
                merged[mapa] = new_entry(ox, oy, w, h)
            target = ensure_region(merged, mapa, ox, oy, w, h)
            tox, toy = target["origin"]
            dy, dx = oy - toy, ox - tox
            nuevos = entry["known"] & ~target["known"][dy:dy + h, dx:dx + w]
            for ty, tx in zip(*np.nonzero(nuevos)):
                cy, cx = (dy + ty) * TILE, (dx + tx) * TILE
                target["img"][cy:cy + TILE, cx:cx + TILE] = entry["img"][ty * TILE:(ty + 1) * TILE, tx * TILE:(tx + 1) * TILE]
            target["known"][dy:dy + h, dx:dx + w] |= entry["known"]
    return merged
