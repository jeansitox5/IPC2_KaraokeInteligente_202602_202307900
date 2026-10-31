"""
voz_android.py - Motor de voz para Android: reconocedor de voz del sistema.

Usa la API SpeechRecognizer de Android desde Python gracias a Chaquopy
(dynamic_proxy permite implementar una interfaz Java con una clase Python).

- Resultados PARCIALES: llegan cada pocos cientos de milisegundos mientras se
  canta, así la letra se sincroniza casi en tiempo real.
- onRmsChanged: nivel de voz continuo -> detector de voz (pausas).
- El reconocedor escucha por frases; al terminar cada una (o ante un error de
  "no se entendió") se vuelve a iniciar solo, para escuchar de forma continua.
- La limpieza del audio la hace el propio reconocedor (supresión de ruido del
  sistema); aquí se limpia el texto (filtro común).

Todo se llama desde el hilo principal (requisito de Android); los manejadores
de Toga ya corren ahí.
"""
import time

from karaoke.audio.motor_voz import MotorVoz, Observacion, limpiar_transcripcion

UMBRAL_RMS_VOZ = 4.0     # dB que reporta Android (aprox. -2 silencio .. 10 voz fuerte)

# Códigos de error de SpeechRecognizer
ERROR_SIN_PERMISO = 9
ERROR_OCUPADO = 8
ERROR_SIN_COINCIDENCIA = 7
ERROR_TIEMPO_SIN_VOZ = 6
ERRORES_IDIOMA = (12, 13)  # idioma no soportado / paquete sin conexión no disponible


class MotorAndroid(MotorVoz):
    nombre = "android"

    def __init__(self, app, cfg):
        super().__init__()
        self.app = app
        self.cfg = cfg
        self.reconocedor = None
        self.intent = None
        self.oyente = None
        self.error = ""
        self.mensaje_estado = ""
        self.sin_conexion = True   # preferir reconocimiento sin internet

    def disponible(self):
        try:
            from android.speech import SpeechRecognizer
        except ImportError:
            return False, "Solo disponible en Android"
        contexto = self.app._impl.native
        if not SpeechRecognizer.isRecognitionAvailable(contexto):
            return False, ("No hay servicio de reconocimiento de voz. Instale o active "
                           "'Speech Recognition and Synthesis' / 'Reconocimiento de voz de Google'.")
        return True, "Reconocedor de voz de Android disponible"

    def iniciar(self, cola):  # pragma: no cover - solo en Android
        from android.speech import RecognitionListener, SpeechRecognizer
        from java import dynamic_proxy

        super().iniciar(cola)
        motor = self

        class Oyente(dynamic_proxy(RecognitionListener)):
            def onReadyForSpeech(self, params):
                motor.mensaje_estado = "Escuchando…"

            def onBeginningOfSpeech(self):
                pass

            def onRmsChanged(self, rms_db):
                voz = rms_db > UMBRAL_RMS_VOZ
                nivel = min(1.0, max(0.0, (rms_db + 2.0) / 12.0))
                motor._emitir(Observacion(None, time.monotonic(), voz=voz, nivel=nivel))

            def onBufferReceived(self, buffer):
                pass

            def onEndOfSpeech(self):
                pass

            def onError(self, error):
                if error == ERROR_SIN_PERMISO:
                    motor.error = "Sin permiso de micrófono"
                    motor.activo = False
                    return
                if error in ERRORES_IDIOMA and motor.sin_conexion:
                    # No está descargado el paquete de español: se usa el reconocimiento en línea.
                    motor.sin_conexion = False
                    motor.mensaje_estado = "Usando reconocimiento en línea (descargue el español sin conexión)"
                    motor._crear_intent()
                motor._reiniciar(0.8 if error == ERROR_OCUPADO else 0.15)

            def onResults(self, resultados):
                motor._entregar(resultados, final=True)
                motor._reiniciar(0.05)

            def onPartialResults(self, resultados):
                motor._entregar(resultados, final=False)

            def onEvent(self, tipo, params):
                pass

        contexto = self.app._impl.native
        self.reconocedor = SpeechRecognizer.createSpeechRecognizer(contexto)
        self.oyente = Oyente()
        self.reconocedor.setRecognitionListener(self.oyente)

        self._crear_intent()
        self.reconocedor.startListening(self.intent)

    def _crear_intent(self):  # pragma: no cover
        from android.content import Intent
        from android.speech import RecognizerIntent

        intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, str(self.cfg["IDIOMA_ANDROID"]))
        intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, True)
        intent.putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, bool(self.sin_conexion))
        intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
        intent.putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE, self.app._impl.native.getPackageName())
        self.intent = intent

    def _entregar(self, resultados, final):  # pragma: no cover
        from android.speech import SpeechRecognizer

        lista = resultados.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
        if lista is None or lista.size() == 0:
            return
        texto = limpiar_transcripcion(str(lista.get(0)))
        if texto:
            self._emitir(Observacion(texto, time.monotonic(), voz=True, final=final))

    def _reiniciar(self, demora):  # pragma: no cover
        if not self.activo or self.reconocedor is None:
            return

        def volver_a_escuchar():
            if self.activo and self.reconocedor is not None:
                try:
                    self.reconocedor.cancel()
                    self.reconocedor.startListening(self.intent)
                except Exception as e:  # noqa: BLE001
                    self.error = str(e)

        self.app.loop.call_later(demora, volver_a_escuchar)

    def detener(self):  # pragma: no cover
        super().detener()
        if self.reconocedor is not None:
            try:
                self.reconocedor.cancel()
                self.reconocedor.destroy()
            except Exception:  # noqa: BLE001
                pass
            self.reconocedor = None
