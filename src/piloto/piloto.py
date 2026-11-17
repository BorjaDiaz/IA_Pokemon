"""Piloto: lleva la partida de objetivo en objetivo.

Reparte el trabajo así:
- Moverse: buscador de caminos sobre los mapas de la ROM (rutas.py). El camino se recalcula si el juego no
  hace lo esperado (un personaje en medio, un bordillo, un diálogo que mueve al jugador).
- Diálogos y escenas: se pasan pulsando A (y START de vez en cuando, que cierra la pantalla de poner nombre).
- Combates: los decide una política aparte (combate.py); por defecto, el ataque más potente con PP. Es el
  hueco donde va la IA que aprende a combatir.
- Curarse: si el equipo baja de VIDA_MINIMA, antes de seguir va al Centro Pokémon más cercano.
"""
from src.piloto.combate import mejor_ataque
from src.piloto.rutas import DIRECCIONES, ruta
from src.utils.mapas import HIERBA, MAPAS, POR_NOMBRE

VIDA_MINIMA = 0.35          # por debajo, primero a curarse
VIDA_CURADO = 0.95
PP_MINIMOS = 0.15           # sin PP en los ataques de daño no se gana ningún combate
START_CADA = 30             # pulsaciones de diálogo entre cada START
FALLOS_PARA_RODEAR = 2      # intentos sin moverse antes de dar la casilla por bloqueada
PASOS_BLOQUEO = 40          # decisiones que dura ese bloqueo (los personajes se mueven)
COLL_COUNTER = 0x90
SPRITE_NURSE = None         # se deduce: el primer personaje de cada Centro Pokémon es la enfermera


class Objetivo:
    """Algo que conseguir. `hecho(juego)` dice si ya está; `destino` dice a dónde ir para conseguirlo:
    ("mapa", NOMBRE): entrar en ese mapa; ("casilla", NOMBRE, (x, y)): pisar esa casilla;
    ("hablar", NOMBRE, (x, y)): ponerse junto a esa casilla (o al otro lado de un mostrador) y pulsar A;
    ("hierba",): andar por la hierba alta más cercana (para entrenar con los combates salvajes)."""

    def __init__(self, nombre, hecho, destino):
        self.nombre, self.hecho, self.destino = nombre, hecho, destino


def casillas_para_hablar(mapa, x, y):
    """{(casilla del jugador): dirección en la que mirar} para hablar con lo que hay en (x, y)."""
    opciones = {}
    for direccion, (dx, dy) in DIRECCIONES.items():
        px, py = x - dx, y - dy                     # pegado, mirando hacia (x, y)
        if mapa.andable(px, py):
            opciones[(px, py)] = direccion
        elif mapa.colision_en(px, py) == COLL_COUNTER and mapa.andable(px - dx, py - dy):
            opciones[(px - dx, py - dy)] = direccion  # al otro lado del mostrador
    return opciones


class Piloto:
    def __init__(self, juego, politica_combate=None, registro=print):
        self.juego = juego
        self.politica_combate = politica_combate or mejor_ataque
        self.registro = registro
        self.plan = None
        self.bloqueadas = {}        # nodo -> decisiones que le quedan bloqueado
        self.fallos = 0
        self.pulsaciones_escena = 0
        self.decisiones = 0
        self.estaba_en_combate = False
        self.combates = {"ganados": 0, "perdidos": 0}
        self.ultimo_mapa = None

    # ------------------------------------------------------------- destinos
    def _destino(self, destino):
        """(es_destino(nodo), mirar) para un destino de Objetivo; mirar = {casilla: dirección} o None."""
        tipo = destino[0]
        if tipo == "hierba":        # otra casilla de hierba distinta de la actual: así no se queda quieto
            aqui = self.juego.nodo()
            return (lambda n: n != aqui and MAPAS[n[0]].colision_en(n[1], n[2]) in HIERBA), None
        mapa = POR_NOMBRE[destino[1]]
        if tipo == "mapa":
            return (lambda n: n[0] == mapa.clave), None
        if tipo == "casilla":
            return (lambda n: n == (mapa.clave,) + tuple(destino[2])), None
        opciones = casillas_para_hablar(mapa, *destino[2])
        return (lambda n: n[0] == mapa.clave and n[1:] in opciones), opciones

    def _centro_pokemon(self):
        """Destino para curarse: delante de la enfermera del Centro Pokémon más cercano."""
        centros = {}
        for mapa in MAPAS.values():
            if mapa.nombre.endswith("POKECENTER_1F") and mapa.objetos:
                enfermera = mapa.objetos[0]
                for casilla, direccion in casillas_para_hablar(mapa, enfermera["x"], enfermera["y"]).items():
                    centros[(mapa.clave,) + casilla] = direccion
        return (lambda n: n in centros), {n: d for n, d in centros.items()}

    # --------------------------------------------------------------- bucle
    def conseguir(self, objetivo, max_decisiones=20_000):
        """Juega hasta que objetivo.hecho(juego). Devuelve True si lo consigue."""
        inicio = self.decisiones
        while not objetivo.hecho(self.juego):
            if self.decisiones - inicio >= max_decisiones:
                return False
            self.decidir(objetivo)
        return True

    def decidir(self, objetivo):
        j = self.juego
        self.decisiones += 1
        self.bloqueadas = {n: k - 1 for n, k in self.bloqueadas.items() if k > 1}
        if j.en_combate():
            if not self.estaba_en_combate:
                self.estaba_en_combate, self.vida_antes = True, j.vida()
            self.plan = None
            self.politica_combate(j)
            return
        if self.estaba_en_combate:
            self.estaba_en_combate = False
            resultado = "perdidos" if j.vida() <= 0 else "ganados"
            self.combates[resultado] += 1
        if j.en_escena():
            self.plan = None
            self.pulsaciones_escena += 1
            j.pulsar("start" if self.pulsaciones_escena % START_CADA == 0 else "a", 6, 10)
            return
        self.pulsaciones_escena = 0
        nodo = j.nodo()
        if nodo is None:            # entre dos mapas
            j.esperar(8)
            return
        if nodo[0] != self.ultimo_mapa:
            self.ultimo_mapa = nodo[0]
            self.registro(f"  [{j.tiempo_juego():7.1f} s] {MAPAS[nodo[0]].nombre}")

        curarse = j.equipo() > 0 and (j.vida() < VIDA_MINIMA or j.pp() < PP_MINIMOS)
        if curarse or getattr(self, "curando", False):
            self.curando = j.vida() < VIDA_CURADO or j.pp() < 0.9
        es_destino, mirar = self._centro_pokemon() if getattr(self, "curando", False) else self._destino(objetivo.destino)
        self.plan_tipo = objetivo.destino[0]
        if self.plan_tipo == "hierba" and not getattr(self, "curando", False):
            self.plan = None        # el destino cambia a cada paso

        if not self.plan or self.plan_origen != nodo:
            ocupadas = {(nodo[0], x, y) for x, y in j.personajes()} | set(self.bloqueadas)
            self.plan = ruta(nodo, es_destino, ocupadas - {nodo})
            if self.plan is None:   # sin camino con esos bloqueos: se olvidan y se espera un poco
                self.plan = ruta(nodo, es_destino)
                self.bloqueadas.clear()
                j.pulsar("b")
                if self.plan is None:
                    raise RuntimeError(f"No hay camino desde {MAPAS[nodo[0]].nombre} {nodo[1:]} hasta {objetivo.destino}")
        if not self.plan:           # en el destino
            self._actuar_en_destino(nodo, mirar)
            return
        self._dar_paso(nodo)

    def _actuar_en_destino(self, nodo, mirar):
        j = self.juego
        if mirar is None:           # bastaba con llegar; si el objetivo sigue sin cumplirse, A
            if self.plan_tipo != "hierba":
                j.pulsar("a")
            return
        direccion = mirar.get(nodo, mirar.get(nodo[1:]))
        if j.mirando() != direccion:
            j.pulsar(direccion, 4, 12)   # toque corto: solo gira
        else:
            j.pulsar("a")

    def _dar_paso(self, nodo):
        j = self.juego
        direccion, esperado = self.plan[0]
        empezado = j.andar(direccion)
        # Un paso normal ya está hecho; una puerta, un salto o un cambio de mapa tardan más
        espera = 0
        limite = 200 if empezado and (esperado[0] != nodo[0]
                                      or abs(esperado[1] - nodo[1]) + abs(esperado[2] - nodo[2]) > 1) else 0
        while j.nodo() != esperado and espera < limite and not (j.en_escena() or j.en_combate()):
            j.esperar(4)
            espera += 4
        ahora = j.nodo()
        if ahora == esperado:
            self.plan.pop(0)
            self.plan_origen, self.fallos = esperado, 0
        elif ahora == nodo:          # no se ha movido: hay algo delante
            self.fallos += 1
            self.plan_origen = nodo
            if self.fallos >= FALLOS_PARA_RODEAR:
                self.bloqueadas[esperado] = PASOS_BLOQUEO
                self.plan, self.fallos = None, 0
                j.pulsar("b")       # por si había un menú abierto
        else:                        # el juego lo ha llevado a otro sitio: se recalcula
            self.plan, self.fallos = None, 0
