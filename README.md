# IA para speedrun de Pokémon Oro en Game Boy Color

Este proyecto busca que una IA complete Pokémon Oro (Game Boy Color, versión en español) lo más rápido posible.

## Objetivo y enfoque

El enfoque actual es **híbrido** (`jugar.py`, carpeta `src/piloto/`):
- **Programado**: moverse (buscador de caminos sobre los mapas extraídos de la ROM), pasar diálogos y escenas,
  e ir al Centro Pokémon cuando faltan PS o PP.
- **Lista de objetivos de la historia** (`src/piloto/objetivos.py`): cada uno dice a dónde ir o con quién hablar
  y se da por hecho con un evento del propio juego. No hay rutas escritas a mano: el camino lo calcula el buscador.
- **Combates**: una política aparte (`src/piloto/combate.py`); hoy, el ataque más potente con PP. Es el hueco
  donde encaja la IA que aprenda a combatir.

Antes se intentó que una sola red (PPO, `train.py`) aprendiera todo mirando la pantalla. Tras 8 millones de pasos
no pasaba de los primeros 10 minutos de juego, y los proyectos públicos con ese método llegan como mucho a la
segunda medalla con muchísimo más cómputo. El código sigue en el proyecto, pero ya no es el camino principal.

Estado: el piloto llega a la **primera medalla** (Pegaso) desde la habitación en ~48 min de juego (~20 s reales).

## Requisitos

- Python 3.10+ (se recomienda 3.11 o 3.12)
- Windows 10/11
- Git
- Un entorno virtual recomendado
- La ROM de Pokémon Oro en español

## Estructura del proyecto

- `jugar.py`: juega la partida con el piloto (enfoque híbrido)
- `src/piloto/`: piloto (rutas.py = buscador de caminos, juego.py = emulador y RAM, piloto.py, combate.py, objetivos.py)
- `tools/build_mapas.py`: extrae de la ROM la geometría de los 368 mapas a `data/mapas.json` (colisiones, puertas,
  conexiones, personajes); `src/utils/mapas.py` la carga
- `train.py`: entrenamiento por refuerzo del enfoque anterior
- `visualizador.py`: gráficas de progreso y mapa de calor de coordenadas
- `src/env/pokemon_env.py`: entorno Gymnasium para el juego
- `src/agents/`: construcción del entorno vectorizado y gestión del modelo
- `src/env/handlers/`: lógica de movimiento, combate y recompensas
- `src/utils/`: configuración y constantes del proyecto
- `tools/build_rom_catalog.py`: genera `data/rom_catalog.json` (event flags y mapas de la ROM)
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

### Jugar con el piloto (enfoque actual)

Una vez, para extraer los mapas de tu ROM:

```bash
python tools/build_mapas.py
```

Después:

```bash
python jugar.py                          # sin ventana, lo más rápido posible
python jugar.py --ventana                # verlo jugar a velocidad real
python jugar.py --ventana --velocidad 4
python jugar.py --desde state/piloto/04.state   # seguir desde un objetivo ya conseguido
```

Al conseguir cada objetivo guarda la partida en `state/piloto/NN.state`; si se atasca, en `state/piloto/atascado.state`.

### Entrenamiento (enfoque anterior)

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
