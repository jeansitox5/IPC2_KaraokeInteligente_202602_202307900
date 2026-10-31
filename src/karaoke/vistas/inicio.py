"""
inicio.py - Menú principal (primer nivel).

(m) manual  (a) automático  (f) alimentación  (p) programa
(w) listar  (x) ver letra   (u) corregir     (b) borrar
(k) configuración (d) diagnóstico  -> opciones agregadas
En Windows también se puede escribir la letra en "Tecla rápida".
"""
import toga
from toga.style import Pack

from karaoke.vistas.base import (
    AZUL, GRIS, NARANJA, TEXTO_GRIS, VERDE, Pantalla, boton, es_movil, etiqueta, rejilla,
)


class PantallaInicio(Pantalla):
    titulo = "Karaoke Inteligente"

    def opciones(self):
        from karaoke.vistas.alimentacion import PantallaAlimentacion
        from karaoke.vistas.configuracion import PantallaConfiguracion
        from karaoke.vistas.consultas import (
            PantallaBorrar, PantallaCorregir, PantallaListado, PantallaVerLetra,
        )
        from karaoke.vistas.diagnostico import PantallaDiagnostico
        from karaoke.vistas.modo_automatico import PantallaModoAutomatico
        from karaoke.vistas.modo_manual import PantallaModoManual
        from karaoke.vistas.programa import PantallaPrograma

        return [
            ("m", "Modo manual", PantallaModoManual, VERDE),
            ("a", "Modo automático", PantallaModoAutomatico, VERDE),
            ("f", "Alimentación", PantallaAlimentacion, AZUL),
            ("p", "Programa del cantante", PantallaPrograma, AZUL),
            ("w", "Listar canciones", PantallaListado, AZUL),
            ("x", "Ver letra por código", PantallaVerLetra, AZUL),
            ("u", "Corregir letra", PantallaCorregir, AZUL),
            ("b", "Borrar canción", PantallaBorrar, NARANJA),
            ("k", "Configuración", PantallaConfiguracion, GRIS),
            ("d", "Diagnóstico", PantallaDiagnostico, GRIS),
        ]

    def construir(self):
        self._mapa = {}
        botones = []
        for letra, texto, clase, color in self.opciones():
            self._mapa[letra] = clase
            botones.append(boton(f"({letra})  {texto}", self._abrir(clase), color=color))

        canciones, lineas = self.app.canciones.contar()
        total, pendientes = self.app.programa.resumen()
        resumen = f"Base de datos: {canciones} canciones · {lineas} líneas"
        if total:
            resumen += f" · Programa: {pendientes} de {total} pendientes"

        hijos = [
            etiqueta("Karaoke Inteligente", 24, negrita=True, color=AZUL),
            etiqueta(resumen, 11, color=TEXTO_GRIS),
            rejilla(botones, 2),
        ]
        if not es_movil():
            self.tecla = toga.TextInput(
                placeholder="Tecla rápida: escriba la letra de la opción",
                on_change=self._tecla,
                style=Pack(margin_top=6),
            )
            hijos.append(self.tecla)
        hijos.append(etiqueta(self.app.mensaje_bd, 10, color=TEXTO_GRIS))
        hijos.append(etiqueta("IPC2 · USAC · 202307900", 9, color=TEXTO_GRIS))
        return self.desplazable(*hijos)

    def _abrir(self, clase):
        def abrir(widget):
            self.app.mostrar(clase(self.app))
        return abrir

    def _tecla(self, widget):
        valor = widget.value
        if not valor:
            return
        letra = valor.strip().lower()[-1:]
        widget.value = ""
        if letra in self._mapa:
            self.app.mostrar(self._mapa[letra](self.app))
