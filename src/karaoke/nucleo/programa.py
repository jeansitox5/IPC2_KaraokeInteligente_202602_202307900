"""
programa.py - Opción (p): programa tentativo del cantante.

Lee la lista de nombres, la relaciona con las canciones de la base y la guarda
en la tabla PROGRAMA. El orden NO es obligatorio: los modos manual y automático
solo SUGIEREN o dan prioridad a la siguiente pendiente.
"""
from difflib import SequenceMatcher

from karaoke.nucleo.texto import normalizar, parsear_programa


def relacionar_nombre(nombre, canciones_repo):
    """Devuelve el código de la canción con ese nombre (exacto, parcial o
    parecido >= 0.8) o None."""
    exacto = canciones_repo.existe_nombre(nombre)
    if exacto:
        return exacto
    parciales = canciones_repo.resolver(nombre)
    if len(parciales) == 1:
        return parciales[0]["codigo"]
    norm = normalizar(nombre)
    mejor, mejor_puntaje = None, 0.0
    for codigo, (nombre_bd, _) in canciones_repo.todas_con_lineas().items():
        p = SequenceMatcher(None, norm, normalizar(nombre_bd)).ratio()
        if p > mejor_puntaje:
            mejor, mejor_puntaje = codigo, p
    return mejor if mejor_puntaje >= 0.8 else None


def cargar_programa(texto, programa_repo, canciones_repo):
    """Guarda el programa. Devuelve (total, encontradas, [no_encontradas])."""
    nombres = parsear_programa(texto)
    elementos = [(n, relacionar_nombre(n, canciones_repo)) for n in nombres]
    programa_repo.reemplazar(elementos)
    no_encontradas = [n for n, c in elementos if c is None]
    return len(elementos), len(elementos) - len(no_encontradas), no_encontradas
