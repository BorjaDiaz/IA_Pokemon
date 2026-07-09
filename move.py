import time
import os
import keyboard
from pyboy import PyBoy

import src.utils.config as config
from src.utils.constantes import *
from auto_mapeado import guardar_evento, guardar_mapa

# ==========================================
# PREPARACIÓN FLAGS
# ==========================================
FLAGS_LOOKUP = {(addr, bit): name for name, (addr, bit) in FLAGS.items()}

def contar_bits_encendidos(memoria_rango):
    """Cuenta cuántos bits están a 1 en un bloque de memoria."""
    return sum(byte.bit_count() for byte in memoria_rango)

# 🏥 NUEVA FUNCIÓN: Suma la vida de todos los Pokémon del equipo
# 🏥 FUNCIÓN ACTUALIZADA: Suma la vida de todos los Pokémon del equipo
def leer_vida_total_equipo(pb):
    hp_total = 0
    
    # En tu versión, el contador de Pokémon está aquí
    party_count = pb.memory[0xDA22] 
    
    # Seguro por si lee basura de la memoria
    if party_count > 6 or party_count == 0:
        return 0
        
    for i in range(party_count):
        # Tu dirección base descubierta + 48 bytes (0x30) por cada Pokémon extra
        base = 0xDA2A + (i * 0x30)
        
        # La vida está a 34 bytes (0x22) de la base
        hp_actual = (pb.memory[base + 0x22] << 8) + pb.memory[base + 0x23]
        hp_total += hp_actual

    return hp_total

# 📈 FUNCIÓN ACTUALIZADA: Suma los niveles de todos los Pokémon del equipo
def leer_nivel_total_equipo(pb):
    nivel_total = 0
    
    party_count = pb.memory[0xDA22]

    if party_count > 6 or party_count == 0:
        return 0

    for i in range(party_count):
        # La base + el salto de cada Pokémon
        base = 0xDA2A + (i * 0x30)
        
        # El nivel está a 31 bytes (0x1F) de la base
        nivel_actual = pb.memory[base + 0x1F]
        
        if 1 <= nivel_actual <= 100:
            nivel_total += nivel_actual

    return nivel_total

def main():
    pb = PyBoy(config.ROM_PATH, window="SDL2")
    pb.tick()

    # ==========================================
    # Cargar estado
    # ==========================================
    if os.path.exists(config.STATE_PATH):
        print(f"💾 Cargando state: {config.STATE_PATH}")
        with open(config.STATE_PATH, "rb") as f:
            pb.load_state(f)
    else:
        print("🆕 Iniciando desde ROM")

    print("🧠 Detector AUTO-LEARNING activo")

    last_pos = (-1, -1)
    last_map = (-1, -1)

    ultimo_tipo_combate = -1        
    
    pb.memory[0xFF70] = 1

    flags_mem_prev = bytes(pb.memory[FLAG_START:FLAG_END+1])
    total_flags_previo = contar_bits_encendidos(flags_mem_prev)

    print(f"📊 Flags iniciales: {total_flags_previo}")
    print(f"📦 Flags conocidos registrados: {len(FLAGS)}")

    # Variables persistentes para detectar cambios en el equipo
    nivel_lider_previo = 0
    nivel_total_previo = leer_nivel_total_equipo(pb)

    try:
        while True:
            pb.tick()

            # ==========================================
            # POSICIÓN Y MAPA
            # ==========================================
            x = pb.memory[ADDR_PLAYER_X]
            y = pb.memory[ADDR_PLAYER_Y]
            grp = pb.memory[ADDR_MAP_GRP]
            mid = pb.memory[ADDR_MAP_ID]

            if (grp, mid) != last_map:
                nombre_mapa = MAP_NAMES.get((grp, mid), "Mapa desconocido")
                print(f"\n🗺️ {nombre_mapa} ({grp},{mid})")
                guardar_mapa(grp, mid, x, y)
                last_map = (grp, mid)

            if (x, y) != last_pos:
                print(f"📍 X:{x} Y:{y}")
                last_pos = (x, y)

            # ==========================================
            # PROGRESO DE LA HISTORIA Y EVENTOS
            # ==========================================
            pb.memory[0xFF70] = 1 
            flags_mem_now = bytes(pb.memory[FLAG_START:FLAG_END+1])
            total_flags_actual = contar_bits_encendidos(flags_mem_now)

            if total_flags_actual > total_flags_previo:
                dif = total_flags_actual - total_flags_previo
                print(f"\n🏆 PROGRESO +{dif} (Total: {total_flags_actual})")

                for i in range(len(flags_mem_prev)):
                    diff = flags_mem_prev[i] ^ flags_mem_now[i]
                    if diff != 0:
                        for bit in range(8):
                            if (diff & (1 << bit)) and ((flags_mem_now[i] >> bit) & 1):
                                addr = FLAG_START + i
                                if addr == 0xD7B7:
                                    continue

                                dir_hex = f"0x{addr:04X}"
                                
                                if (addr, bit) in FLAGS_LOOKUP:
                                    nombre = FLAGS_LOOKUP[(addr, bit)]
                                    print(f"🚩 EVENTO: {nombre.upper()} [RAM: {dir_hex} | Bit: {bit}]")
                                else:
                                    print(f"❓ EVENTO DESCONOCIDO [RAM: {dir_hex} | Bit: {bit}]")
                                    print(f"   📍 Contexto: X={x} Y={y} | mapa={grp},{mid}")
                                    guardar_evento(addr, bit, x, y, grp, mid)

                total_flags_previo = total_flags_actual

            elif total_flags_actual < total_flags_previo:
                total_flags_previo = total_flags_actual

            flags_mem_prev = flags_mem_now

            # ==========================================
            # 📈 TRACKING DE COMBATE
            # ==========================================
            tipo_combate = pb.memory[ADDR_BATTLE_TYPE]

            if tipo_combate != ultimo_tipo_combate:
                if tipo_combate == 0:
                    print("🌍 FUERA DE COMBATE. Explorando el mapa...")
                elif tipo_combate in [1, 2]:
                    print(f"\n⚔️ ¡ENTRANDO EN COMBATE! 👉 Tipo: Entrenador (ID RAM: {tipo_combate})")
                elif tipo_combate > 0:
                    print(f"\n⚔️ ¡ENTRANDO EN COMBATE! 👉 Tipo: Pokémon Salvaje (ID RAM: {tipo_combate})")
                    
                ultimo_tipo_combate = tipo_combate

            # ==========================================
            # 📈 TRACKING DE SUBIDA DE NIVEL (Líder y Equipo)
            # ==========================================
            nivel_actual = pb.memory[ADDR_LIDER_NIVEL]
            
            if nivel_lider_previo == 0 and nivel_actual > 0:
                nivel_lider_previo = nivel_actual
                
            elif nivel_actual > nivel_lider_previo:
                print(f"\n🌟 ¡LEVEL UP DETECTADO! Tu Pokémon ha subido al Nivel {nivel_actual} 🌟")
                nivel_lider_previo = nivel_actual

            # Alerta rápida por consola si el nivel del equipo sube (por combate o captura)
            nivel_equipo_actual = leer_nivel_total_equipo(pb)
            if nivel_equipo_actual > nivel_total_previo:
                subida = nivel_equipo_actual - nivel_total_previo
                print(f"🔰 ¡El nivel total del equipo ha subido +{subida}! (Nuevo Total: {nivel_equipo_actual})")
                nivel_total_previo = nivel_equipo_actual
            elif nivel_equipo_actual < nivel_total_previo:
                # Esto pasaría si dejas un Pokémon en la guardería o PC
                nivel_total_previo = nivel_equipo_actual

            # ==========================================
            # 🕵️‍♂️ DETECTIVE DE RAM (Stats Limpios y Tipos)
            # ==========================================
            if keyboard.is_pressed("v"):
                time.sleep(0.3) 
                
                # --- DATOS JUGADOR (LÍDER) ---
                especie_id = pb.memory[ADDR_LIDER_ESPECIE]
                hp_actual = (pb.memory[ADDR_LIDER_HP_ACTUAL] << 8) + pb.memory[ADDR_LIDER_HP_ACTUAL + 1]
                hp_maximo = (pb.memory[ADDR_LIDER_HP_MAX] << 8) + pb.memory[ADDR_LIDER_HP_MAX + 1] 
                
                atk1 = pb.memory[ADDR_LIDER_ATK1]
                atk2 = pb.memory[ADDR_LIDER_ATK2]
                
                stat_ataque = (pb.memory[ADDR_LIDER_ATQ] << 8) + pb.memory[ADDR_LIDER_ATQ + 1]
                stat_defensa = (pb.memory[ADDR_LIDER_DEF] << 8) + pb.memory[ADDR_LIDER_DEF + 1]
                stat_velocidad = (pb.memory[ADDR_LIDER_VEL] << 8) + pb.memory[ADDR_LIDER_VEL + 1]
                stat_sp_ataque = (pb.memory[ADDR_LIDER_SP_ATQ] << 8) + pb.memory[ADDR_LIDER_SP_ATQ + 1]
                stat_sp_defensa = (pb.memory[ADDR_LIDER_SP_DEF] << 8) + pb.memory[ADDR_LIDER_SP_DEF + 1]
                
                tipos_lider = POKEDEX_TIPOS.get(especie_id, ("Desconocido", "Desconocido"))
                tipo1_lider = tipos_lider[0]
                tipo2_lider = tipos_lider[1]
                
                # --- DATOS RIVAL ---
                rival_nivel = pb.memory[ADDR_RIVAL_NIVEL]
                
                rival_hp_actual = (pb.memory[ADDR_RIVAL_HP_ACTUAL] << 8) + pb.memory[ADDR_RIVAL_HP_ACTUAL + 1]
                rival_hp_maximo = (pb.memory[ADDR_RIVAL_HP_MAX] << 8) + pb.memory[ADDR_RIVAL_HP_MAX + 1]
                
                
                rival_ataque = (pb.memory[ADDR_RIVAL_ATQ] << 8) + pb.memory[ADDR_RIVAL_ATQ + 1]
                rival_defensa = (pb.memory[ADDR_RIVAL_DEF] << 8) + pb.memory[ADDR_RIVAL_DEF + 1]
                rival_velocidad = (pb.memory[ADDR_RIVAL_VEL] << 8) + pb.memory[ADDR_RIVAL_VEL + 1]
                rival_sp_ataque = (pb.memory[ADDR_RIVAL_SP_ATQ] << 8) + pb.memory[ADDR_RIVAL_SP_ATQ + 1]
                rival_sp_defensa = (pb.memory[ADDR_RIVAL_SP_DEF] << 8) + pb.memory[ADDR_RIVAL_SP_DEF + 1]
                
                tipo_atk1 = "Normal" if atk1 in [33, 43] else "???"
                tipo_atk2 = "Normal" if atk2 in [33, 43] else "???"
                
                # --- NUEVOS DATOS DEL GRUPO ---
                vida_total_team = leer_vida_total_equipo(pb)
                nivel_total_team = leer_nivel_total_equipo(pb)
                
                print("\n--- 🧠 AUDITORÍA DE RAM COMPLETA ---")
                
                # 👥 Bloque de Equipo añadido aquí arriba
                print(f"👥 ESTADO DEL GRUPO:")
                print(f"   ❤️ Vida Total del Equipo: {vida_total_team} HP")
                print(f"   📈 Nivel Total del Equipo: {nivel_total_team}")
                print("-------------------------------------------")
                
                print(f"🧑‍🚀 TU POKÉMON LÍDER (Especie ID: {especie_id}):")
                print(f"   ❤️ Vida: {hp_actual} / {hp_maximo} HP | 📈 Nivel: {nivel_actual}")
                print(f"   🎭 Tipos: [{tipo1_lider}] [{tipo2_lider}]")
                print(f"   ⚔️ Stats -> Atk: {stat_ataque} | Def: {stat_defensa} | Vel: {stat_velocidad}")
                print(f"   🌀 Stats Esp -> Atk.Esp: {stat_sp_ataque} | Def.Esp: {stat_sp_defensa}")
                print(f"   🎒 Ataques -> Slot 1: ID [{atk1}] (Tipo: {tipo_atk1})")
                print(f"                 Slot 2: ID [{atk2}] (Tipo: {tipo_atk2})")
                print("-------------------------------------------")
                print(f"👹 POKÉMON RIVAL:")
                print(f"   ❤️ Vida: {rival_hp_actual} / {rival_hp_maximo} HP | 📈 Nivel: {rival_nivel}")
                print(f"   ⚔️ Stats -> Atk: {rival_ataque} | Def: {rival_defensa} | Vel: {rival_velocidad}")
                print(f"   🌀 Stats Esp -> Atk.Esp: {rival_sp_ataque} | Def.Esp: {rival_sp_defensa}")
                print("-------------------------------------------\n")

            # ==========================================
            # QUICK SAVE PERSONALIZADO (F5)
            # ==========================================
            if keyboard.is_pressed("f5"):
                time.sleep(0.3) 
                print("\n⏸️ [PAUSA] Guardado de Estado iniciado.")
                nombre_state = input("👉 Escribe un nombre para el state (ej. antes_del_lider): ")
                
                if nombre_state.strip():
                    ruta_guardado = os.path.join(config.STATES_DIR, f"{nombre_state}.state")
                    with open(ruta_guardado, "wb") as f:
                        pb.save_state(f)
                    print(f"💾 ¡Guardado con éxito en: {ruta_guardado}!\n")
                else:
                    print("❌ Guardado cancelado (no pusiste nombre).\n")

            # ==========================================
            # SALIR (Esc)
            # ==========================================
            if keyboard.is_pressed("esc"):
                print("🛑 Salida")
                break

            time.sleep(0.01)

    finally:
        pb.stop()
        print("✅ Emulador cerrado")

if __name__ == "__main__":
    main()