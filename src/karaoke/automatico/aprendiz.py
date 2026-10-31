"""
aprendiz.py - Captura canciones que NO están en la base (requisito R10).

Mientras el cantante canta algo desconocido, cada transcripción final se va
guardando en TMP_LETRAS:
- Las muestras de Whisper se traslapan (4 s cada 2 s), así que antes de agregar
  se quita la parte repetida: el final de lo anterior que coincide con el
  inicio de lo nuevo.
- Se cambia de línea cuando hay una pausa o la línea ya es muy larga.
Al terminar queda "pendiente" con la primera línea como nombre provisional,
para que el usuario la corrija y la promueva en (f) -> (v).
"""
from karaoke.nucleo.texto import normalizar

PAUSA_NUEVA_LINEA_SEG = 2.5


def quitar_traslape(anteriores, nuevas):
    """anteriores/nuevas: listas de palabras originales. Devuelve las nuevas
    sin el prefijo que ya estaba al final de las anteriores."""
    a = [normalizar(p) for p in anteriores]
    n = [normalizar(p) for p in nuevas]
    for k in range(min(len(a), len(n)), 0, -1):
        if a[-k:] == n[:k]:
            return nuevas[k:]
    return nuevas


class Aprendiz:
    def __init__(self, temporales_repo, cfg):
        self.repo = temporales_repo
        self.cfg = cfg
        self.id_tmp = None
        self.linea = []          # palabras de la línea en construcción
        self.recientes = []      # últimas palabras agregadas (para el traslape)
        self.ultimo_t = None
        self.total_lineas = 0

    @property
    def activo(self):
        return self.id_tmp is not None

    def iniciar(self):
        self.id_tmp = self.repo.crear("(capturando)")
        self.linea, self.recientes, self.ultimo_t, self.total_lineas = [], [], None, 0
        return self.id_tmp

    def agregar(self, texto, t):
        if not self.activo or not texto:
            return
        nuevas = quitar_traslape(self.recientes, texto.split())
        if not nuevas:
            return
        if self.ultimo_t is not None and t - self.ultimo_t > PAUSA_NUEVA_LINEA_SEG:
            self._cerrar_linea()
        for palabra in nuevas:
            self.linea.append(palabra)
            if len(" ".join(self.linea)) >= self.cfg["CARACTERES_PROMEDIO_LINEA"]:
                self._cerrar_linea()
        self.recientes = (self.recientes + nuevas)[-20:]
        self.ultimo_t = t

    def agregar_frase(self, texto, t):
        """Android entrega frases completas: cada una es una línea."""
        if not self.activo or not texto:
            return
        self._cerrar_linea()
        self.linea = texto.split()
        self._cerrar_linea()
        self.ultimo_t = t

    def _cerrar_linea(self):
        if self.linea:
            self.repo.agregar_linea(self.id_tmp, " ".join(self.linea))
            self.total_lineas += 1
            self.linea = []

    def finalizar(self):
        """Devuelve el id_tmp si se capturó algo; si no, borra el registro vacío."""
        if not self.activo:
            return None
        self._cerrar_linea()
        id_tmp = self.id_tmp
        lineas = self.repo.lineas(id_tmp)
        if lineas:
            provisional = lineas[0][:60]
            self.repo.cambiar_estado(id_tmp, "pendiente", nombre_provisional=provisional)
        else:
            self.repo.borrar(id_tmp)
            id_tmp = None
        self.id_tmp = None
        return id_tmp
