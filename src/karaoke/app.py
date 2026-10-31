"""
Karaoke Inteligente - IPC2, USAC (202307900)

Punto de entrada de la aplicación Toga. Al iniciar:
  1. Detecta/crea la base CANCIONES (carpeta de datos de la app).
  2. Carga la configuración y las letras en el buscador.
  3. Muestra el menú principal.

La App también funciona como "contexto": las pantallas y la lógica acceden a
los repositorios, al buscador y a la configuración a través de ella.
"""
import toga

from karaoke import plataforma
from karaoke.config import Configuracion
from karaoke.datos.base_datos import BaseDatos
from karaoke.datos.canciones_repo import CancionesRepo
from karaoke.datos.config_repo import ConfigRepo
from karaoke.datos.programa_repo import ProgramaRepo
from karaoke.datos.temporales_repo import TemporalesRepo
from karaoke.nucleo.buscador import Buscador


class KaraokeInteligente(toga.App):
    """Aplicación principal del Karaoke Inteligente."""

    def startup(self):
        # ---- datos
        self.db = BaseDatos(self.paths.data)
        self.mensaje_bd = self.db.mensaje
        self.canciones = CancionesRepo(self.db)
        self.programa = ProgramaRepo(self.db)
        self.temporales = TemporalesRepo(self.db)
        self.cfg = Configuracion(ConfigRepo(self.db))
        self.buscador = Buscador()
        self.recargar_buscador()

        # ---- ventana
        self.pantalla = None
        self.main_window = toga.MainWindow(title=self.formal_name, size=(1000, 760))
        from karaoke.vistas.inicio import PantallaInicio

        self.mostrar(PantallaInicio(self))
        self.main_window.show()

    # ------------------------------------------------------------ navegación
    def mostrar(self, pantalla):
        """Cambia el contenido de la ventana por otra pantalla."""
        if self.pantalla is not None:
            self.pantalla.al_salir()
        self.pantalla = pantalla
        self.main_window.content = pantalla.construir()
        self.loop.create_task(pantalla.al_mostrar())

    def recargar_buscador(self):
        self.buscador.cargar(self.canciones.todas_con_lineas())

    # ------------------------------------------------------------ motor de voz
    async def crear_motor(self, forzado=None):
        """Crea el motor de voz según la configuración (patrón Estrategia)."""
        from karaoke.audio.motor_voz import MotorSimulado

        tipo = forzado or self.cfg["MOTOR_VOZ"]
        if tipo == "auto":
            tipo = "android" if plataforma.es_android() else "whisper"
        if tipo == "simulado":
            return MotorSimulado()
        if tipo == "android":
            from karaoke.audio.voz_android import MotorAndroid
            return MotorAndroid(self, self.cfg)
        ruta_wav = None
        if tipo == "archivo":
            ruta_wav = await self.main_window.dialog(
                toga.OpenFileDialog("Elegir grabación WAV", file_types=["wav"])
            )
            if not ruta_wav:
                return None
        from karaoke.audio.whisper_win import MotorWhisper
        return MotorWhisper(self.cfg, self.paths.app / "resources" / "whisper", ruta_wav)

    # ------------------------------------------------------------ salida
    def on_exit(self):
        if self.pantalla is not None:
            self.pantalla.al_salir()
        self.db.cerrar()
        return True


def main():
    return KaraokeInteligente()
