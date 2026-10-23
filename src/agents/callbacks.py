from stable_baselines3.common.callbacks import BaseCallback

import src.utils.constantes as c


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
