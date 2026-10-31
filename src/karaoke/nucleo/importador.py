"""
importador.py - Opción (t): carga canciones desde texto plano.
"""
from dataclasses import dataclass, field

from karaoke.nucleo.texto import parsear_canciones, preparar_lineas


@dataclass
class ReporteImportacion:
    cargadas: list = field(default_factory=list)      # [(codigo, nombre)]
    duplicadas: list = field(default_factory=list)    # [nombre]
    sin_letra: list = field(default_factory=list)     # [nombre]

    def resumen(self):
        partes = [f"{len(self.cargadas)} canción(es) cargada(s)"]
        if self.duplicadas:
            partes.append(f"{len(self.duplicadas)} ya existía(n): " + ", ".join(self.duplicadas))
        if self.sin_letra:
            partes.append(f"{len(self.sin_letra)} sin letra: " + ", ".join(self.sin_letra))
        return ". ".join(partes) + "."


def importar_texto(texto, repo, max_caracteres=120, origen="archivo"):
    reporte = ReporteImportacion()
    for nombre, lineas in parsear_canciones(texto):
        lineas = preparar_lineas(lineas, max_caracteres)
        if not lineas:
            reporte.sin_letra.append(nombre)
        elif repo.existe_nombre(nombre):
            reporte.duplicadas.append(nombre)
        else:
            codigo = repo.agregar(nombre, lineas, origen=origen)
            reporte.cargadas.append((codigo, nombre))
    return reporte
