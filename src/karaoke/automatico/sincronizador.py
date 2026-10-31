"""
sincronizador.py - El corazón del modo automático.

Decide QUÉ canción se canta y EN QUÉ LÍNEA va el cantante, a partir de
observaciones de voz a texto que llegan con retraso y con errores.

Máquina de estados:
    ESCUCHANDO -> IDENTIFICANDO -> SIGUIENDO -> FIN -> (repetir / otra canción)
                              \\-> NUEVA (canción que no está en la base)
    SIGUIENDO se "congela" (pausa) cuando no hay voz.

Predictor-corrector (idea de un filtro de Kalman simplificado):
    posición estimada  p̂(t) = p + v·(t − t_ref)
    - PREDICE: entre observaciones la letra avanza sola a v palabras/segundo,
      así la pantalla no va atrasada aunque la IA tarde en responder.
    - CORRIGE: cada observación ubica al cantante (p_obs) y acerca la estimación:
      p = p̂ + 0.6·(p_obs − p̂); la velocidad se ajusta con promedio exponencial.
    - Si p_obs está muy lejos (repitió una línea o saltó), solo se salta cuando
      hay certeza (puntaje alto o dos observaciones coherentes).
    - Sin voz por más de SILENCIO_PAUSA_SEG la predicción se detiene.

Todas las funciones reciben el instante 'ahora' (time.monotonic) para que se
puedan probar con tiempos simulados.
"""
ESCUCHANDO = "ESCUCHANDO"
IDENTIFICANDO = "IDENTIFICANDO"
SIGUIENDO = "SIGUIENDO"
NUEVA = "CAPTURANDO NUEVA"
FIN = "FIN DE CANCIÓN"

PALABRAS_MAX = 12        # se usan las últimas N palabras de cada observación
PUNTAJE_SEGUIR = 0.45    # mínimo para aceptar una observación dentro de la canción actual
PUNTAJE_SALTO_SEGURO = 0.75


class Sincronizador:
    def __init__(self, buscador, cfg):
        self.buscador = buscador
        self.cfg = cfg
        self.estado = ESCUCHANDO
        self.cancion = None          # CancionIndexada que se sigue
        self.p = 0.0                 # posición (palabras) en t_ref
        self.v = float(cfg["VELOCIDAD_INICIAL"])
        self.t_ref = None
        self.ultima_voz = None
        self.ignorado = False        # tecla (i): el operador suspendió el proceso
        self.prioridad = None        # código de la siguiente canción del PROGRAMA
        self.ultima_terminada = None # para detectar "repetir la misma canción"
        self._prev_obs = None        # (p_obs, t) de la última observación aceptada
        self._salto_pendiente = None
        self._candidata = None
        self._rival = (None, 0)
        self._contador_nueva = 0
        self._ultimo_puntaje = 0.0
        self.inicio_linea_t = {}     # [OPC] instante en que empezó cada línea

    # ------------------------------------------------------------- consultas
    def prediccion(self, ahora):
        if self.cancion is None:
            return 0.0
        if self.t_ref is None:
            return self.p
        efectivo = ahora
        if self.ultima_voz is not None:
            # Sin voz: la predicción se congela SILENCIO_PAUSA_SEG después de la última voz.
            efectivo = min(ahora, max(self.ultima_voz, self.t_ref) + self.cfg["SILENCIO_PAUSA_SEG"])
        dt = max(0.0, efectivo - self.t_ref)
        return min(self.p + self.v * dt, float(self.cancion.total_palabras))

    def linea_actual(self, ahora):
        """Índice de la línea que se debe resaltar (con anticipación ADELANTO_SEG)."""
        if self.cancion is None:
            return None
        if self.estado == FIN:
            return len(self.cancion.lineas) - 1
        return self.cancion.linea_en(self.prediccion(ahora + self.cfg["ADELANTO_SEG"]))

    def en_pausa(self, ahora):
        if self.ignorado:
            return True
        if self.estado != SIGUIENDO or self.ultima_voz is None:
            return False
        return ahora - self.ultima_voz > self.cfg["SILENCIO_PAUSA_SEG"]

    def texto_estado(self, ahora):
        if self.ignorado:
            return "IGNORANDO (presione s para seguir)"
        if self.en_pausa(ahora):
            return "EN PAUSA (silencio)"
        return self.estado

    # ---------------------------------------------------------- observaciones
    def procesar(self, obs):
        """Procesa una observación. Devuelve una lista de eventos (tuplas)."""
        if obs.voz:
            self.ultima_voz = obs.t_fin if self.ultima_voz is None else max(self.ultima_voz, obs.t_fin)
        if self.ignorado or obs.texto is None:
            return []
        pal = obs.palabras[-PALABRAS_MAX:]
        if not pal:
            return []
        if len(pal) >= 3 and len(set(pal)) <= 2:
            return []   # vocalización ("la la la", "mi mi mi"): se ignora
        if self.estado in (ESCUCHANDO, IDENTIFICANDO, FIN):
            return self._identificar(pal, obs.t_fin)
        if self.estado == SIGUIENDO:
            return self._seguir(pal, obs.t_fin)
        return []  # NUEVA: el aprendiz se encarga del texto

    def _identificar(self, pal, t):
        eventos = []
        venia_de_fin = self.estado == FIN
        if self.estado == ESCUCHANDO:
            self.estado = IDENTIFICANDO
        if len(pal) < 3:
            return eventos
        resultados = self.buscador.alinear(pal)
        # Bonificaciones: siguiente del programa y repetir la canción recién terminada.
        for r in resultados:
            if r.codigo == self.prioridad:
                r.puntaje += 0.10
            if venia_de_fin and r.codigo == self.ultima_terminada:
                c = self.buscador.canciones[r.codigo]
                if c.linea_en(r.posicion) <= 1:
                    r.puntaje += 0.10
        resultados.sort(key=lambda r: -r.puntaje)
        mejor = resultados[0] if resultados else None
        segundo = resultados[1].puntaje if len(resultados) > 1 else 0.0
        umbral = self.cfg["UMBRAL_IDENTIFICACION"]
        self._ultimo_puntaje = mejor.puntaje if mejor else 0.0

        if mejor and mejor.puntaje >= umbral and (
            mejor.puntaje - segundo >= 0.10 or self._candidata == mejor.codigo
        ):
            repetida = venia_de_fin and mejor.codigo == self.ultima_terminada
            self._iniciar(mejor.codigo, mejor.posicion, t)
            eventos.append(("cancion_repetida" if repetida else "identificada", mejor.codigo))
            return eventos
        self._candidata = mejor.codigo if mejor and mejor.puntaje >= umbral else None

        distintas = len({p for p in pal if len(p) >= 2})
        if (not mejor or mejor.puntaje < self.cfg["UMBRAL_NUEVA"]) and distintas >= 4:
            self._contador_nueva += 1
        else:
            self._contador_nueva = 0
        if self._contador_nueva >= 3:
            self._contador_nueva = 0
            self.estado = NUEVA
            self.cancion = None
            eventos.append(("nueva_detectada", None))
        return eventos

    def _iniciar(self, codigo, posicion, t):
        self.cancion = self.buscador.canciones[codigo]
        self.estado = SIGUIENDO
        self.p = float(posicion)
        self.t_ref = t
        self.v = float(self.cfg["VELOCIDAD_INICIAL"])
        self._prev_obs = (float(posicion), t)
        self._salto_pendiente = None
        self._candidata = None
        self._rival = (None, 0)
        self._contador_nueva = 0

    def _seguir(self, pal, t):
        eventos = []
        posiciones = self.buscador.posiciones(pal, self.cancion.codigo)
        mejor_local = max((s for s, _ in posiciones), default=0.0)
        self._ultimo_puntaje = mejor_local

        if mejor_local < PUNTAJE_SEGUIR:
            # No coincide con la canción actual: ¿cantan otra?
            otras = [a for a in self.buscador.alinear(pal) if a.codigo != self.cancion.codigo]
            if otras and otras[0].puntaje >= self.cfg["UMBRAL_IDENTIFICACION"]:
                codigo, veces = self._rival
                veces = veces + 1 if codigo == otras[0].codigo else 1
                self._rival = (otras[0].codigo, veces)
                if veces >= 2:
                    anterior = self.cancion.codigo
                    self._iniciar(otras[0].codigo, otras[0].posicion, t)
                    eventos.append(("cambio", anterior))
                    eventos.append(("identificada", self.cancion.codigo))
            return eventos
        self._rival = (None, 0)

        p_hat = self.prediccion(t)
        # Entre las mejores posiciones (casi empatadas) se elige la más cercana a la predicción.
        cercanas = [pos for s, pos in posiciones if s >= mejor_local - 0.05]
        p_obs = min(cercanas, key=lambda pos: abs(pos - p_hat))
        diferencia = p_obs - p_hat
        linea = self.cancion.linea_en(p_hat)
        tolerancia = max(4, self.cancion.palabras_de_linea(linea))

        if abs(diferencia) <= tolerancia:
            self._actualizar_velocidad(p_obs, t)
            self.p = p_hat + 0.6 * diferencia
            self.t_ref = t
            self._prev_obs = (p_obs, t)
            self._salto_pendiente = None
        elif mejor_local >= PUNTAJE_SALTO_SEGURO or (
            self._salto_pendiente is not None and abs(self._salto_pendiente - p_obs) <= tolerancia
        ):
            if diferencia < 0:
                eventos.append(("linea_repetida", self.cancion.linea_en(p_obs - 1)))
            else:
                eventos.append(("salto", self.cancion.linea_en(p_obs)))
            self.p = float(p_obs)
            self.t_ref = t
            self._prev_obs = (p_obs, t)
            self._salto_pendiente = None
        else:
            self._salto_pendiente = p_obs
        return eventos

    def _actualizar_velocidad(self, p_obs, t):
        if self._prev_obs is None:
            return
        p0, t0 = self._prev_obs
        dt = t - t0
        if dt >= 0.8 and p_obs > p0:
            instantanea = (p_obs - p0) / dt
            instantanea = min(max(instantanea, 0.8), 5.0)
            self.v = 0.7 * self.v + 0.3 * instantanea

    # ------------------------------------------------------------- reloj
    def tick(self, ahora):
        """Se llama ~10 veces por segundo. Detecta el fin de la canción."""
        eventos = []
        if self.estado != SIGUIENDO or self.cancion is None:
            return eventos
        silencio = ahora - self.ultima_voz if self.ultima_voz is not None else 0.0
        pred = self.prediccion(ahora)
        total = self.cancion.total_palabras
        ultima_linea = self.cancion.linea_en(pred) >= len(self.cancion.lineas) - 1
        if (pred >= total - 0.5 and silencio >= 2.0) or (
            ultima_linea and silencio >= self.cfg["SILENCIO_FIN_SEG"]
        ):
            self.estado = FIN
            self.ultima_terminada = self.cancion.codigo
            eventos.append(("fin_cancion", self.cancion.codigo))
        return eventos

    # ------------------------------------------- respaldo manual del operador
    def _fijar_linea(self, idx, ahora):
        idx = min(max(idx, 0), len(self.cancion.lineas) - 1)
        self.p = float(self.cancion.inicio_linea[idx])
        self.t_ref = ahora
        self.ultima_voz = ahora
        self._prev_obs = (self.p, ahora)
        self._salto_pendiente = None

    def avanzar(self, ahora):
        if self.cancion is None:
            return
        actual = self.linea_actual(ahora)
        if actual >= len(self.cancion.lineas) - 1:
            self.estado = FIN
            self.ultima_terminada = self.cancion.codigo
            return [("fin_cancion", self.cancion.codigo)]
        self.estado = SIGUIENDO
        self._fijar_linea(actual + 1, ahora)
        return []

    def retroceder(self, ahora):
        if self.cancion is not None:
            self.estado = SIGUIENDO
            self._fijar_linea(self.linea_actual(ahora) - 1, ahora)

    def repetir_linea(self, ahora):
        if self.cancion is not None:
            self.estado = SIGUIENDO
            self._fijar_linea(self.linea_actual(ahora), ahora)

    def repetir_cancion(self, ahora):
        if self.cancion is not None:
            self.estado = SIGUIENDO
            self._fijar_linea(0, ahora)

    def ignorar(self, ahora):
        if self.cancion is not None:
            self.p = self.prediccion(ahora)
            self.t_ref = ahora
        self.ignorado = True

    def seguir(self, ahora):
        self.ignorado = False
        self.ultima_voz = ahora
        if self.cancion is not None:
            self.t_ref = ahora

    def otra_cancion(self):
        self.estado = ESCUCHANDO
        self.cancion = None
        self._candidata = None

    def fijar(self, codigo, linea, ahora):
        """Coloca una canción y línea concretas (al pasar de manual a automático)."""
        self._iniciar(codigo, self.buscador.canciones[codigo].inicio_linea[linea], ahora)
        self.ultima_voz = ahora
