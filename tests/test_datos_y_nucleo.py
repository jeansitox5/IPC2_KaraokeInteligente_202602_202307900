"""Pruebas de la base de datos, texto, importador, buscador y programa."""
from karaoke.datos.base_datos import BaseDatos
from karaoke.datos.canciones_repo import CancionesRepo
from karaoke.nucleo.importador import importar_texto
from karaoke.nucleo.programa import cargar_programa
from karaoke.nucleo.texto import normalizar, parsear_canciones, partir_linea


# ------------------------------------------------------------------ texto
def test_normalizar_quita_tildes_y_signos():
    assert normalizar("¡Corazón, AQUÍ!") == "corazon aqui"


def test_partir_linea_larga():
    partes = partir_linea("uno dos tres cuatro cinco seis", 12)
    assert all(len(p) <= 12 for p in partes)
    assert " ".join(partes) == "uno dos tres cuatro cinco seis"


def test_parsear_bloques():
    texto = "A\nl1\nl2\n\nB\nm1\n\n\nC\n"
    assert parsear_canciones(texto) == [("A", ["l1", "l2"]), ("B", ["m1"]), ("C", [])]


# ------------------------------------------------------------- base de datos
def test_crea_y_detecta_base(tmp_path):
    db = BaseDatos(tmp_path)
    assert db.era_nueva and "creada" in db.mensaje
    db.cerrar()
    db2 = BaseDatos(tmp_path)
    assert not db2.era_nueva and "encontrada" in db2.mensaje
    tablas = {f[0] for f in db2.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"NOMBRES", "LETRAS", "PROGRAMA", "TMP_NOMBRES", "TMP_LETRAS", "CONFIGURACION", "HISTORIAL"} <= tablas
    db2.cerrar()


def test_codigo_automatico_y_borrado_en_cascada(tmp_path):
    db = BaseDatos(tmp_path)
    repo = CancionesRepo(db)
    c1 = repo.agregar("Uno", ["a b c", "d e f"])
    c2 = repo.agregar("Dos", ["g h i"])
    assert c2 == c1 + 1
    assert repo.borrar(c1)
    assert repo.obtener(c1) is None
    assert db.conn.execute("SELECT COUNT(*) FROM LETRAS WHERE codigo=?", (c1,)).fetchone()[0] == 0
    db.cerrar()


def test_importar_reporta_duplicados(ctx):
    rep = importar_texto("Lluvia de octubre\nuna linea\n\nNueva\notra\n", ctx.canciones)
    assert rep.duplicadas == ["Lluvia de octubre"]
    assert len(rep.cargadas) == 1


def test_resolver_por_nombre_y_codigo(ctx):
    assert ctx.canciones.resolver("1")[0]["codigo"] == 1
    assert ctx.canciones.resolver("lluvia")[0]["nombre_cancion"] == "Lluvia de octubre"


def test_reemplazar_lineas(ctx):
    ctx.canciones.reemplazar_lineas(1, ["nueva primera", "nueva segunda"], nombre="Camino nuevo")
    assert ctx.canciones.lineas(1) == ["nueva primera", "nueva segunda"]
    assert ctx.canciones.obtener(1)["nombre_cancion"] == "Camino nuevo"


# ------------------------------------------------------------------ buscador
def test_buscar_dos_o_tres_palabras(ctx):
    r = ctx.buscador.buscar_fragmento("charcos del parque")
    assert r[0].nombre == "Lluvia de octubre" and r[0].linea == 4


def test_buscar_con_error_de_escritura(ctx):
    r = ctx.buscador.buscar_fragmento("compilador me grita")
    assert r[0].nombre == "Código y madrugada"
    r = ctx.buscador.buscar_fragmento("compilasor me grita")
    assert r[0].nombre == "Código y madrugada"


def test_alinear_transcripcion_con_errores(ctx):
    oido = normalizar("los niños corren con barco de papel yo guardo en el bolsillo").split()
    mejor = ctx.buscador.alinear(oido)[0]
    cancion = ctx.buscador.canciones[mejor.codigo]
    assert cancion.nombre == "Lluvia de octubre"
    assert mejor.puntaje > 0.8
    assert cancion.linea_en(mejor.posicion) == 6


def test_alinear_tolera_ruido_fuerte_de_reconocimiento(ctx):
    """Con una transcripción muy degradada (palabras perdidas y mal oídas,
    como pasa seguido con Whisper/Android), el puntaje cae por debajo del
    umbral anterior (0.55) pero sigue arriba del actual (0.45) y sigue
    identificando la canción correcta. Ver UMBRAL_IDENTIFICACION en config.py."""
    oido = "un perito dueno acompana bentas xenor marinba".split()
    mejor = ctx.buscador.alinear(oido)[0]
    cancion = ctx.buscador.canciones[mejor.codigo]
    assert cancion.nombre == "Mercado de colores"
    assert 0.45 <= mejor.puntaje < 0.55

    ajeno = "programacion orientada a objetos con herencia multiple".split()
    resultados_ajenos = ctx.buscador.alinear(ajeno)
    assert not resultados_ajenos or resultados_ajenos[0].puntaje < 0.45


# ------------------------------------------------------------------ programa
def test_programa_orden_no_estricto(ctx):
    texto = "Lluvia de octubre\ncamino a chimaltenango\nNo existe\n"
    total, encontradas, faltan = cargar_programa(texto, ctx.programa, ctx.canciones)
    assert (total, encontradas, faltan) == (3, 2, ["No existe"])
    assert ctx.programa.siguiente_pendiente()["nombre_cancion"] == "Lluvia de octubre"
    camino = ctx.canciones.existe_nombre("Camino a Chimaltenango")
    ctx.programa.marcar_cantada(camino)            # se cantó la segunda antes
    assert ctx.programa.siguiente_pendiente()["nombre_cancion"] == "Lluvia de octubre"
    ctx.programa.marcar_cantada(camino)            # repetirla no rompe nada
    ctx.programa.reiniciar()
    assert ctx.programa.resumen() == (3, 2)
