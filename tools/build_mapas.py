"""Genera data/mapas.json leyendo la geometría de todos los mapas directamente de la ROM (Pokémon Oro ES).

Para cada mapa: tamaño, tileset, rejilla de colisiones (una celda = una casilla del jugador), puertas y
escaleras (warps) con su destino, conexiones con los mapas vecinos, eventos por coordenada, carteles y
personajes/objetos con el evento que los oculta. Es lo que necesita un buscador de caminos.

Estructuras según el desensamblado pret/pokegold (data/maps/maps.asm, macros/scripts/maps.asm). En la ROM
española la tabla de mapas está en el mismo sitio que en la inglesa (25:40ED, comprobado con los 368 mapas
del catálogo) y la de tilesets no (05:56D3 en vez de 05:56BE, comprobado con lo que el juego carga en WRAM:
tests/test_mapas.py).

Uso:
    python tools/build_mapas.py
"""
import json
import os
import re
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROM_PATH = os.path.join(BASE, "roms", "Pokemon_Oro.gbc")
CATALOG_PATH = os.path.join(BASE, "data", "rom_catalog.json")
OUT_PATH = os.path.join(BASE, "data", "mapas.json")
PRET_BASE = "https://raw.githubusercontent.com/pret/pokegold/master/"

MAP_GROUP_POINTERS = (0x25, 0x40ED)
TILESETS = (0x05, 0x56D3)
TILESET_LENGTH = 15
MAP_LENGTH = 9
ENTORNOS = {1: "TOWN", 2: "ROUTE", 3: "INDOOR", 4: "CAVE", 5: "ENVIRONMENT_5", 6: "GATE", 7: "DUNGEON"}
# Bits del byte de conexiones, en el orden en que van sus structs
CONEXIONES = [("norte", 8), ("sur", 4), ("oeste", 2), ("este", 1)]


def offset(banco, direccion):
    return banco * 0x4000 + (direccion - 0x4000 if banco else direccion)


def con_signo(byte):
    return byte - 256 if byte > 127 else byte


class Rom:
    def __init__(self, datos):
        self.d = datos

    def b(self, o):
        return self.d[o]

    def w(self, o):
        return self.d[o] | self.d[o + 1] << 8


def leer_permisos():
    """{byte de colisión: "LAND" | "WATER" | "WALL"} y sus nombres, de pret (son constantes del motor)."""
    def fetch(path):
        with urllib.request.urlopen(PRET_BASE + path) as resp:
            return resp.read().decode("utf-8").splitlines()
    permisos = []
    for linea in fetch("data/collision/collision_permissions.asm"):
        m = re.match(r"\s*db (\w+)_TILE", linea)
        if m:
            permisos.append(m.group(1))
    assert len(permisos) == 256, len(permisos)
    nombres = {}
    for linea in fetch("constants/collision_constants.asm"):
        m = re.match(r"DEF COLL_(\w+)\s+EQU \$([0-9a-f]{2})", linea)
        if m:
            nombres[int(m.group(2), 16)] = m.group(1)
    return permisos, nombres


def leer_mapa(rom, cabecera):
    banco_attrs, tileset, entorno = rom.b(cabecera), rom.b(cabecera + 1), rom.b(cabecera + 2)
    a = offset(banco_attrs, rom.w(cabecera + 3))
    alto, ancho = rom.b(a + 1), rom.b(a + 2)
    bloques = offset(rom.b(a + 3), rom.w(a + 4))
    banco_eventos = rom.b(a + 6)
    eventos = offset(banco_eventos, rom.w(a + 9))
    bits = rom.b(a + 11)

    conexiones, c = {}, a + 12
    for nombre, bit in CONEXIONES:
        if bits & bit:
            # grupo, mapa, puntero a la franja, destino en WRAM, largo, ancho del vecino, alineación y, x, ventana
            conexiones[nombre] = {"mapa": [rom.b(c), rom.b(c + 1)],
                                  "y": con_signo(rom.b(c + 8)), "x": con_signo(rom.b(c + 9))}
            c += 12

    # Colisiones: cada bloque son 2x2 casillas; el tileset da 4 bytes de colisión por bloque
    t = offset(*TILESETS) + TILESET_LENGTH * tileset
    colisiones = offset(rom.b(t + 6), rom.w(t + 7))
    filas = []
    for cy in range(alto * 2):
        fila = bytearray()
        for cx in range(ancho * 2):
            bloque = rom.b(bloques + (cy // 2) * ancho + cx // 2)
            fila.append(rom.b(colisiones + bloque * 4 + (cy % 2) * 2 + cx % 2))
        filas.append(fila.hex())

    e = eventos + 2  # dos bytes de relleno
    n = rom.b(e); e += 1
    warps = []
    for _ in range(n):  # y, x, warp de destino (desde 1; 255 = el último usado), grupo, mapa
        warps.append({"x": rom.b(e + 1), "y": rom.b(e), "warp": rom.b(e + 2), "mapa": [rom.b(e + 3), rom.b(e + 4)]})
        e += 5
    n = rom.b(e); e += 1
    coord = []
    for _ in range(n):  # escena, y, x, relleno, script, relleno
        coord.append({"x": rom.b(e + 2), "y": rom.b(e + 1), "escena": rom.b(e)})
        e += 8
    n = rom.b(e); e += 1
    bg = []
    for _ in range(n):  # y, x, función, script
        bg.append({"x": rom.b(e + 1), "y": rom.b(e), "tipo": rom.b(e + 2)})
        e += 5
    n = rom.b(e); e += 1
    objetos = []
    for _ in range(n):  # sprite, y+4, x+4, movimiento, radio, horas (2), paleta/tipo, alcance, script, evento
        evento = rom.w(e + 11)
        objetos.append({"x": rom.b(e + 2) - 4, "y": rom.b(e + 1) - 4, "sprite": rom.b(e), "movimiento": rom.b(e + 3),
                        "tipo": rom.b(e + 7) & 0x0F, "alcance": rom.b(e + 8),
                        "evento": None if evento == 0xFFFF else evento})
        e += 13

    return {"tileset": tileset, "entorno": ENTORNOS.get(entorno, str(entorno)), "ancho": ancho * 2, "alto": alto * 2,
            "colision": filas, "warps": warps, "conexiones": conexiones, "coord_events": coord,
            "bg_events": bg, "objetos": objetos}


def main():
    with open(ROM_PATH, "rb") as f:
        rom = Rom(f.read())
    with open(CATALOG_PATH, encoding="utf-8") as f:
        catalogo = json.load(f)
    eventos_por_indice = {info["index"]: nombre for nombre, info in catalogo["event_flags"].items()}
    permisos, nombres = leer_permisos()

    tabla = offset(*MAP_GROUP_POINTERS)
    mapas = {}
    for clave, nombre in catalogo["maps"].items():
        grupo, numero = map(int, clave.split(","))
        cabecera = offset(MAP_GROUP_POINTERS[0], rom.w(tabla + 2 * (grupo - 1))) + MAP_LENGTH * (numero - 1)
        mapa = leer_mapa(rom, cabecera)
        assert mapa["entorno"] == catalogo["entornos"][clave], (nombre, mapa["entorno"])
        mapa["nombre"] = nombre
        for objeto in mapa["objetos"]:  # el evento que lo oculta, por su nombre
            if objeto["evento"] is not None:
                objeto["evento"] = eventos_por_indice.get(objeto["evento"], objeto["evento"])
        mapas[clave] = mapa

    salida = {"rom": catalogo["rom"], "permisos": permisos, "colisiones": {f"{k:02x}": v for k, v in sorted(nombres.items())},
              "mapas": mapas}
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, separators=(",", ":"))
    casillas = sum(m["ancho"] * m["alto"] for m in mapas.values())
    print(f"{len(mapas)} mapas, {casillas:,} casillas, {sum(len(m['warps']) for m in mapas.values())} warps, "
          f"{sum(len(m['objetos']) for m in mapas.values())} personajes/objetos -> {OUT_PATH} "
          f"({os.path.getsize(OUT_PATH) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
