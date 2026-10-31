"""
whisper_win.py - Motor de voz para Windows: captura + limpieza + Whisper.

Whisper (de OpenAI) en su versión whisper.cpp, que es un programa de C++ muy
eficiente que corre en la CPU sin internet. Va incluido en el instalador:
    resources/whisper/whisper-cli.exe  (+ DLLs)
    resources/whisper/ggml-*.bin       (modelo multilingüe)

Funcionamiento (dos hilos para no congelar la pantalla):
    hilo de captura:  micrófono -> búfer circular + nivel de voz cada 0.1 s
    hilo de Whisper:  cada SALTO_SEG toma los últimos VENTANA_SEG del búfer,
                      limpia, revisa si hay voz y, si hay, transcribe.
"""
import os
import subprocess
import tempfile
import threading
import time
import wave
from pathlib import Path

from karaoke.audio.motor_voz import MotorVoz, Observacion, limpiar_transcripcion

CALIBRACION_SEG = 2.0


def buscar_modelo(carpeta: Path):
    for patron in ("ggml-base-q5_1.bin", "ggml-base.bin", "ggml-small*.bin", "ggml-*.bin"):
        encontrados = sorted(carpeta.glob(patron))
        encontrados = [m for m in encontrados if ".en." not in m.name]  # solo inglés: no sirve
        if encontrados:
            return encontrados[0]
    return None


class MotorWhisper(MotorVoz):
    nombre = "whisper"

    def __init__(self, cfg, carpeta_whisper, ruta_wav=None):
        super().__init__()
        self.cfg = cfg
        self.carpeta = Path(carpeta_whisper)
        self.exe = self.carpeta / ("whisper-cli.exe" if os.name == "nt" else "whisper-cli")
        self.modelo = buscar_modelo(self.carpeta) if self.carpeta.exists() else None
        self.ruta_wav = ruta_wav
        self.fuente = None
        self.perfil = None
        self.piso_db = -60.0
        self.mensaje_estado = ""
        self._hilo = None

    # ------------------------------------------------------------- estado
    def disponible(self):
        if not self.exe.exists():
            return False, f"No se encontró {self.exe.name} en {self.carpeta}"
        if self.modelo is None:
            return False, f"No se encontró un modelo ggml-*.bin en {self.carpeta}"
        try:
            import numpy  # noqa: F401
        except ImportError:
            return False, "Falta numpy"
        if self.ruta_wav is None:
            from karaoke.audio.captura import FuenteMicrofono
            ok, msg = FuenteMicrofono.disponible()
            if not ok:
                return False, msg
        return True, f"Whisper listo ({self.modelo.name})"

    # -------------------------------------------------------------- ciclo
    def iniciar(self, cola):
        from karaoke.audio.captura import Bufer, FuenteArchivo, FuenteMicrofono

        super().iniciar(cola)
        self.bufer = Bufer(segundos=max(12, self.cfg["VENTANA_SEG"] * 3))
        if self.ruta_wav:
            self.fuente = FuenteArchivo(self.ruta_wav, self.bufer, self._al_nivel)
        else:
            self.fuente = FuenteMicrofono(self.bufer, self._al_nivel)
        self.fuente.iniciar()
        self._hilo = threading.Thread(target=self._bucle, daemon=True)
        self._hilo.start()

    def detener(self):
        super().detener()
        if self.fuente is not None:
            self.fuente.detener()

    def _al_nivel(self, db, t):
        """Nivel de voz en tiempo real (lo usa el sincronizador para pausar)."""
        voz = db > self.piso_db + 10.0
        nivel = min(1.0, max(0.0, (db - self.piso_db) / 40.0))
        self._emitir(Observacion(texto=None, t_fin=t, voz=voz, nivel=nivel))

    def _bucle(self):
        from karaoke.audio import limpieza

        # 1) Calibración: perfil del ruido de fondo.
        self.mensaje_estado = "Calibrando ruido de fondo (guarde silencio)…"
        time.sleep(CALIBRACION_SEG)
        ruido = self.bufer.ultimos(CALIBRACION_SEG)
        if len(ruido):
            self.perfil = limpieza.PerfilRuido()
            self.perfil.calibrar(ruido)
            self.piso_db = limpieza.nivel_db(limpieza.filtro_banda(limpieza.quitar_dc(ruido), 16000))
        self.mensaje_estado = "Escuchando…"

        ventana = float(self.cfg["VENTANA_SEG"])
        salto = float(self.cfg["SALTO_SEG"])
        proxima = time.monotonic()
        while self.activo:
            proxima += salto
            espera = proxima - time.monotonic()
            if espera > 0:
                time.sleep(espera)
            t_fin = time.monotonic()
            audio = self.bufer.ultimos(ventana)
            if len(audio) < 16000:
                continue
            base = limpieza.filtro_banda(limpieza.quitar_dc(audio), 16000)
            voz, _ = limpieza.hay_voz(base, 16000, self.piso_db)
            if not voz:
                self._emitir(Observacion(texto=None, t_fin=t_fin, voz=False))
                continue
            limpio = limpieza.limpiar(audio, 16000, self.perfil)
            texto = limpiar_transcripcion(self.transcribir(limpio))
            if texto:
                self._emitir(Observacion(texto=texto, t_fin=t_fin, voz=True))
            if time.monotonic() > proxima + salto:  # Whisper tardó más que el salto
                proxima = time.monotonic()

    # -------------------------------------------------------- transcribir
    def transcribir(self, audio):
        """Guarda la muestra como WAV temporal y llama a whisper-cli."""
        import numpy as np

        ruta = Path(tempfile.gettempdir()) / f"karaoke_muestra_{os.getpid()}.wav"
        pcm = (np.clip(audio, -1, 1) * 32767).astype(np.int16)
        with wave.open(str(ruta), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(16000)
            w.writeframes(pcm.tobytes())
        cmd = [
            str(self.exe), "-m", str(self.modelo), "-f", str(ruta),
            "-l", str(self.cfg["IDIOMA"]), "-t", str(self.cfg["WHISPER_HILOS"]),
            "-nt", "-np",
        ]
        if self.contexto:
            cmd += ["--prompt", self.contexto]
        opciones = {}
        if os.name == "nt":
            opciones["creationflags"] = subprocess.CREATE_NO_WINDOW  # sin ventana negra
        try:
            r = subprocess.run(
                cmd, capture_output=True, timeout=20, cwd=str(self.carpeta), **opciones
            )
        except (subprocess.TimeoutExpired, OSError) as e:
            self.mensaje_estado = f"Error de Whisper: {e}"
            return ""
        return r.stdout.decode("utf-8", errors="replace").strip()
