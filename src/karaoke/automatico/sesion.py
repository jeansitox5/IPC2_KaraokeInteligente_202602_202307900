"""
sesion.py - Coordina una sesión del modo automático.

    motor de voz --(cola de observaciones)--> Sincronizador --> pantalla
                                          \\-> Aprendiz (canciones nuevas)
Además registra el HISTORIAL, marca el PROGRAMA y le pasa a Whisper las
líneas que se esperan.

La pantalla llama a tick() unas 10 veces por segundo desde el hilo de la
interfaz; los motores solo escriben en la cola (seguro entre hilos).
"""
import queue
import time

from karaoke.automatico.aprendiz import Aprendiz
from karaoke.automatico.sincronizador import FIN, NUEVA, ESCUCHANDO, SIGUIENDO, Sincronizador


class SesionAutomatica:
    def __init__(self, contexto, motor):
        self.ctx = contexto              # la App: repos, buscador, cfg
        self.motor = motor
        self.cola = queue.Queue()
        self.sinc = Sincronizador(contexto.buscador, contexto.cfg)
        self.aprendiz = Aprendiz(contexto.temporales, contexto.cfg)
        self.cantadas = 0
        self.nuevas_capturadas = 0
        self.ultimo_nivel = 0.0
        self.ultimo_texto = ""
        self.mensaje = ""
        self._actualizar_prioridad()

    # ----------------------------------------------------------- ciclo
    def iniciar(self):
        self.motor.iniciar(self.cola)

    def detener(self):
        self.motor.detener()
        if self.aprendiz.activo:
            if self.aprendiz.finalizar():
                self.nuevas_capturadas += 1
        if self.sinc.estado == SIGUIENDO and self.sinc.cancion is not None:
            self.ctx.canciones.registrar_historial(self.sinc.cancion.codigo, "automatico", False)

    def tick(self, ahora=None):
        ahora = time.monotonic() if ahora is None else ahora
        eventos = []
        while True:
            try:
                obs = self.cola.get_nowait()
            except queue.Empty:
                break
            if obs.texto is None:
                self.ultimo_nivel = obs.nivel
            else:
                self.ultimo_texto = obs.texto
            eventos += self.sinc.procesar(obs)
            if self.sinc.estado == NUEVA and obs.texto and obs.final:
                if self.motor.nombre == "android":
                    self.aprendiz.agregar_frase(obs.texto, obs.t_fin)
                else:
                    self.aprendiz.agregar(obs.texto, obs.t_fin)
        eventos += self.sinc.tick(ahora)

        # Canción nueva: termina la captura tras un silencio largo.
        if self.sinc.estado == NUEVA and self.sinc.ultima_voz is not None:
            if ahora - self.sinc.ultima_voz > self.ctx.cfg["SILENCIO_FIN_SEG"]:
                self._terminar_captura()
                eventos.append(("nueva_guardada", None))

        for evento in eventos:
            self._atender(evento)
        self._actualizar_contexto(ahora)
        return eventos

    def _atender(self, evento):
        tipo, dato = evento
        if tipo == "nueva_detectada":
            self.aprendiz.iniciar()
            self.mensaje = "Canción no encontrada: capturando la letra en tablas temporales…"
        elif tipo in ("identificada", "cancion_repetida"):
            nombre = self.ctx.buscador.canciones[dato].nombre
            self.mensaje = ("Repitiendo: " if tipo == "cancion_repetida" else "Identificada: ") + nombre
        elif tipo == "fin_cancion":
            self.cantadas += 1
            self.ctx.canciones.registrar_historial(dato, "automatico", True)
            self.ctx.canciones.incrementar_cantada(dato)
            self.ctx.programa.marcar_cantada(dato)
            self._actualizar_prioridad()
            sig = self.ctx.programa.siguiente_pendiente()
            self.mensaje = "Canción terminada." + (
                f" Siguiente del programa: {sig['nombre_cancion']}" if sig else ""
            )
        elif tipo == "cambio":
            self.ctx.canciones.registrar_historial(dato, "automatico", False)
        elif tipo == "linea_repetida":
            self.mensaje = "El cantante repitió una línea."
        elif tipo == "nueva_guardada":
            self.mensaje = "Letra nueva guardada. Revísela en Alimentación → (v)."

    def _terminar_captura(self):
        if self.aprendiz.finalizar():
            self.nuevas_capturadas += 1
        self.sinc.estado = ESCUCHANDO

    def _actualizar_prioridad(self):
        sig = self.ctx.programa.siguiente_pendiente()
        self.sinc.prioridad = sig["codigo"] if sig else None

    def _actualizar_contexto(self, ahora):
        """Le dice a Whisper qué líneas se esperan (mejora la transcripción)."""
        c = self.sinc.cancion
        if c is None or self.sinc.estado != SIGUIENDO:
            self.motor.poner_contexto("")
            return
        i = self.sinc.linea_actual(ahora)
        self.motor.poner_contexto(" ".join(c.lineas[i:i + 2]))

    # ------------------------------------------- botones de respaldo
    def boton(self, letra, ahora=None):
        ahora = time.monotonic() if ahora is None else ahora
        s = self.sinc
        eventos = []
        if letra == "c":
            eventos = s.avanzar(ahora) or []
        elif letra == "a":
            s.retroceder(ahora)
        elif letra == "l":
            s.repetir_linea(ahora)
        elif letra == "r":
            if s.cancion is None and s.ultima_terminada:
                s.fijar(s.ultima_terminada, 0, ahora)
            else:
                s.repetir_cancion(ahora)
        elif letra == "i":
            s.ignorar(ahora)
        elif letra == "s":
            s.seguir(ahora)
        elif letra == "n":
            if s.estado == SIGUIENDO and s.cancion is not None:
                self.ctx.canciones.registrar_historial(s.cancion.codigo, "automatico", False)
            if s.estado == NUEVA:
                self._terminar_captura()
            s.otra_cancion()
            self.mensaje = "Escuchando la siguiente canción…"
        for e in eventos:
            self._atender(e)

    def estado_para_pantalla(self, ahora=None):
        ahora = time.monotonic() if ahora is None else ahora
        s = self.sinc
        return {
            "estado": s.texto_estado(ahora),
            "cancion": s.cancion,
            "linea": s.linea_actual(ahora),
            "velocidad": s.v,
            "puntaje": s._ultimo_puntaje,
            "fin": s.estado == FIN,
        }
