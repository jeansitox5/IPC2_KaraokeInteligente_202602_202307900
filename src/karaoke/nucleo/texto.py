"""
texto.py - Utilidades de texto compartidas por todo el programa.

normalizar("¡Corazón, AQUÍ!")  ->  "corazon aqui"
Se usa para comparar lo que se escucha o teclea con las letras guardadas,
sin que importen mayúsculas, tildes ni signos.
"""
import re
import unicodedata

_NO_ALFANUM = re.compile(r"[^0-9a-z]+")


def normalizar(texto: str) -> str:
    if not texto:
        return ""
    texto = unicodedata.normalize("NFD", texto.lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")  # quita tildes
    return _NO_ALFANUM.sub(" ", texto).strip()


def palabras(texto: str) -> list:
    return normalizar(texto).split()


def partir_linea(linea: str, maximo: int) -> list:
    """Parte una línea demasiado larga en el espacio más cercano al límite."""
    linea = " ".join(linea.split())
    if maximo <= 0 or len(linea) <= maximo:
        return [linea] if linea else []
    partes = []
    while len(linea) > maximo:
        corte = linea.rfind(" ", 0, maximo + 1)
        if corte <= 0:
            corte = maximo
        partes.append(linea[:corte].strip())
        linea = linea[corte:].strip()
    if linea:
        partes.append(linea)
    return partes


def preparar_lineas(lineas, maximo: int) -> list:
    """Limpia espacios, quita líneas vacías y parte las largas."""
    resultado = []
    for linea in lineas:
        resultado.extend(partir_linea(linea, maximo))
    return resultado


def parsear_canciones(texto: str) -> list:
    """Formato del archivo para la opción (t):

        Nombre de la canción
        primera línea
        segunda línea
        <línea en blanco>
        Otra canción
        ...

    Devuelve [(nombre, [lineas]), ...]. Un bloque sin letra se devuelve con
    lista vacía para que el importador lo reporte.
    """
    canciones = []
    bloque = []
    for cruda in texto.splitlines() + [""]:
        linea = cruda.strip()
        if linea:
            bloque.append(linea)
        elif bloque:
            canciones.append((bloque[0], bloque[1:]))
            bloque = []
    return canciones


def parsear_programa(texto: str) -> list:
    """PROGRAMA: un nombre de canción por línea; vacías y # comentarios se ignoran."""
    return [
        l.strip() for l in texto.splitlines() if l.strip() and not l.strip().startswith("#")
    ]
