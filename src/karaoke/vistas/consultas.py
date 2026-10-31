"""
consultas.py - Opciones (w), (x), (u) y (b).

(w) códigos y nombres de 10 en 10
(x) letra de una canción por código, de 10 en 10 líneas
(u) corregir la letra por nombre o código
(b) borrar canción y su letra por nombre o código, con confirmación
"""
import toga
from toga.style import Pack
from toga.style.pack import COLUMN

from karaoke.vistas.base import (
    AZUL, GRIS, NARANJA, TEXTO_GRIS, VERDE, Paginador, Pantalla, area_texto, boton, entrada,
    etiqueta, fila,
)


# ====================================================================== (w)
class PantallaListado(Pantalla):
    titulo = "(w) Canciones en la base"

    def construir(self):
        total, _ = self.app.canciones.contar()
        self.pag = Paginador(total, self.app.cfg["LINEAS_POR_PAGINA"])
        self.lista = toga.Box(style=Pack(direction=COLUMN, gap=6))
        self.lbl_pag = etiqueta("", 11, color=TEXTO_GRIS)
        self._llenar()
        return self.desplazable(
            self.encabezado(),
            etiqueta("Toque una canción para ver su letra.", 11, color=TEXTO_GRIS),
            self.lista,
            self.lbl_pag,
            fila(boton("◀ Anterior", self._anterior, color=GRIS), boton("Siguiente ▶", self._siguiente, color=GRIS)),
        )

    def _llenar(self):
        self.lista.clear()
        filas = self.app.canciones.listar(self.pag.desplazamiento, self.pag.por_pagina)
        if not filas:
            self.lista.add(etiqueta("La base de datos no tiene canciones. Use (f) Alimentación.", 12, color=NARANJA))
        for f in filas:
            texto = f"[{f['codigo']}]  {f['nombre_cancion']}  ·  {f['num_lineas']} líneas"
            self.lista.add(boton(texto, self._ver(f["codigo"]), color=AZUL))
        self.lbl_pag.text = f"{self.pag.texto()} · {self.pag.total} canciones en total"

    def _ver(self, codigo):
        return lambda w: self.app.mostrar(PantallaVerLetra(self.app, codigo))

    def _anterior(self, w):
        self.pag.anterior()
        self._llenar()

    def _siguiente(self, w):
        self.pag.siguiente()
        self._llenar()


# ====================================================================== (x)
class PantallaVerLetra(Pantalla):
    titulo = "(x) Ver letra por código"

    def __init__(self, app, codigo=None):
        super().__init__(app)
        self.codigo_inicial = codigo

    def construir(self):
        self.entrada = entrada("Código de la canción", al_confirmar=self._ver)
        self.lbl_nombre = etiqueta("", 15, negrita=True, color=AZUL)
        self.lbl_letra = etiqueta("", 14)
        self.lbl_pag = etiqueta("", 11, color=TEXTO_GRIS)
        self.lineas, self.pag = [], None
        if self.codigo_inicial is not None:
            self.entrada.value = str(self.codigo_inicial)
            self._ver(None)
        return self.desplazable(
            self.encabezado(),
            fila(self.entrada, boton("Ver", self._ver, flex=0)),
            self.lbl_nombre, self.lbl_letra, self.lbl_pag,
            fila(boton("◀ Anterior", self._anterior, color=GRIS), boton("Siguiente ▶", self._siguiente, color=GRIS)),
        )

    def _ver(self, widget):
        texto = (self.entrada.value or "").strip()
        self.lineas, self.pag = [], None
        if not texto.isdigit():
            self.lbl_nombre.text = "Escriba un código numérico."
            self.lbl_letra.text = self.lbl_pag.text = ""
            return
        cancion = self.app.canciones.obtener(int(texto))
        if cancion is None:
            self.lbl_nombre.text = f"NO EXISTE ninguna canción con el código {texto}."
            self.lbl_letra.text = self.lbl_pag.text = ""
            return
        self.lbl_nombre.text = f"[{cancion['codigo']}] {cancion['nombre_cancion']}"
        self.lineas = self.app.canciones.lineas(cancion["codigo"])
        self.pag = Paginador(len(self.lineas), self.app.cfg["LINEAS_POR_PAGINA"])
        self._mostrar()

    def _mostrar(self):
        if not self.pag:
            return
        ini = self.pag.desplazamiento
        grupo = self.lineas[ini:ini + self.pag.por_pagina]
        self.lbl_letra.text = "\n".join(f"{ini + i + 1:>3}. {l}" for i, l in enumerate(grupo))
        self.lbl_pag.text = f"{self.pag.texto()} · {len(self.lineas)} líneas"

    def _anterior(self, w):
        if self.pag:
            self.pag.anterior()
            self._mostrar()

    def _siguiente(self, w):
        if self.pag:
            self.pag.siguiente()
            self._mostrar()


# ====================================================================== común
class _PantallaElegirCancion(Pantalla):
    """Busca una canción por nombre o código y llama a self.elegida(cancion)."""

    def construir(self):
        self.entrada = entrada("Nombre o código de la canción", al_confirmar=self._buscar)
        self.cuerpo = toga.Box(style=Pack(direction=COLUMN, gap=8))
        return self.desplazable(
            self.encabezado(),
            fila(self.entrada, boton("Buscar", self._buscar, flex=0)),
            self.cuerpo,
        )

    def _buscar(self, widget):
        self.cuerpo.clear()
        encontradas = self.app.canciones.resolver(self.entrada.value or "")
        if not encontradas:
            self.cuerpo.add(etiqueta("No se encontró ninguna canción con ese nombre o código.", 12, color=NARANJA))
        elif len(encontradas) == 1:
            self.elegida(encontradas[0])
        else:
            self.cuerpo.add(etiqueta("Hay varias coincidencias, elija una:", 11, color=TEXTO_GRIS))
            for c in encontradas[:20]:
                self.cuerpo.add(boton(f"[{c['codigo']}] {c['nombre_cancion']}", self._elegir(c), color=AZUL))

    def _elegir(self, cancion):
        def manejador(widget):
            self.cuerpo.clear()
            self.elegida(cancion)
        return manejador

    def elegida(self, cancion):
        raise NotImplementedError


# ====================================================================== (u)
class PantallaCorregir(_PantallaElegirCancion):
    titulo = "(u) Corregir letra"

    def elegida(self, cancion):
        self.codigo = cancion["codigo"]
        self.nombre = entrada("Nombre", valor=cancion["nombre_cancion"])
        self.texto = area_texto("\n".join(self.app.canciones.lineas(self.codigo)), alto=320)
        self.cuerpo.add(etiqueta(f"Corrigiendo la canción con código {self.codigo}. Puede editar, "
                                 "agregar o borrar renglones (un renglón = una línea).", 11, color=TEXTO_GRIS))
        self.cuerpo.add(self.nombre)
        self.cuerpo.add(self.texto)
        self.cuerpo.add(boton("Guardar cambios", self._guardar, color=VERDE))

    async def _guardar(self, widget):
        from karaoke.nucleo.texto import preparar_lineas

        lineas = preparar_lineas((self.texto.value or "").splitlines(), self.app.cfg["MAX_CARACTERES_LINEA"])
        nombre = (self.nombre.value or "").strip()
        if not lineas or not nombre:
            await self.error("Datos incompletos", "La canción necesita nombre y al menos una línea.")
            return
        otro = self.app.canciones.existe_nombre(nombre)
        if otro and otro != self.codigo:
            await self.error("Nombre repetido", f"Ya existe otra canción llamada «{nombre}».")
            return
        self.app.canciones.reemplazar_lineas(self.codigo, lineas, nombre=nombre)
        self.app.recargar_buscador()
        await self.info("Letra corregida", f"Se guardaron {len(lineas)} líneas para «{nombre}».")


# ====================================================================== (b)
class PantallaBorrar(_PantallaElegirCancion):
    titulo = "(b) Borrar canción"

    def elegida(self, cancion):
        self.cancion = cancion
        n = len(self.app.canciones.lineas(cancion["codigo"]))
        self.cuerpo.add(etiqueta(f"[{cancion['codigo']}] {cancion['nombre_cancion']} · {n} líneas", 14, negrita=True))
        self.cuerpo.add(boton("Borrar esta canción y su letra", self._borrar, color=NARANJA))

    async def _borrar(self, widget):
        c = self.cancion
        seguro = await self.confirmar(
            "Confirmar borrado",
            f"¿Está seguro de borrar «{c['nombre_cancion']}» (código {c['codigo']}) y toda su letra?\n"
            "Esta acción no se puede deshacer.",
        )
        if not seguro:
            self.cuerpo.clear()
            self.cuerpo.add(etiqueta("No se borró nada.", 12, color=VERDE))
            return
        self.app.canciones.borrar(c["codigo"])
        self.app.recargar_buscador()
        self.cuerpo.clear()
        self.cuerpo.add(etiqueta(f"Se borró «{c['nombre_cancion']}» y su letra.", 12, color=VERDE))
