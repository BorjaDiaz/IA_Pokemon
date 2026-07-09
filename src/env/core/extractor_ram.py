import src.utils.constantes as c

class RamExtractor:
    def __init__(self, pyboy_instance):
        self.pb = pyboy_instance

    def get_all_flags(self):
        self.pb.memory[0xFF70] = 1
        mem = bytes(self.pb.memory[c.FLAG_START:c.FLAG_END+1])
        return {(c.FLAG_START + i, b): (mem[i] >> b) & 1 for i in range(len(mem)) for b in range(8)}

    def leer_vida_total_equipo(self):
        hp_total = 0
        party_count = self.pb.memory[0xDA22] 
        if party_count > 6 or party_count == 0:
            return 0
        for i in range(party_count):
            base = 0xDA2A + (i * 0x30)
            hp_actual = (self.pb.memory[base + 0x22] << 8) + self.pb.memory[base + 0x23]
            hp_total += hp_actual
        return hp_total

    def leer_nivel_total_equipo(self):
        nivel_total = 0
        party_count = self.pb.memory[0xDA22]
        if party_count > 6 or party_count == 0:
            return 0
        for i in range(party_count):
            base = 0xDA2A + (i * 0x30)
            nivel_actual = self.pb.memory[base + 0x1F]
            if 1 <= nivel_actual <= 100:
                nivel_total += nivel_actual
        return nivel_total
    
    def leer_max_vida_total_equipo(self):
        hp_max_total = 0
        party_count = self.pb.memory[0xDA22]
        if party_count > 6 or party_count == 0:
            return 0
        for i in range(party_count):
            base = 0xDA2A + (i * 0x30)
            hp_max_actual = (self.pb.memory[base + 0x24] << 8) + self.pb.memory[base + 0x25]
            hp_max_total += hp_max_actual
        return hp_max_total