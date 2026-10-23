import json
import os
import subprocess
import time

from src.agents.env_builder import build_vectorized_env
from src.agents.agent_manager import AgentManager
from src.agents.callbacks import AnalisisCallback, SplitsCallback, StopFileCallback, STOP_FILE, lanzar_analisis, quitar_parar
import src.utils.config as config


def shutdown_training(env, gestor_agente=None, model=None):
    try:
        if gestor_agente is not None and model is not None:
            gestor_agente.save_model(model)
        if env is not None:
            env.close()
    except (BrokenPipeError, EOFError, KeyboardInterrupt):
        print("⚠️ Cierre del entorno interrumpido; se ha ignorado el error de shutdown.")
    finally:
        print("💾 Progreso guardado correctamente.")
        print("👋 Sesión de entrenamiento finalizada.")


def preparar_run():
    """Crea runs/<fecha_hora>/ y la comunica a los clones (procesos hijos) por variable de entorno."""
    run_dir = os.path.join(config.RUNS_DIR, time.strftime("%Y-%m-%d_%H%M%S"))
    os.makedirs(run_dir, exist_ok=True)
    os.environ["POKEMON_RUN_DIR"] = run_dir
    config.RUN_DIR = run_dir
    return run_dir


def guardar_info_run(run_dir, **extra):
    """runs/<id>/run.json: con qué código y configuración se entrenó (para comparar ejecuciones)."""
    path = os.path.join(run_dir, "run.json")
    try:
        with open(path, encoding="utf-8") as f:
            info = json.load(f)
    except (OSError, ValueError):
        try:
            commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                                    cwd=config.BASE_DIR).stdout.strip()
            cambios = bool(subprocess.run(["git", "status", "--porcelain", "--", "src", "train.py"], capture_output=True,
                                          text=True, cwd=config.BASE_DIR).stdout.strip())
        except OSError:
            commit, cambios = "", False
        info = {
            "inicio": time.strftime("%Y-%m-%d %H:%M:%S"),
            "git_commit": commit + ("+cambios" if cambios else ""),
            "config": {k: getattr(config, k) for k in (
                "NUM_CLONES", "TOTAL_TIMESTEPS", "PPO_LEARNING_RATE", "PPO_TARGET_KL", "PPO_GAMMA", "PPO_ENT_COEF", "PPO_N_STEPS",
                "PPO_BATCH_SIZE", "FRAME_STACK", "FRAMES_POR_ACCION", "FRAMES_PULSACION", "MAX_STEPS_PER_EPISODE",
                "MAX_STEPS_SIN_PROGRESO", "CURRENT_STAGE")},
            "estado_inicial": config.CURRICULUM_STATES[config.CURRENT_STAGE],
        }
    info.update(extra)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(info, f, indent=1, ensure_ascii=False)


def main():
    run_dir = preparar_run()
    # Un PARAR olvidado de una parada anterior pararía el entrenamiento nada más empezar
    quitar_parar()
    if os.path.exists(STOP_FILE):
        raise SystemExit(f"Hay un PARAR que no se puede borrar ({STOP_FILE}). Bórralo y vuelve a lanzar.")

    print("\n🚀 INICIO DEL ENTRENAMIENTO SPEEDRUN")
    print("================================")
    print("Opciones:")
    print("- Presiona Ctrl+C (o crea un archivo o carpeta llamado PARAR en la carpeta del proyecto) para detener y guardar")
    print("- El modelo se guardará automáticamente al finalizar")
    print(f"- Copias de seguridad cada {config.CHECKPOINT_FREQ:,} pasos en ia/checkpoints/")
    print(f"- Datos de esta ejecución en runs/{os.path.basename(run_dir)}/ (análisis y mapas en analisis/, "
          f"se actualizan cada {config.CHECKPOINT_FREQ:,} pasos)")
    print("- Gráficas: en otra terminal, tensorboard --logdir logs/tensorboard")
    print("================================")

    # 1. Preparamos el entorno virtual (clones)
    env = build_vectorized_env()

    # 2. Inicializamos el gestor del agente y cargamos el cerebro
    gestor_agente = AgentManager(env)
    model = gestor_agente.load_or_create_model()
    guardar_info_run(run_dir, modelo="continuado" if gestor_agente.cargado else "nuevo",
                     pasos_al_empezar=model.num_timesteps)

    print("\n🔥 ¡Entrenando! El agente empezará a aprender en el entorno de speedrun.")

    # 3. Bucle de entrenamiento con control explícito de parada/guardado.
    # Si se continúa un modelo, el contador de pasos sigue (curva continua en TensorBoard y
    # nombres de checkpoints que no se pisan)
    try:
        model.learn(total_timesteps=config.TOTAL_TIMESTEPS,
                    callback=[gestor_agente.checkpoint_callback(), SplitsCallback(), StopFileCallback(),
                              AnalisisCallback(run_dir, config.CHECKPOINT_FREQ)],
                    reset_num_timesteps=not gestor_agente.cargado, tb_log_name="PPO")
    except KeyboardInterrupt:
        print("\n🛑 Entrenamiento detenido por el usuario. Guardando progreso...")
    finally:
        shutdown_training(env, gestor_agente=gestor_agente, model=model)
        guardar_info_run(run_dir, fin=time.strftime("%Y-%m-%d %H:%M:%S"), pasos_al_terminar=model.num_timesteps)
        print(f"📊 Generando el análisis final en runs/{os.path.basename(run_dir)}/analisis/ ...")
        lanzar_analisis(run_dir).wait()


if __name__ == "__main__":
    main()
