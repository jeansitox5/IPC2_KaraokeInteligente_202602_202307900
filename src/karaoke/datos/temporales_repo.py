"""
temporales_repo.py - TMP_NOMBRES y TMP_LETRAS.

Requisito R10: una canción que el modo automático no encuentra se transcribe
aquí primero; el usuario la corrige y le pone nombre en (f)->(v), y recién
entonces se "promueve" a las tablas permanentes NOMBRES y LETRAS.
"""


class TemporalesRepo:
    def __init__(self, db):
        self.db = db

    def crear(self, nombre_provisional="(capturando)"):
        with self.db.transaccion() as c:
            return c.execute(
                "INSERT INTO TMP_NOMBRES (nombre_provisional) VALUES (?)", (nombre_provisional,)
            ).lastrowid

    def agregar_linea(self, id_tmp, linea, confianza=None):
        with self.db.transaccion() as c:
            n = c.execute(
                "SELECT COALESCE(MAX(numero_linea), 0) + 1 FROM TMP_LETRAS WHERE id_tmp = ?",
                (id_tmp,),
            ).fetchone()[0]
            c.execute(
                "INSERT INTO TMP_LETRAS (id_tmp, numero_linea, linea, confianza) VALUES (?, ?, ?, ?)",
                (id_tmp, n, linea, confianza),
            )

    def lineas(self, id_tmp):
        return [
            f["linea"]
            for f in self.db.conn.execute(
                "SELECT linea FROM TMP_LETRAS WHERE id_tmp = ? ORDER BY numero_linea", (id_tmp,)
            )
        ]

    def obtener(self, id_tmp):
        f = self.db.conn.execute("SELECT * FROM TMP_NOMBRES WHERE id_tmp = ?", (id_tmp,)).fetchone()
        return dict(f) if f else None

    def cambiar_estado(self, id_tmp, estado, nombre_provisional=None):
        with self.db.transaccion() as c:
            if nombre_provisional:
                c.execute(
                    "UPDATE TMP_NOMBRES SET estado = ?, nombre_provisional = ? WHERE id_tmp = ?",
                    (estado, nombre_provisional, id_tmp),
                )
            else:
                c.execute("UPDATE TMP_NOMBRES SET estado = ? WHERE id_tmp = ?", (estado, id_tmp))

    def borrar(self, id_tmp):
        with self.db.transaccion() as c:
            c.execute("DELETE FROM TMP_NOMBRES WHERE id_tmp = ?", (id_tmp,))

    def listar_pendientes(self):
        filas = self.db.conn.execute(
            "SELECT t.id_tmp, t.nombre_provisional, t.fecha_captura, "
            "(SELECT COUNT(*) FROM TMP_LETRAS l WHERE l.id_tmp = t.id_tmp) AS num_lineas "
            "FROM TMP_NOMBRES t WHERE t.estado = 'pendiente' ORDER BY t.id_tmp"
        ).fetchall()
        return [dict(f) for f in filas]

    def promover(self, id_tmp, nombre, lineas, canciones_repo):
        """Copia la canción corregida a NOMBRES/LETRAS en UNA transacción."""
        with self.db.transaccion() as c:
            codigo = canciones_repo.agregar(nombre, lineas, origen="automatico", conn=c)
            c.execute("UPDATE TMP_NOMBRES SET estado = 'promovida' WHERE id_tmp = ?", (id_tmp,))
            return codigo
