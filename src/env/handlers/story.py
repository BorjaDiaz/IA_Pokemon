import json
import os
import time
import numpy as np
import src.utils.config as config
import src.utils.constantes as c
from src.utils import rom_catalog

class StoryHandler:
    def __init__(self, rank, logger):
        self.rank = rank
        self.logger = logger
        self.hitos_nuevos = []  # hitos conseguidos en el último procesar(), para las capturas

    def procesar(self, pb, ram, rewards, active_flags, tuplas_historia, step_count):
        """active_flags: bytes de flags ya vistos en el episodio (se actualiza en el sitio)."""
        reward = 0.0
        self.hitos_nuevos = []
        flags = ram.get_flag_bytes()
        nuevos = flags & ~active_flags
        if not nuevos.any():
            return reward
        active_flags |= flags

        for i in np.flatnonzero(nuevos):
            for b in range(8):
                if not (nuevos[i] >> b) & 1:
                    continue
                f_id = (c.FLAG_START + int(i), b)

                if f_id in tuplas_historia:
                    # Hito del speedrun: gran premio y savestate para el curriculum
                    nombre_evento = tuplas_historia[f_id]
                    self.hitos_nuevos.append(nombre_evento)
                    bonus = rewards.calcular_bonus_prisa_flag(step_count)
                    reward += c.REWARD_FLAG_STORY + bonus
                    print(f"🌟 [Clon {self.rank}] ¡HIT HISTÓRICO! -> {nombre_evento}")
                    if self.logger:
                        self.logger.log_step({"evento": "LOGRO_HISTORIA", "flag": nombre_evento, "step": step_count})

                    self._guardar_si_es_record(pb, ram, nombre_evento, step_count)

                elif rom_catalog.is_story_flag(*f_id):
                    # Evento de historia menor; los de visibilidad, entrenador y temporales no puntúan
                    nombre_evento = rom_catalog.flag_name(*f_id)
                    reward += c.REWARD_FLAG_UNKNOWN
                    if config.VERBOSE:
                        print(f"🧭 [Clon {self.rank}] Evento de historia: {nombre_evento}")
                    if self.logger:
                        self.logger.log_step({"evento": "PROGRESO_HISTORIA", "flag": nombre_evento, "step": step_count})

        return reward

    def _guardar_si_es_record(self, pb, ram, hito, step_count):
        """Guarda state/best_speedrun_<hito>.state solo si es el menor tiempo de partida conseguido
        para ese hito (por cualquier clon, en cualquier ejecución). Récords en state/records.json."""
        tiempo = ram.leer_tiempo_juego()
        records = cargar_records()
        anterior = records.get(hito, {}).get("tiempo_juego_s")
        if anterior is not None and tiempo >= anterior:
            return
        try:
            ruta_estado = os.path.join(config.STATES_DIR, f"best_speedrun_{hito}.state")
            tmp = ruta_estado + f".tmp{self.rank}"
            with open(tmp, "wb") as f:
                pb.save_state(f)
            os.replace(tmp, ruta_estado)
            # Releer justo antes de escribir: otro clon puede haber batido el récord mientras tanto
            records = cargar_records()
            records[hito] = {"tiempo_juego_s": round(tiempo, 2), "pasos": step_count, "clon": self.rank,
                             "run": os.path.basename(os.path.abspath(config.RUN_DIR)),
                             "fecha": time.strftime("%Y-%m-%d %H:%M:%S")}
            tmp = config.RECORDS_PATH + f".tmp{self.rank}"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=1, ensure_ascii=False)
            os.replace(tmp, config.RECORDS_PATH)
            mejora = f" (antes {anterior:.1f} s)" if anterior is not None else ""
            print(f"🏆 [Clon {self.rank}] ¡Récord! {hito} en {tiempo:.1f} s de partida{mejora}")
        except Exception:
            pass


def cargar_records():
    try:
        with open(config.RECORDS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}
