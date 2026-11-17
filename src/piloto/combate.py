"""Políticas de combate: qué botón pulsar en cada momento de un combate.

Una política es una función (juego) -> None que pulsa un botón. `mejor_ataque` es la de referencia: elige el
ataque de más potencia al que le queden PP. Aquí es donde encaja la IA que aprenda a combatir (qué ataque usar
contra cada rival, cuándo cambiar o curarse): basta con pasar otra política al Piloto.
"""
from src.utils import rom_catalog

# WRAM banco 0 (símbolos de pret/pokegold)
ADDR_BATTLE_MON_MOVES, ADDR_BATTLE_MON_PP = 0xCB0E, 0xCB14
ADDR_MENU_ROWS, ADDR_MENU_COLS, ADDR_MENU_CURSOR_Y, ADDR_MENU_CURSOR_X = 0xCEDA, 0xCEDB, 0xCEE0, 0xCEE1


def ataques(juego):
    """[(hueco, id, potencia, pp)] de los ataques del Pokémon que está combatiendo."""
    lista = []
    for hueco in range(4):
        ataque = juego.pb.memory[ADDR_BATTLE_MON_MOVES + hueco]
        if ataque:
            potencia = rom_catalog.MOVES.get(ataque, ("?", 0, 0))[1]
            lista.append((hueco, ataque, potencia, juego.pb.memory[ADDR_BATTLE_MON_PP + hueco] & 0x3F))
    return lista


def mejor_ataque(juego):
    """Ataca con el movimiento de más potencia que tenga PP. Si no queda ninguno, A (el juego usa Forcejeo)."""
    mis_ataques = ataques(juego)
    con_pp = [(potencia, -hueco) for hueco, _, potencia, pp in mis_ataques if potencia > 0 and pp > 0]
    if not con_pp:
        juego.pulsar("a", 6, 10)
        return
    elegido = -max(con_pp)[1]
    filas, columnas = juego.pb.memory[ADDR_MENU_ROWS], juego.pb.memory[ADDR_MENU_COLS]
    cursor = juego.pb.memory[ADDR_MENU_CURSOR_Y]
    # Menú principal (LUCHA / PKMN / MOCHILA / ESC, 2 x 2): el cursor tiene que estar en LUCHA
    if columnas == 2 and filas == 2:
        if cursor != 1:
            juego.pulsar("up", 4, 8)
        elif juego.pb.memory[ADDR_MENU_CURSOR_X] != 1:
            juego.pulsar("left", 4, 8)
        else:
            juego.pulsar("a", 6, 10)
        return
    # Menú de ataques: una columna con tantas filas como ataques. Esos valores se quedan puestos al cerrarse
    # el menú, así que si el cursor no responde es que hay un texto delante y lo que toca es A
    if columnas == 1 and filas == len(mis_ataques) and cursor - 1 != elegido:
        juego.pulsar("down", 4, 8)
        if juego.pb.memory[ADDR_MENU_CURSOR_Y] != cursor:
            return
    juego.pulsar("a", 6, 10)


def atacar_siempre(juego):
    """La política más simple: A en todo (LUCHAR y el ataque que esté marcado)."""
    juego.pulsar("a", 6, 10)
