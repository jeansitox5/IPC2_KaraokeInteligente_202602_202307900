"""
captura.py - Fuentes de audio para Windows (micrófono o archivo WAV).

Ambas llenan un búfer circular con audio a 16 kHz mono y llaman a
'al_nivel(nivel_db, t)' unas 10 veces por segundo, para que el sincronizador
sepa en tiempo real si hay voz (y la letra no avance en los silencios).
"""
import threading
import time
import wave

import numpy as np

SR = 16000


class Bufer:
    """Búfer circular seguro entre hilos con los últimos N segundos de audio."""

    def __init__(self, segundos=12):
        self.datos = np.zeros(int(SR * segundos), dtype=np.float32)
        self.escritas = 0
        self.lock = threading.Lock()

    def escribir(self, bloque):
        with self.lock:
            n = len(bloque)
            tam = len(self.datos)
            if n >= tam:
                self.datos[:] = bloque[-tam:]
            else:
                inicio = self.escritas % tam
                fin = inicio + n
                if fin <= tam:
                    self.datos[inicio:fin] = bloque
                else:
                    corte = tam - inicio
                    self.datos[inicio:] = bloque[:corte]
                    self.datos[:n - corte] = bloque[corte:]
            self.escritas += n

    def ultimos(self, segundos):
        with self.lock:
            n = min(int(SR * segundos), len(self.datos), self.escritas)
            if n == 0:
                return np.zeros(0, dtype=np.float32)
            fin = self.escritas % len(self.datos)
            if fin >= n:
                return self.datos[fin - n:fin].copy()
            return np.concatenate([self.datos[len(self.datos) - (n - fin):], self.datos[:fin]])


class FuenteMicrofono:
    def __init__(self, bufer, al_nivel):
        self.bufer = bufer
        self.al_nivel = al_nivel
        self.stream = None

    @staticmethod
    def disponible():
        try:
            import sounddevice as sd
            sd.query_devices(kind="input")
            return True, "Micrófono detectado"
        except Exception as e:  # noqa: BLE001 - se informa al usuario
            return False, f"No se encontró micrófono: {e}"

    def iniciar(self):
        import sounddevice as sd

        def callback(indata, frames, tiempo, estado):
            bloque = indata[:, 0].copy()
            self.bufer.escribir(bloque)
            rms = float(np.sqrt(np.mean(bloque ** 2)))
            self.al_nivel(20.0 * np.log10(max(rms, 1e-7)), time.monotonic())

        self.stream = sd.InputStream(
            samplerate=SR, channels=1, dtype="float32", blocksize=SR // 10, callback=callback
        )
        self.stream.start()

    def detener(self):
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None


class FuenteArchivo:
    """Reproduce un WAV 'en tiempo real' como si fuera el micrófono
    (pruebas repetibles y demostración)."""

    def __init__(self, ruta, bufer, al_nivel):
        self.ruta = ruta
        self.bufer = bufer
        self.al_nivel = al_nivel
        self._activo = False

    def _leer(self):
        with wave.open(str(self.ruta), "rb") as w:
            canales, ancho, sr = w.getnchannels(), w.getsampwidth(), w.getframerate()
            crudo = w.readframes(w.getnframes())
        if ancho != 2:
            raise ValueError("El WAV debe ser PCM de 16 bits.")
        x = np.frombuffer(crudo, dtype=np.int16).astype(np.float32) / 32768.0
        if canales > 1:
            x = x.reshape(-1, canales).mean(axis=1)
        if sr != SR:  # remuestreo lineal sencillo a 16 kHz
            t_viejo = np.arange(len(x)) / sr
            t_nuevo = np.arange(0, t_viejo[-1], 1.0 / SR)
            x = np.interp(t_nuevo, t_viejo, x).astype(np.float32)
        return x

    def iniciar(self):
        audio = self._leer()
        self._activo = True

        def reproducir():
            paso = SR // 10
            inicio = time.monotonic()
            for k in range(0, len(audio), paso):
                if not self._activo:
                    return
                bloque = audio[k:k + paso]
                self.bufer.escribir(bloque)
                rms = float(np.sqrt(np.mean(bloque ** 2))) if len(bloque) else 0.0
                self.al_nivel(20.0 * np.log10(max(rms, 1e-7)), time.monotonic())
                espera = inicio + (k + paso) / SR - time.monotonic()
                if espera > 0:
                    time.sleep(espera)

        threading.Thread(target=reproducir, daemon=True).start()

    def detener(self):
        self._activo = False
