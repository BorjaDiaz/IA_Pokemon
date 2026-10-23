import os
import subprocess
import sys

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


class StopFileCallback(BaseCallback):
    """Para el entrenamiento de forma ordenada (guardando el modelo) si existe el archivo PARAR
    en la carpeta del proyecto. Sirve cuando no se puede pulsar Ctrl+C (p. ej. lanzado en segundo plano)."""

    def _on_step(self):
        if self.n_calls % 100 == 0 and os.path.exists(STOP_FILE):
            os.remove(STOP_FILE)
            print("\n🛑 Archivo PARAR encontrado: deteniendo el entrenamiento y guardando...")
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
            self.hitos_vistos.update(h for h in splits if h in c.FLAGS)
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
        return True
