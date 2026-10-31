"""
alimentacion.py - Opción (f): alimentar la base CANCIONES.

(t) desde un archivo de texto plano (o texto pegado, o el ejemplo incluido)
(e) manualmente, campo por campo; una línea vacía termina la canción
(v) revisar canciones capturadas por el modo automático (tablas temporales)
"""
import toga
from toga.style import Pack
from toga.style.pack import COLUMN

from karaoke import plataforma
from karaoke.nucleo.importador import importar_texto
from karaoke.nucleo.texto import preparar_lineas
from karaoke.vistas.base import (
    AZUL, GRIS, NARANJA, TEXTO_GRIS, VERDE, Pantalla, area_texto, boton, entrada, etiqueta, fila,
)


class PantallaAlimentacion(Pantalla):
    titulo = "Alimentación"

    def construir(self):
        pendientes = len(self.app.temporales.listar_pendientes())
        return self.desplazable(
            self.encabezado(),
            boton("(t) Cargar desde archivo de texto", lambda w: self.app.mostrar(PantallaImportar(self.app))),
            boton("(e) Escribir una canción manualmente", lambda w: self.app.mostrar(PantallaCaptura(self.app))),
            boton(f"(v) Revisar canciones capturadas ({pendientes} pendientes)",
                  lambda w: self.app.mostrar(PantallaRevisar(self.app)), color=VERDE),
            etiqueta("Formato del archivo: nombre de la canción en la primera línea, su letra "
                     "debajo (una línea por renglón) y una línea en blanco entre canciones.", 11,
                     color=TEXTO_GRIS),
        )


# ====================================================================== (t)
class PantallaImportar(Pantalla):
    titulo = "(t) Cargar desde archivo"

    def construir(self):
        self.resultado = etiqueta("", 12, color=VERDE)
        self.pegado = area_texto(placeholder="…o pegue aquí el texto con el formato del archivo")
        return self.desplazable(
            self.encabezado(),
            fila(boton("Elegir archivo…", self._elegir),
                 boton("Cargar ejemplo incluido", self._ejemplo, color=GRIS)),
            self.pegado,
            boton("Importar el texto pegado", self._pegado, color=VERDE),
            self.resultado,
        )

    async def _elegir(self, widget):
        try:
            elegido = await plataforma.elegir_archivo_texto(self.app)
        except Exception as e:  # noqa: BLE001
            await self.error("No se pudo abrir", str(e))
            return
        if elegido:
            nombre, texto = elegido
            self._importar(texto, f"Archivo {nombre}: ")

    def _ejemplo(self, widget):
        ruta = self.app.paths.app / "resources" / "ejemplos" / "canciones.txt"
        self._importar(ruta.read_text(encoding="utf-8"), "Ejemplo: ")

    def _pegado(self, widget):
        self._importar(self.pegado.value or "", "Texto pegado: ")

    def _importar(self, texto, prefijo):
        if not texto.strip():
            self.resultado.text = "No hay texto para importar."
            return
        reporte = importar_texto(texto, self.app.canciones, self.app.cfg["MAX_CARACTERES_LINEA"])
        self.app.recargar_buscador()
        self.resultado.text = prefijo + reporte.resumen()
        if reporte.cargadas:
            self.resultado.text += "\n" + "\n".join(f"  [{c}] {n}" for c, n in reporte.cargadas)


# ====================================================================== (e)
class PantallaCaptura(Pantalla):
    titulo = "(e) Captura manual"

    def construir(self):
        self.lineas = []
        self.nombre = entrada("Nombre de la canción")
        self.artista = entrada("Artista (opcional)")
        self.linea = entrada("Línea 1 (Enter para agregar; vacía para terminar)", al_confirmar=self._agregar)
        self.lista = etiqueta("", 12)
        self.resultado = etiqueta("", 12, color=VERDE)
        return self.desplazable(
            self.encabezado(),
            self.nombre, self.artista, self.linea,
            fila(boton("Agregar línea", self._agregar), boton("Terminar y guardar", self._guardar, color=VERDE)),
            etiqueta("Líneas ingresadas:", 11, color=TEXTO_GRIS),
            self.lista, self.resultado,
        )

    def _agregar(self, widget):
        texto = (self.linea.value or "").strip()
        if not texto:   # línea vacía = se terminó de ingresar la canción
            self.app.loop.create_task(self._guardar_async())
            return
        self.lineas.append(texto)
        self.linea.value = ""
        self.linea.placeholder = f"Línea {len(self.lineas) + 1} (vacía para terminar)"
        self.lista.text = "\n".join(f"{i + 1}. {l}" for i, l in enumerate(self.lineas))
        self.linea.focus()

    def _guardar(self, widget):
        self.app.loop.create_task(self._guardar_async())

    async def _guardar_async(self):
        nombre = (self.nombre.value or "").strip()
        if not nombre:
            await self.error("Falta el nombre", "Escriba el nombre de la canción.")
            return
        if not self.lineas:
            await self.error("Sin letra", "Agregue al menos una línea.")
            return
        if self.app.canciones.existe_nombre(nombre):
            await self.error("Ya existe", f"Ya hay una canción llamada «{nombre}».")
            return
        lineas = preparar_lineas(self.lineas, self.app.cfg["MAX_CARACTERES_LINEA"])
        codigo = self.app.canciones.agregar(nombre, lineas, origen="manual",
                                           artista=(self.artista.value or "").strip() or None)
        self.app.recargar_buscador()
        await self.info("Canción guardada", f"Se guardó «{nombre}» con el código {codigo} "
                                            f"({len(lineas)} líneas).")
        self.app.mostrar(PantallaCaptura(self.app))


# ====================================================================== (v)
class PantallaRevisar(Pantalla):
    titulo = "(v) Canciones capturadas"

    def construir(self):
        self.cuerpo = toga.Box(style=Pack(direction=COLUMN, gap=8))
        self._lista()
        return self.desplazable(self.encabezado(), self.cuerpo)

    def _lista(self):
        self.cuerpo.clear()
        pendientes = self.app.temporales.listar_pendientes()
        if not pendientes:
            self.cuerpo.add(etiqueta("No hay canciones capturadas pendientes de revisar.", 12))
            return
        self.cuerpo.add(etiqueta("Letras capturadas por el modo automático. Corríjalas, póngales "
                                 "nombre y páselas a la base permanente.", 11, color=TEXTO_GRIS))
        for p in pendientes:
            texto = f"#{p['id_tmp']} · {p['nombre_provisional']} ({p['num_lineas']} líneas, {p['fecha_captura']})"
            self.cuerpo.add(boton(texto, self._abrir(p["id_tmp"]), color=AZUL))

    def _abrir(self, id_tmp):
        return lambda widget: self._editor(id_tmp)

    def _editor(self, id_tmp):
        self.cuerpo.clear()
        registro = self.app.temporales.obtener(id_tmp)
        self.id_tmp = id_tmp
        self.nombre = entrada("Nombre real de la canción", valor=registro["nombre_provisional"])
        self.texto = area_texto("\n".join(self.app.temporales.lineas(id_tmp)), alto=300)
        self.cuerpo.add(etiqueta("Nombre:", 11, color=TEXTO_GRIS))
        self.cuerpo.add(self.nombre)
        self.cuerpo.add(etiqueta("Letra (una línea por renglón, corrija lo que haga falta):", 11, color=TEXTO_GRIS))
        self.cuerpo.add(self.texto)
        self.cuerpo.add(fila(
            boton("Guardar en la base", self._promover, color=VERDE),
            boton("Descartar", self._descartar, color=NARANJA),
            boton("Volver", lambda w: self._lista(), color=GRIS),
        ))

    async def _promover(self, widget):
        nombre = (self.nombre.value or "").strip()
        lineas = preparar_lineas((self.texto.value or "").splitlines(), self.app.cfg["MAX_CARACTERES_LINEA"])
        if not nombre or not lineas:
            await self.error("Datos incompletos", "La canción necesita nombre y al menos una línea.")
            return
        if self.app.canciones.existe_nombre(nombre):
            await self.error("Ya existe", f"Ya hay una canción llamada «{nombre}». Cambie el nombre.")
            return
        codigo = self.app.temporales.promover(self.id_tmp, nombre, lineas, self.app.canciones)
        self.app.recargar_buscador()
        await self.info("Canción guardada", f"«{nombre}» pasó a la base con el código {codigo}.")
        self._lista()

    async def _descartar(self, widget):
        if await self.confirmar("Descartar", "¿Seguro que desea descartar esta captura?"):
            self.app.temporales.cambiar_estado(self.id_tmp, "descartada")
            self._lista()
