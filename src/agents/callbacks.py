import os

from stable_baselines3.common.callbacks import BaseCallback

import src.utils.config as config
import src.utils.constantes as c

STOP_FILE = os.path.join(config.BASE_DIR, "PARAR")


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
    """

    def __init__(self):
        super().__init__()
        self.hitos_vistos = set()

    def _on_step(self):
        for info in self.locals["infos"]:
            splits = info.get("splits")
            if splits is None:
                continue
            self.hitos_vistos.update(h for h in splits if h in c.FLAGS)
            for hito in self.hitos_vistos:
                conseguido = hito in splits
                self.logger.record_mean(f"exito/{hito}", float(conseguido))
                if conseguido:
                    self.logger.record_mean(f"splits/{hito}", splits[hito])
        return True
