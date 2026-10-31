"""
limpieza.py - "Limpiar" el sonido antes de transcribirlo (Windows).

Pasos (todos con numpy):
  1. quitar_dc        resta el promedio: elimina el desplazamiento del micrófono.
  2. filtro_banda     deja solo 80-4000 Hz, donde está la voz (quita retumbe y siseo).
  3. resta_espectral  resta el "perfil" del ruido de fondo grabado al inicio.
  4. normalizar       lleva el volumen a un nivel fijo (voces bajas o lejanas).
  5. hay_voz (VAD)    decide si vale la pena mandar la muestra a Whisper.
"""
import numpy as np

TRAMA = 512          # muestras por trama para la resta espectral (32 ms a 16 kHz)
SALTO = TRAMA // 2   # 50 % de traslape (con ventana de Hann suma constante)


def quitar_dc(x):
    return x - np.mean(x)


def filtro_banda(x, sr, bajo=80.0, alto=4000.0):
    espectro = np.fft.rfft(x)
    frecuencias = np.fft.rfftfreq(len(x), 1.0 / sr)
    espectro[(frecuencias < bajo) | (frecuencias > alto)] = 0
    return np.fft.irfft(espectro, n=len(x)).astype(np.float32)


def _tramas(x):
    if len(x) < TRAMA:
        x = np.pad(x, (0, TRAMA - len(x)))
    n = 1 + (len(x) - TRAMA) // SALTO
    ventana = np.hanning(TRAMA).astype(np.float32)
    return np.stack([x[i * SALTO:i * SALTO + TRAMA] * ventana for i in range(n)]), n


class PerfilRuido:
    """Espectro promedio del ruido de fondo (se graba con el cantante callado)."""

    def __init__(self):
        self.magnitud = None

    def calibrar(self, x):
        tramas, _ = _tramas(quitar_dc(x.astype(np.float32)))
        self.magnitud = np.mean(np.abs(np.fft.rfft(tramas, axis=1)), axis=0)

    @property
    def listo(self):
        return self.magnitud is not None


def resta_espectral(x, perfil, alfa=1.5, piso=0.08):
    if perfil is None or not perfil.listo or len(x) < TRAMA:
        return x
    tramas, n = _tramas(x)
    espectro = np.fft.rfft(tramas, axis=1)
    magnitud = np.abs(espectro)
    fase = np.angle(espectro)
    limpia = np.maximum(magnitud - alfa * perfil.magnitud, piso * magnitud)
    tramas_limpias = np.fft.irfft(limpia * np.exp(1j * fase), n=TRAMA, axis=1)
    salida = np.zeros(SALTO * (n - 1) + TRAMA, dtype=np.float32)
    for i in range(n):  # suma con traslape (overlap-add)
        salida[i * SALTO:i * SALTO + TRAMA] += tramas_limpias[i]
    return salida[:len(x)]


def normalizar(x, rms_objetivo=0.1, pico_max=0.95):
    rms = float(np.sqrt(np.mean(x ** 2))) if len(x) else 0.0
    if rms < 1e-6:
        return x
    y = x * (rms_objetivo / rms)
    pico = float(np.max(np.abs(y)))
    if pico > pico_max:
        y = y * (pico_max / pico)
    return y.astype(np.float32)


def nivel_db(x):
    rms = float(np.sqrt(np.mean(np.square(x)))) if len(x) else 0.0
    return 20.0 * np.log10(max(rms, 1e-7))


def hay_voz(x, sr, piso_db, margen_db=8.0, fraccion_min=0.3):
    """VAD por energía: tramos de 30 ms por encima del piso de ruido + margen."""
    tam = int(0.03 * sr)
    if len(x) < tam:
        return False, 0.0
    n = len(x) // tam
    tramos = x[:n * tam].reshape(n, tam)
    energia = 20.0 * np.log10(np.maximum(np.sqrt(np.mean(tramos ** 2, axis=1)), 1e-7))
    activos = float(np.mean(energia > piso_db + margen_db))
    return activos >= fraccion_min, activos


def limpiar(x, sr, perfil=None):
    """Cadena completa (pasos 1 a 4)."""
    y = quitar_dc(x.astype(np.float32))
    y = filtro_banda(y, sr)
    y = resta_espectral(y, perfil)
    return normalizar(y)
