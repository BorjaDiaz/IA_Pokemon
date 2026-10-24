import os
import shutil
import subprocess
import sys
import time
from collections import deque

from stable_baselines3.common.callbacks import BaseCallback

import src.utils.config as config
import src.utils.constantes as c

STOP_FILE = os.path.join(config.BASE_DIR, "PARAR")


def lanzar_analisis(run_dir):
    """Ejecuta visualizador.py para esta ejecución en otro proceso (no frena el entrenamiento).
    Resultado en runs/<id>/analisis/; su salida en runs/<id>/analisis/visualizador.log."""
    salida = os.path.join(run_dir, "analisis")
    os.makedirs(salida, exist_ok=True)
    log = open(os.path.join(salida, "visualizador.log"), "w", encoding="utf-8")
    entorno = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.Popen([sys.executable, os.path.join(config.BASE_DIR, "visualizador.py"), "--run", os.path.basename(run_dir)],
                            cwd=config.BASE_DIR, stdout=log, stderr=subprocess.STDOUT, env=entorno)


class AnalisisCallback(BaseCallback):
    """Regenera el análisis de la ejecución (resumen.txt, gráficas y mapas) cada `cada_pasos` pasos."""

    def __init__(self, run_dir, cada_pasos):
        super().__init__()
        self.run_dir = run_dir
        self.cada_llamadas = None
        self.cada_pasos = cada_pasos
        self.proceso = None

    def _on_training_start(self):
        self.cada_llamadas = max(1, self.cada_pasos // self.training_env.num_envs)

    def _on_step(self):
        # Si el anterior aún no ha terminado, se espera a la siguiente vez
        if self.n_calls % self.cada_llamadas == 0 and (self.proceso is None or self.proceso.poll() is not None):
            self.proceso = lanzar_analisis(self.run_dir)
        return True


def quitar_parar():
    """Borra PARAR, sea un archivo o una carpeta (vacía o no). Si no se puede (p. ej. abierto en
    otro programa), no pasa nada: la parada ya se ha hecho."""
    try:
        if os.path.isdir(STOP_FILE):
            shutil.rmtree(STOP_FILE)
        elif os.path.exists(STOP_FILE):
            os.remove(STOP_FILE)
    except OSError as e:
        print(f"⚠️ No se pudo borrar {STOP_FILE} ({e}); bórralo a mano antes del próximo entrenamiento.")


class StopFileCallback(BaseCallback):
    """Para el entrenamiento de forma ordenada (guardando el modelo) si existe un archivo o una carpeta
    llamado PARAR en la carpeta del proyecto. Sirve cuando no se puede pulsar Ctrl+C (p. ej. lanzado
    en segundo plano)."""

    def _on_step(self):
        if self.n_calls % 100 == 0 and os.path.exists(STOP_FILE):
            print("\n🛑 PARAR encontrado: deteniendo el entrenamiento y guardando...")
            quitar_parar()
            return False
        return True


class SplitsCallback(BaseCallback):
    """Envía a TensorBoard, por cada hito del speedrun:

    - splits/<HITO>: pasos medios hasta conseguirlo (solo episodios que lo consiguen)
    - exito/<HITO>: fracción de episodios que lo consiguen

    Solo aparecen los hitos que algún clon ha conseguido alguna vez.

    Con salidas mezcladas, eso es para los episodios que empiezan en el estado base (la habitación);
    los que empiezan en un hito van a desde_<HITO>/exito/... y desde_<HITO>/splits/..., porque sus
    pasos no son comparables. salidas/desde_base: fracción de episodios que empiezan en el estado base.

    Y por episodio, los combates: combate/<tipo>_<resultado> (salvaje_ganado, entrenador_perdido...)
    y combate/pasos_en_combate.
    """

    def __init__(self):
        super().__init__()
        self.hitos_vistos = set()

    def _on_step(self):
        base = config.CURRICULUM_STATES[config.CURRENT_STAGE]
        for info in self.locals["infos"]:
            splits = info.get("splits")
            if splits is None:
                continue
            salida = info.get("salida", base)
            prefijo = "" if salida == base else salida.replace("best_speedrun_", "desde_").replace(".state", "") + "/"
            self.logger.record_mean("salidas/desde_base", float(salida == base))
            self.hitos_vistos.update(h for h in splits if h in c.HITOS)
            for hito in self.hitos_vistos:
                conseguido = hito in splits
                self.logger.record_mean(f"{prefijo}exito/{hito}", float(conseguido))
                if conseguido:
                    self.logger.record_mean(f"{prefijo}splits/{hito}", splits[hito])
            combates = info.get("combates")
            if combates:
                for tipo in ("salvaje", "entrenador"):
                    for resultado, n in combates[tipo].items():
                        self.logger.record_mean(f"combate/{tipo}_{resultado}", n)
                self.logger.record_mean("combate/pasos_en_combate", combates["pasos_en_combate"])
                self.logger.record_mean("combate/huidas_penalizadas", combates.get("huidas_penalizadas", 0))
        return True


class SimulacroCallback(BaseCallback):
    """Retira el simulacro de combate cuando ya gana: con SIMULACRO_EXITO de victorias en los últimos
    SIMULACRO_VENTANA simulacros, los clones pasan a PROB_SIMULACRO_DOMINADO. Así no se queda dependiendo
    del simulacro y sigue aprendiendo con los combates de la ruta."""

    def __init__(self):
        super().__init__()
        self.recientes = deque(maxlen=config.SIMULACRO_VENTANA)
        self.retirado = False

    def _on_step(self):
        for info in self.locals["infos"]:
            if info.get("salida") != config.SALIDA_SIMULACRO:
                continue
            ganado = info["combates"]["salvaje"]["ganado"] > 0
            self.recientes.append(ganado)
            self.logger.record_mean("simulacro/ganados", float(ganado))
        if (not self.retirado and len(self.recientes) == self.recientes.maxlen
                and sum(self.recientes) / len(self.recientes) >= config.SIMULACRO_EXITO):
            self.retirado = True
            self.training_env.env_method("fijar_prob_simulacro", config.PROB_SIMULACRO_DOMINADO)
            print(f"\n🎓 Simulacro de combate dominado ({100 * sum(self.recientes) / len(self.recientes):.0f}% "
                  f"de victorias): se retira, sigue con los combates de la ruta")
        return True


PAUSA_MAX_S = 300  # un hueco mayor entre comprobaciones del vigilante es una suspensión del PC


class VigilanteCallback(BaseCallback):
    """Para el entrenamiento solo, de forma ordenada (como PARAR), si:
    - se supera MAX_MINUTOS de entrenamiento (sin contar suspensiones ni hibernaciones del PC);
    - empeora lo ya dominado: desde el inicio, VIGILAR_HITO se consigue en menos de VIGILAR_EXITO_MIN
      (solo si en esta ejecución ya había llegado a dominarlo: una IA nueva empieza en 0%)
      de los últimos VIGILAR_VENTANA episodios;
    - el aprendizaje es inestable (approx_kl > VIGILAR_KL_MAX o explained_variance < VIGILAR_EV_MIN)
      durante VIGILAR_RONDAS_INESTABLE rondas seguidas;
    - (opcional) VIGILAR_RONDAS_ESTANCADO rondas sin hitos ni récords nuevos.

    Además guarda en MODELO_MEJOR el modelo con la mejor media de hitos por episodio desde el inicio.
    `motivo` dice por qué paró (None si terminó normal o lo paró el usuario); `degradado` es True si
    paró por empeorar o por inestabilidad (train.py deja entonces el mejor modelo para el siguiente arranque).
    """

    def __init__(self):
        super().__init__()
        self.motivo = None
        self.degradado = False
        self.ultimo_reloj = None
        self.segundos_activo = 0.0
        self.recientes = deque(maxlen=config.VIGILAR_VENTANA)  # hitos conseguidos por episodio desde el inicio
        self.mejor = None
        self.rondas_inestable = 0
        self.rondas_sin_novedad = 0
        self.hito_dominado = False  # VIGILAR_HITO llegó a VIGILAR_EXITO_MIN en esta ejecución
        self.hitos_vistos = set()
        self.novedad = False
        self.records_mtime = self._mtime_records()

    @staticmethod
    def _mtime_records():
        return os.path.getmtime(config.RECORDS_PATH) if os.path.exists(config.RECORDS_PATH) else None

    def _parar(self, motivo, degradado=False):
        self.motivo, self.degradado = motivo, degradado
        print(f"\n🛑 Vigilante: {motivo}. Deteniendo el entrenamiento y guardando...")
        return False

    def _on_training_start(self):
        self.ultimo_reloj = time.time()

    def _sumar_tiempo_activo(self):
        """Suma el tiempo desde la última comprobación, salvo si es un hueco largo: el PC estuvo
        suspendido o hibernando (con 12 clones, 100 pasos son ~2 s y una actualización de PPO, ~30 s)."""
        ahora = time.time()
        hueco = ahora - self.ultimo_reloj
        if hueco < PAUSA_MAX_S:
            self.segundos_activo += hueco
        self.ultimo_reloj = ahora

    def _on_step(self):
        if self.motivo_pendiente:
            return self._parar(*self.motivo_pendiente)
        base = config.CURRICULUM_STATES[config.CURRENT_STAGE]
        for info in self.locals["infos"]:
            splits = info.get("splits")
            if splits is None:
                continue
            nuevos = {h for h in splits if h in c.HITOS} - self.hitos_vistos
            if nuevos:
                self.hitos_vistos |= nuevos
                self.novedad = True
            if info.get("salida", base) == base:
                self.recientes.append({h for h in splits if h in c.HITOS})
        if self.n_calls % 100 == 0:
            self._sumar_tiempo_activo()
        if config.MAX_MINUTOS and self.n_calls % 100 == 0 and self.segundos_activo > config.MAX_MINUTOS * 60:
            return self._parar(f"alcanzado el tiempo máximo ({config.MAX_MINUTOS} min)")
        return True

    def _on_rollout_start(self):
        # Aquí ya están las métricas de la última actualización de la red (antes de volcarlas a TensorBoard)
        valores = self.model.logger.name_to_value
        kl, ev = valores.get("train/approx_kl"), valores.get("train/explained_variance")
        if kl is not None and ev is not None:
            inestable = kl > config.VIGILAR_KL_MAX or ev < config.VIGILAR_EV_MIN or kl != kl or ev != ev  # NaN
            self.rondas_inestable = self.rondas_inestable + 1 if inestable else 0

        mtime = self._mtime_records()
        if mtime != self.records_mtime:
            self.records_mtime, self.novedad = mtime, True
        self.rondas_sin_novedad = 0 if self.novedad else self.rondas_sin_novedad + 1
        self.novedad = False

        if len(self.recientes) == self.recientes.maxlen:
            media = sum(len(h) for h in self.recientes) / len(self.recientes)
            if self.mejor is None or media > self.mejor:
                self.mejor = media
                self.model.save(config.MODELO_MEJOR)
                print(f"⭐ Vigilante: mejor modelo hasta ahora ({media:.2f} hitos por episodio desde el inicio) "
                      f"guardado en {os.path.basename(config.MODELO_MEJOR)}")

    def _on_rollout_end(self):
        # Las comprobaciones que paran van aquí: SB3 solo hace caso al valor de _on_step, así que se marca
        # y el siguiente _on_step devuelve False
        if len(self.recientes) == self.recientes.maxlen:
            exito = sum(config.VIGILAR_HITO in h for h in self.recientes) / len(self.recientes)
            if exito >= config.VIGILAR_EXITO_MIN:
                self.hito_dominado = True
            elif self.hito_dominado:
                self.motivo_pendiente = (f"{config.VIGILAR_HITO} ha bajado al {100 * exito:.0f}% "
                                         f"(mínimo {100 * config.VIGILAR_EXITO_MIN:.0f}%)", True)
        if self.rondas_inestable >= config.VIGILAR_RONDAS_INESTABLE:
            self.motivo_pendiente = (f"aprendizaje inestable {self.rondas_inestable} rondas seguidas", True)
        if config.VIGILAR_RONDAS_ESTANCADO and self.rondas_sin_novedad >= config.VIGILAR_RONDAS_ESTANCADO:
            self.motivo_pendiente = (f"{self.rondas_sin_novedad} rondas sin hitos ni récords nuevos", False)

    motivo_pendiente = None
