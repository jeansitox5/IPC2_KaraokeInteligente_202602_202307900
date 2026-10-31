"""
buscador.py - Encuentra canción y línea a partir de un fragmento de letra.

Dos usos:
1. buscar_fragmento(): modo manual. El operador teclea 2-3 palabras que oyó.
2. alinear(): modo automático. Recibe lo que transcribió la IA (con errores) y
   devuelve qué canción es, con qué puntaje (0 a 1) y en qué palabra va el
   cantante. Compara el texto contra cada "ventana" de la letra con
   difflib.SequenceMatcher, que tolera palabras mal transcritas.

Las letras se cargan una vez en memoria (son pocas) para que buscar sea rápido.
"""
from dataclasses import dataclass
from difflib import SequenceMatcher

from karaoke.nucleo.texto import normalizar


@dataclass
class CancionIndexada:
    codigo: int
    nombre: str
    lineas: list            # texto original de cada línea
    lineas_norm: list       # cada línea normalizada
    palabras: list          # todas las palabras normalizadas, en orden
    linea_de_palabra: list  # palabras[i] pertenece a la línea linea_de_palabra[i]
    inicio_linea: list      # índice de la primera palabra de cada línea

    @property
    def total_palabras(self):
        return len(self.palabras)

    def palabras_de_linea(self, idx):
        fin = self.inicio_linea[idx + 1] if idx + 1 < len(self.inicio_linea) else len(self.palabras)
        return fin - self.inicio_linea[idx]

    def linea_en(self, posicion):
        """Línea que corresponde a una posición (índice de palabra)."""
        if not self.palabras:
            return 0
        i = min(max(int(posicion), 0), len(self.palabras) - 1)
        return self.linea_de_palabra[i]


@dataclass
class Coincidencia:
    codigo: int
    nombre: str
    linea: int        # índice 0..n-1
    texto: str
    puntaje: float


@dataclass
class Alineacion:
    codigo: int
    puntaje: float
    posicion: int     # índice de la palabra SIGUIENTE a lo escuchado


class Buscador:
    def __init__(self):
        self.canciones = {}
        self._indice = {}   # palabra -> {codigos}

    def cargar(self, datos):
        """datos = {codigo: (nombre, [lineas])} (de CancionesRepo.todas_con_lineas)."""
        self.canciones = {}
        self._indice = {}
        for codigo, (nombre, lineas) in datos.items():
            lineas_norm = [normalizar(l) for l in lineas]
            palabras, linea_de_palabra, inicio = [], [], []
            for i, ln in enumerate(lineas_norm):
                inicio.append(len(palabras))
                for p in ln.split():
                    palabras.append(p)
                    linea_de_palabra.append(i)
            self.canciones[codigo] = CancionIndexada(
                codigo, nombre, list(lineas), lineas_norm, palabras, linea_de_palabra, inicio
            )
            for p in set(palabras):
                if len(p) >= 3:
                    self._indice.setdefault(p, set()).add(codigo)

    # ======================================================= modo manual
    def buscar_fragmento(self, consulta, limite=10, minimo=0.34):
        q = normalizar(consulta).split()
        if not q:
            return []
        frase = " ".join(q)
        resultados = []
        for c in self.canciones.values():
            for i, ln in enumerate(c.lineas_norm):
                siguiente = c.lineas_norm[i + 1] if i + 1 < len(c.lineas_norm) else ""
                if f" {frase} " in f" {ln} ":
                    puntaje = 1.0
                elif frase in f"{ln} {siguiente}":
                    puntaje = 0.95       # la frase cruza a la línea siguiente
                else:
                    puntaje = 0.9 * self._proporcion_palabras(q, ln.split())
                if puntaje >= minimo:
                    resultados.append(Coincidencia(c.codigo, c.nombre, i, c.lineas[i], puntaje))
        resultados.sort(key=lambda r: (-r.puntaje, r.codigo, r.linea))
        return resultados[:limite]

    @staticmethod
    def _proporcion_palabras(consulta, palabras_linea):
        """Qué fracción de las palabras tecleadas aparece en la línea
        (tolerando errores de escritura: parecido >= 0.8)."""
        if not palabras_linea:
            return 0.0
        encontradas = 0
        for q in consulta:
            if q in palabras_linea or any(
                SequenceMatcher(None, q, p).ratio() >= 0.8 for p in palabras_linea
            ):
                encontradas += 1
        return encontradas / len(consulta)

    # ===================================================== modo automático
    def candidatas(self, palabras_oidas):
        """Canciones que comparten al menos 2 palabras (de 3+ letras) con lo oído.
        Evita comparar contra toda la base."""
        conteo = {}
        for p in set(palabras_oidas):
            for codigo in self._indice.get(p, ()):
                conteo[codigo] = conteo.get(codigo, 0) + 1
        minimo = 2 if len(set(palabras_oidas)) >= 4 else 1
        return [c for c, n in conteo.items() if n >= minimo]

    def posiciones(self, palabras_oidas, codigo):
        """Puntaje de lo oído contra CADA ventana de la canción.
        Devuelve [(puntaje, posicion_siguiente), ...].

        puntaje = 0.5 · parecido de caracteres (reescalado)  +  0.5 · fracción de
        palabras oídas (de 3+ letras) que aparecen en la ventana.
        El parecido de caracteres por sí solo da ~0.5 entre textos que no tienen
        nada que ver; por eso se reescala y se combina con las palabras."""
        c = self.canciones.get(codigo)
        if c is None or not palabras_oidas or not c.palabras:
            return []
        n = len(palabras_oidas)
        oido = " ".join(palabras_oidas)
        # Para cada palabra oída importante: en qué posiciones de la canción aparece.
        importantes = [p for p in palabras_oidas if len(p) >= 3] or list(palabras_oidas)
        vocab = set(c.palabras)
        apariciones = []
        for p in importantes:
            parecidas = {w for w in vocab if w == p or (
                abs(len(w) - len(p)) <= 2 and SequenceMatcher(None, p, w).ratio() >= 0.8)}
            apariciones.append([i for i, w in enumerate(c.palabras) if w in parecidas])
        resultado = []
        ultimo_inicio = max(0, len(c.palabras) - n)
        for inicio in range(0, ultimo_inicio + 1):
            fin = inicio + n
            aciertos = sum(1 for lista in apariciones if any(inicio <= i < fin for i in lista))
            fraccion = aciertos / len(apariciones)
            if fraccion < 0.25:
                continue
            ventana = " ".join(c.palabras[inicio:fin])
            ratio = SequenceMatcher(None, oido, ventana, autojunk=False).ratio()
            caracteres = max(0.0, (ratio - 0.4) / 0.6)
            resultado.append((0.5 * caracteres + 0.5 * fraccion, min(fin, len(c.palabras))))
        return resultado

    def alinear(self, palabras_oidas, codigos=None):
        """Mejor alineación por canción, ordenadas de mayor a menor puntaje."""
        if not palabras_oidas:
            return []
        if codigos is None:
            codigos = self.candidatas(palabras_oidas)
        alineaciones = []
        for codigo in codigos:
            pos = self.posiciones(palabras_oidas, codigo)
            if pos:
                puntaje, posicion = max(pos)
                alineaciones.append(Alineacion(codigo, puntaje, posicion))
        alineaciones.sort(key=lambda a: -a.puntaje)
        return alineaciones
