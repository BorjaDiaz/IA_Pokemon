import src.utils.config as config
from src.utils import rom_catalog


# ==========================================
# 🏆 SISTEMA DE RECOMPENSAS Y PENALIZACIONES
# ==========================================

# Valores antes de dividir entre 10 en PokemonGoldEnv.step

# Exploración (baldosas y mapas cuentan una vez por episodio)
REWARD_STEP = -0.005                 # Penalización por cada paso (para incentivar rapidez)
REWARD_NEW_TILE = 0.05              # Por pisar una baldosa nueva
REWARD_NEW_MAP = 5.0               # Por entrar a una zona/mapa nuevo
PENALTY_SAME_TILE = -0.005          # Por quedarse en la misma baldosa fuera de combate y escenas
PENALTY_REVISIT_TILE = -0.001       # Por volver a una baldosa ya pisada
PENALTY_NO_PROGRESS = -10.0         # Al cortar el episodio por no avanzar

# Supervivencia y Progreso
REWARD_HEAL = 10.0
REWARD_LEVEL_UP = 5.0               # Por cada nivel ganado (no cuenta al entrar un Pokémon nuevo en el equipo)

# Combate: un combate salvaje típico sale aproximadamente neutro (daño + K.O. ≈ pasos en combate),
# para que el agente no aprenda a farmear combates en la hierba en lugar de avanzar
REWARD_COMBAT_ENEMY_FAINTED = 2.0   # Por debilitar a un Pokémon rival
PENALTY_COMBAT_DAMAGE_RECEIVED = -1.0 # Por recibir daño
PENALTY_COMBAT_STEP = -0.05         # Penalización por paso en combate (para que no alargue batallas)
PENALTY_TEAM_FAINTED = -15.0        # Game Over (equipo debilitado)
REWARD_DAMAGE_MULT = 0.05           # Por cada PS de daño causado

# Historia (Flags)
REWARD_FLAG_STORY = 100.0           # Por conseguir un hito de FLAGS
REWARD_FLAG_UNKNOWN = 2.0           # Por otro event flag de historia (no visibilidad/entrenador/temporal)

MAX_STEPS_PER_EPISODE = getattr(config, 'MAX_STEPS_PER_EPISODE', 500000)

# ==========================================
# MEMORIA BASE (WRAM banco 1, verificada en tests/test_rom_addresses.py)
# ==========================================
WRAM_BANK = 1
ADDR_MAP_GRP  = rom_catalog.RAM["wMapGroup"]
ADDR_MAP_ID   = rom_catalog.RAM["wMapNumber"]
ADDR_PLAYER_Y = rom_catalog.RAM["wYCoord"]
ADDR_PLAYER_X = rom_catalog.RAM["wXCoord"]

# ==========================================
# ESTADO DEL JUEGO / COMBATE
# ==========================================
ADDR_BATTLE_MODE = rom_catalog.RAM["wBattleMode"]  # 0 = Mapa, 1 = Salvaje, 2 = Entrenador
ADDR_PARTY_COUNT = rom_catalog.RAM["wPartyCount"]
ADDR_SCRIPT_RUNNING = rom_catalog.RAM["wScriptRunning"]  # != 0 durante escenas y diálogos

# ==========================================
# RANGO FLAGS
# ==========================================
FLAG_START = rom_catalog.RAM["wEventFlags"]
FLAG_END   = FLAG_START + 255

# ==========================================
# HITOS DEL SPEEDRUN (event flags de pret, en orden aproximado de la ruta)
# ==========================================
FLAGS = {name: rom_catalog.EVENT_FLAGS[name] for name in [
    "EVENT_GOT_A_POKEMON_FROM_ELM",
    "EVENT_GOT_MYSTERY_EGG_FROM_MR_POKEMON",
    "EVENT_GAVE_MYSTERY_EGG_TO_ELM",
    "EVENT_BEAT_FALKNER",
    "EVENT_CLEARED_SLOWPOKE_WELL",
    "EVENT_BEAT_BUGSY",
    "EVENT_GOT_HM01_CUT",
    "EVENT_BEAT_WHITNEY",
    "EVENT_GOT_SQUIRTBOTTLE",
    "EVENT_FOUGHT_SUDOWOODO",
    "EVENT_BEAT_MORTY",
    "EVENT_GOT_HM03_SURF",
    "EVENT_BEAT_CHUCK",
    "EVENT_GOT_HM02_FLY",
    "EVENT_GOT_SECRETPOTION_FROM_PHARMACY",
    "EVENT_BEAT_JASMINE",
    "EVENT_DECIDED_TO_HELP_LANCE",
    "EVENT_CLEARED_ROCKET_HIDEOUT",
    "EVENT_BEAT_PRYCE",
    "EVENT_CLEARED_RADIO_TOWER",
    "EVENT_BEAT_CLAIR",
    "EVENT_GOT_HM06_WHIRLPOOL",
    "EVENT_GOT_HM04_STRENGTH",
    "EVENT_GOT_HM07_WATERFALL",
    "EVENT_BEAT_ELITE_4_WILL",
    "EVENT_BEAT_ELITE_4_KOGA",
    "EVENT_BEAT_ELITE_4_BRUNO",
    "EVENT_BEAT_ELITE_4_KAREN",
    "EVENT_BEAT_CHAMPION_LANCE",
    "EVENT_BEAT_ELITE_FOUR",
]}

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
# MEMORIA COMBATE: POKÉMON RIVAL (wEnemyMon)
# ==========================================
ADDR_RIVAL_NIVEL      = 0xD0FC
ADDR_RIVAL_TIPO1      = 0xD10D
ADDR_RIVAL_TIPO2      = 0xD10E
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
# Constantes de pret (p. ej. ROUTE_29, PLAYERS_HOUSE_1F), indexadas por (grupo, número)
MAP_NAMES = dict(rom_catalog.MAPS)


# ==========================================
# 📊 TABLA DE TIPOS - POKÉMON GEN 2 (Oro/Plata)
# ==========================================
# 0: Normal, 1: Lucha, 2: Volador, 3: Veneno, 4: Tierra, 5: Roca, 7: Bicho, 8: Fantasma, 9: Acero
# 20: Fuego, 21: Agua, 22: Planta, 23: Eléctrico, 24: Psíquico, 25: Hielo, 26: Dragón, 27: Siniestro

TABLA_TIPOS = {
    # ATACANTE: { DEFENSOR: MULTIPLICADOR }
    0:  {5: 0.5, 9: 0.5, 8: 0.0},                              # Normal
    1:  {0: 2.0, 5: 2.0, 9: 2.0, 25: 2.0, 27: 2.0, 2: 0.5, 3: 0.5, 7: 0.5, 24: 0.5, 8: 0.0}, # Lucha
    2:  {1: 2.0, 7: 2.0, 22: 2.0, 5: 0.5, 9: 0.5, 23: 0.5},   # Volador
    3:  {22: 2.0, 3: 0.5, 4: 0.5, 5: 0.5, 8: 0.5, 9: 0.0},     # Veneno
    4:  {3: 2.0, 5: 2.0, 20: 2.0, 23: 2.0, 9: 2.0, 7: 0.5, 22: 0.5, 2: 0.0}, # Tierra
    5:  {2: 2.0, 7: 2.0, 20: 2.0, 25: 2.0, 1: 0.5, 4: 0.5, 9: 0.5}, # Roca
    7:  {22: 2.0, 24: 2.0, 27: 2.0, 1: 0.5, 2: 0.5, 3: 0.5, 20: 0.5, 8: 0.5, 9: 0.5}, # Bicho
    8:  {8: 2.0, 24: 2.0, 27: 0.5, 9: 0.5, 0: 0.0},           # Fantasma
    9:  {5: 2.0, 25: 2.0, 20: 0.5, 21: 0.5, 23: 0.5, 9: 0.5}, # Acero
    20: {7: 2.0, 9: 2.0, 22: 2.0, 25: 2.0, 5: 0.5, 20: 0.5, 21: 0.5, 26: 0.5}, # Fuego
    21: {4: 2.0, 5: 2.0, 20: 2.0, 21: 0.5, 22: 0.5, 26: 0.5}, # Agua
    22: {4: 2.0, 5: 2.0, 21: 2.0, 2: 0.5, 3: 0.5, 7: 0.5, 9: 0.5, 20: 0.5, 22: 0.5, 26: 0.5}, # Planta
    23: {2: 2.0, 21: 2.0, 22: 0.5, 23: 0.5, 26: 0.5, 4: 0.0}, # Eléctrico
    24: {1: 2.0, 3: 2.0, 9: 0.5, 24: 0.5, 27: 0.0},           # Psíquico
    25: {2: 2.0, 4: 2.0, 22: 2.0, 26: 2.0, 9: 0.5, 20: 0.5, 21: 0.5, 25: 0.5}, # Hielo
    26: {26: 2.0, 9: 0.5},                                     # Dragón
    27: {8: 2.0, 24: 2.0, 1: 0.5, 27: 0.5}                    # Siniestro
}

# Diccionario para que los prints queden bonitos en el log
NOMBRES_TIPOS = {
    0: "Normal", 1: "Lucha", 2: "Volador", 3: "Veneno", 4: "Tierra", 5: "Roca", 
    7: "Bicho", 8: "Fantasma", 9: "Acero", 20: "Fuego", 21: "Agua", 22: "Planta", 
    23: "Eléctrico", 24: "Psíquico", 25: "Hielo", 26: "Dragón", 27: "Siniestro"
}


class GestorCombate:
    def __init__(self, pyboy_instance):
        self.pb = pyboy_instance
        
    def leer_stat_2bytes(self, direccion):
        """Lee valores de 2 bytes (Big Endian) como Vida, Ataque, etc."""
        high = self.pb.memory[WRAM_BANK, direccion]
        low = self.pb.memory[WRAM_BANK, direccion + 1]
        return (high << 8) + low

    def leer_vida_enemigo(self):
        return self.leer_stat_2bytes(ADDR_RIVAL_HP_ACTUAL)

    def leer_tipos_enemigo_nombres(self):
        tipo1 = self.pb.memory[WRAM_BANK, ADDR_RIVAL_TIPO1]
        tipo2 = self.pb.memory[WRAM_BANK, ADDR_RIVAL_TIPO2]
        t1_nombre = NOMBRES_TIPOS.get(tipo1, "Desconocido")
        t2_nombre = NOMBRES_TIPOS.get(tipo2, "Desconocido")
        return [t1_nombre] if tipo1 == tipo2 else [t1_nombre, t2_nombre]

    def leer_ataques_lider(self):
        ataques = []
        slots = [ADDR_LIDER_ATK1, ADDR_LIDER_ATK2, ADDR_LIDER_ATK3, ADDR_LIDER_ATK4]
        for i, addr in enumerate(slots):
            atk_id = self.pb.memory[WRAM_BANK, addr]
            if atk_id != 0 and atk_id in MOVES_DB:
                nombre, tipo, _, _, _ = MOVES_DB[atk_id]
                ataques.append((i + 1, atk_id, nombre, tipo))
        return ataques

    def imprimir_auditoria(self, tipo_combate_id):
        # 1. Recopilar datos del LÍDER
        esp_id = self.pb.memory[WRAM_BANK, ADDR_LIDER_ESPECIE]
        lvl_lider = self.pb.memory[WRAM_BANK, ADDR_LIDER_NIVEL]
        hp_act = self.leer_stat_2bytes(ADDR_LIDER_HP_ACTUAL)
        hp_max = self.leer_stat_2bytes(ADDR_LIDER_HP_MAX)
        atk_l = self.leer_stat_2bytes(ADDR_LIDER_ATQ)
        def_l = self.leer_stat_2bytes(ADDR_LIDER_DEF)
        vel_l = self.leer_stat_2bytes(ADDR_LIDER_VEL)
        spa_l = self.leer_stat_2bytes(ADDR_LIDER_SP_ATQ)
        spd_l = self.leer_stat_2bytes(ADDR_LIDER_SP_DEF)

        tipos_lider = POKEDEX_TIPOS.get(esp_id, ("Desconocido", "Desconocido"))
        str_tipos_lider = f"[{tipos_lider[0]}]" if tipos_lider[0] == tipos_lider[1] else f"[{tipos_lider[0]}] [{tipos_lider[1]}]"
        
        ataques_str = ""
        for atk in self.leer_ataques_lider():
            ataques_str += f"\n   🎒 Slot {atk[0]}: ID [{atk[1]}] {atk[2]} (Tipo: {atk[3]})"

        # 2. Recopilar datos del RIVAL
        lvl_rival = self.pb.memory[WRAM_BANK, ADDR_RIVAL_NIVEL]
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