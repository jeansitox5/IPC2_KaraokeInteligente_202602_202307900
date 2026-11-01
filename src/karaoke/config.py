"""
config.py - Valores por defecto del Karaoke Inteligente.

AQUÍ se cambian los valores "de fábrica". Los valores que el usuario cambia
desde la pantalla (k) Configuración se guardan en la tabla CONFIGURACION de la
base de datos y tienen prioridad sobre estos.

Promedios del enunciado (10 líneas por canción y 80 caracteres por línea):
    LINEAS_PROMEDIO_CANCION, CARACTERES_PROMEDIO_LINEA, LINEAS_POR_PAGINA,
    MAX_CARACTERES_LINEA.
No limitan cuánto texto se puede guardar (LETRAS.linea es TEXT): solo afectan
la paginación, el partido de líneas largas, el ancho de la vista y la
estimación inicial de duración.
"""

# clave: (valor por defecto, descripción)
DEFAULTS = {
    # --- Promedios del enunciado ---------------------------------------
    "LINEAS_POR_PAGINA": (10, "Canciones por grupo en (w) y líneas por grupo en (x)."),
    "LINEAS_PROMEDIO_CANCION": (10, "Líneas promedio por canción (estimaciones y progreso)."),
    "CARACTERES_PROMEDIO_LINEA": (80, "Caracteres promedio por línea (ancho de la vista)."),
    "MAX_CARACTERES_LINEA": (120, "Una línea más larga se parte al importar o capturar."),
    # --- Voz a texto ---------------------------------------------------
    "MOTOR_VOZ": ("auto", "auto, whisper, android, simulado o archivo."),
    "IDIOMA": ("es", "Idioma para Whisper (Windows)."),
    "IDIOMA_ANDROID": ("es-GT", "Idioma del reconocedor de Android (es-GT, es-MX, es-US, es-ES)."),
    "VENTANA_SEG": (4.0, "Duración de cada muestra de audio para Whisper (segundos)."),
    "SALTO_SEG": (2.0, "Cada cuánto se toma una muestra para Whisper (segundos)."),
    "WHISPER_HILOS": (4, "Hilos de CPU que usa Whisper."),
    # --- Sincronización ------------------------------------------------
    "UMBRAL_IDENTIFICACION": (0.45, "Puntaje mínimo (0 a 1) para reconocer una canción."),
    "UMBRAL_NUEVA": (0.35, "Por debajo de este puntaje la letra se considera nueva."),
    "VELOCIDAD_INICIAL": (2.5, "Palabras por segundo al empezar a seguir una canción."),
    "ADELANTO_SEG": (0.5, "Segundos de anticipación de la línea resaltada."),
    "SILENCIO_PAUSA_SEG": (1.5, "Segundos sin voz para congelar el avance (pausa)."),
    "SILENCIO_FIN_SEG": (6.0, "Segundos sin voz para dar por terminada una canción."),
}


class Configuracion:
    """Valores de configuración con su tipo correcto (int, float o str)."""

    def __init__(self, repo=None):
        self._repo = repo
        self._valores = {clave: valor for clave, (valor, _) in DEFAULTS.items()}
        if repo is not None:
            repo.asegurar_defaults(DEFAULTS)
            for clave, texto in repo.obtener_todos().items():
                if clave in DEFAULTS:
                    try:
                        self._valores[clave] = self._convertir(clave, texto)
                    except ValueError:
                        pass  # valor corrupto en la BD: se queda el de fábrica

    @staticmethod
    def _convertir(clave, texto):
        tipo = type(DEFAULTS[clave][0])
        texto = str(texto).strip()
        if tipo is int:
            return int(float(texto))
        if tipo is float:
            return float(texto.replace(",", "."))
        return texto

    def __getitem__(self, clave):
        return self._valores[clave]

    def get(self, clave, defecto=None):
        return self._valores.get(clave, defecto)

    def descripcion(self, clave):
        return DEFAULTS[clave][1]

    def establecer(self, clave, texto):
        """Valida, guarda en memoria y en la BD. Lanza ValueError si no es válido."""
        valor = self._convertir(clave, texto)
        if isinstance(valor, (int, float)) and valor < 0:
            raise ValueError(f"{clave} no puede ser negativo")
        self._valores[clave] = valor
        if self._repo is not None:
            self._repo.guardar(clave, str(valor), DEFAULTS[clave][1])

    def restaurar(self):
        for clave, (valor, _) in DEFAULTS.items():
            self.establecer(clave, str(valor))
