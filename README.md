# IA para speedrun de Pokémon Oro en Game Boy Color

Este proyecto entrena una inteligencia artificial para jugar a Pokémon Oro (Game Boy Color, versión en español) y completar la partida lo más rápido posible mediante Reinforcement Learning.

## Objetivo

Entrenar un agente que:
- controle el emulador con PyBoy,
- observe la pantalla y la RAM del juego,
- aprenda acciones como mover, interactuar y combatir,
- y progrese por la historia con una estrategia orientada a speedrun.

## Requisitos

- Python 3.10+ (se recomienda 3.11 o 3.12)
- Windows 10/11
- Git
- Un entorno virtual recomendado
- La ROM de Pokémon Oro en español

## Estructura del proyecto

- `main_entrenar.py`: entrada de entrenamiento principal
- `train.py`: flujo modular de entrenamiento
- `src/env/pokemon_env.py`: entorno Gymnasium para el juego
- `src/agents/`: construcción del entorno vectorizado y gestión del modelo
- `src/env/handlers/`: lógica de movimiento, combate y recompensas
- `src/utils/`: configuración y constantes del proyecto
- `state/`: estados guardados del juego
- `roms/`: ROMs del juego
- `logs/`: logs de entrenamiento
- `coordinates/`: coordenadas exploradas por la IA

## Instalación

1. Clona el repositorio:

```bash
git clone https://github.com/BorjaDiaz/IA_Pokemon.git
cd IA_Pokemon
```

2. Crea un entorno virtual:

```bash
python -m venv .venv
```

3. Activa el entorno virtual en PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

4. Instala las dependencias:

```bash
python -m pip install --upgrade pip
python -m pip install gymnasium stable-baselines3 pyboy numpy matplotlib
```

## Preparar la ROM

Coloca la ROM de Pokémon Oro en la carpeta `roms/` con uno de estos nombres:

- `Pokemon_Oro.gbc`

El proyecto espera que el archivo exista en:

```text
roms/Pokemon_Oro.gbc
```

## Ejecutar el proyecto

### Entrenamiento principal

```bash
python main_entrenar.py
```

### Entrenamiento modular

```bash
python train.py
```

## Variables importantes

El archivo `src/utils/config.py` contiene configuraciones como:
- ruta de la ROM,
- carpeta de estados,
- número de clones,
- modo speedrun,
- activación de logs,
- máximo de pasos por episodio.

## Notas importantes

- El proyecto está pensado para trabajar con PyBoy y emulación en tiempo real.
- El entrenamiento puede tardar bastante y requiere recursos de CPU/GPU.
- Si usas Windows, es posible que tu antivirus marque algunos DLLs de SDL2 como sospechosos; normalmente son falsos positivos de paquetes de PyBoy/SDL2.
- Para evitar problemas, puedes añadir la carpeta `.venv` como excepción si tu antivirus lo requiere.

## Recomendaciones para el reto

- Usa `.venv` para aislar dependencias.
- Mantén la ROM fuera de Git si no quieres versionarla.
- Revisa los logs y los estados guardados para analizar el progreso del agente.
- Si el proyecto se vuelve grande, conviene mover modelos pesados a Git LFS o almacenarlos fuera del repositorio.

## Troubleshooting

### Error: `ModuleNotFoundError: No module named 'config'`

Asegúrate de ejecutar desde la raíz del proyecto y de usar el entorno virtual activado.

### Error: `gym` / `gymnasium`

Este proyecto ya usa `gymnasium`. Si sigues viendo advertencias de `gym`, desinstala la versión antigua:

```bash
python -m pip uninstall -y gym
python -m pip install -U gymnasium
```

### Error con SDL2 / PyBoy

Si tu antivirus bloquea un DLL, comprueba que el archivo provenga de la carpeta `.venv/Lib/site-packages/sdl2dll/dll` y añade esa ruta como excepción si es necesario.
