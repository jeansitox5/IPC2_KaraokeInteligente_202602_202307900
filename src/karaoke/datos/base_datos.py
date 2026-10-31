"""
base_datos.py - Creación, detección y preparación de la base CANCIONES.

Requisito R09: si CANCIONES.db no existe se crean todas las tablas; si existe,
se prepara para usarla (llaves foráneas, integridad, tablas nuevas que falten
y recuperación de capturas interrumpidas).
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

VERSION_ESQUEMA = 1

ESQUEMA = """
-- Tabla del enunciado: NOMBRES (codigo, nombre_cancion) + campos agregados
CREATE TABLE IF NOT EXISTS NOMBRES (
    codigo              INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_cancion      TEXT NOT NULL,
    nombre_normalizado  TEXT NOT NULL UNIQUE,
    artista             TEXT,
    origen              TEXT NOT NULL DEFAULT 'manual'
                        CHECK (origen IN ('archivo', 'manual', 'automatico')),
    fecha_registro      TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    veces_cantada       INTEGER NOT NULL DEFAULT 0
);

-- Tabla del enunciado: LETRAS (codigo, linea) + campos agregados
CREATE TABLE IF NOT EXISTS LETRAS (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo              INTEGER NOT NULL REFERENCES NOMBRES(codigo) ON DELETE CASCADE,
    numero_linea        INTEGER NOT NULL,
    linea               TEXT NOT NULL,
    linea_normalizada   TEXT NOT NULL,
    duracion_seg        REAL,
    UNIQUE (codigo, numero_linea)
);
CREATE INDEX IF NOT EXISTS idx_letras_codigo ON LETRAS(codigo);

-- Programa tentativo del cantante
CREATE TABLE IF NOT EXISTS PROGRAMA (
    posicion            INTEGER PRIMARY KEY,
    nombre_texto        TEXT NOT NULL,
    codigo              INTEGER REFERENCES NOMBRES(codigo) ON DELETE SET NULL,
    estado              TEXT NOT NULL DEFAULT 'pendiente'
                        CHECK (estado IN ('pendiente', 'cantada', 'saltada', 'no_encontrada'))
);

-- Tablas temporales para canciones nuevas detectadas en modo automático
CREATE TABLE IF NOT EXISTS TMP_NOMBRES (
    id_tmp              INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_provisional  TEXT NOT NULL,
    fecha_captura       TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    estado              TEXT NOT NULL DEFAULT 'capturando'
                        CHECK (estado IN ('capturando', 'pendiente', 'promovida', 'descartada'))
);
CREATE TABLE IF NOT EXISTS TMP_LETRAS (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    id_tmp              INTEGER NOT NULL REFERENCES TMP_NOMBRES(id_tmp) ON DELETE CASCADE,
    numero_linea        INTEGER NOT NULL,
    linea               TEXT NOT NULL,
    confianza           REAL
);

-- Parámetros editables desde la opción (k)
CREATE TABLE IF NOT EXISTS CONFIGURACION (
    clave               TEXT PRIMARY KEY,
    valor               TEXT NOT NULL,
    descripcion         TEXT
);

-- Registro de lo cantado en cada sesión
CREATE TABLE IF NOT EXISTS HISTORIAL (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_hora          TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    codigo              INTEGER REFERENCES NOMBRES(codigo) ON DELETE SET NULL,
    modo                TEXT NOT NULL CHECK (modo IN ('manual', 'automatico')),
    completada          INTEGER NOT NULL DEFAULT 1
);
"""


class BaseDatos:
    """Conexión única a CANCIONES.db."""

    NOMBRE_ARCHIVO = "CANCIONES.db"

    def __init__(self, carpeta):
        carpeta = Path(carpeta)
        carpeta.mkdir(parents=True, exist_ok=True)
        self.ruta = carpeta / self.NOMBRE_ARCHIVO
        # Se pregunta ANTES de conectar: sqlite3.connect crearía el archivo vacío.
        self.era_nueva = not self.ruta.exists()
        self.conn = sqlite3.connect(self.ruta, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.mensaje = self._preparar()

    def _preparar(self):
        if self.era_nueva:
            self.conn.executescript(ESQUEMA)
            self.conn.execute(f"PRAGMA user_version = {VERSION_ESQUEMA}")
            self.conn.commit()
            return "Base de datos CANCIONES creada con todas sus tablas."

        integridad = self.conn.execute("PRAGMA integrity_check").fetchone()[0]
        if integridad != "ok":
            raise RuntimeError(f"La base de datos está dañada: {integridad}")
        # Crea las tablas que falten (por ejemplo, de una versión anterior).
        self.conn.executescript(ESQUEMA)
        version = self.conn.execute("PRAGMA user_version").fetchone()[0]
        if version < VERSION_ESQUEMA:
            self.conn.execute(f"PRAGMA user_version = {VERSION_ESQUEMA}")
        # Capturas que quedaron a medias por un cierre inesperado.
        self.conn.execute(
            "UPDATE TMP_NOMBRES SET estado = 'pendiente' WHERE estado = 'capturando'"
        )
        self.conn.commit()
        canciones, lineas = self.contar()
        return f"Base de datos CANCIONES encontrada: {canciones} canciones, {lineas} líneas."

    def contar(self):
        c = self.conn.execute("SELECT COUNT(*) FROM NOMBRES").fetchone()[0]
        l = self.conn.execute("SELECT COUNT(*) FROM LETRAS").fetchone()[0]
        return c, l

    @contextmanager
    def transaccion(self):
        """Todo o nada: si algo falla dentro del with, se deshace."""
        try:
            yield self.conn
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def cerrar(self):
        self.conn.close()
