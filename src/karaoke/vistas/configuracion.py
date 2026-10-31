"""
configuracion.py - Opción (k): cambiar parámetros sin tocar el código.

Aquí se cambian, entre otros, los promedios del enunciado (10 líneas por
canción, 80 caracteres por línea). Se guardan en la tabla CONFIGURACION.
"""
from karaoke.config import DEFAULTS
from karaoke.vistas.base import (
    GRIS, TEXTO_GRIS, VERDE, Pantalla, agrupar, boton, entrada, envolver, etiqueta, fila,
)

SECCIONES = [
    ("Promedios del enunciado", ["LINEAS_POR_PAGINA", "LINEAS_PROMEDIO_CANCION",
                                 "CARACTERES_PROMEDIO_LINEA", "MAX_CARACTERES_LINEA"]),
    ("Voz a texto", ["MOTOR_VOZ", "IDIOMA", "IDIOMA_ANDROID", "VENTANA_SEG", "SALTO_SEG", "WHISPER_HILOS"]),
    ("Sincronización", ["UMBRAL_IDENTIFICACION", "UMBRAL_NUEVA", "VELOCIDAD_INICIAL",
                        "ADELANTO_SEG", "SILENCIO_PAUSA_SEG", "SILENCIO_FIN_SEG"]),
]
MOTORES = {"auto", "whisper", "android", "simulado", "archivo"}


class PantallaConfiguracion(Pantalla):
    titulo = "(k) Configuración"

    def construir(self):
        self.campos = {}
        hijos = [self.encabezado()]
        for titulo, claves in SECCIONES:
            hijos.append(fila(etiqueta(titulo, 14, negrita=True)))
            for clave in claves:
                campo = entrada(valor=str(self.app.cfg[clave]))
                self.campos[clave] = campo
                hijos.append(fila(etiqueta(envolver(f"{clave} — {DEFAULTS[clave][1]}", 34), 10, color=TEXTO_GRIS)))
                hijos.append(fila(campo))
        self.resultado = etiqueta("", 12, color=VERDE)
        hijos += [
            agrupar(boton("Guardar", self._guardar, color=VERDE), boton("Valores de fábrica", self._restaurar, color=GRIS)),
            fila(self.resultado),
        ]
        return self.desplazable(*hijos)

    async def _guardar(self, widget):
        errores = []
        for clave, campo in self.campos.items():
            valor = (campo.value or "").strip()
            if clave == "MOTOR_VOZ" and valor not in MOTORES:
                errores.append(f"MOTOR_VOZ debe ser uno de: {', '.join(sorted(MOTORES))}")
                continue
            try:
                self.app.cfg.establecer(clave, valor)
            except ValueError:
                errores.append(f"{clave}: «{valor}» no es un valor válido")
        if errores:
            await self.error("Revise estos valores", "\n".join(errores))
        else:
            self.resultado.text = "Configuración guardada."

    async def _restaurar(self, widget):
        if await self.confirmar("Valores de fábrica", "¿Restaurar todos los valores por defecto?"):
            self.app.cfg.restaurar()
            for clave, campo in self.campos.items():
                campo.value = str(self.app.cfg[clave])
            self.resultado.text = "Se restauraron los valores de fábrica."
