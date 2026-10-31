"""
karaoke.py - Vista compartida por los modos manual y automático.

    estado · canción
    línea anterior        (gris)
    LÍNEA ACTUAL          (grande, resaltada)
    siguiente línea
    la que viene después  (gris)
    información · mensaje
    botones (c) (a) (l) (r) (i) (s) (n) (f) ...
"""
import textwrap

import toga
from toga.style import Pack
from toga.style.pack import COLUMN

from karaoke.vistas.base import (
    AZUL, CLARO, TEXTO_GRIS, VERDE, boton, es_movil, etiqueta, fila, rejilla, tam,
)


class VistaKaraoke:
    def __init__(self, app, acciones, extras=None):
        """acciones = [(letra, texto, función, color), ...]"""
        self.app = app
        self.acciones = {letra: funcion for letra, _, funcion, _ in acciones}
        cfg = app.cfg
        self.ancho = 15 if es_movil() else max(30, min(int(cfg["CARACTERES_PROMEDIO_LINEA"] * 0.7), 70))

        self.lbl_estado = etiqueta("", 11, negrita=True, color=VERDE, flex=1)
        self.lbl_cancion = etiqueta("", 13, negrita=True, color=AZUL, flex=1)
        self.lbl_anterior = etiqueta("", 14, color=TEXTO_GRIS, flex=1)
        self.lbl_actual = toga.Label(
            "",
            style=Pack(font_size=tam(24), font_weight="bold", color=AZUL,
                       background_color=CLARO, margin=(10, 8), flex=1),
        )
        self.lbl_sig1 = etiqueta("", 16, flex=1)
        self.lbl_sig2 = etiqueta("", 14, color=TEXTO_GRIS, flex=1)
        self.lbl_info = etiqueta("", 10, color=TEXTO_GRIS, flex=1)
        self.lbl_mensaje = etiqueta("", 11, color=AZUL, flex=1)

        botones = [
            boton(f"({letra}) {texto}", self._presionar(letra), color=color)
            for letra, texto, _, color in acciones
        ]
        hijos = [
            fila(self.lbl_estado), fila(self.lbl_cancion), fila(self.lbl_anterior),
            fila(self.lbl_actual), fila(self.lbl_sig1), fila(self.lbl_sig2),
            fila(self.lbl_info), fila(self.lbl_mensaje),
            rejilla(botones, 1 if es_movil() else 4),
        ]
        if not es_movil():
            self.tecla = toga.TextInput(
                placeholder="Tecla rápida: escriba c, a, l, r, i, s, n, f…", on_change=self._tecla
            )
            hijos.append(self.tecla)
        if extras:
            hijos.extend(extras)
        self.widget = toga.Box(children=hijos, style=Pack(direction=COLUMN, gap=6))

    def _presionar(self, letra):
        def manejador(widget):
            self.acciones[letra]()
        return manejador

    def _tecla(self, widget):
        valor = widget.value
        if not valor:
            return
        letra = valor.strip().lower()[-1:]
        widget.value = ""
        if letra in self.acciones:
            self.acciones[letra]()

    def _envolver(self, texto, ancho):
        return textwrap.fill(texto, width=ancho) if texto else ""

    def mostrar(self, nombre="", codigo=None, lineas=None, idx=None, estado="", info="", mensaje=""):
        nombre_cancion = f"[{codigo}] {nombre}" if codigo is not None else nombre
        self.lbl_estado.text = self._envolver(estado, self.ancho + 12)
        self.lbl_cancion.text = self._envolver(nombre_cancion, self.ancho + 10)
        lineas = lineas or []
        if idx is None or not lineas:
            self.lbl_anterior.text = ""
            self.lbl_actual.text = "…"
            self.lbl_sig1.text = ""
            self.lbl_sig2.text = ""
        else:
            def linea(i):
                return lineas[i] if 0 <= i < len(lineas) else ""
            self.lbl_anterior.text = self._envolver(linea(idx - 1), self.ancho + 10)
            self.lbl_actual.text = self._envolver(linea(idx).upper(), self.ancho)
            self.lbl_sig1.text = self._envolver(linea(idx + 1), self.ancho + 6)
            self.lbl_sig2.text = self._envolver(linea(idx + 2), self.ancho + 10)
        self.lbl_info.text = self._envolver(info, self.ancho + 12)
        self.lbl_mensaje.text = self._envolver(mensaje, self.ancho + 10)
