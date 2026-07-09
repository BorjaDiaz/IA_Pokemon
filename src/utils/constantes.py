import os


# ==========================================
# 🏆 SISTEMA DE RECOMPENSAS Y PENALIZACIONES
# ==========================================

# Exploración
REWARD_STEP = -0.005                 # Penalización por cada paso (para incentivar rapidez)
REWARD_NEW_TILE = 0.05              # Por pisar una baldosa nueva
REWARD_NEW_MAP = 5.0               # Por entrar a una zona/mapa nuevo

# Supervivencia y Progreso
REWARD_HEAL = 10.0
REWARD_HEAL_MAP = 20.0              # Curarse fuera de combate (Centros Pokémon, pociones)
REWARD_LEVEL_UP = 15.0              # Multiplicador por cada nivel ganado en el equipo

# Combate
REWARD_COMBAT_DAMAGE_CAUSED = 2.0   # Por hacer daño válido a un enemigo
REWARD_COMBAT_ENEMY_FAINTED = 10.0  # Por debilitar a un Pokémon rival
REWARD_COMBAT_HEAL = 5.0            # Por curarse en medio de un combate
PENALTY_COMBAT_DAMAGE_RECEIVED = -1.0 # Por recibir daño
PENALTY_COMBAT_STEP = -0.05         # Penalización por paso en combate (para que no alargue batallas)
PENALTY_TEAM_FAINTED = -15.0        # Game Over (equipo debilitado)
REWARD_HEALTHY_TEAM = 0.02  # Pequeño bonus por estar sano
HEALTHY_THRESHOLD = 0.70 
REWARD_HEALTHY_STEP = 0.02   # 70% de la vida total
REWARD_DAMAGE_MULT = 0.5

# Historia (Flags)
REWARD_FLAG_STORY = 100.0           # Por conseguir un objetivo clave de la historia
REWARD_FLAG_UNKNOWN = 2.0           # Por activar un evento menor o desconocido

# Umbrales de Tiempo / Estancamiento
FRAMES_STUCK_WARNING = 10           # Frames quietos antes de empezar a penalizar
FRAMES_STUCK_MAX = 400              # Límite máximo antes de considerar que la IA está "en coma"
MAX_STUCK_PENALTY = 0.5             # Castigo máximo por quedarse atascado en un rincón

# ==========================================
# MEMORIA BASE
# ==========================================
ADDR_MAP_GRP  = 0xDA00
ADDR_MAP_ID   = 0xDA01
ADDR_PLAYER_Y = 0xD20E
ADDR_PLAYER_X = 0xD20D

# ==========================================
# ESTADO DEL JUEGO / COMBATE
# ==========================================

ADDR_BATTLE_TYPE = 0xD11E # 0 = Mapa, 1 = Salvaje, 2 = Entrenador
ADDR_PARTY_COUNT = 0xDC0F
ADDR_PARTY_HP = 0xDA22
ADDR_PARTY_LEVEL = 0xDA22
# ==========================================
# RANGO FLAGS
# ==========================================
FLAG_START = 0xD7B7
FLAG_END   = 0xD8B6

# ==========================================
# FLAGS CONOCIDOS (HISTORIA)
# ==========================================
FLAGS = {
    "got_cyndaquil": (0xD87F, 0),
    "got_totodile":  (0xD87F, 1),
    "got_chikorita": (0xD87F, 2),
    "has_pokemon_1": (0xD7BA, 3),
    "has_pokemon_2": (0xD7BA, 5),
    "player_is_trainer": (0xD7BA, 2),
    "got_pokegear_1": (0xD88F, 7),
    "got_pokegear_2": (0xD890, 0),
    "rival_stole_pokemon": (0xD8A4, 2),
    "got_pokedex": (0xD8A8, 5),
    "entered_route_29": (0xD8A2, 1),
    "beat_falkner": (0xD8B0, 0),
    "beat_bugsy":   (0xD8B0, 1),
    "beat_whitney": (0xD8B0, 2),
    "beat_morty":   (0xD8B0, 3),
    "beat_chuck":   (0xD8B0, 4),
    "beat_jasmine": (0xD8B0, 5),
    "beat_pryce":   (0xD8B0, 6),
    "beat_clair":   (0xD8B0, 7),
}

# ==========================================
# FLAGS SECUNDARIAS 
# ==========================================
FLAGS_SECONDARYS = {
    "got_radio": (0xD81B, 5),
    "gave_mystery_egg": (0xD8A9, 1),
}


# ==========================================
# MEMORIA COMBATE: TU POKÉMON (LÍDER)
# ==========================================
ADDR_LIDER_ESPECIE    = 0xDA2A # ID del Pokémon para buscar sus tipos
ADDR_LIDER_ATK1       = 0xDA2C
ADDR_LIDER_ATK2       = 0xDA2D
ADDR_LIDER_ATK3       = 0xDA2E
ADDR_LIDER_ATK4       = 0xDA2F
ADDR_LIDER_NIVEL      = 0xDA49
ADDR_LIDER_HP_ACTUAL  = 0xDA4C 
ADDR_LIDER_HP_MAX     = 0xDA4E 
ADDR_LIDER_ATQ        = 0xDA50 
ADDR_LIDER_DEF        = 0xDA52 
ADDR_LIDER_VEL        = 0xDA54 
ADDR_LIDER_SP_ATQ     = 0xDA56 
ADDR_LIDER_SP_DEF     = 0xDA58 

# ==========================================
# MEMORIA COMBATE: POKÉMON RIVAL (¡Corregido!)
# ==========================================
ADDR_RIVAL_NIVEL      = 0xD0FC
ADDR_RIVAL_TIPO1      = 0xD0FD
ADDR_RIVAL_TIPO2      = 0xD0FE
ADDR_RIVAL_HP_ACTUAL  = 0xD0FF # Fila ajustada al Big Endian real
ADDR_RIVAL_HP_MAX     = 0xD101 
ADDR_RIVAL_ATQ        = 0xD103 
ADDR_RIVAL_DEF        = 0xD105 
ADDR_RIVAL_VEL        = 0xD107 
ADDR_RIVAL_SP_ATQ     = 0xD109 
ADDR_RIVAL_SP_DEF     = 0xD10B 

# ==========================================
# MINI POKÉDEX (IDs -> Tipos Base)
# ==========================================
POKEDEX_TIPOS = {
    152: ("Planta", "Planta"),     # Chikorita
    155: ("Fuego", "Fuego"),       # Cyndaquil
    158: ("Agua", "Agua"),         # Totodile
    16:  ("Normal", "Volador"),    # Pidgey
    19:  ("Normal", "Normal"),     # Rattata
    161: ("Normal", "Normal"),     # Sentret
    163: ("Normal", "Volador"),    # Hoothoot
    # Añadiremos más si la IA los necesita
}

# ==========================================
# 🥊 BASE DE DATOS DE ATAQUES (Early Game)
# Formato: ID: (Nombre, Tipo, Potencia, Precisión, Efecto/Clase)
# Clase: "D" (Daño), "S" (Status/Baja stats rival), "B" (Buff/Sube tus stats)
# ==========================================
MOVES_DB = {
    0:  ("Ninguno", "Normal", 0, 0, "S"), # Hueco vacío
    33: ("Placaje", "Normal", 35, 95, "D"),
    43: ("Malicioso", "Normal", 0, 100, "S"),
    10: ("Arañazo", "Normal", 40, 100, "D"),
    52: ("Ascuas", "Fuego", 40, 100, "D"),
    55: ("Pistola Agua", "Agua", 40, 100, "D"),
    22: ("Látigo Cepa", "Planta", 35, 100, "D"),
    45: ("Gruñido", "Normal", 0, 100, "S"),
    # Puedes ir añadiendo más IDs a medida que los veas en la auditoría
}


# ==========================================
# NOMBRES DE MAPAS
# ==========================================
MAP_NAMES = {
    (1, 1): "Ciudad Olivo (Exterior)", (1, 2): "Centro Pokémon de Olivo", (1, 3): "Cafetería de Olivo", (1, 4): "Casa del Pescador", (1, 5): "Gimnasio de Olivo", (1, 6): "Ruta 39 (Entrada a Olivo)", (1, 7): "Faro (Piso 1)", (1, 8): "Faro (Piso 2)", (1, 9): "Faro (Piso 3)", (1, 10): "Faro (Piso 4)", (1, 11): "Faro (Piso 5)", (1, 12): "Faro (Piso 6)",
    (2, 1): "Ciudad Iris (Exterior)", (2, 2): "Teatro de Danza", (2, 3): "Torre Quemada (PB)", (2, 4): "Torre Quemada (Sótano)", (2, 5): "Centro Pokémon Iris", (2, 6): "Gimnasio de Iris", (2, 7): "Torre Hojalata (Entrada)", (2, 8): "Torre Hojalata (Piso 1)",
    (3, 1): "Ciudad Trigal (Exterior)", (3, 2): "Gimnasio de Trigal", (3, 3): "Centro Pokémon Trigal", (3, 4): "Centro Comercial (Piso 1)", (3, 5): "Centro Comercial (Piso 2)", (3, 6): "Centro Comercial (Piso 3)", (3, 7): "Centro Comercial (Piso 4)", (3, 8): "Centro Comercial (Piso 5)", (3, 9): "Centro Comercial (Piso 6)", (3, 10): "Centro Comercial (Elevador)", (3, 11): "Centro Comercial (Sótano)", (3, 12): "Radio (Piso 1)", (3, 13): "Radio (Piso 2)", (3, 14): "Radio (Piso 3)", (3, 15): "Radio (Piso 4)", (3, 16): "Radio (Piso 5)", (3, 17): "Subterráneo (Pasillo)", (3, 18): "Subterráneo (Almacén)", (3, 19): "Magnetotren",
    (4, 1): "Ciudad Orquídea (Exterior)", (4, 2): "Gimnasio Orquídea", (4, 3): "Centro Pokémon Orquídea", (4, 4): "Farmacia Pokémon", (4, 5): "Casa Extra",
    (5, 1): "Pueblo Caoba (Exterior)", (5, 2): "Gimnasio Caoba", (5, 3): "Tienda Souvenirs", (5, 4): "Escondite Rocket (Sótano 1)", (5, 5): "Escondite Rocket (Sótano 2)", (5, 6): "Escondite Rocket (Sótano 3)",
    (7, 1): "Ciudad Endrino (Exterior)", (7, 2): "Gimnasio Endrino", (7, 3): "Centro Pokémon Endrino", (7, 4): "Cueva Dragón", (7, 5): "Cueva Dragón (Santuario)",
    (9, 1): "Ciudad Malva (Exterior)", (9, 2): "Gimnasio Malva", (9, 3): "Escuela Pokémon", (9, 4): "Centro Pokémon Malva", (9, 5): "Torre Bellsprout (Piso 1)", (9, 6): "Torre Bellsprout (Piso 2)", (9, 7): "Torre Bellsprout (Piso 3)",
    (10, 1): "Pueblo Azalea (Exterior)", (10, 2): "Gimnasio Azalea", (10, 3): "Centro Pokémon Azalea", (10, 4): "Casa de César", (10, 5): "Pozo Slowpoke (Piso 1)", (10, 6): "Pozo Slowpoke (Sótano 1)",
    (11, 1): "Cueva Unión (Piso 1)", (11, 2): "Cueva Unión (Sótano 1)", (11, 3): "Cueva Unión (Sótano 2)", (13, 1): "Cueva Helada (Piso 1)", (13, 2): "Cueva Helada (Sótano 1)", (13, 3): "Cueva Helada (Sótano 2)", (13, 4): "Cueva Helada (Sótano 3)", (15, 1): "Encinar", (16, 1): "Ruinas Alfa", (16, 2): "Ruinas Alfa (Sótano)", (18, 1): "Monte Mortero (Centro)", (18, 2): "Monte Mortero (Sótano 1)", (18, 3): "Monte Mortero (Lados)", (21, 1): "Islas Remolino (Piso 1)", (21, 2): "Islas Remolino (Sótano 1)", (21, 3): "Islas Remolino (Lugia)",
    (22, 1): "Ruta 26", (22, 2): "Ruta 27", (22, 3): "Calle Victoria", (22, 4): "Liga Pokémon (Hall)", (22, 5): "Liga Pokémon (Mento)", (22, 6): "Liga Pokémon (Koga)", (22, 7): "Liga Pokémon (Bruno)", (22, 8): "Liga Pokémon (Karen)", (22, 9): "Liga Pokémon (Lance)",
    (24, 3): "Ruta 29", (24, 4): "Pueblo Primavera (Exterior)", (24, 5): "Laboratorio del Prof. Elm", (24, 6): "Tu Casa (Planta Baja)", (24, 7): "Tu Habitación", (24, 8): "Casa del Vecino",(24, 9): "Casa del Rival",
    (25, 1): "Ruta 30", (25, 2): "Ruta 31", (25, 3): "Centro Pokémon Ruta 31", (25, 4): "Cueva Oscura", (25, 5): "Casa del Sr. Pokémon", (25, 6): "Casa de los Bonguris",
    (26, 1): "Ciudad Cerezo (Exterior)", (26, 2): "Centro Pokémon Cerezo", (26, 3): "Tienda Pokémon Cerezo", (26, 4): "Casa del Guía", (26, 5): "Casa Extra Cerezo",
    (28, 1): "Parque Nacional", (28, 2): "Caseta Ruta 35", (28, 3): "Caseta Ruta 36",
    (29, 1): "Ruta 43", (29, 2): "Lago de la Furia", (29, 3): "Caseta Ruta 43",
    (31, 1): "Ruta 32", (31, 2): "Ruta 33", (31, 4): "Centro Pokémon Ruta 32",
    (32, 1): "Ruta 34", (32, 2): "Ruta 35", (32, 3): "Guardería Pokémon",
    (33, 1): "Ruta 36", (33, 2): "Ruta 37",
    (34, 1): "Ruta 38", (34, 2): "Ruta 39", (34, 4): "Granja Mu-mu",
    (35, 1): "Ruta 40", (35, 2): "Ruta 41",
    (36, 1): "Ruta 42", (36, 2): "Ruta 44",
    (37, 1): "Ruta 45", (37, 2): "Ruta 46",
}


# ==========================================
# 📊 TABLA DE TIPOS - POKÉMON GEN 2 (Oro/Plata)
# ==========================================
# 0: Normal, 1: Lucha, 2: Volador, 3: Veneno, 4: Tierra, 5: Roca, 6: Bicho, 7: Fantasma, 8: Acero
# 20: Fuego, 21: Agua, 22: Planta, 23: Eléctrico, 24: Psíquico, 25: Hielo, 26: Dragón, 27: Siniestro

TABLA_TIPOS = {
    # ATACANTE: { DEFENSOR: MULTIPLICADOR }
    0:  {5: 0.5, 8: 0.5, 7: 0.0},                              # Normal
    1:  {0: 2.0, 5: 2.0, 8: 2.0, 25: 2.0, 27: 2.0, 2: 0.5, 3: 0.5, 6: 0.5, 24: 0.5, 7: 0.0}, # Lucha
    2:  {1: 2.0, 6: 2.0, 22: 2.0, 5: 0.5, 8: 0.5, 23: 0.5},   # Volador
    3:  {22: 2.0, 3: 0.5, 4: 0.5, 5: 0.5, 7: 0.5, 8: 0.0},     # Veneno
    4:  {3: 2.0, 5: 2.0, 20: 2.0, 23: 2.0, 8: 2.0, 6: 0.5, 22: 0.5, 2: 0.0}, # Tierra
    5:  {2: 2.0, 6: 2.0, 20: 2.0, 25: 2.0, 1: 0.5, 4: 0.5, 8: 0.5}, # Roca
    6:  {22: 2.0, 24: 2.0, 27: 2.0, 1: 0.5, 2: 0.5, 3: 0.5, 20: 0.5, 7: 0.5, 8: 0.5}, # Bicho
    7:  {7: 2.0, 24: 2.0, 27: 0.5, 8: 0.5, 0: 0.0},           # Fantasma
    8:  {5: 2.0, 25: 2.0, 20: 0.5, 21: 0.5, 23: 0.5, 8: 0.5}, # Acero
    20: {6: 2.0, 8: 2.0, 22: 2.0, 25: 2.0, 5: 0.5, 20: 0.5, 21: 0.5, 26: 0.5}, # Fuego
    21: {4: 2.0, 5: 2.0, 20: 2.0, 21: 0.5, 22: 0.5, 26: 0.5}, # Agua
    22: {4: 2.0, 5: 2.0, 21: 2.0, 2: 0.5, 3: 0.5, 6: 0.5, 8: 0.5, 20: 0.5, 22: 0.5, 26: 0.5}, # Planta
    23: {2: 2.0, 21: 2.0, 22: 0.5, 23: 0.5, 26: 0.5, 4: 0.0}, # Eléctrico
    24: {1: 2.0, 3: 2.0, 8: 0.5, 24: 0.5, 27: 0.0},           # Psíquico
    25: {2: 2.0, 4: 2.0, 22: 2.0, 26: 2.0, 8: 0.5, 20: 0.5, 21: 0.5, 25: 0.5}, # Hielo
    26: {26: 2.0, 8: 0.5},                                     # Dragón
    27: {7: 2.0, 24: 2.0, 1: 0.5, 27: 0.5}                    # Siniestro
}

# Diccionario para que los prints queden bonitos en el log
NOMBRES_TIPOS = {
    0: "Normal", 1: "Lucha", 2: "Volador", 3: "Veneno", 4: "Tierra", 5: "Roca", 
    6: "Bicho", 7: "Fantasma", 8: "Acero", 20: "Fuego", 21: "Agua", 22: "Planta", 
    23: "Eléctrico", 24: "Psíquico", 25: "Hielo", 26: "Dragón", 27: "Siniestro"
}


class GestorCombate:
    def __init__(self, pyboy_instance):
        self.pb = pyboy_instance
        
    def leer_stat_2bytes(self, direccion):
        """Lee valores de 2 bytes (Big Endian) como Vida, Ataque, etc."""
        high = self.pb.memory[direccion]
        low = self.pb.memory[direccion + 1]
        return (high << 8) + low

    def leer_vida_jugador(self):
        return self.leer_stat_2bytes(ADDR_LIDER_HP_ACTUAL)

    def leer_vida_enemigo(self):
        return self.leer_stat_2bytes(ADDR_RIVAL_HP_ACTUAL)

    def leer_tipos_enemigo_nombres(self):
        tipo1 = self.pb.memory[ADDR_RIVAL_TIPO1]
        tipo2 = self.pb.memory[ADDR_RIVAL_TIPO2]
        t1_nombre = NOMBRES_TIPOS.get(tipo1, "Desconocido")
        t2_nombre = NOMBRES_TIPOS.get(tipo2, "Desconocido")
        return [t1_nombre] if tipo1 == tipo2 else [t1_nombre, t2_nombre]

    def leer_ataques_lider(self):
        ataques = []
        slots = [ADDR_LIDER_ATK1, ADDR_LIDER_ATK2, ADDR_LIDER_ATK3, ADDR_LIDER_ATK4]
        for i, addr in enumerate(slots):
            atk_id = self.pb.memory[addr]
            if atk_id != 0 and atk_id in MOVES_DB:
                nombre, tipo, _, _, _ = MOVES_DB[atk_id]
                ataques.append((i + 1, atk_id, nombre, tipo))
        return ataques

    def imprimir_auditoria(self, tipo_combate_id):
        # 1. Recopilar datos del LÍDER
        esp_id = self.pb.memory[ADDR_LIDER_ESPECIE]
        lvl_lider = self.pb.memory[ADDR_LIDER_NIVEL]
        hp_act = self.leer_stat_2bytes(ADDR_LIDER_HP_ACTUAL)
        hp_max = self.leer_stat_2bytes(ADDR_LIDER_HP_MAX)
        atk_l = self.leer_stat_2bytes(ADDR_LIDER_ATQ)
        def_l = self.leer_stat_2bytes(ADDR_LIDER_DEF)
        vel_l = self.leer_stat_2bytes(ADDR_LIDER_VEL)
        spa_l = self.leer_stat_2bytes(ADDR_LIDER_SP_ATQ)
        spd_l = self.leer_stat_2bytes(ADDR_LIDER_SP_DEF)
        if tipo_combate_id in [1, 2]:
            tipo_lbl = "Entrenador"
        elif tipo_combate_id > 0:
            tipo_lbl = "Pokémon Salvaje"
        else:
            tipo_lbl = "Desconocido"
        
        tipos_lider = POKEDEX_TIPOS.get(esp_id, ("Desconocido", "Desconocido"))
        str_tipos_lider = f"[{tipos_lider[0]}]" if tipos_lider[0] == tipos_lider[1] else f"[{tipos_lider[0]}] [{tipos_lider[1]}]"
        
        ataques_str = ""
        for atk in self.leer_ataques_lider():
            ataques_str += f"\n   🎒 Slot {atk[0]}: ID [{atk[1]}] {atk[2]} (Tipo: {atk[3]})"

        # 2. Recopilar datos del RIVAL
        lvl_rival = self.pb.memory[ADDR_RIVAL_NIVEL]
        hp_act_r = self.leer_stat_2bytes(ADDR_RIVAL_HP_ACTUAL)
        hp_max_r = self.leer_stat_2bytes(ADDR_RIVAL_HP_MAX)
        atk_r = self.leer_stat_2bytes(ADDR_RIVAL_ATQ)
        def_r = self.leer_stat_2bytes(ADDR_RIVAL_DEF)
        vel_r = self.leer_stat_2bytes(ADDR_RIVAL_VEL)
        spa_r = self.leer_stat_2bytes(ADDR_RIVAL_SP_ATQ)
        spd_r = self.leer_stat_2bytes(ADDR_RIVAL_SP_DEF)
        
        tipos_rival = self.leer_tipos_enemigo_nombres()
        str_tipos_rival = " ".join([f"[{t}]" for t in tipos_rival])
        
        tipo_lbl = "Pokémon Salvaje" if tipo_combate_id == 1 else "Entrenador" if tipo_combate_id == 2 else "Desconocido"
        # 3. Imprimir el bloque ASCII
        print(f"\n⚔️ ¡ENTRANDO EN COMBATE! 👉 Tipo: {tipo_lbl} (ID RAM: {tipo_combate_id})")
        print("--- 🧠 AUDITORÍA DE RAM COMPLETA ---")
        print(f"🧑‍🚀 TU POKÉMON (Especie ID: {esp_id}):")
        print(f"   ❤️ Vida: {hp_act} / {hp_max} HP | 📈 Nivel: {lvl_lider}")
        print(f"   🎭 Tipos: {str_tipos_lider}")
        print(f"   ⚔️ Stats -> Atk: {atk_l} | Def: {def_l} | Vel: {vel_l}")
        print(f"   🌀 Stats Esp -> Atk.Esp: {spa_l} | Def.Esp: {spd_l}")
        print(f"   🎒 Ataques -> {ataques_str.strip()}")
        print("-------------------------------------------")
        print(f"👹 POKÉMON RIVAL:")
        print(f"   ❤️ Vida: {hp_act_r} / {hp_max_r} HP | 📈 Nivel: {lvl_rival}")
        print(f"   🎭 Tipos: {str_tipos_rival}")
        print(f"   ⚔️ Stats -> Atk: {atk_r} | Def: {def_r} | Vel: {vel_r}")
        print(f"   🌀 Stats Esp -> Atk.Esp: {spa_r} | Def.Esp: {spd_r}")
        print("-------------------------------------------\n")