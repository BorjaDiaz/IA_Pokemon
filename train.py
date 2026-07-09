from src.agents.env_builder import build_vectorized_env
from src.agents.agent_manager import AgentManager


def main():
    # 1. Preparamos el entorno virtual (clones)
    env = build_vectorized_env()
    
    # 2. Inicializamos el gestor del agente y cargamos el cerebro
    gestor_agente = AgentManager(env)
    model = gestor_agente.load_or_create_model()

    print("\n🔥 ¡Entrenando! Pulsa Ctrl+C en esta consola para detener y guardar.")

    # 3. Bucle de entrenamiento a prueba de fallos
    try:
        model.learn(total_timesteps=5_000_000)
    except KeyboardInterrupt:
        print("\n🛑 Entrenamiento detenido manualmente por el usuario. Guardando progreso...")
    finally:
        gestor_agente.save_model(model)
        env.close()
        print("👋 ¡Hasta la próxima sesión de entrenamiento!")

if __name__ == "__main__":
    main()