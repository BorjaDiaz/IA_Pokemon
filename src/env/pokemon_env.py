import gymnasium as gym
import numpy as np
import os
import glob
import json
import random
import time
from gymnasium import spaces
from pyboy import PyBoy
from pyboy.utils import WindowEvent

import src.utils.config as config
import src.utils.constantes as c
from src.utils import rom_catalog
from src.utils.logger import Logger
from src.utils.frame_capturer import FrameCapturer
from src.utils.map_atlas import MapAtlas
from src.env.core.extractor_ram import RamExtractor
from src.env.handlers.reward_system import RewardSystem

from src.env.handlers.combat import CombatHandler
from src.env.handlers.movement import MovementHandler
from src.env.handlers.story import StoryHandler, cargar_records

# Pantalla de 10 x 9 casillas de 16 px; en la observación (72 x 80) cada casilla ocupa 8 x 8 px
CASILLAS_X, CASILLAS_Y, JUGADOR_COL, JUGADOR_FILA = 10, 9, 4, 4


def nuevas_estadisticas_combate():
    """Combates de un episodio por tipo y resultado (huido incluye capturas), y cuántas huidas se
    penalizaron por huir cuando hacía falta entrenar."""
    return {"salvaje": {"ganado": 0, "huido": 0, "perdido": 0},
            "entrenador": {"ganado": 0, "huido": 0, "perdido": 0},
            "pasos_en_combate": 0, "huidas_penalizadas": 0}

class PokemonGoldEnv(gym.Env):
    simulacro = fin_simulacro = False  # episodio de simulacro de combate (ver reset)

    def __init__(self, rank=0, ventana=None, velocidad=None, salida_fija=None):
        """ventana: True para ver el juego en una ventana (por defecto, según SPEEDRUN_MODE).
        velocidad: 1 = tiempo real, 2 = el doble... 0 = sin límite (por defecto, según SPEEDRUN_MODE).
        salida_fija: savestate desde el que empiezan siempre los episodios (por defecto, salidas mezcladas).
        Se pasan como parámetros porque los clones en procesos aparte no ven los cambios hechos a config."""
        super().__init__()
        self.rank = rank
        self.ventana = (not config.SPEEDRUN_MODE) if ventana is None else ventana
        self.salida_fija = salida_fija
        self.total_speedrun_reward = 0.0
        self.ultimo_tipo_combate = 0
        self.episode_counter = 0
        # Todo lo de esta ejecución va a su carpeta (runs/<fecha_hora>/ cuando se lanza con train.py)
        self.metrics_path = os.path.join(config.RUN_DIR, "metrics.jsonl")

        # Cada clon empieza su propio archivo de coordenadas (mapa de calor) al arrancar
        coords_dir = os.path.join(config.RUN_DIR, "coordinates")
        os.makedirs(coords_dir, exist_ok=True)
        self.coords_path = os.path.join(coords_dir, f"coords_clon_{self.rank}.txt")
        open(self.coords_path, "w").close()
        # Imagen de los mapas reconstruida con lo que ve este clon (se conserva entre entrenamientos)
        self.atlas = MapAtlas(rank)

        # 🧠 Exploración: las recompensas usan los conjuntos del episodio; all_maps_seen es solo para métricas
        self.last_speedrun_pos = (-1, -1)
        self.last_speedrun_map = (-1, -1)
        self.episode_maps = set()
        self.episode_tiles = set()
        self.all_maps_seen = set()
        # ⏱️ Splits: paso del episodio en que se llega por primera vez a cada mapa o hito
        self.splits = {}
        self.combates = nuevas_estadisticas_combate()
        self.combate_actual = None
        # Generador propio para elegir la salida de cada episodio (distinto en cada clon)
        self.rng = random.Random(time.time_ns() + rank)
        self.prob_simulacro = config.PROB_SIMULACRO_COMBATE  # SimulacroCallback lo baja cuando ya gana
        self.salida = config.CURRICULUM_STATES[config.CURRENT_STAGE]
        self.mapas_previos = set()

        # Trackeo de salud y niveles del equipo durante la partida
        self.vida_equipo_anterior = 999
        self.max_vida_equipo_anterior = 0
        self.party_count_anterior = 0
        self.nivel_max_previo = 0
        # Para las barras de la observación: PS del equipo y nivel respecto al objetivo del tramo (0..1)
        self.fraccion_vida = 0.0
        self.fraccion_nivel = 0.0

        # Inicialización del emulador (sin sonido: no se usa y cuesta tiempo de CPU)
        self.pb = PyBoy(config.ROM_PATH, window="SDL2" if self.ventana else "null", sound_emulated=False)
        if velocidad is None:
            velocidad = 1 if self.ventana else 0
        self.pb.set_emulation_speed(velocidad)
        # Congela el reloj del cartucho: misma hora/día en cada episodio, episodios reproducibles
        self.pb.rtc_lock_experimental(True)

        # 🔌 Conexión de módulos base
        self.ram = RamExtractor(self.pb)
        self.rewards = RewardSystem(rank=self.rank)
        self.gestor = c.GestorCombate(self.pb)
        self.logger = Logger(rank, os.path.join(config.RUN_DIR, "logs")) if config.ENABLE_LOGS else None
        # 📸 Capturas por eventos: tira de pantallas al acabar cada episodio y una al conseguir un hito
        self.capturer = FrameCapturer(rank, output_dir=os.path.join(config.RUN_DIR, "capturas"))

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
        # Canal 0: pantalla en grises a mitad de resolución.
        # Canal 1: casillas de la pantalla ya pisadas en este episodio (255) para que el agente
        #          vea qué zonas le darán recompensa por explorar. VecFrameStack apila los últimos frames.
        self.observation_space = spaces.Box(low=0, high=255, shape=(2, 72, 80), dtype=np.uint8)

        # Mapeo invertido de flags para saber qué evento ocurrió
        self.tuplas_historia = {(int(v[0]), v[1]): k for k, v in c.FLAGS.items()}
        self.hitos_por_mapa = {}
        for hito, (mapa, requisito, prohibido) in c.HITOS_MAPA.items():
            self.hitos_por_mapa.setdefault(mapa, []).append((hito, requisito, prohibido))
        self.hitos_previos = set()

    def _log_episode_summary(self, reward, reason):
        payload = {
            "rank": self.rank,
            "episode": self.episode_counter,
            "steps": self.steps_count,
            "reward": round(float(reward), 4),
            "maps_discovered": len(self.episode_maps),
            "tiles_discovered": len(self.episode_tiles),
            "total_maps_seen": len(self.all_maps_seen),
            "reason": reason,
            "tiempo_juego_s": round(self.ram.leer_tiempo_juego(), 1),
            "timestamp": round(time.time(), 1),
            "salida": self.salida,
            "nivel_inicio": self.nivel_inicio,
            "nivel_fin": self.ram.leer_nivel_max_equipo(),
            "splits": self.splits,
            "combates": self.combates,
        }
        try:
            with open(self.metrics_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload) + "\n")
        except Exception:
            pass

    def reset(self, seed=None, options=None):
        self.episode_counter += 1
        self.episode_maps = set()
        self.episode_tiles = set()
        self.splits = {}
        self.combates = nuevas_estadisticas_combate()
        self.combate_actual = None

        # Sistema de Curriculum Learning (Cargar partida avanzada)
        ruta_salida = self._elegir_salida()
        # Simulacro: combate_<HITO>_NN.state, guardado en la hierba después de ese hito. Todos sus
        # episodios se registran juntos como "simulacro_combate"
        self.simulacro = os.path.dirname(ruta_salida) == config.SIMULACRO_DIR
        self.fin_simulacro = False
        if self.simulacro:
            hito_simulacro = os.path.basename(ruta_salida)[len("combate_"):].rsplit("_", 1)[0]
            self.salida = config.SALIDA_SIMULACRO
            self.mapas_previos = self._mapas_previos(f"best_speedrun_{hito_simulacro}.state")
        else:
            self.salida = ruta_salida
            # Si se empieza en un hito, los mapas recorridos para llegar a él ya cuentan como visitados:
            # volver a casa no debe dar recompensa de exploración
            self.mapas_previos = self._mapas_previos(self.salida)
        # Los hitos hasta el de la salida (incluido) ya están conseguidos: no se vuelven a premiar
        hito_salida = hito_simulacro if self.simulacro else (
            self.salida[len("best_speedrun_"):-len(".state")] if self.salida.startswith("best_speedrun_") else None)
        self.hitos_previos = set(c.HITOS[:c.HITOS.index(hito_salida) + 1]) if hito_salida in c.HITOS else set()
        self.episode_maps = set(self.mapas_previos)
        self.h_story.mapas_episodio = self.episode_maps
        if config.USE_CURRICULUM:
            path = os.path.join(config.STATES_DIR, ruta_salida)
            # Sin el savestate el episodio seguiría donde acabó el anterior sin avisar
            if not os.path.exists(path):
                raise FileNotFoundError(f"No existe el savestate del curriculum: {path}")
            with open(path, "rb") as f: self.pb.load_state(f)
        if self.simulacro:
            # El mapa del combate ya es conocido: no da recompensa de mapa nuevo ni dispara hitos de llegada
            self.episode_maps.add((self.ram.leer(c.ADDR_MAP_GRP), self.ram.leer(c.ADDR_MAP_ID)))

        # Reseteo de variables de control del speedrun
        self.steps_count = 0
        self.total_speedrun_reward = 0.0
        self.last_speedrun_pos, self.last_speedrun_map = (-1, -1), (-1, -1)

        self.vida_equipo_anterior = self.ram.leer_vida_total_equipo()
        self.max_vida_equipo_anterior = self.ram.leer_max_vida_total_equipo()
        self.party_count_anterior = self.ram.leer_party_count()
        self.nivel_max_previo = self.nivel_inicio = self.ram.leer_nivel_max_equipo()
        self.fraccion_vida = self.vida_equipo_anterior / self.max_vida_equipo_anterior if self.max_vida_equipo_anterior > 0 else 0.0
        self.fraccion_nivel = min(1.0, self.nivel_max_previo / self._nivel_objetivo())
        self.active_flags = self.ram.get_flag_bytes()

        # Resetear también las vidas que guardan los handlers internamente
        self.h_combat.vida_enemigo_anterior = 999
        self.h_movement.steps_sin_progreso = 0

        self.capturer.new_episode()

        return self._get_obs(), {}

    def _pulsar(self, action):
        """Mantiene el botón FRAMES_PULSACION frames y espera hasta completar FRAMES_POR_ACCION.
        Solo se dibuja el último frame (el que se observa); dibujar los demás no aporta nada y es lo más caro."""
        dibujar_todos = self.ventana  # con ventana, que se vea fluido
        p, r = self.actions[action]
        self.pb.send_input(p)
        ok = self.pb.tick(config.FRAMES_PULSACION, dibujar_todos)
        self.pb.send_input(r)
        ok = ok and self.pb.tick(config.FRAMES_POR_ACCION - config.FRAMES_PULSACION - 1, dibujar_todos)
        ok = ok and self.pb.tick(1, True)
        if not ok:
            print(f"\n🛑 [Clon {self.rank}] Ventana cerrada o Esc pulsado. Deteniendo...")
            raise KeyboardInterrupt

    def step(self, action):
        # 🎮 Ejecutar acción en el emulador
        self._pulsar(action)

        self.steps_count += 1
        reward = c.REWARD_STEP

        # 📍 Leer coordenadas y mapa actuales del speedrun
        x, y = self.ram.leer(c.ADDR_PLAYER_X), self.ram.leer(c.ADDR_PLAYER_Y)
        grp, mid = self.ram.leer(c.ADDR_MAP_GRP), self.ram.leer(c.ADDR_MAP_ID)
        current_speedrun_tile, current_speedrun_map = (grp, mid, x, y), (grp, mid)
        map_name = c.MAP_NAMES.get(current_speedrun_map, f"Mapa {grp}-{mid}")

        # Registrar cada cambio de casilla para el mapa de calor (episodio,grupo,mapa,x,y)
        if (x, y) != self.last_speedrun_pos or current_speedrun_map != self.last_speedrun_map:
            with open(self.coords_path, "a") as f:
                f.write(f"{self.episode_counter},{grp},{mid},{x},{y}\n")

        tipo_combate = self.ram.leer(c.ADDR_BATTLE_MODE)
        en_combate = tipo_combate > 0
        en_script = self.ram.leer(c.ADDR_SCRIPT_RUNNING) != 0
        self.atlas.capture(self.pb, grp, mid, x, y, en_combate, en_script)
        vida_actual_equipo = self.ram.leer_vida_total_equipo()
        max_vida_equipo = self.ram.leer_max_vida_total_equipo()
        party_count = self.ram.leer_party_count()
        nivel_max = self.ram.leer_nivel_max_equipo()

        # Si cambia el equipo (captura, Pokémon nuevo) o la vida máxima (subida de nivel),
        # el salto de PS no es curación ni daño, y un Pokémon nuevo no es una subida de nivel:
        # se toman los valores actuales como nueva referencia
        if party_count != self.party_count_anterior or max_vida_equipo != self.max_vida_equipo_anterior:
            self.vida_equipo_anterior = vida_actual_equipo
        if party_count != self.party_count_anterior:
            self.nivel_max_previo = nivel_max
        self.party_count_anterior, self.max_vida_equipo_anterior = party_count, max_vida_equipo

        # 📜 Eventos del juego (antes que el movimiento: un evento nuevo cuenta como progreso)
        reward += self.h_story.procesar(self.pb, self.ram, self.rewards, self.active_flags, self.tuplas_historia, self.steps_count)
        if self.h_story.hubo_progreso:
            self.h_movement.registrar_progreso()

        # 🗺️ 1. GESTIÓN DE MOVIMIENTO Y ATASCOS (Delegado)
        r_mov, sin_progreso = self.h_movement.procesar(
            x, y, self.last_speedrun_pos, current_speedrun_tile, self.episode_tiles, map_name, en_combate, en_script,
            # Solo exteriores y cuevas fuera de los mapas ya recorridos antes de la salida: casas, Centros
            # Pokémon y tiendas no dan recompensa de exploración (al Centro Pokémon se va a curarse)
            explorable=current_speedrun_map not in self.mapas_previos and rom_catalog.es_explorable(current_speedrun_map),
            cuenta_progreso=rom_catalog.es_explorable(current_speedrun_map),
        )
        reward += r_mov

        # ⚔️ Seguimiento de combates: tipo, duración y resultado (para medir si aprende a combatir)
        if en_combate and self.combate_actual is None:
            self.combate_actual = {"tipo": "entrenador" if tipo_combate == 2 else "salvaje", "inicio": self.steps_count,
                                   "ps_rival": None, "rival": self.ram.leer(c.ADDR_RIVAL_ESPECIE),
                                   "nivel_rival": self.ram.leer(c.ADDR_RIVAL_NIVEL), "mapa": map_name}
            if config.VERBOSE:
                self.gestor.imprimir_auditoria(tipo_combate)
            if self.logger:
                self.logger.log_step({"evento": "INICIO_COMBATE", "tipo": self.combate_actual["tipo"], "mapa": map_name, "step": self.steps_count})
        if en_combate:
            self.combate_actual["ps_rival"] = self.gestor.leer_vida_enemigo()
            # Debilitado alguna vez en este combate (al final del combate la RAM del rival puede cambiar)
            self.combate_actual["ko"] = self.combate_actual.get("ko") or (
                self.combate_actual["ps_rival"] == 0 and self.combate_actual.get("ps_visto", False))
            self.combate_actual["ps_visto"] = self.combate_actual.get("ps_visto") or self.combate_actual["ps_rival"] > 0
            # El nivel del rival se relee en cada paso: al empezar el combate puede no estar cargado aún
            self.combate_actual["nivel_rival"] = self.ram.leer(c.ADDR_RIVAL_NIVEL)
        elif self.combate_actual is not None:
            # El equipo cae en el mismo paso en que acaba el combate: eso es perder, no huir. Si no,
            # rival debilitado = ganado; si no, ha huido (o capturado)
            if vida_actual_equipo <= 0 and party_count > 0:
                resultado = "perdido"
            elif self.combate_actual.get("ko") or self.combate_actual["ps_rival"] == 0:
                resultado = "ganado"
            else:
                resultado = "huido"
            reward += self._cerrar_combate(resultado)
        self.ultimo_tipo_combate = tipo_combate

        # ⚔️ 2. GESTIÓN DE COMBATE (Delegado)
        objetivo = self._nivel_objetivo()
        self.h_combat.bajo_objetivo = nivel_max < objetivo
        self.fraccion_vida = vida_actual_equipo / max_vida_equipo if max_vida_equipo > 0 else 0.0
        self.fraccion_nivel = min(1.0, nivel_max / objetivo)
        r_comb, _ = self.h_combat.procesar(
            self.pb, self.ram, self.rewards, self.gestor,
            en_combate, vida_actual_equipo, self.vida_equipo_anterior,
            self.steps_count, map_name
        )
        reward += r_comb
        # Entrenar cuando hace falta es progreso: sin esto, subir de nv 5 a 8 (~12 combates, ~1.560 pasos)
        # se cortaba por "sin progreso" a los 1.000 pasos, a mitad del entrenamiento
        if self.h_combat.ko_bajo_objetivo:
            self.h_movement.registrar_progreso()

        # 🏥 Curación y niveles
        if not en_combate and vida_actual_equipo > self.vida_equipo_anterior and self.vida_equipo_anterior != 999:
            curacion = vida_actual_equipo - self.vida_equipo_anterior
            reward += self.rewards.calcular_premio_curacion(curacion, max_vida_equipo)
            if config.VERBOSE: print(f"💊 [Clon {self.rank}] ¡Curación! (+{curacion} HP).")
        self.vida_equipo_anterior = vida_actual_equipo

        # Solo cuentan los niveles ganados por debajo del objetivo del tramo (sin farmear de más)
        if self.nivel_max_previo > 0 and nivel_max > self.nivel_max_previo:
            premiados = max(0, min(nivel_max, objetivo) - self.nivel_max_previo)
            reward += c.REWARD_LEVEL_UP * premiados
            if premiados:
                self.h_movement.registrar_progreso()
            if config.VERBOSE: print(f"🌟 [Clon {self.rank}] ¡Nivel {nivel_max}! (objetivo {objetivo})")
        self.nivel_max_previo = nivel_max

        # 🌍 3. GESTIÓN DE MAPAS Y FLAGS DE HISTORIA (Delegado)
        if current_speedrun_map not in self.episode_maps:
            self.episode_maps.add(current_speedrun_map)
            self.all_maps_seen.add(current_speedrun_map)
            self.splits[map_name] = self.steps_count
            if rom_catalog.es_explorable(current_speedrun_map):
                reward += c.REWARD_NEW_MAP
            # Entrar por primera vez en un mapa (también interiores) da margen de pasos, sin recompensa:
            # el principio es casa → Pueblo Primavera → laboratorio, y con 1.000 pasos sin ninguna pista
            # dentro de las casas no llegaba nunca. Una vez por mapa y episodio: no sirve de refugio
            self.h_movement.registrar_progreso()
            if config.VERBOSE: print(f"🌍 [Clon {self.rank}] ¡Mapa descubierto! -> {map_name}")
            if self.logger: self.logger.log_step({"evento": "NUEVO_MAPA", "mapa": map_name, "step": self.steps_count})

        # Hitos de ruta: llegar a un mapa clave (con su requisito, p. ej. tener ya el huevo para la vuelta)
        reward += self._comprobar_hitos_mapa(current_speedrun_map)


        # 📸 Capturas: pantalla en memoria cada pocos pasos y foto de cada hito
        pantalla = self.pb.screen.ndarray[:, :, :3]
        self.capturer.record(pantalla, self.steps_count)
        for hito in self.h_story.hitos_nuevos:
            self.splits[hito] = self.steps_count
            self.capturer.milestone(pantalla, self.episode_counter, hito, map_name, (x, y), self.steps_count,
                                    self.ram.leer_tiempo_juego())

        # 💀 CONDICIÓN DE MUERTE
        debilitado = vida_actual_equipo <= 0 and party_count > 0
        if debilitado and self.combate_actual is not None:
            self._cerrar_combate("perdido")
        if debilitado:
            reward += c.PENALTY_TEAM_FAINTED
            if self.logger: self.logger.log_step({"evento": "EQUIPO_DEBILITADO", "mapa": map_name, "step": self.steps_count})

        # Guardar estado para el siguiente step
        self.last_speedrun_pos, self.last_speedrun_map = (x, y), current_speedrun_map
        reward /= 10.0  # Normalizamos la recompensa para Stable Baselines
        self.total_speedrun_reward += reward

        # ✂️ Cortes de episodio (un único registro en metrics.jsonl por episodio).
        # Debilitado y sin progreso son finales reales (terminated): PPO no debe suponer que la
        # partida sigue. El límite de pasos es un corte por tiempo (truncated): la partida seguiría.
        if debilitado:
            reason = "fainted"
        elif sin_progreso:
            reason = "no_progress"
        elif self.fin_simulacro:
            reason = "fin_combate"
        elif self.steps_count >= config.MAX_STEPS_PER_EPISODE:
            reason = "max_steps"
        else:
            reason = None
        if reason or self.steps_count % 2048 == 0:
            self.atlas.save()
        if reason:
            self._log_episode_summary(self.total_speedrun_reward, reason)
            print(f"🏁 [Clon {self.rank}] FIN DEL EPISODIO ({reason}) | Pasos: {self.steps_count} | Puntuación: {round(self.total_speedrun_reward, 2)}")
            hitos = [f"{h} @ {p}" for h, p in self.splits.items() if h in c.HITOS]
            if hitos:
                print(f"⏱️ [Clon {self.rank}] Hitos del episodio: {' | '.join(hitos)}")
            if not self.simulacro:  # los simulacros, cortos y muchos, desplazarían las capturas de la ruta
                self.capturer.episode_end(pantalla, self.episode_counter, reason, map_name, (x, y),
                                          self.steps_count, self.total_speedrun_reward, self.ram.leer_tiempo_juego())

        terminated = reason in ("fainted", "no_progress")
        # Al acabar el simulacro la partida seguiría: corte por tiempo, PPO estima lo que vendría después
        truncated = reason in ("max_steps", "fin_combate")
        info = {"splits": dict(self.splits), "combates": self.combates, "salida": self.salida} if reason else {}
        return self._get_obs(), reward, terminated, truncated, info

    def _elegir_salida(self):
        """Savestate desde el que empieza el episodio (ver SALIDAS_MEZCLADAS en config.py)."""
        if self.salida_fija:
            return self.salida_fija
        base = config.CURRICULUM_STATES[config.CURRENT_STAGE]
        if not config.SALIDAS_MEZCLADAS:
            return base
        # Hitos conseguidos hasta ahora por cualquier clon, en orden de la ruta (se revisa en cada episodio)
        hitos = [f"best_speedrun_{h}.state" for h in c.HITOS
                 if os.path.exists(os.path.join(config.STATES_DIR, f"best_speedrun_{h}.state"))]
        simulacros = sorted(glob.glob(os.path.join(config.STATES_DIR, config.SIMULACRO_DIR, "combate_*.state")))
        if simulacros and self.rng.random() < getattr(self, "prob_simulacro", config.PROB_SIMULACRO_COMBATE):
            return os.path.join(config.SIMULACRO_DIR, os.path.basename(self.rng.choice(simulacros)))
        if not hitos or self.rng.random() < config.PROB_SALIDA_INICIO:
            return base
        return self.rng.choice(hitos)

    def fijar_prob_simulacro(self, prob):
        """Lo llama SimulacroCallback (desde el proceso principal) para retirar el simulacro de combate."""
        self.prob_simulacro = prob

    def _mapas_previos(self, salida):
        """Mapas recorridos para llegar al hito de la salida (guardados con su récord en records.json)."""
        if not salida.startswith("best_speedrun_"):
            return set()
        hito = salida[len("best_speedrun_"):-len(".state")]
        record = cargar_records().get(hito, {})
        return {tuple(m) for m in record.get("mapas_previos", [])}

    def _cerrar_combate(self, resultado):
        combate, self.combate_actual = self.combate_actual, None
        self.fin_simulacro = self.simulacro
        pasos = self.steps_count - combate["inicio"]
        self.combates[combate["tipo"]][resultado] += 1
        self.combates["pasos_en_combate"] += pasos
        penalizada = resultado == "huido" and self._huida_penalizable(combate)
        if penalizada:
            self.combates["huidas_penalizadas"] += 1
        if self.logger:
            self.logger.log_step({"evento": "FIN_COMBATE", "tipo": combate["tipo"], "resultado": resultado, "pasos": pasos,
                                  "rival": combate["rival"], "nivel_rival": combate["nivel_rival"],
                                  "huida_penalizada": penalizada, "mapa": combate["mapa"], "step": self.steps_count})
        # Ganar al rival en Ciudad Cerezo (el único entrenador de ese mapa) es un hito de la vuelta a Elm
        if (combate["tipo"] == "entrenador" and resultado == "ganado" and combate["mapa"] == "CHERRYGROVE_CITY"):
            return self._hito(c.HITO_RIVAL_CEREZO)
        return c.PENALTY_HUIR_BAJO_OBJETIVO if penalizada else 0.0

    def _huida_penalizable(self, combate):
        """Huir de un salvaje solo se penaliza si hacía falta entrenar y el combate era razonable."""
        return (combate["tipo"] == "salvaje"
                and self.h_combat.bajo_objetivo                          # le falta nivel para el siguiente reto
                and combate["nivel_rival"] <= self.nivel_max_previo     # el salvaje no es más fuerte
                and self.fraccion_vida > c.VIDA_MIN_PARA_LUCHAR)        # y tiene vida para pelear

    def _hito(self, hito):
        """Premia un hito una sola vez por episodio (y nunca si ya estaba conseguido en la salida)."""
        if hito in self.splits or hito in self.hitos_previos:
            return 0.0
        self.splits[hito] = self.steps_count
        self.h_movement.registrar_progreso()
        return self.h_story.conseguir_hito(self.pb, self.ram, self.rewards, hito, self.steps_count)

    def _hito_conseguido(self, hito):
        if hito in self.splits or hito in self.hitos_previos:
            return True
        return hito in rom_catalog.EVENT_FLAGS and self._evento_activo(hito)

    def _nivel_objetivo(self):
        """Nivel adecuado para el siguiente reto: el de la primera fila de NIVELES_OBJETIVO sin conseguir."""
        for hito, nivel in c.NIVELES_OBJETIVO:
            if not self._hito_conseguido(hito):
                return nivel
        return 100

    def _evento_activo(self, nombre):
        addr, bit = rom_catalog.EVENT_FLAGS[nombre]
        return bool((self.ram.leer(addr) >> bit) & 1)

    def _comprobar_hitos_mapa(self, mapa):
        """Hitos de llegada a mapas clave: exigen su evento `requisito` activo y `prohibido` sin activar
        (p. ej. la vuelta a Elm solo cuenta llevando el huevo y antes de entregarlo)."""
        reward = 0.0
        for hito, requisito, prohibido in self.hitos_por_mapa.get(mapa, []):
            if requisito is not None and not self._evento_activo(requisito):
                continue
            if prohibido is not None and self._evento_activo(prohibido):
                continue
            reward += self._hito(hito)
        return reward

    def _get_obs(self):
        # Grises (pesos 77/150/29 ≈ 0.299/0.587/0.114) y media de cada bloque 2x2: 144x160 -> 72x80
        rgb = self.pb.screen.ndarray[:, :, :3].astype(np.uint16)
        gris = (rgb[:, :, 0] * 77 + rgb[:, :, 1] * 150 + rgb[:, :, 2] * 29) >> 8
        gris = (gris[0::2, 0::2] + gris[1::2, 0::2] + gris[0::2, 1::2] + gris[1::2, 1::2]) >> 2

        # Casillas visibles ya pisadas en este episodio (vacío en combate: la pantalla no muestra el mapa)
        visitadas = np.zeros((CASILLAS_Y, CASILLAS_X), dtype=np.uint8)
        if not self.ram.leer(c.ADDR_BATTLE_MODE):
            x, y = self.ram.leer(c.ADDR_PLAYER_X), self.ram.leer(c.ADDR_PLAYER_Y)
            grp, mid = self.ram.leer(c.ADDR_MAP_GRP), self.ram.leer(c.ADDR_MAP_ID)
            for fila in range(CASILLAS_Y):
                for col in range(CASILLAS_X):
                    if (grp, mid, x - JUGADOR_COL + col, y - JUGADOR_FILA + fila) in self.episode_tiles:
                        visitadas[fila, col] = 255
        exploracion = np.kron(visitadas, np.ones((8, 8), dtype=np.uint8))

        # Barras arriba del canal 2 (la pantalla no muestra la vida fuera de combate): filas 0-1 = PS del
        # equipo, filas 2-3 = nivel respecto al objetivo del tramo. Sirven para decidir curarse o entrenar
        exploracion[0:2, :] = 0
        exploracion[0:2, :int(round(80 * self.fraccion_vida))] = 255
        exploracion[2:4, :] = 0
        exploracion[2:4, :int(round(80 * self.fraccion_nivel))] = 255
        return np.stack([gris.astype(np.uint8), exploracion])

    def close(self):
        self.atlas.save()
        self.pb.stop()
