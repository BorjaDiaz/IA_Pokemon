"""El emulador visto por el piloto: pulsar botones y leer de la RAM lo que hace falta para decidir.

Direcciones de WRAM según los símbolos de pret/pokegold (la ROM española comparte esa disposición)."""
from pyboy import PyBoy

from src.utils import config, rom_catalog
from src.utils.mapas import MAPAS

WRAM = 1
ADDR_OBJECT_STRUCTS, OBJECT_LENGTH, NUM_OBJECT_STRUCTS = 0xD1FD, 0x28, 13
OBJECT_MAP_X, OBJECT_MAP_Y = 0x10, 0x11
# Del struct del jugador (el primero): 255 en OBJECT_WALKING = parado; 1 en OBJECT_STEP_TYPE = sin paso ni giro en curso
OBJECT_WALKING, OBJECT_STEP_TYPE = 0x07, 0x09
PARADO, SIN_PASO = 255, 1
ADDR_PLAYER_DIRECTION = 0xD205           # 0 abajo, 4 arriba, 8 izquierda, 12 derecha
DIRECCION = {0: "down", 4: "up", 8: "left", 12: "right"}
ADDR_PARTY_MON1, PARTYMON_LENGTH = 0xDA2A, 0x30
FPS = 59.73


class Juego:
    def __init__(self, ventana=False, velocidad=None):
        self.pb = PyBoy(config.ROM_PATH, window="SDL2" if ventana else "null", sound_emulated=False)
        self.pb.set_emulation_speed((1 if ventana else 0) if velocidad is None else velocidad)
        self.pb.rtc_lock_experimental(True)  # misma hora en cada partida: partidas repetibles
        self.ventana = ventana
        self.frames = 0

    # ------------------------------------------------------------ control
    def cargar(self, ruta):
        with open(ruta, "rb") as f:
            self.pb.load_state(f)
        self.esperar(2)

    def guardar(self, ruta):
        with open(ruta, "wb") as f:
            self.pb.save_state(f)

    def esperar(self, frames):
        if not self.pb.tick(frames, self.ventana):
            raise KeyboardInterrupt("ventana cerrada")
        self.frames += frames

    def pulsar(self, boton, frames=8, despues=8):
        """Mantiene el botón `frames` fotogramas y espera `despues` más (16 en total = una casilla andando)."""
        self.pb.button_press(boton)
        self.esperar(frames)
        self.pb.button_release(boton)
        self.esperar(despues)

    def quieto(self):
        """El jugador no está andando ni girando."""
        return (self.leer(ADDR_OBJECT_STRUCTS + OBJECT_WALKING) == PARADO
                and self.leer(ADDR_OBJECT_STRUCTS + OBJECT_STEP_TYPE) == SIN_PASO)

    def andar(self, direccion, espera_inicio=28, espera_fin=48):
        """Un paso en esa dirección. Mantiene el botón hasta que el paso empieza (si no miraba hacia allí,
        primero gira) y espera a que termine: el juego actualiza las coordenadas al final del paso, así que
        pulsar a ritmo fijo desincroniza el plan. Devuelve True si el paso llegó a empezar; False si hay
        algo delante (o se ha abierto un diálogo o un combate)."""
        self.pb.button_press(direccion)
        empezado = False
        for frame in range(espera_inicio):
            self.esperar(1)
            if self.leer(ADDR_OBJECT_STRUCTS + OBJECT_WALKING) != PARADO:
                empezado = True
                break
            # Al girar, wScriptRunning se activa unos fotogramas: solo cuenta como escena pasado el giro
            if frame >= 12 and (self.en_escena() or self.en_combate()):
                break
        self.pb.button_release(direccion)
        for _ in range(espera_fin):
            if self.quieto() or self.en_escena() or self.en_combate():
                break
            self.esperar(1)
        self.esperar(1)
        return empezado

    def cerrar(self):
        self.pb.stop(save=False)

    # ------------------------------------------------------------ lectura
    def leer(self, direccion):
        return self.pb.memory[WRAM, direccion]

    def nodo(self):
        """(mapa, x, y) del jugador, o None en una transición entre mapas."""
        mapa = (self.leer(rom_catalog.RAM["wMapGroup"]), self.leer(rom_catalog.RAM["wMapNumber"]))
        x, y = self.leer(rom_catalog.RAM["wXCoord"]), self.leer(rom_catalog.RAM["wYCoord"])
        if mapa not in MAPAS or not MAPAS[mapa].dentro(x, y):
            return None
        return (mapa, x, y)

    def mirando(self):
        return DIRECCION.get(self.leer(ADDR_PLAYER_DIRECTION) & 0x0C, "down")

    def en_combate(self):
        return self.leer(rom_catalog.RAM["wBattleMode"]) != 0

    def en_escena(self):
        return self.leer(rom_catalog.RAM["wScriptRunning"]) != 0

    def evento(self, nombre):
        direccion, bit = rom_catalog.EVENT_FLAGS[nombre]
        return bool((self.leer(direccion) >> bit) & 1)

    def equipo(self):
        n = self.leer(rom_catalog.RAM["wPartyCount"])
        return n if n <= 6 else 0

    def vida(self):
        """Fracción de PS del equipo (0 sin equipo)."""
        actual = maxima = 0
        for i in range(self.equipo()):
            base = ADDR_PARTY_MON1 + i * PARTYMON_LENGTH
            actual += (self.leer(base + 0x22) << 8) + self.leer(base + 0x23)
            maxima += (self.leer(base + 0x24) << 8) + self.leer(base + 0x25)
        return actual / maxima if maxima else 0.0

    def pp(self):
        """Fracción de PP que quedan en los ataques que hacen daño (0 sin ataques de daño)."""
        actuales = maximos = 0
        for i in range(self.equipo()):
            base = ADDR_PARTY_MON1 + i * PARTYMON_LENGTH
            for hueco in range(4):
                ataque = rom_catalog.MOVES.get(self.leer(base + 0x02 + hueco))
                if ataque and ataque[1] > 0:
                    actuales += self.leer(base + 0x17 + hueco) & 0x3F
                    maximos += ataque[2]
        return actuales / maximos if maximos else 0.0

    def nivel(self):
        return max((self.leer(ADDR_PARTY_MON1 + i * PARTYMON_LENGTH + 0x1F) for i in range(self.equipo())), default=0)

    def personajes(self):
        """Casillas (x, y) ocupadas ahora por personajes y objetos del mapa (sin contar al jugador)."""
        ocupadas = set()
        for i in range(1, NUM_OBJECT_STRUCTS):
            base = ADDR_OBJECT_STRUCTS + i * OBJECT_LENGTH
            if self.leer(base):  # sprite 0 = hueco libre
                ocupadas.add((self.leer(base + OBJECT_MAP_X) - 4, self.leer(base + OBJECT_MAP_Y) - 4))
        return ocupadas

    def tiempo_juego(self):
        """Tiempo de partida en segundos (el de la ficha del entrenador)."""
        r = rom_catalog.RAM
        horas = (self.leer(r["wGameTimeHours"]) << 8) | self.leer(r["wGameTimeHours"] + 1)
        return (horas * 3600 + self.leer(r["wGameTimeMinutes"]) * 60 + self.leer(r["wGameTimeSeconds"])
                + self.leer(r["wGameTimeFrames"]) / 60)
