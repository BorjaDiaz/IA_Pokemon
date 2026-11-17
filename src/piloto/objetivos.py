"""Lista de objetivos de la historia, en orden. Cada uno se da por hecho con un evento del propio juego.

El piloto no sigue una ruta escrita a mano: cada objetivo solo dice a dónde hay que llegar o con quién hablar, y
el camino lo calcula el buscador sobre los mapas de la ROM. Los combates que salen por el camino (salvajes,
entrenadores, el rival) los resuelve la política de combate.
"""
from src.piloto.piloto import Objetivo


def evento(nombre):
    return lambda juego: juego.evento(nombre)


def nivel(minimo):
    return lambda juego: juego.nivel() >= minimo


OBJETIVOS = [
    # Laboratorio de Elm: la Poké Ball de Cyndaquil está en (6, 3)
    Objetivo("Pokémon inicial", evento("EVENT_GOT_A_POKEMON_FROM_ELM"), ("hablar", "ELMS_LAB", (6, 3))),
    # Al entrar en casa del Sr. Pokémon salta la escena en la que da el Huevo Misterioso
    Objetivo("Huevo Misterioso", evento("EVENT_GOT_MYSTERY_EGG_FROM_MR_POKEMON"), ("mapa", "MR_POKEMONS_HOUSE")),
    # De vuelta, en Ciudad Cerezo espera el rival; después, hablar con Elm (5, 2)
    Objetivo("Entregar el huevo a Elm", evento("EVENT_GAVE_MYSTERY_EGG_TO_ELM"), ("hablar", "ELMS_LAB", (5, 2))),
    # Primera medalla. Pegaso lleva un Pidgey de nivel 7 y un Pidgeotto de nivel 9
    Objetivo("Llegar a Ciudad Malva", lambda juego: juego.nodo() and juego.nodo()[0] == (10, 5), ("mapa", "VIOLET_CITY")),
    Objetivo("Entrenar hasta el nivel 13", nivel(13), ("hierba",)),
    Objetivo("Medalla Céfiro (Pegaso)", evento("EVENT_BEAT_FALKNER"), ("hablar", "VIOLET_GYM", (5, 1))),
]
