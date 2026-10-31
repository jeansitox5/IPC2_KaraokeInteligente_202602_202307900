"""
base.py - Piezas comunes de todas las pantallas (estilos, botones, encabezado).

Cada pantalla hereda de Pantalla e implementa construir(), que devuelve el
contenido que se coloca en la ventana principal.
"""
import toga
from toga.style import Pack
from toga.style.pack import CENTER, COLUMN, ROW

from karaoke import plataforma

AZUL = "#1F3A5F"
VERDE = "#2A9D8F"
NARANJA = "#E76F51"
GRIS = "#55657A"
AMARILLO = "#F4B860"
CLARO = "#E6F4F1"
TEXTO_GRIS = "#6B7785"


def es_movil():
    return plataforma.es_android()


def tam(base):
    """Tamaño de letra: un poco más grande en el teléfono."""
    return base + 2 if es_movil() else base


def etiqueta(texto="", tamano=13, negrita=False, color=None, centrado=False, fondo=None, flex=0):
    estilo = Pack(font_size=tam(tamano), flex=flex)
    if negrita:
        estilo.font_weight = "bold"
    if color:
        estilo.color = color
    if fondo:
        estilo.background_color = fondo
    if centrado:
        estilo.text_align = CENTER
    return toga.Label(texto, style=estilo)


def boton(texto, accion, color=AZUL, flex=1, alto=None, texto_color="white"):
    return toga.Button(
        texto,
        on_press=accion,
        style=Pack(
            flex=flex,
            height=alto or (52 if es_movil() else 40),
            background_color=color,
            color=texto_color,
            font_weight="bold",
            font_size=tam(11),
        ),
    )


def fila(*widgets, gap=8):
    return toga.Box(children=list(widgets), style=Pack(direction=ROW, gap=gap))


def columna(*widgets, gap=8, margin=0):
    return toga.Box(children=list(widgets), style=Pack(direction=COLUMN, gap=gap, margin=margin))


def rejilla(widgets, columnas):
    filas = []
    for i in range(0, len(widgets), columnas):
        grupo = list(widgets[i:i + columnas])
        while len(grupo) < columnas:  # relleno para que todas las columnas midan igual
            grupo.append(toga.Box(style=Pack(flex=1)))
        filas.append(fila(*grupo))
    return columna(*filas)


def entrada(placeholder="", al_confirmar=None, flex=1, valor=""):
    estilo = Pack(flex=flex, font_size=tam(12))
    if es_movil():
        estilo.height = 52
    return toga.TextInput(value=valor, placeholder=placeholder, on_confirm=al_confirmar, style=estilo)


def area_texto(valor="", placeholder="", alto=220):
    return toga.MultilineTextInput(
        value=valor, placeholder=placeholder, style=Pack(height=alto, font_size=tam(12))
    )


class Pantalla:
    titulo = ""

    def __init__(self, app):
        self.app = app

    # Cada pantalla define su contenido
    def construir(self):
        raise NotImplementedError

    async def al_mostrar(self):
        """Se ejecuta después de mostrar la pantalla (puede ser asíncrono)."""

    def al_salir(self):
        """Se ejecuta antes de cambiar a otra pantalla."""

    # ---------------------------------------------------------- utilidades
    def encabezado(self, titulo=None, volver=True):
        hijos = []
        if volver:
            hijos.append(boton("← Menú", self.ir_menu, color=GRIS, flex=0, alto=None))
        hijos.append(etiqueta(titulo or self.titulo, 18, negrita=True, color=AZUL, flex=1))
        return toga.Box(children=hijos, style=Pack(direction=ROW, gap=12, align_items=CENTER, margin_bottom=8))

    def desplazable(self, *widgets, margin=16):
        caja = toga.Box(children=list(widgets), style=Pack(direction=COLUMN, gap=10, margin=margin))
        return toga.ScrollContainer(content=caja, horizontal=False, style=Pack(flex=1))

    def ir_menu(self, widget=None):
        from karaoke.vistas.inicio import PantallaInicio

        self.app.mostrar(PantallaInicio(self.app))

    async def info(self, titulo, mensaje):
        await self.app.main_window.dialog(toga.InfoDialog(titulo, mensaje))

    async def error(self, titulo, mensaje):
        await self.app.main_window.dialog(toga.ErrorDialog(titulo, mensaje))

    async def confirmar(self, titulo, mensaje):
        return await self.app.main_window.dialog(toga.ConfirmDialog(titulo, mensaje))


class Paginador:
    """Controla grupos de N elementos (de 10 en 10 por defecto)."""

    def __init__(self, total, por_pagina):
        self.total = total
        self.por_pagina = max(1, por_pagina)
        self.pagina = 0

    @property
    def paginas(self):
        return max(1, -(-self.total // self.por_pagina))

    @property
    def desplazamiento(self):
        return self.pagina * self.por_pagina

    def siguiente(self):
        if self.pagina < self.paginas - 1:
            self.pagina += 1

    def anterior(self):
        if self.pagina > 0:
            self.pagina -= 1

    def texto(self):
        return f"Grupo {self.pagina + 1} de {self.paginas}"
