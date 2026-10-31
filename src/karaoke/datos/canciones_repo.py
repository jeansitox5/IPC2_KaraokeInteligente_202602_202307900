"""
canciones_repo.py - Acceso a NOMBRES, LETRAS e HISTORIAL (patrón Repositorio).

Ninguna pantalla escribe SQL: todas llaman a estos métodos.
"""
from karaoke.nucleo.texto import normalizar


class CancionesRepo:
    def __init__(self, db):
        self.db = db

    # ------------------------------------------------------------ escritura
    def agregar(self, nombre, lineas, origen="manual", artista=None, conn=None):
        """Inserta la canción y sus líneas en una sola transacción.
        Devuelve el código generado automáticamente."""
        nombre = " ".join(nombre.split())
        if not nombre:
            raise ValueError("El nombre de la canción no puede estar vacío.")
        lineas = [l for l in (" ".join(x.split()) for x in lineas) if l]
        if not lineas:
            raise ValueError("La canción debe tener al menos una línea.")

        def _insertar(c):
            cur = c.execute(
                "INSERT INTO NOMBRES (nombre_cancion, nombre_normalizado, artista, origen) "
                "VALUES (?, ?, ?, ?)",
                (nombre, normalizar(nombre), artista, origen),
            )
            codigo = cur.lastrowid
            c.executemany(
                "INSERT INTO LETRAS (codigo, numero_linea, linea, linea_normalizada) "
                "VALUES (?, ?, ?, ?)",
                [(codigo, i + 1, l, normalizar(l)) for i, l in enumerate(lineas)],
            )
            return codigo

        if conn is not None:  # ya dentro de una transacción de otro repositorio
            return _insertar(conn)
        with self.db.transaccion() as c:
            return _insertar(c)

    def reemplazar_lineas(self, codigo, lineas, nombre=None):
        lineas = [l for l in (" ".join(x.split()) for x in lineas) if l]
        if not lineas:
            raise ValueError("La canción debe tener al menos una línea.")
        with self.db.transaccion() as c:
            if nombre:
                nombre = " ".join(nombre.split())
                c.execute(
                    "UPDATE NOMBRES SET nombre_cancion = ?, nombre_normalizado = ? WHERE codigo = ?",
                    (nombre, normalizar(nombre), codigo),
                )
            c.execute("DELETE FROM LETRAS WHERE codigo = ?", (codigo,))
            c.executemany(
                "INSERT INTO LETRAS (codigo, numero_linea, linea, linea_normalizada) "
                "VALUES (?, ?, ?, ?)",
                [(codigo, i + 1, l, normalizar(l)) for i, l in enumerate(lineas)],
            )

    def borrar(self, codigo):
        """Borra la canción; sus líneas se borran solas (ON DELETE CASCADE)."""
        with self.db.transaccion() as c:
            return c.execute("DELETE FROM NOMBRES WHERE codigo = ?", (codigo,)).rowcount > 0

    def incrementar_cantada(self, codigo):
        with self.db.transaccion() as c:
            c.execute(
                "UPDATE NOMBRES SET veces_cantada = veces_cantada + 1 WHERE codigo = ?",
                (codigo,),
            )

    def guardar_duraciones(self, codigo, duraciones):
        """[OPC] duraciones = {numero_linea: segundos} aprendidas en modo automático."""
        with self.db.transaccion() as c:
            c.executemany(
                "UPDATE LETRAS SET duracion_seg = ? WHERE codigo = ? AND numero_linea = ?",
                [(seg, codigo, n) for n, seg in duraciones.items()],
            )

    # ------------------------------------------------------------ lectura
    def existe_nombre(self, nombre):
        fila = self.db.conn.execute(
            "SELECT codigo FROM NOMBRES WHERE nombre_normalizado = ?", (normalizar(nombre),)
        ).fetchone()
        return fila["codigo"] if fila else None

    def obtener(self, codigo):
        fila = self.db.conn.execute("SELECT * FROM NOMBRES WHERE codigo = ?", (codigo,)).fetchone()
        return dict(fila) if fila else None

    def lineas(self, codigo):
        filas = self.db.conn.execute(
            "SELECT linea FROM LETRAS WHERE codigo = ? ORDER BY numero_linea", (codigo,)
        ).fetchall()
        return [f["linea"] for f in filas]

    def contar(self):
        return self.db.contar()

    def listar(self, desplazamiento=0, limite=10):
        filas = self.db.conn.execute(
            "SELECT n.codigo, n.nombre_cancion, n.artista, n.origen, n.veces_cantada, "
            "(SELECT COUNT(*) FROM LETRAS l WHERE l.codigo = n.codigo) AS num_lineas "
            "FROM NOMBRES n ORDER BY n.codigo LIMIT ? OFFSET ?",
            (limite, desplazamiento),
        ).fetchall()
        return [dict(f) for f in filas]

    def resolver(self, nombre_o_codigo):
        """Busca por código (si es número) o por nombre (exacto y luego parcial).
        Devuelve una lista de canciones (dict)."""
        texto = str(nombre_o_codigo).strip()
        if not texto:
            return []
        if texto.isdigit():
            c = self.obtener(int(texto))
            return [c] if c else []
        norm = normalizar(texto)
        exacta = self.db.conn.execute(
            "SELECT * FROM NOMBRES WHERE nombre_normalizado = ?", (norm,)
        ).fetchall()
        if exacta:
            return [dict(f) for f in exacta]
        parcial = self.db.conn.execute(
            "SELECT * FROM NOMBRES WHERE nombre_normalizado LIKE ? ORDER BY codigo",
            (f"%{norm}%",),
        ).fetchall()
        return [dict(f) for f in parcial]

    def todas_con_lineas(self):
        """{codigo: (nombre, [lineas])} para cargar el buscador en memoria."""
        resultado = {}
        for f in self.db.conn.execute("SELECT codigo, nombre_cancion FROM NOMBRES ORDER BY codigo"):
            resultado[f["codigo"]] = (f["nombre_cancion"], [])
        for f in self.db.conn.execute("SELECT codigo, linea FROM LETRAS ORDER BY codigo, numero_linea"):
            if f["codigo"] in resultado:
                resultado[f["codigo"]][1].append(f["linea"])
        return resultado

    # ------------------------------------------------------------ historial
    def registrar_historial(self, codigo, modo, completada=True):
        with self.db.transaccion() as c:
            c.execute(
                "INSERT INTO HISTORIAL (codigo, modo, completada) VALUES (?, ?, ?)",
                (codigo, modo, 1 if completada else 0),
            )
