"""Datos compartidos por las pruebas: una base temporal con las canciones de ejemplo."""
from pathlib import Path

import pytest

from karaoke.config import Configuracion
from karaoke.datos.base_datos import BaseDatos
from karaoke.datos.canciones_repo import CancionesRepo
from karaoke.datos.config_repo import ConfigRepo
from karaoke.datos.programa_repo import ProgramaRepo
from karaoke.datos.temporales_repo import TemporalesRepo
from karaoke.nucleo.buscador import Buscador
from karaoke.nucleo.importador import importar_texto

EJEMPLO = Path(__file__).parent.parent / "src" / "karaoke" / "resources" / "ejemplos" / "canciones.txt"


class Contexto:
    """Imita lo que la App ofrece a la lógica (repos, buscador, cfg)."""

    def __init__(self, carpeta):
        self.db = BaseDatos(carpeta)
        self.canciones = CancionesRepo(self.db)
        self.programa = ProgramaRepo(self.db)
        self.temporales = TemporalesRepo(self.db)
        self.cfg = Configuracion(ConfigRepo(self.db))
        self.buscador = Buscador()

    def recargar_buscador(self):
        self.buscador.cargar(self.canciones.todas_con_lineas())


@pytest.fixture
def ctx(tmp_path):
    c = Contexto(tmp_path)
    importar_texto(EJEMPLO.read_text(encoding="utf-8"), c.canciones)
    c.recargar_buscador()
    yield c
    c.db.cerrar()
