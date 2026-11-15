"""Geometría de los mapas leída de la ROM (data/mapas.json, lo genera tools/build_mapas.py).

Coordenadas en casillas del jugador, las mismas que wXCoord / wYCoord. Un mapa se identifica por
(grupo, número), como wMapGroup / wMapNumber.
"""
import json
import os

MAPAS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "mapas.json")

if not os.path.exists(MAPAS_PATH):
    raise FileNotFoundError(f"Falta {MAPAS_PATH}: genera los mapas con  python tools/build_mapas.py")
with open(MAPAS_PATH, encoding="utf-8") as _f:
    _datos = json.load(_f)

# Permiso de cada byte de colisión: "LAND" (se anda), "WATER" (Surf) o "WALL"
PERMISOS = _datos["permisos"]
NOMBRES_COLISION = {int(k, 16): v for k, v in _datos["colisiones"].items()}
HIERBA = {0x14, 0x18}                                       # hierba alta: combates salvajes
# Bordillos: solo se pueden saltar en su dirección (dx, dy)
BORDILLOS = {0xA0: (1, 0), 0xA1: (-1, 0), 0xA2: (0, -1), 0xA3: (0, 1), 0xA4: (1, 1), 0xA5: (-1, 1)}


class Mapa:
    def __init__(self, clave, datos):
        self.clave = clave
        self.nombre = datos["nombre"]
        self.ancho, self.alto = datos["ancho"], datos["alto"]
        self.entorno, self.tileset = datos["entorno"], datos["tileset"]
        self.colision = [bytes.fromhex(fila) for fila in datos["colision"]]
        self.warps = [dict(w, mapa=tuple(w["mapa"])) for w in datos["warps"]]
        self.conexiones = {lado: dict(c, mapa=tuple(c["mapa"])) for lado, c in datos["conexiones"].items()}
        self.coord_events, self.bg_events, self.objetos = datos["coord_events"], datos["bg_events"], datos["objetos"]

    def dentro(self, x, y):
        return 0 <= x < self.ancho and 0 <= y < self.alto

    def colision_en(self, x, y):
        """Byte de colisión de la casilla, o None fuera del mapa."""
        return self.colision[y][x] if self.dentro(x, y) else None

    def permiso(self, x, y):
        c = self.colision_en(x, y)
        return "WALL" if c is None else PERMISOS[c]

    def andable(self, x, y):
        return self.permiso(x, y) == "LAND"


MAPAS = {tuple(int(v) for v in clave.split(",")): Mapa(tuple(int(v) for v in clave.split(",")), datos)
         for clave, datos in _datos["mapas"].items()}
POR_NOMBRE = {m.nombre: m for m in MAPAS.values()}
