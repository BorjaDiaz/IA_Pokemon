import numpy as np

import src.utils.constantes as c

class RamExtractor:
    def __init__(self, pyboy_instance):
        self.pb = pyboy_instance

    def leer(self, addr):
        """Lee un byte de WRAM banco 1 sin depender del banco que tenga activo el juego."""
        return self.pb.memory[c.WRAM_BANK, addr]

    def get_flag_bytes(self):
        """Los 256 bytes de wEventFlags como array (bit b del byte i = flag (FLAG_START + i, b))."""
        return np.array(self.pb.memory[c.WRAM_BANK, c.FLAG_START:c.FLAG_END+1], dtype=np.uint8)

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
