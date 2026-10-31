"""
diagnostico.py - Opción (d): revisa que todo esté listo para el modo automático.

Muestra plataforma, base de datos y motor de voz, y permite una prueba de
8 segundos: se ve el nivel del micrófono y lo que la IA transcribe.
"""
import asyncio
import queue
import time

from karaoke import plataforma
from karaoke.vistas.base import AZUL, NARANJA, TEXTO_GRIS, VERDE, Pantalla, boton, envolver, etiqueta, fila

DURACION_PRUEBA = 8.0


class PantallaDiagnostico(Pantalla):
    titulo = "(d) Diagnóstico"

    def construir(self):
        canciones, lineas = self.app.canciones.contar()
        self.lbl_motor = etiqueta("Revisando motor de voz…", 12)
        self.lbl_nivel = etiqueta("", 14, color=VERDE)
        self.lbl_texto = etiqueta("", 13)
        self.btn = boton(f"Probar voz ({int(DURACION_PRUEBA)} s)", self._probar, color=AZUL)
        return self.desplazable(
            self.encabezado(),
            fila(etiqueta(f"Plataforma: {plataforma.describir()}", 12)),
            fila(etiqueta(f"Base de datos: {self.app.db.ruta}", 11, color=TEXTO_GRIS)),
            fila(etiqueta(f"{canciones} canciones · {lineas} líneas", 12)),
            fila(etiqueta(f"Motor configurado: {self.app.cfg['MOTOR_VOZ']}", 12)),
            fila(self.lbl_motor), fila(self.btn), fila(self.lbl_nivel), fila(self.lbl_texto),
        )

    async def al_mostrar(self):
        motor = await self.app.crear_motor()
        if motor is None:
            self.lbl_motor.text = envolver("No se eligió archivo de audio.")
            return
        ok, msg = motor.disponible()
        self.lbl_motor.text = envolver(("✔ " if ok else "✖ ") + msg)
        self.lbl_motor.style.color = VERDE if ok else NARANJA

    async def _probar(self, widget):
        motor = await self.app.crear_motor()
        if motor is None:
            return
        ok, msg = motor.disponible()
        if not ok:
            await self.error("Motor no disponible", msg)
            return
        if motor.nombre == "android" and not await plataforma.pedir_permiso_microfono(self.app):
            await self.error("Sin permiso", "La app no tiene permiso para usar el micrófono.")
            return
        if motor.nombre == "simulado":
            await self.info("Modo simulado", "El motor simulado no usa micrófono. Cambie MOTOR_VOZ a 'auto' en (k).")
            return
        self.btn.enabled = False
        cola = queue.Queue()
        motor.iniciar(cola)
        textos = []
        fin = time.monotonic() + DURACION_PRUEBA + (2.0 if motor.nombre == "whisper" else 0.0)
        try:
            while time.monotonic() < fin:
                while not cola.empty():
                    obs = cola.get_nowait()
                    if obs.texto is None:
                        barras = int(round(obs.nivel * 20))
                        self.lbl_nivel.text = "Nivel: " + "█" * barras + "░" * (20 - barras)
                    elif obs.final or not textos:
                        textos.append(obs.texto)
                    else:
                        textos[-1] = obs.texto
                estado = getattr(motor, "mensaje_estado", "")
                self.lbl_texto.text = envolver((estado + "\n" if estado else "") + "Transcrito: " + " | ".join(textos[-4:]))
                await asyncio.sleep(0.1)
        finally:
            motor.detener()
            self.btn.enabled = True
        self.lbl_texto.text = envolver("Transcrito: " + (" | ".join(textos) if textos else "(nada; hable más cerca del micrófono)"))
