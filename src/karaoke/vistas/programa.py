"""
programa.py (vista) - Opción (p): alimentar el programa tentativo del cantante.
"""
import toga
from toga.style import Pack
from toga.style.pack import COLUMN

from karaoke import plataforma
from karaoke.nucleo.programa import cargar_programa
from karaoke.vistas.base import (
    AZUL, GRIS, NARANJA, TEXTO_GRIS, VERDE, Pantalla, area_texto, boton, etiqueta, fila,
)

SIMBOLOS = {"pendiente": "◻", "cantada": "✔", "saltada": "↷", "no_encontrada": "✖"}


class PantallaPrograma(Pantalla):
    titulo = "(p) Programa del cantante"

    def construir(self):
        self.pegado = area_texto(placeholder="…o pegue aquí los nombres (uno por línea)", alto=140)
        self.resultado = etiqueta("", 12, color=VERDE)
        self.lista = toga.Box(style=Pack(direction=COLUMN, gap=4))
        self._llenar()
        return self.desplazable(
            self.encabezado(),
            etiqueta("Archivo PROGRAMA: el nombre de cada canción en el orden en que se cantará. "
                     "El orden es una sugerencia: en los modos manual y automático se puede saltar, "
                     "repetir o cantar otra.", 11, color=TEXTO_GRIS),
            fila(boton("Elegir archivo PROGRAMA…", self._elegir),
                 boton("Cargar ejemplo", self._ejemplo, color=GRIS)),
            self.pegado,
            boton("Usar el texto pegado", self._pegado, color=VERDE),
            self.resultado,
            etiqueta("Programa actual:", 13, negrita=True, color=AZUL),
            self.lista,
            fila(boton("Reiniciar estados", self._reiniciar, color=GRIS),
                 boton("Vaciar programa", self._vaciar, color=NARANJA)),
        )

    def _llenar(self):
        self.lista.clear()
        filas = self.app.programa.listar()
        if not filas:
            self.lista.add(etiqueta("(no hay programa cargado)", 12, color=TEXTO_GRIS))
        for f in filas:
            nombre = f["nombre_cancion"] or f["nombre_texto"]
            codigo = f"[{f['codigo']}] " if f["codigo"] else ""
            self.lista.add(etiqueta(f"{f['posicion']}. {SIMBOLOS[f['estado']]} {codigo}{nombre} — {f['estado']}", 12))

    def _cargar(self, texto, origen):
        total, encontradas, faltan = cargar_programa(texto, self.app.programa, self.app.canciones)
        self.resultado.text = f"{origen}: {total} canciones, {encontradas} encontradas en la base."
        if faltan:
            self.resultado.text += "\nNo encontradas (cárguelas con (f) Alimentación): " + ", ".join(faltan)
        self._llenar()

    async def _elegir(self, widget):
        elegido = await plataforma.elegir_archivo_texto(self.app)
        if elegido:
            self._cargar(elegido[1], elegido[0])

    def _ejemplo(self, widget):
        ruta = self.app.paths.app / "resources" / "ejemplos" / "PROGRAMA.txt"
        self._cargar(ruta.read_text(encoding="utf-8"), "Ejemplo")

    def _pegado(self, widget):
        if (self.pegado.value or "").strip():
            self._cargar(self.pegado.value, "Texto pegado")

    def _reiniciar(self, widget):
        self.app.programa.reiniciar()
        self._llenar()

    async def _vaciar(self, widget):
        if await self.confirmar("Vaciar programa", "¿Borrar el programa actual?"):
            self.app.programa.vaciar()
            self._llenar()
