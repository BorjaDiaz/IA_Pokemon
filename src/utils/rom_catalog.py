import json
import os

CATALOG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "rom_catalog.json")

with open(CATALOG_PATH, encoding="utf-8") as _f:
    _catalog = json.load(_f)

RAM = {name: int(addr, 16) for name, addr in _catalog["ram"].items()}
MAPS = {tuple(int(x) for x in key.split(",")): name for key, name in _catalog["maps"].items()}
EVENT_FLAGS = {name: (int(info["addr"], 16), info["bit"]) for name, info in _catalog["event_flags"].items()}
EVENT_FLAG_NAMES = {pos: name for name, pos in EVENT_FLAGS.items()}
EVENT_FLAG_KIND = {name: info["kind"] for name, info in _catalog["event_flags"].items()}


def map_name(group, number):
    """Devuelve la constante del mapa (p. ej. ROUTE_29) o 'Mapa g-n' si no existe."""
    return MAPS.get((group, number), f"Mapa {group}-{number}")


def flag_name(addr, bit):
    """Nombre del event flag en (addr, bit), o None si es un hueco sin usar."""
    return EVENT_FLAG_NAMES.get((addr, bit))


def is_story_flag(addr, bit):
    """True si el flag es de historia (no temporal, de entrenador ni de visibilidad)."""
    name = flag_name(addr, bit)
    return name is not None and EVENT_FLAG_KIND[name] == "historia"
