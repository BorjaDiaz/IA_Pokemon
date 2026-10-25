import numpy as np

import src.utils.constantes as c
from src.utils import rom_catalog

class RamExtractor:
    def __init__(self, pyboy_instance):
        self.pb = pyboy_instance

    def leer(self, addr):
        """Lee un byte de WRAM banco 1 sin depender del banco que tenga activo el juego."""
        return self.pb.memory[c.WRAM_BANK, addr]

    def get_flag_bytes(self):
        """Los 256 bytes de wEventFlags como array (bit b del byte i = flag (FLAG_START + i, b))."""
        return np.array(self.pb.memory[c.WRAM_BANK, c.FLAG_START:c.FLAG_END+1], dtype=np.uint8)

    def leer_tiempo_juego(self):
        """Tiempo de partida del juego en segundos (el de la ficha del entrenador): el reloj del speedrun."""
        horas = (self.leer(c.ADDR_GAME_TIME_HOURS) << 8) | self.leer(c.ADDR_GAME_TIME_HOURS + 1)
        minutos, segundos = self.leer(c.ADDR_GAME_TIME_MINUTES), self.leer(c.ADDR_GAME_TIME_SECONDS)
        frames = self.leer(c.ADDR_GAME_TIME_FRAMES)
        return horas * 3600 + minutos * 60 + segundos + frames / 60

    def leer_party_count(self):
        return self.leer(c.ADDR_PARTY_COUNT)

    def leer_vida_total_equipo(self):
        hp_total = 0
        party_count = self.leer_party_count()
        if party_count > 6 or party_count == 0:
            return 0
        for i in range(party_count):
            base = 0xDA2A + (i * 0x30)
            hp_actual = (self.leer(base + 0x22) << 8) + self.leer(base + 0x23)
            hp_total += hp_actual
        return hp_total

    def leer_nivel_total_equipo(self):
        nivel_total = 0
        party_count = self.leer_party_count()
        if party_count > 6 or party_count == 0:
            return 0
        for i in range(party_count):
            base = 0xDA2A + (i * 0x30)
            nivel_actual = self.leer(base + 0x1F)
            if 1 <= nivel_actual <= 100:
                nivel_total += nivel_actual
        return nivel_total

    def leer_nivel_max_equipo(self):
        """Nivel del Pokémon más fuerte del equipo (0 si no hay equipo)."""
        party_count = self.leer_party_count()
        if party_count > 6 or party_count == 0:
            return 0
        niveles = [self.leer(0xDA2A + i * 0x30 + 0x1F) for i in range(party_count)]
        return max((n for n in niveles if 1 <= n <= 100), default=0)

    def leer_max_vida_total_equipo(self):
        hp_max_total = 0
        party_count = self.leer_party_count()
        if party_count > 6 or party_count == 0:
            return 0
        for i in range(party_count):
            base = 0xDA2A + (i * 0x30)
            hp_max_actual = (self.leer(base + 0x24) << 8) + self.leer(base + 0x25)
            hp_max_total += hp_max_actual
        return hp_max_total

    def leer_pp_ataques(self):
        """(PP actuales, PP máximos) de los ataques que hacen daño de todo el equipo. Sin ellos no se
        puede ganar un combate: el rival de Cerezo era imposible con Placaje a 0 PP. Por Pokémon: ataques
        en +0x02..0x05 y PP en +0x17..0x1A (6 bits bajos = PP actuales, 2 altos = Más PP usados)."""
        party_count = self.leer_party_count()
        if party_count > 6 or party_count == 0:
            return 0, 0
        actuales = maximos = 0
        for i in range(party_count):
            base = 0xDA2A + i * 0x30
            for slot in range(4):
                ataque = rom_catalog.MOVES.get(self.leer(base + 0x02 + slot))
                if ataque is None or ataque[1] == 0:
                    continue
                pp = self.leer(base + 0x17 + slot)
                actuales += pp & 0x3F
                maximos += ataque[2] + (ataque[2] // 5) * (pp >> 6)
        return actuales, maximos
