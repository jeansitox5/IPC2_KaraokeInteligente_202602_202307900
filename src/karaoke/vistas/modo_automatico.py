"""
modo_automatico.py - Opción (a).

La IA escucha, identifica la canción y la letra avanza sola al ritmo del
cantante. Los botones quedan como RESPALDO del operador (por si la IA se
equivoca) y (m) pasa al modo manual sin perder la canción ni la línea.
"""
import asyncio
import time

import toga
from toga.style import Pack
from toga.style.pack import COLUMN

from karaoke import plataforma
from karaoke.automatico.sesion import SesionAutomatica
from karaoke.vistas.base import (
    AMARILLO, AZUL, GRIS, NARANJA, TEXTO_GRIS, VERDE, Pantalla, boton, entrada, etiqueta, fila,
)
from karaoke.vistas.karaoke import VistaKaraoke


class PantallaModoAutomatico(Pantalla):
    titulo = "Modo automático"

    def __init__(self, app, motor_forzado=None):
        super().__init__(app)
        self.motor_forzado = motor_forzado
        self.sesion = None
        self._activo = False

    def construir(self):
        self.cuerpo = toga.Box(style=Pack(direction=COLUMN, gap=10))
        self.lbl_motor = etiqueta("Preparando el motor de voz…", 12, color=TEXTO_GRIS)
        self.cuerpo.add(self.lbl_motor)
        return self.desplazable(self.encabezado(), self.cuerpo)

    async def al_mostrar(self):
        motor = await self.app.crear_motor(self.motor_forzado)
        if motor is None:
            self.lbl_motor.text = "Se canceló la selección del archivo de audio."
            return
        ok, mensaje = motor.disponible()
        if not ok:
            self._mostrar_problema(mensaje)
            return
        if motor.nombre == "android" and not await plataforma.pedir_permiso_microfono(self.app):
            self._mostrar_problema("Sin permiso para usar el micrófono. Puede darlo en "
                                   "Ajustes > Aplicaciones > Karaoke Inteligente > Permisos.")
            return
        self.motor = motor
        self.lbl_motor.text = f"Motor de voz: {motor.nombre} — {mensaje}"
        self._construir_vista()
        self.sesion = SesionAutomatica(self.app, motor)
        self.sesion.iniciar()
        self._activo = True
        asyncio.ensure_future(self._bucle())

    def _mostrar_problema(self, mensaje):
        self.lbl_motor.text = mensaje
        self.lbl_motor.style.color = NARANJA
        self.cuerpo.add(fila(
            boton("Usar modo simulado", lambda w: self.app.mostrar(PantallaModoAutomatico(self.app, "simulado")), color=GRIS),
            boton("Ir al modo manual", self._a_manual_btn, color=VERDE),
            boton("Diagnóstico", self._diagnostico, color=AZUL),
        ))

    def _diagnostico(self, widget):
        from karaoke.vistas.diagnostico import PantallaDiagnostico
        self.app.mostrar(PantallaDiagnostico(self.app))

    def _construir_vista(self):
        acciones = [
            ("c", "Continuar", lambda: self._boton("c"), VERDE),
            ("a", "Atrás", lambda: self._boton("a"), AZUL),
            ("l", "Línea igual", lambda: self._boton("l"), AZUL),
            ("r", "Repetir", lambda: self._boton("r"), AZUL),
            ("i", "Ignorar", lambda: self._boton("i"), AMARILLO),
            ("s", "Seguir", lambda: self._boton("s"), VERDE),
            ("n", "Otra canción", lambda: self._boton("n"), GRIS),
            ("m", "A manual", self._a_manual, GRIS),
            ("f", "Fin", self._finalizar, NARANJA),
        ]
        extras = []
        if self.motor.nombre == "simulado":
            self.simulado = entrada("Escriba lo que 'se escuchó' y presione Enter", al_confirmar=self._simular)
            extras = [etiqueta("Modo simulado (pruebas sin micrófono):", 11, color=TEXTO_GRIS),
                      fila(self.simulado, boton("Enviar", self._simular, flex=0))]
        self.lbl_oido = etiqueta("", 10, color=TEXTO_GRIS)
        extras.append(self.lbl_oido)
        self.vista = VistaKaraoke(self.app, acciones, extras)
        self.cuerpo.add(self.vista.widget)

    def _simular(self, widget):
        texto = self.simulado.value.strip()
        if texto:
            self.motor.escuchar_texto(texto)
        self.simulado.value = ""

    def _boton(self, letra):
        if self.sesion is not None:
            self.sesion.boton(letra)
            self._render()

    # ------------------------------------------------------------ bucle
    async def _bucle(self):
        while self._activo:
            try:
                self.sesion.tick()
                self._render()
            except Exception as e:  # noqa: BLE001 - se muestra y se sigue escuchando
                self.lbl_motor.text = f"Error: {e}"
            await asyncio.sleep(0.1)

    def _render(self):
        ahora = time.monotonic()
        e = self.sesion.estado_para_pantalla(ahora)
        c = e["cancion"]
        barras = int(round(self.sesion.ultimo_nivel * 10))
        medidor = "█" * barras + "░" * (10 - barras)
        if c is None:
            nombre, codigo, lineas, idx = "Esperando que el cantante empiece…", None, [], None
            info = f"voz: {medidor}"
        else:
            nombre, codigo, lineas, idx = c.nombre, c.codigo, c.lineas, e["linea"]
            info = (f"línea {idx + 1} de {len(lineas)} · {e['velocidad']:.1f} palabras/s · "
                    f"coincidencia {e['puntaje']:.0%} · voz: {medidor}")
        mensaje = self.sesion.mensaje or getattr(self.motor, "mensaje_estado", "")
        info += f" · cantadas: {self.sesion.cantadas}"
        self.vista.mostrar(nombre, codigo, lineas, idx, f"AUTOMÁTICO · {e['estado']}", info, mensaje)
        self.lbl_oido.text = f"Oído: {self.sesion.ultimo_texto[-90:]}" if self.sesion.ultimo_texto else ""

    # ------------------------------------------------------------ salir
    def al_salir(self):
        self._activo = False
        if self.sesion is not None:
            self.sesion.detener()
            self.sesion = None

    def _a_manual(self):
        from karaoke.vistas.modo_manual import PantallaModoManual

        codigo = linea = None
        cantadas = 0
        if self.sesion is not None:
            c = self.sesion.sinc.cancion
            if c is not None:
                codigo, linea = c.codigo, self.sesion.sinc.linea_actual(time.monotonic())
            cantadas = self.sesion.cantadas
        self.app.mostrar(PantallaModoManual(self.app, codigo, linea or 0, cantadas))

    def _a_manual_btn(self, widget):
        self._a_manual()

    def _finalizar(self):
        asyncio.ensure_future(self._finalizar_async())

    async def _finalizar_async(self):
        cantadas = self.sesion.cantadas if self.sesion else 0
        nuevas = self.sesion.nuevas_capturadas if self.sesion else 0
        self.al_salir()
        texto = f"Se cantaron {cantadas} canción(es)."
        if nuevas:
            texto += f" Se capturaron {nuevas} letra(s) nueva(s): revíselas en Alimentación → (v)."
        await self.info("Sesión finalizada", texto)
        self.ir_menu()
