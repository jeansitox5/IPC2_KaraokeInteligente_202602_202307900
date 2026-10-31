"""
plataforma.py - Todo lo que depende del sistema operativo.

El resto del programa pregunta aquí "¿estoy en Android?" en lugar de revisar
el sistema por su cuenta. Así lo específico de cada plataforma queda aislado.
"""
import asyncio
import platform
import sys

import toga


def nombre():
    """'android', 'windows', 'linux', 'macOS'... según Toga."""
    return toga.platform.current_platform


def es_android():
    return nombre() == "android"


def es_windows():
    return nombre() == "windows"


def describir():
    return f"{nombre()} · Python {platform.python_version()}"


def leer_bytes_como_texto(datos: bytes) -> str:
    """Decodifica un archivo de texto: UTF-8 (con o sin BOM) o, si falla, latin-1
    (archivos guardados con el Bloc de notas antiguo)."""
    try:
        return datos.decode("utf-8-sig")
    except UnicodeDecodeError:
        return datos.decode("latin-1")


# ---------------------------------------------------------------- archivos
async def elegir_archivo_texto(app):
    """Abre el selector de archivos del sistema.

    Devuelve (nombre_archivo, texto) o None si el usuario cancela.
    - Windows: diálogo de Toga.
    - Android: Toga no implementa ese diálogo, así que se usa el selector de
      Android (Intent ACTION_GET_CONTENT) y se lee el contenido con el
      ContentResolver (Android no deja abrir rutas libremente).
    """
    if es_android():
        return await _elegir_archivo_android(app)
    ruta = await app.main_window.dialog(
        toga.OpenFileDialog("Elegir archivo de texto", file_types=None)
    )
    if not ruta:
        return None
    with open(ruta, "rb") as f:
        return (str(ruta), leer_bytes_como_texto(f.read()))


async def _elegir_archivo_android(app):  # pragma: no cover - solo en Android
    from android.app import Activity
    from android.content import Intent
    from java import jarray, jbyte

    intent = Intent(Intent.ACTION_GET_CONTENT)
    intent.addCategory(Intent.CATEGORY_OPENABLE)
    intent.setType("*/*")

    futuro = asyncio.get_running_loop().create_future()

    def al_terminar(codigo, datos):
        if not futuro.done():
            futuro.set_result((codigo, datos))

    app._impl.start_activity(
        Intent.createChooser(intent, "Elegir archivo de texto"), on_complete=al_terminar
    )
    codigo, datos = await futuro
    if codigo != Activity.RESULT_OK or datos is None or datos.getData() is None:
        return None
    uri = datos.getData()
    contexto = app._impl.native
    flujo = contexto.getContentResolver().openInputStream(uri)
    partes = []
    buf = jarray(jbyte)(64 * 1024)
    while True:
        n = flujo.read(buf)
        if n == -1:
            break
        partes.append(bytes(buf)[:n])
    flujo.close()
    nombre_archivo = uri.getLastPathSegment() or "archivo"
    return (str(nombre_archivo), leer_bytes_como_texto(b"".join(partes)))


# ---------------------------------------------------------------- micrófono
PERMISO_MICROFONO = "android.permission.RECORD_AUDIO"


def tiene_permiso_microfono(app):
    if not es_android():
        return True
    from android.content.pm import PackageManager  # pragma: no cover

    return (  # pragma: no cover
        app._impl._native_checkSelfPermission(PERMISO_MICROFONO)
        == PackageManager.PERMISSION_GRANTED
    )


async def pedir_permiso_microfono(app):
    """En Android muestra el diálogo del sistema para el micrófono.
    Devuelve True si queda concedido. En Windows siempre es True."""
    if tiene_permiso_microfono(app):
        return True
    from android.content.pm import PackageManager  # pragma: no cover

    futuro = asyncio.get_running_loop().create_future()  # pragma: no cover

    def al_terminar(permisos, resultados):  # pragma: no cover
        concedido = dict(zip(permisos, resultados)).get(PERMISO_MICROFONO)
        if not futuro.done():
            futuro.set_result(concedido == PackageManager.PERMISSION_GRANTED)

    app._impl.request_permissions([PERMISO_MICROFONO], on_complete=al_terminar)  # pragma: no cover
    return await futuro  # pragma: no cover


def python_info():
    return sys.version.split()[0]
