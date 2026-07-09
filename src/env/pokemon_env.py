import gymnasium as gym
import numpy as np
import os
import glob
from gymnasium import spaces
from pyboy import PyBoy
from pyboy.utils import WindowEvent

import src.utils.config as config
import src.utils.constantes as c
from src.utils.logger import Logger
from src.env.core.extractor_ram import RamExtractor
from src.env.handlers.reward_system import RewardSystem

from src.env.handlers.combat import CombatHandler
from src.env.handlers.movement import MovementHandler
from src.env.handlers.story import StoryHandler

class PokemonGoldEnv(gym.Env):
    def __init__(self, rank=0):
        super().__init__()
        self.rank = rank
        self.total_speedrun_reward = 0.0
        self.ultimo_tipo_combate = 0

        # 🧠 Memoria persistente del entorno speedrun
        self.last_speedrun_pos = (-1, -1)
        self.last_speedrun_map = (-1, -1)
        self.speedrun_visited_maps = set()
        self.speedrun_visited_tiles = set()

        # Trackeo de salud y niveles del equipo durante la partida
        self.vida_equipo_anterior = 999
        self.nivel_total_previo = 0

        # Inicialización del emulador
        window_type = "null" if config.SPEEDRUN_MODE else "SDL2"
        self.pb = PyBoy(config.ROM_PATH, window=window_type)
        self.pb.set_emulation_speed(0 if config.SPEEDRUN_MODE else 1)
        
        # 🔌 Conexión de módulos base
        self.ram = RamExtractor(self.pb)
        self.rewards = RewardSystem(rank=self.rank)
        self.gestor = c.GestorCombate(self.pb)
        self.logger = Logger(rank, config.LOG_DIR) if config.ENABLE_LOGS else None

        # 🔌 Instanciación de los Handlers delegados
        self.h_combat = CombatHandler(self.rank, self.logger)
        self.h_movement = MovementHandler(self.rank)
        self.h_story = StoryHandler(self.rank, self.logger)

        # Configuración de acciones y espacios de Gym
        self.actions = [
            (WindowEvent.PRESS_ARROW_UP, WindowEvent.RELEASE_ARROW_UP),
            (WindowEvent.PRESS_ARROW_DOWN, WindowEvent.RELEASE_ARROW_DOWN),
            (WindowEvent.PRESS_ARROW_LEFT, WindowEvent.RELEASE_ARROW_LEFT),
            (WindowEvent.PRESS_ARROW_RIGHT, WindowEvent.RELEASE_ARROW_RIGHT),
            (WindowEvent.PRESS_BUTTON_A, WindowEvent.RELEASE_BUTTON_A),
            (WindowEvent.PRESS_BUTTON_B, WindowEvent.RELEASE_BUTTON_B),
        ]
        self.action_space = spaces.Discrete(len(self.actions))
        self.observation_space = spaces.Box(low=0, high=255, shape=(3, 144, 160), dtype=np.uint8)
        
        # Mapeo invertido de flags para saber qué evento ocurrió
        self.tuplas_historia = {(int(v[0]), v[1]): k for k, v in c.FLAGS.items()}

    def reset(self, seed=None, options=None):
        # Limpiar coordenadas previas en el clon 0
        if self.rank == 0 and os.path.exists("coordinates"):
            for archivo in glob.glob("coordinates/*"):
                os.remove(archivo)
            
        # Sistema de Curriculum Learning (Cargar partida avanzada)
        if config.USE_CURRICULUM:
            path = os.path.join(config.STATES_DIR, config.CURRICULUM_STATES[config.CURRENT_STAGE])
            if os.path.exists(path):
                with open(path, "rb") as f: self.pb.load_state(f)

        if hasattr(self, 'steps_count') and self.steps_count > 0:
            print(f"🏁 [Clon {self.rank}] FIN DEL EPISODIO | Pasos: {self.steps_count} | Puntuación Speedrun Final: {round(self.total_speedrun_reward, 2)}")

        # Reseteo de variables de control del speedrun
        self.steps_count = 0
        self.total_speedrun_reward = 0.0
        self.last_speedrun_pos, self.last_speedrun_map = (-1, -1), (-1, -1)
        
        self.vida_equipo_anterior = self.ram.leer_vida_total_equipo()
        self.nivel_total_previo = self.ram.leer_nivel_total_equipo()
        self.active_flags = self.ram.get_all_flags()
        
        # Resetear también las vidas que guardan los handlers internamente
        self.h_combat.vida_enemigo_anterior = 999
        self.h_movement.steps_estancado = 0
        
        return self._get_obs(), {}

    def step(self, action):
        if not self.pb.tick():
            print(f"\n🛑 [Clon {self.rank}] Ventana cerrada o Esc pulsado. Deteniendo...")
            raise KeyboardInterrupt

        # 🎮 Ejecutar acción en el emulador
        p, r = self.actions[action]
        self.pb.send_input(p)
        for _ in range(7): 
            if not self.pb.tick(): raise KeyboardInterrupt
        
        self.pb.send_input(r)
        for _ in range(4): 
            if not self.pb.tick(): raise KeyboardInterrupt

        self.steps_count += 1
        reward = c.REWARD_STEP

        # 📍 Leer coordenadas y mapa actuales del speedrun
        x, y = self.pb.memory[c.ADDR_PLAYER_X], self.pb.memory[c.ADDR_PLAYER_Y]
        grp, mid = self.pb.memory[c.ADDR_MAP_GRP], self.pb.memory[c.ADDR_MAP_ID]
        current_speedrun_tile, current_speedrun_map = (grp, mid, x, y), (grp, mid)
        map_name = c.MAP_NAMES.get(current_speedrun_map, f"Mapa {grp}-{mid}")

        # Guardar coordenadas cada 5 pasos para el mapa de calor
        if self.steps_count % 5 == 0:
            os.makedirs("coordinates", exist_ok=True)
            with open(f"coordinates/coords_clon_{self.rank}.txt", "a") as f:
                f.write(f"{x},{y},{grp},{mid}\n")

        # --- 💥 BLOQUE MOVIDO AQUÍ PARA QUE EXISTA 'en_combate' ---
        tipo_combate = self.pb.memory[c.ADDR_BATTLE_TYPE]
        en_combate = tipo_combate > 0
        vida_actual_equipo = self.ram.leer_vida_total_equipo()

        # 🗺️ 1. GESTIÓN DE MOVIMIENTO Y ATASCOS (Delegado)
        # Ahora que 'en_combate' ya está definido arriba, funciona perfecto
        r_mov, done_atasco = self.h_movement.procesar(x, y, self.last_speedrun_pos, current_speedrun_tile, self.speedrun_visited_tiles, map_name, en_combate)
        reward += r_mov
        if done_atasco:
            return self._get_obs(), -1.0, False, True, {} # Termina el episodio por atasco
        
        # Pequeño control visual aquí en el orquestador al entrar/salir de combate
        if tipo_combate != self.ultimo_tipo_combate:
            if not en_combate:
                print(f"🌍 [Clon {self.rank}] FUERA DE COMBATE. Explorando el mapa...")
                if self.logger: 
                    self.logger.log_step({"evento": "FIN_COMBATE", "mapa": map_name, "step": self.steps_count})
            else:
                self.gestor.imprimir_auditoria(tipo_combate)
                if self.logger:
                    tipo_str = "Entrenador" if tipo_combate in [1, 2] else "Salvaje"
                    self.logger.log_step({"evento": "INICIO_COMBATE", "tipo": tipo_str, "mapa": map_name, "step": self.steps_count})
            
            self.ultimo_tipo_combate = tipo_combate

        # ⚔️ 2. GESTIÓN DE COMBATE (Delegado)
        r_comb, _ = self.h_combat.procesar(
            self.pb, self.ram, self.rewards, self.gestor, 
            en_combate, vida_actual_equipo, self.vida_equipo_anterior, 
            self.steps_count, map_name
        )
        reward += r_comb

        # 🏥 Curación y niveles (Se quedan aquí porque no requieren un archivo entero)
        if not en_combate and vida_actual_equipo > self.vida_equipo_anterior and self.vida_equipo_anterior != 999:
            max_vida = self.ram.leer_max_vida_total_equipo()
            curacion = vida_actual_equipo - self.vida_equipo_anterior
            reward += self.rewards.calcular_premio_curacion(curacion, max_vida)
            print(f"💊 [Clon {self.rank}] ¡Curación! (+{curacion} HP).")
            
        self.vida_equipo_anterior = vida_actual_equipo

        nivel_actual_total = self.ram.leer_nivel_total_equipo()
        if self.nivel_total_previo > 0 and nivel_actual_total > self.nivel_total_previo:
            subida = nivel_actual_total - self.nivel_total_previo
            reward += c.REWARD_LEVEL_UP * subida 
            print(f"\n🌟 [Clon {self.rank}] ¡Aumento de Nivel! (+{subida} niveles) 🌟")
            self.nivel_total_previo = nivel_actual_total
        elif self.nivel_total_previo == 0 and nivel_actual_total > 0:
            self.nivel_total_previo = nivel_actual_total

        # 🌍 3. GESTIÓN DE MAPAS Y FLAGS DE HISTORIA (Delegado)
        if current_speedrun_map not in self.speedrun_visited_maps:
            self.speedrun_visited_maps.add(current_speedrun_map)
            reward += c.REWARD_NEW_MAP
            print(f"🌍 [Clon {self.rank}] ¡Mapa descubierto! -> {map_name}")
            if self.logger: self.logger.log_step({"evento": "NUEVO_MAPA", "mapa": map_name, "step": self.steps_count})

        reward += self.h_story.procesar(self.pb, self.ram, self.rewards, self.active_flags, self.tuplas_historia, self.steps_count)

        # 💀 CONDICIÓN DE MUERTE (Cortes de Episodio)
        party_count = self.pb.memory[0xDA22]
        if vida_actual_equipo <= 0 and party_count > 0:
            print(f"💀 [Clon {self.rank}] ¡Equipo debilitado! Reiniciando...")
            if self.logger: self.logger.log_step({"evento": "EQUIPO_DEBILITADO", "mapa": map_name, "step": self.steps_count})
            return self._get_obs(), (reward + c.PENALTY_TEAM_FAINTED) / 10.0, False, True, {}

        # Guardar estado para el siguiente step
        self.last_speedrun_pos, self.last_speedrun_map = (x, y), current_speedrun_map
        self.total_speedrun_reward += reward

        # Normalizamos la recompensa para Stable Baselines
        return self._get_obs(), reward / 10.0, False, self.steps_count >= config.MAX_STEPS_PER_EPISODE, {}

    def _get_obs(self):
        img = self.pb.screen.ndarray
        return np.transpose(img[:,:,:3], (2, 0, 1))

    def close(self):
        self.pb.stop()