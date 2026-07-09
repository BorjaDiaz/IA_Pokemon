from src.agents.env_builder import build_vectorized_env
from src.agents.agent_manager import AgentManager


def main():
    print("\n🚀 INICIO DEL ENTRENAMIENTO SPEEDRUN")
    print("================================")
    print("Opciones:")
    print("- Presiona Ctrl+C para detener y guardar el progreso")
    print("- El modelo se guardará automáticamente al finalizar")
    print("================================")

    # 1. Preparamos el entorno virtual (clones)
    env = build_vectorized_env()

    # 2. Inicializamos el gestor del agente y cargamos el cerebro
    gestor_agente = AgentManager(env)
    model = gestor_agente.load_or_create_model()

    print("\n🔥 ¡Entrenando! El agente empezará a aprender en el entorno de speedrun.")

    # 3. Bucle de entrenamiento con control explícito de parada/guardado
    try:
        model.learn(total_timesteps=5_000_000)
    except KeyboardInterrupt:
        print("\n🛑 Entrenamiento detenido por el usuario. Guardando progreso...")
    finally:
        gestor_agente.save_model(model)
        env.close()
        print("💾 Progreso guardado correctamente.")
        print("👋 Sesión de entrenamiento finalizada.")


if __name__ == "__main__":
    main()