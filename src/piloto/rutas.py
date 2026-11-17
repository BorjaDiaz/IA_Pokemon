"""Buscador de caminos sobre los mapas de la ROM (src/utils/mapas.py).

Un nodo es (mapa, x, y) con mapa = (grupo, número). Desde una casilla se puede:
- andar a una casilla vecina de suelo;
- saltar un bordillo: la casilla de bordillo se pisa como cualquier otra y, estando encima, empujar en su
  dirección salta el escalón (la casilla siguiente, que es pared) y se cae dos casillas más allá;
- cruzar una puerta, escalera o cueva al pisarla, o una alfombra de salida al empujar hacia fuera;
- pasar al mapa vecino por el borde, si hay conexión.
Devuelve la lista de pasos (dirección, nodo esperado) hasta el nodo de destino más cercano.
"""
import heapq

from src.utils.mapas import BORDILLOS, HIERBA, MAPAS, PERMISOS

DIRECCIONES = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
LADO = {"up": "norte", "down": "sur", "left": "oeste", "right": "este"}
# Se cruzan al pisarlas
WARP_AL_PISAR = {0x60, 0x68, 0x71, 0x72, 0x73, 0x74, 0x75, 0x79, 0x7A, 0x7B, 0x7C, 0x7D}
# Alfombras de salida: se cruzan empujando en su dirección estando encima
ALFOMBRAS = {0x70: "down", 0x76: "left", 0x78: "up", 0x7E: "right"}
# Bordillos en diagonal: valen en sus dos direcciones
BORDILLOS_DOBLES = {0xA4: {(1, 0), (0, 1)}, 0xA5: {(-1, 0), (0, 1)}}
COSTE_HIERBA = 4  # la hierba alta da combates: mejor rodearla si cuesta poco


def destino_warp(warp):
    """Nodo al que lleva un warp, o None si no tiene destino fijo (vuelve por donde se entró)."""
    mapa = MAPAS.get(warp["mapa"])
    if mapa is None or not 1 <= warp["warp"] <= len(mapa.warps):
        return None
    w = mapa.warps[warp["warp"] - 1]
    return (mapa.clave, w["x"], w["y"])


def _warp_en(mapa, x, y):
    return next((w for w in mapa.warps if (w["x"], w["y"]) == (x, y)), None)


def vecinos(nodo, bloqueadas=frozenset()):
    """(dirección, nodo siguiente, coste) de cada movimiento posible desde `nodo`."""
    clave, x, y = nodo
    mapa = MAPAS[clave]
    aqui = mapa.colision_en(x, y)
    for direccion, (dx, dy) in DIRECCIONES.items():
        if aqui in BORDILLOS and ((dx, dy) == BORDILLOS[aqui] or (dx, dy) in BORDILLOS_DOBLES.get(aqui, ())):
            caida = (clave, x + 2 * dx, y + 2 * dy)   # comprobado en el emulador (Ruta 30)
            if mapa.andable(caida[1], caida[2]) and caida not in bloqueadas:
                yield direccion, caida, 2
            continue
        if ALFOMBRAS.get(aqui) == direccion:
            warp = _warp_en(mapa, x, y)
            destino = destino_warp(warp) if warp else None
            if destino:
                yield direccion, destino, 2
                continue
        nx, ny = x + dx, y + dy
        if not mapa.dentro(nx, ny):
            conexion = mapa.conexiones.get(LADO[direccion])
            if conexion:
                vecino = MAPAS[conexion["mapa"]]
                if dx:   # este / oeste: x fija, y desplazada
                    destino = (vecino.clave, conexion["x"], y + conexion["y"])
                else:    # norte / sur: y fija, x desplazada
                    destino = (vecino.clave, x + conexion["x"], conexion["y"])
                if vecino.andable(destino[1], destino[2]) and destino not in bloqueadas:
                    yield direccion, destino, 1
            continue
        c = mapa.colision[ny][nx]
        if PERMISOS[c] != "LAND" or (clave, nx, ny) in bloqueadas:
            continue
        if c in WARP_AL_PISAR:
            warp = _warp_en(mapa, nx, ny)
            destino = destino_warp(warp) if warp else None
            if destino:
                yield direccion, destino, 2
                continue
        yield direccion, (clave, nx, ny), COSTE_HIERBA if c in HIERBA else 1


def ruta(origen, es_destino, bloqueadas=frozenset(), max_nodos=200_000):
    """Camino más barato desde `origen` hasta el primer nodo para el que es_destino(nodo) es cierto.
    Devuelve [(dirección, nodo esperado), ...] ([] si ya está en el destino) o None si no hay camino."""
    if es_destino(origen):
        return []
    previo, coste = {origen: None}, {origen: 0}
    cola, cuenta = [(0, 0, origen)], 0
    while cola and len(previo) < max_nodos:
        c, _, nodo = heapq.heappop(cola)
        if c > coste[nodo]:
            continue
        if es_destino(nodo):
            pasos = []
            while previo[nodo] is not None:
                anterior, direccion = previo[nodo]
                pasos.append((direccion, nodo))
                nodo = anterior
            return pasos[::-1]
        for direccion, siguiente, paso in vecinos(nodo, bloqueadas):
            nuevo = c + paso
            if nuevo < coste.get(siguiente, 1 << 30):
                coste[siguiente], previo[siguiente] = nuevo, (nodo, direccion)
                cuenta += 1
                heapq.heappush(cola, (nuevo, cuenta, siguiente))
    return None
