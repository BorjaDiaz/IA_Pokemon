"""Genera data/rom_catalog.json con los event flags y mapas de Pokémon Oro (ES).

Fuente: desensamblado pret/pokegold (constants/event_flags.asm y
constants/map_constants.asm). La ROM española (POKEMON_GLDAAUS) comparte la
disposición de WRAM con la US: se ha comprobado contando referencias en el
código de la ROM y leyendo los savestates del proyecto.

Uso:
    python tools/build_rom_catalog.py
"""
import json
import os
import urllib.request

PRET_BASE = "https://raw.githubusercontent.com/pret/pokegold/master/"
EVENT_FLAGS_START = 0xD7B7  # wEventFlags
OUT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "rom_catalog.json")

# Direcciones de WRAM (banco 1) verificadas contra la ROM española
RAM = {
    "wEnemyMonSpecies": 0xD0EF,
    "wEnemyMonLevel": 0xD0FC,
    "wEnemyMonStatus": 0xD0FD,
    "wEnemyMonHP": 0xD0FF,        # 2 bytes, big endian
    "wEnemyMonMaxHP": 0xD101,     # 2 bytes, big endian
    "wEnemyMonType1": 0xD10D,
    "wEnemyMonType2": 0xD10E,
    "wBattleMode": 0xD116,        # 0 = mapa, 1 = salvaje, 2 = entrenador
    "wBattleType": 0xD119,
    "wScriptRunning": 0xD15F,
    "wPlayerMapX": 0xD20D,        # coordenadas del sprite del jugador (= wXCoord + 4)
    "wPlayerMapY": 0xD20E,
    "wGameTimeHours": 0xD1EB,     # 2 bytes big endian, luego minutos, segundos y frames
    "wGameTimeMinutes": 0xD1ED,
    "wGameTimeSeconds": 0xD1EE,
    "wGameTimeFrames": 0xD1EF,
    "wStatusFlags": 0xD571,       # bit 0 = Pokédex
    "wMoney": 0xD573,             # 3 bytes, BCD
    "wJohtoBadges": 0xD57C,       # bit 0 Céfiro ... bit 7 Dragón
    "wKantoBadges": 0xD57D,
    "wPokegearFlags": 0xD67C,     # bit 7 = Pokégear obtenido
    "wEventFlags": EVENT_FLAGS_START,
    "wMapGroup": 0xDA00,
    "wMapNumber": 0xDA01,
    "wYCoord": 0xDA02,
    "wXCoord": 0xDA03,
    "wPartyCount": 0xDA22,
    "wPartyMons": 0xDA2A,         # 6 structs de 0x30 bytes
    "wPokedexCaught": 0xDBE4,
}

JOHTO_BADGES = ["ZEPHYR", "HIVE", "PLAIN", "FOG", "MINERAL", "STORM", "GLACIER", "RISING"]


def fetch(path):
    with urllib.request.urlopen(PRET_BASE + path) as resp:
        return resp.read().decode("utf-8").splitlines()


def parse_event_flags(lines):
    """Replica las macros const_def / const / const_skip / const_next de rgbds."""
    index, flags = 0, {}
    for line in lines:
        s = line.split(";")[0].strip()
        if s == "const_def":
            index = 0
        elif s.startswith("const_skip"):
            index += 1
        elif s.startswith("const_next"):
            index = int(s.split()[1])
        elif s.startswith("const "):
            flags[s.split()[1]] = index
            index += 1
    return flags


def parse_maps(lines):
    group, number, maps = 0, 0, {}
    for line in lines:
        s = line.split(";")[0].strip()
        if s.startswith("newgroup"):
            group, number = group + 1, 0
        elif s.startswith("map_const "):
            number += 1
            maps[f"{group},{number}"] = s.split()[1].rstrip(",")
    return maps


def flag_kind(index):
    # Rangos según los comentarios de event_flags.asm
    if index < 8:
        return "temporal"
    if index < 1000:
        return "historia"
    if index < 1600:
        return "entrenador"
    return "visibilidad"  # muestra/oculta NPCs y objetos (no es progreso real)


def main():
    flags = parse_event_flags(fetch("constants/event_flags.asm"))
    maps = parse_maps(fetch("constants/map_constants.asm"))

    catalog = {
        "rom": "POKEMON_GLDAAUS",
        "ram": {k: f"0x{v:04X}" for k, v in RAM.items()},
        "johto_badges": {name: [f"0x{RAM['wJohtoBadges']:04X}", bit] for bit, name in enumerate(JOHTO_BADGES)},
        "event_flags": {
            name: {
                "addr": f"0x{EVENT_FLAGS_START + i // 8:04X}",
                "bit": i % 8,
                "index": i,
                "kind": flag_kind(i),
            }
            for name, i in sorted(flags.items(), key=lambda kv: kv[1])
        },
        "maps": maps,
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=1, ensure_ascii=False)
    print(f"{len(flags)} event flags y {len(maps)} mapas -> {OUT_PATH}")


if __name__ == "__main__":
    main()
