"""
motor_voz.py - Interfaz común de los motores de voz a texto (patrón Estrategia).

Cada motor (Whisper en Windows, reconocedor de Android, simulado) produce
"observaciones" y las deja en una cola. El resto del programa no sabe qué
motor está usando: solo lee observaciones.
"""
import queue
import time
from dataclasses import dataclass, field

from karaoke.nucleo.texto import palabras as _palabras

# Frases que Whisper "inventa" cuando el audio está casi vacío.
ALUCINACIONES = (
    "gracias por ver", "suscribete", "subtitulos", "subtitulado", "amara org",
    "gracias por su atencion",
)
# Etiquetas que solo se descartan si son TODO el texto ("la música suena" es letra válida).
ETIQUETAS = {"musica", "aplausos", "risas", "silencio"}


@dataclass
class Observacion:
    """Lo que el motor 'oyó' en un momento.

    texto:  lo transcrito; None si solo informa el nivel de voz.
    t_fin:  instante (time.monotonic) en que terminó el audio observado.
    voz:    True si había voz.
    nivel:  intensidad 0..1 aproximada (para el medidor).
    final:  False en resultados parciales de Android.
    """
    texto: str | None
    t_fin: float
    voz: bool = True
    nivel: float = 0.0
    final: bool = True
    palabras: list = field(default_factory=list)

    def __post_init__(self):
        if self.texto:
            self.palabras = _palabras(self.texto)


def limpiar_transcripcion(texto):
    """Filtro común: descarta alucinaciones y repeticiones absurdas."""
    if not texto:
        return ""
    texto = " ".join(texto.replace("\n", " ").split())
    # Whisper marca música/ruido entre corchetes o paréntesis
    for a, b in (("[", "]"), ("(", ")"), ("*", "*")):
        while a in texto and b in texto[texto.index(a) + 1:]:
            i = texto.index(a)
            j = texto.index(b, i + 1)
            texto = (texto[:i] + " " + texto[j + 1:]).strip()
    norm = " ".join(_palabras(texto))
    if not norm or norm in ETIQUETAS or any(a in norm for a in ALUCINACIONES):
        return ""
    lista = norm.split()
    if len(lista) >= 5 and max(lista.count(p) for p in set(lista)) > 4:
        return ""
    return " ".join(texto.split())


class MotorVoz:
    nombre = "base"

    def __init__(self):
        self.cola = None
        self.activo = False
        self.contexto = ""

    def disponible(self):
        """(True/False, mensaje para la pantalla de diagnóstico)."""
        return True, "Disponible"

    def iniciar(self, cola: queue.Queue):
        self.cola = cola
        self.activo = True

    def detener(self):
        self.activo = False

    def poner_contexto(self, texto):
        """Líneas que se esperan a continuación (Whisper las usa como pista)."""
        self.contexto = texto or ""

    def _emitir(self, obs: Observacion):
        if self.cola is not None and self.activo:
            self.cola.put(obs)


class MotorSimulado(MotorVoz):
    """El operador escribe lo que 'se escuchó'. Sirve para probar la
    sincronización sin micrófono y en la demostración."""
    nombre = "simulado"

    def escuchar_texto(self, texto):
        ahora = time.monotonic()
        self._emitir(Observacion(texto=texto, t_fin=ahora, voz=True, nivel=0.6))

    def silencio(self):
        self._emitir(Observacion(texto=None, t_fin=time.monotonic(), voz=False))
