"""
modo_manual.py - Opción (m).

1. Si hay PROGRAMA, se sugiere la siguiente canción (se puede aceptar u omitir).
2. Si no, el operador escribe 2-3 palabras que escuchó; el buscador muestra las
   coincidencias (canción + línea) y el operador elige.
3. La letra se muestra desde esa línea y se avanza con (c).
Teclas: (c) continuar (a) atrás (l) línea igual (r) repetir canción
        (i) ignorar (s) seguir (n) otra canción (f) finalizar la sesión.
"""
import asyncio

import toga
from toga.style import Pack
from toga.style.pack import COLUMN

from karaoke.vistas.base import (
    AMARILLO, AZUL, GRIS, NARANJA, TEXTO_GRIS, VERDE, Pantalla, boton, entrada, etiqueta, fila,
)
from karaoke.vistas.karaoke import VistaKaraoke


class PantallaModoManual(Pantalla):
    titulo = "Modo manual"

    def __init__(self, app, codigo=None, linea=0, cantadas=0):
        super().__init__(app)
        self.codigo = codigo
        self.idx = linea
        self.cantadas = cantadas
        self.pausado = False
        self.repeticiones = 0
        self.mensaje = ""
        self.ultima = None

    def construir(self):
        self.cuerpo = toga.Box(style=Pack(direction=COLUMN, gap=10))
        if self.codigo is not None:
            self._mostrar_cancion()
        else:
            self._mostrar_busqueda()
        return self.desplazable(self.encabezado(), self.cuerpo)

    # ================================================================ búsqueda
    def _mostrar_busqueda(self):
        self.cuerpo.clear()
        sig = self.app.programa.siguiente_pendiente()
        if sig:
            self.cuerpo.add(etiqueta(f"Siguiente del programa: [{sig['codigo']}] {sig['nombre_cancion']}",
                                     13, negrita=True, color=AZUL))
            self.cuerpo.add(fila(
                boton("Cantar esta", lambda w: self._empezar(sig["codigo"], 0), color=VERDE),
                boton("Omitir del programa", lambda w: self._omitir(sig["posicion"]), color=GRIS),
            ))
        self.entrada = entrada("Escriba 2 o 3 palabras que escuchó", al_confirmar=self._buscar)
        self.cuerpo.add(fila(self.entrada, boton("Buscar", self._buscar, flex=0)))
        self.resultados = toga.Box(style=Pack(direction=COLUMN, gap=6))
        self.cuerpo.add(self.resultados)
        if self.mensaje:
            self.cuerpo.add(etiqueta(self.mensaje, 12, color=VERDE))
        if self.ultima is not None:
            self.cuerpo.add(boton("(r) Repetir la canción anterior", lambda w: self._empezar(self.ultima, 0), color=AZUL))
        self.cuerpo.add(etiqueta(f"Canciones cantadas en esta sesión: {self.cantadas}", 11, color=TEXTO_GRIS))
        self.cuerpo.add(boton("(f) Finalizar la sesión", self._finalizar_btn, color=NARANJA))

    def _omitir(self, posicion):
        self.app.programa.marcar(posicion, "saltada")
        self._mostrar_busqueda()

    def _buscar(self, widget):
        self.resultados.clear()
        texto = self.entrada.value.strip()
        if not texto:
            return
        coincidencias = self.app.buscador.buscar_fragmento(texto)
        if not coincidencias:
            self.resultados.add(etiqueta("No se encontró ninguna canción con esas palabras.", 12, color=NARANJA))
            return
        if len(coincidencias) == 1 or coincidencias[0].puntaje - coincidencias[1].puntaje >= 0.3:
            self.resultados.add(etiqueta("Coincidencia clara:", 11, color=TEXTO_GRIS))
        for c in coincidencias:
            texto_boton = f"[{c.codigo}] {c.nombre} — línea {c.linea + 1}: {c.texto[:45]}"
            self.resultados.add(boton(texto_boton, self._elegir(c.codigo, c.linea), color=AZUL))

    def _elegir(self, codigo, linea):
        return lambda widget: self._empezar(codigo, linea)

    # ================================================================ canción
    def _empezar(self, codigo, linea):
        self.codigo, self.idx = codigo, linea
        self.pausado, self.repeticiones, self.mensaje = False, 0, ""
        self._mostrar_cancion()

    def _mostrar_cancion(self):
        self.cuerpo.clear()
        self.nombre = self.app.canciones.obtener(self.codigo)["nombre_cancion"]
        self.lineas = self.app.canciones.lineas(self.codigo)
        acciones = [
            ("c", "Continuar", self.continuar, VERDE),
            ("a", "Atrás", self.atras, AZUL),
            ("l", "Línea igual", self.linea_igual, AZUL),
            ("r", "Repetir", self.repetir, AZUL),
            ("i", "Ignorar", self.ignorar, AMARILLO),
            ("s", "Seguir", self.seguir, VERDE),
            ("n", "Otra canción", self.otra, GRIS),
            ("f", "Fin", self.finalizar, NARANJA),
        ]
        self.vista = VistaKaraoke(self.app, acciones)
        self.cuerpo.add(self.vista.widget)
        self._refrescar()

    def _refrescar(self):
        estado = "MANUAL · IGNORANDO (presione s para seguir)" if self.pausado else "MANUAL"
        info = f"línea {self.idx + 1} de {len(self.lineas)} · cantadas en la sesión: {self.cantadas}"
        self.vista.mostrar(self.nombre, self.codigo, self.lineas, self.idx, estado, info, self.mensaje)

    def continuar(self):
        if self.codigo is None:
            return
        if self.pausado:
            return
        if self.idx >= len(self.lineas) - 1:
            self._terminar_cancion()
            return
        self.idx += 1
        self.repeticiones, self.mensaje = 0, ""
        self._refrescar()

    def atras(self):
        if self.codigo is None:
            return
        if not self.pausado and self.idx > 0:
            self.idx -= 1
            self._refrescar()

    def linea_igual(self):
        if self.codigo is None:
            return
        if self.pausado:
            return
        self.repeticiones += 1
        self.mensaje = f"El cantante repite esta línea (×{self.repeticiones + 1})"
        self._refrescar()

    def repetir(self):
        if self.codigo is None:
            return
        if self.pausado:
            return
        self.idx, self.repeticiones = 0, 0
        self.mensaje = "Repitiendo la misma canción desde el inicio"
        self._refrescar()

    def ignorar(self):
        if self.codigo is None:
            return
        self.pausado = True
        self.mensaje = "Proceso suspendido (afinación o ejercicios de voz)"
        self._refrescar()

    def seguir(self):
        if self.codigo is None:
            return
        self.pausado = False
        self.mensaje = ""
        self._refrescar()

    def otra(self):
        if self.codigo is None:
            return
        self.app.canciones.registrar_historial(self.codigo, "manual", completada=False)
        self.codigo, self.mensaje = None, ""
        self._mostrar_busqueda()

    def _terminar_cancion(self):
        self.app.canciones.registrar_historial(self.codigo, "manual", completada=True)
        self.app.canciones.incrementar_cantada(self.codigo)
        self.app.programa.marcar_cantada(self.codigo)
        self.cantadas += 1
        self.mensaje = f"«{self.nombre}» terminada. Busque la siguiente o presione (r) para repetirla."
        self.ultima = self.codigo
        self.codigo = None
        self._mostrar_busqueda()

    # ================================================================ fin
    def finalizar(self):
        asyncio.ensure_future(self._finalizar())

    def _finalizar_btn(self, widget):
        self.finalizar()

    async def _finalizar(self):
        if self.codigo is not None and self.idx > 0:
            self.app.canciones.registrar_historial(self.codigo, "manual", completada=False)
        await self.info("Sesión finalizada", f"Se cantaron {self.cantadas} canción(es) en esta sesión.")
        self.ir_menu()
