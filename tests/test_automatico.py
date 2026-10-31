"""Pruebas del modo automático con observaciones simuladas (sin micrófono).

Se simula un cantante que avanza a 2.5 palabras por segundo y un motor que
entrega lo oído cada 2 segundos (como Whisper) con un poco de retraso.
"""
from karaoke.audio.motor_voz import MotorSimulado, Observacion, limpiar_transcripcion
from karaoke.automatico.aprendiz import quitar_traslape
from karaoke.automatico.sesion import SesionAutomatica
from karaoke.automatico.sincronizador import FIN, NUEVA, SIGUIENDO, Sincronizador

VEL = 2.5


def _cancion(ctx, nombre):
    codigo = ctx.canciones.existe_nombre(nombre)
    return ctx.buscador.canciones[codigo]


def _obs(cancion, t, ventana=4.0, vel=VEL, inicio=0.0):
    """Lo que 'oiría' el motor en la ventana que termina en t."""
    fin = int((t - inicio) * vel)
    ini = max(0, int((t - ventana - inicio) * vel))
    texto = " ".join(cancion.palabras[ini:fin])
    return Observacion(texto=texto, t_fin=t, voz=True)


def _voz(t):
    return Observacion(texto=None, t_fin=t, voz=True)


def test_identifica_y_sigue_el_ritmo(ctx):
    c = _cancion(ctx, "Mercado de colores")
    s = Sincronizador(ctx.buscador, ctx.cfg)
    t = 4.0
    while t <= 30.0:
        s.procesar(_voz(t))
        s.procesar(_obs(c, t))
        t += 2.0
    assert s.estado == SIGUIENDO and s.cancion.codigo == c.codigo
    # A los 31 s el cantante va en la palabra ~77: la línea mostrada debe coincidir (±1)
    esperada = c.linea_en(31.0 * VEL)
    s.procesar(_voz(31.0))
    assert abs(s.linea_actual(31.0) - esperada) <= 1
    assert 2.0 <= s.v <= 3.0


def test_se_congela_en_silencio_y_retoma(ctx):
    c = _cancion(ctx, "Bicicleta azul")
    s = Sincronizador(ctx.buscador, ctx.cfg)
    for t in (4.0, 6.0, 8.0):
        s.procesar(_voz(t))
        s.procesar(_obs(c, t))
    assert s.estado == SIGUIENDO
    linea = s.linea_actual(8.0)
    # 10 segundos sin voz: la línea no avanza
    assert s.en_pausa(18.0)
    assert s.linea_actual(18.0) <= linea + 1


def test_vocalizacion_no_identifica(ctx):
    s = Sincronizador(ctx.buscador, ctx.cfg)
    s.procesar(Observacion("la la la la la la", 2.0))
    assert s.cancion is None


def test_cancion_nueva_y_aprendiz(ctx):
    motor = MotorSimulado()
    sesion = SesionAutomatica(ctx, motor)
    sesion.iniciar()
    frases = [
        "hoy camino descalzo sobre arena tibia del puerto",
        "gaviotas dibujan círculos encima de barcos pesqueros",
        "un faro lejano parpadea mientras cae la tarde",
        "y mi guitarra vieja canta sola junto al mar",
    ]
    t = 0.0
    for f in frases:
        t += 3.0
        sesion.cola.put(Observacion(f, t))
        sesion.tick(t)
    assert sesion.sinc.estado == NUEVA and sesion.aprendiz.activo
    sesion.tick(t + 20.0)  # silencio largo: termina la captura
    pendientes = ctx.temporales.listar_pendientes()
    assert len(pendientes) == 1 and pendientes[0]["num_lineas"] >= 1
    codigo = ctx.temporales.promover(
        pendientes[0]["id_tmp"], "Faro del puerto", ctx.temporales.lineas(pendientes[0]["id_tmp"]), ctx.canciones
    )
    assert ctx.canciones.obtener(codigo)["origen"] == "automatico"


def test_fin_de_cancion_y_programa(ctx):
    from karaoke.nucleo.programa import cargar_programa

    cargar_programa("Estrellas en el techo\n", ctx.programa, ctx.canciones)
    c = _cancion(ctx, "Estrellas en el techo")
    sesion = SesionAutomatica(ctx, MotorSimulado())
    sesion.iniciar()
    duracion = c.total_palabras / VEL
    t = 4.0
    while t <= duracion + 1:
        sesion.cola.put(_voz(t))
        sesion.cola.put(_obs(c, t))
        sesion.tick(t)
        t += 2.0
    sesion.tick(t + 8.0)
    assert sesion.sinc.estado == FIN
    assert sesion.cantadas == 1
    assert ctx.programa.siguiente_pendiente() is None


def test_quitar_traslape():
    assert quitar_traslape("a b c d".split(), "c d e f".split()) == ["e", "f"]
    assert quitar_traslape([], "x y".split()) == ["x", "y"]


def test_filtro_alucinaciones():
    assert limpiar_transcripcion("[Música]") == ""
    assert limpiar_transcripcion("Gracias por ver el video") == ""
    assert limpiar_transcripcion("la música suena en el parque") != ""
