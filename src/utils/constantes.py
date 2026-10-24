import src.utils.config as config
from src.utils import rom_catalog


# ==========================================
# 🏆 SISTEMA DE RECOMPENSAS Y PENALIZACIONES
# ==========================================

# Valores antes de dividir entre 10 en PokemonGoldEnv.step

# Exploración (baldosas y mapas cuentan una vez por episodio)
REWARD_STEP = -0.005                 # Penalización por cada paso (para incentivar rapidez)
REWARD_NEW_TILE = 0.05              # Por pisar una baldosa nueva
REWARD_NEW_MAP = 1.0               # Por entrar a una zona/mapa nuevo (con 5.0 se desviaba a las casas
                                    # del pueblo: cada una valía tanto como 100 casillas nuevas)
PENALTY_SAME_TILE = -0.005          # Por quedarse en la misma baldosa fuera de combate y escenas
PENALTY_REVISIT_TILE = -0.001       # Por volver a una baldosa ya pisada
PENALTY_NO_PROGRESS = -10.0         # Al cortar el episodio por no avanzar

# Supervivencia: daño y curación proporcionales a la fracción de PS del equipo. Curarse da algo menos
# de lo que quita el daño (no compensa hacerse daño para curarse), pero con la vida baja ir al Centro
# Pokémon vale la pena, y quedarse sin Pokémon corta el episodio
PENALTY_DAMAGE_FRAC = -5.0          # Por perder el 100% de los PS del equipo (proporcional)
REWARD_HEAL_FRAC = 4.0              # Por recuperar el 100% de los PS del equipo (proporcional)
# Equipo debilitado: fin del episodio. Con -15, combatir sin curarse hasta caer salía a cuenta (5 victorias
# ≈ +3,0, daño -0,5, caer -1,5: +1,0) y de vuelta con el huevo caía en la Ruta 30 en vez de ir a curarse
PENALTY_TEAM_FAINTED = -60.0

# Nivel objetivo por tramo: subir de nivel y ganar combates se premia mientras el Pokémon más fuerte
# esté por debajo del nivel adecuado para el siguiente reto; por encima, ya no (nada de farmear sin fin).
# El objetivo de cada fila vale hasta conseguir su hito.
NIVELES_OBJETIVO = [
    ("RIVAL_CHERRYGROVE_SUPERADO", 8),   # rival con su inicial a nivel 5
    ("EVENT_BEAT_FALKNER", 12),          # Pidgeotto nv. 9
    ("EVENT_BEAT_BUGSY", 17),            # Scyther nv. 16
    ("EVENT_BEAT_WHITNEY", 21),          # Miltank nv. 19
    ("EVENT_BEAT_MORTY", 26),            # Gengar nv. 25
]
REWARD_LEVEL_UP = 15.0              # Por cada nivel ganado por debajo del objetivo
# K.O. a un rival. Un combate salvaje dura ~130 pasos (casi todo pasar textos): con una penalización
# extra por paso en combate, ganarlo salía en -0,17 y el agente aprendió a huir siempre (0 de 4.299).
# Ahora, por debajo del objetivo ganar vale ~+0,5 y por encima lo mejor sigue siendo huir.
REWARD_KO_BAJO_OBJETIVO = 6.0
REWARD_KO_SOBRE_OBJETIVO = 0.5
# Huir de un salvaje se penaliza solo si hacía falta entrenar y el combate era razonable: el Pokémon
# propio está por debajo del nivel objetivo, el salvaje no es de mayor nivel y el equipo tiene más del
# 50% de PS. Si no, huir es gratis (de uno más fuerte, con la vida baja o con nivel suficiente).
# Tras ~10 M de pasos huyendo de todo (6.592 de 6.592), sin esto nunca probaba a luchar.
PENALTY_HUIR_BAJO_OBJETIVO = -3.0
VIDA_MIN_PARA_LUCHAR = 0.5
REWARD_DAMAGE_MULT = 0.05           # Por cada PS de daño causado (por encima del objetivo)
# Por debajo del objetivo, cada golpe vale su fracción de los PS máximos del rival: quitárselos todos
# suma 3,0 además del K.O. Al azar se dan ~0,9 golpes por combate pero casi nunca se gana (0 de 47 en
# el emulador): sin premio por golpe no había ninguna señal de que atacar era lo bueno.
REWARD_DAMAGE_FRAC_BAJO_OBJETIVO = 3.0

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
ADDR_GAME_TIME_HOURS = rom_catalog.RAM["wGameTimeHours"]
ADDR_GAME_TIME_MINUTES = rom_catalog.RAM["wGameTimeMinutes"]
ADDR_GAME_TIME_SECONDS = rom_catalog.RAM["wGameTimeSeconds"]
ADDR_GAME_TIME_FRAMES = rom_catalog.RAM["wGameTimeFrames"]

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

# Hitos intermedios de ruta: primera llegada del episodio a mapas clave entre dos hitos de historia
# (entre el primer Pokémon y el Huevo Misterioso no hay ningún evento que guíe al agente).
# Cuentan como hitos: premio, savestate de récord y salidas mezcladas.
# Cada hito de mapa puede exigir un evento ya activo (requisito). Así se guía también la VUELTA a Elm
# con el huevo (por mapas ya visitados, que no dan recompensa de exploración) y los hitos hacia Malva
# no cuentan antes de entregar el huevo (no compensa saltarse la vuelta).
_MAPA_POR_NOMBRE = {nombre: clave for clave, nombre in rom_catalog.MAPS.items()}
_HUEVO, _HUEVO_ENTREGADO = "EVENT_GOT_MYSTERY_EGG_FROM_MR_POKEMON", "EVENT_GAVE_MYSTERY_EGG_TO_ELM"
# (mapa, requisito, prohibido): el hito solo cuenta con el evento `requisito` activo y `prohibido` sin activar.
# Así la vuelta solo se premia mientras se lleva el huevo, y una vez entregado lo único que da puntos es
# avanzar hacia Malva (volver atrás ya no da nada).
HITOS_MAPA = {nombre: (_MAPA_POR_NOMBRE[mapa], requisito, prohibido) for nombre, mapa, requisito, prohibido in [
    ("LLEGADA_CHERRYGROVE_CITY", "CHERRYGROVE_CITY", None, _HUEVO),
    ("LLEGADA_ROUTE_30", "ROUTE_30", None, _HUEVO),
    ("LLEGADA_MR_POKEMONS_HOUSE", "MR_POKEMONS_HOUSE", None, _HUEVO),
    ("VUELTA_CHERRYGROVE_CITY", "CHERRYGROVE_CITY", _HUEVO, _HUEVO_ENTREGADO),
    ("VUELTA_ROUTE_29", "ROUTE_29", _HUEVO, _HUEVO_ENTREGADO),
    ("VUELTA_NEW_BARK_TOWN", "NEW_BARK_TOWN", _HUEVO, _HUEVO_ENTREGADO),
    ("VUELTA_ELMS_LAB", "ELMS_LAB", _HUEVO, _HUEVO_ENTREGADO),
    ("LLEGADA_ROUTE_31", "ROUTE_31", _HUEVO_ENTREGADO, None),
    ("LLEGADA_VIOLET_CITY", "VIOLET_CITY", _HUEVO_ENTREGADO, None),
    ("LLEGADA_VIOLET_GYM", "VIOLET_GYM", _HUEVO_ENTREGADO, None),
]}

# Guía de la vuelta a Elm con el huevo: en estos mapas ya recorridos no hay recompensa de exploración y
# encontrar el camino solo por el hito de llegada no salía (0 de ~150 episodios). Llevando el huevo (y
# sin haberlo entregado), cada casilla que se acerca a la salida más que nunca en el episodio vale
# REWARD_VUELTA_AVANCE. Objetivo (x, y) de cada mapa, None = ese eje no cuenta; sacados de los cambios de
# mapa reales: la Ruta 30 sale a Cerezo por el sur (y=54), Cerezo y la Ruta 29 por el este (x=40, x=59)
# y la puerta del laboratorio de Elm está en (6, 3). Solo premia superar la mejor marca: ir y volver no paga.
VUELTA_GUIA = {_MAPA_POR_NOMBRE[mapa]: objetivo for mapa, objetivo in [
    ("ROUTE_30", (None, 54)),
    ("CHERRYGROVE_CITY", (40, None)),
    ("ROUTE_29", (59, None)),
    ("NEW_BARK_TOWN", (6, 3)),
]}
VUELTA_REQUISITO, VUELTA_PROHIBIDO = _HUEVO, _HUEVO_ENTREGADO
REWARD_VUELTA_AVANCE = 0.3   # por casilla (Ruta 30 + Cerezo + Ruta 29 + Pueblo Primavera ≈ 130 casillas ≈ +4)

# Eventos de historia menores que NO dan su pequeña recompensa: son desvíos que un speedrun no hace
# (volver a casa a hablar con mamá, objetos ocultos fuera de la ruta). Premiarlos enseñaría a volver atrás.
EVENTOS_DESVIO = {"EVENT_TALKED_TO_MOM_AFTER_MYSTERY_EGG_QUEST"}
def es_desvio(nombre_evento):
    return nombre_evento in EVENTOS_DESVIO or "_HIDDEN_" in nombre_evento
# Ganar al rival en Ciudad Cerezo, a la vuelta con el huevo (su evento de visibilidad ya está activo al
# empezar la partida, así que se detecta como "combate contra entrenador ganado en CHERRYGROVE_CITY")
HITO_RIVAL_CEREZO = "RIVAL_CHERRYGROVE_SUPERADO"

# Todos los hitos en orden de la ruta (eventos, llegadas a mapas y el rival). El orden importa: la salida
# mezclada empieza desde el más avanzado conseguido, y al empezar en un hito no cuentan los anteriores
HITOS = list(FLAGS)
def _insertar_tras(hito, nuevos):
    i = HITOS.index(hito) + 1
    HITOS[i:i] = nuevos
_insertar_tras("EVENT_GOT_A_POKEMON_FROM_ELM", ["LLEGADA_CHERRYGROVE_CITY", "LLEGADA_ROUTE_30", "LLEGADA_MR_POKEMONS_HOUSE"])
_insertar_tras(_HUEVO, ["VUELTA_CHERRYGROVE_CITY", HITO_RIVAL_CEREZO, "VUELTA_ROUTE_29", "VUELTA_NEW_BARK_TOWN", "VUELTA_ELMS_LAB"])
_insertar_tras(_HUEVO_ENTREGADO, ["LLEGADA_ROUTE_31", "LLEGADA_VIOLET_CITY", "LLEGADA_VIOLET_GYM"])

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
ADDR_RIVAL_ESPECIE    = rom_catalog.RAM["wEnemyMonSpecies"]
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

    def leer_vida_max_enemigo(self):
        return self.leer_stat_2bytes(ADDR_RIVAL_HP_MAX)

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