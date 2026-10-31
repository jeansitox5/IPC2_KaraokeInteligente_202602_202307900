"""
Karaoke Inteligente - IPC2, USAC
Punto de entrada de la aplicación Toga.

Fase 0: esqueleto que comprueba que Toga y Briefcase funcionan.
Muestra la plataforma detectada para confirmar que el mismo código
corre en Windows y, en la Fase 0-B, en Android.
"""
import platform

import toga
from toga.style import Pack
from toga.style.pack import CENTER, COLUMN


class KaraokeInteligente(toga.App):
    """Aplicación principal del Karaoke Inteligente."""

    def startup(self):
        """Toga llama a este método una sola vez, al iniciar la app."""
        titulo = toga.Label(
            "Karaoke Inteligente",
            style=Pack(font_size=24, font_weight="bold", text_align=CENTER),
        )
        # self.version viene de pyproject.toml: una sola fuente de verdad.
        subtitulo = toga.Label(
            f"Versión {self.version} · esqueleto (Fase 0)",
            style=Pack(font_size=12, text_align=CENTER),
        )
        info = toga.Label(
            f"Plataforma: {toga.platform.current_platform} · "
            f"Python {platform.python_version()}",
            style=Pack(font_size=11, text_align=CENTER),
        )
        boton = toga.Button(
            "Probar evento",
            on_press=self.al_presionar_probar,
            style=Pack(margin_top=16, height=48, width=220),
        )

        contenido = toga.Box(
            children=[titulo, subtitulo, info, boton],
            style=Pack(direction=COLUMN, margin=24, gap=8, align_items=CENTER),
        )

        self.main_window = toga.MainWindow(title=self.formal_name)
        self.main_window.content = contenido
        self.main_window.show()

    async def al_presionar_probar(self, widget):
        """Manejador del botón: confirma que los eventos funcionan."""
        await self.main_window.dialog(
            toga.InfoDialog(
                "Funciona",
                "Los eventos de Toga responden correctamente.",
            )
        )


def main():
    """Briefcase y __main__.py llaman a esta función para crear la app."""
    return KaraokeInteligente()
