"""
programa_repo.py - Tabla PROGRAMA (lista tentativa del cantante).
Estados: pendiente, cantada, saltada, no_encontrada.
"""


class ProgramaRepo:
    def __init__(self, db):
        self.db = db

    def reemplazar(self, elementos):
        """elementos = [(nombre_texto, codigo_o_None), ...] en orden."""
        with self.db.transaccion() as c:
            c.execute("DELETE FROM PROGRAMA")
            c.executemany(
                "INSERT INTO PROGRAMA (posicion, nombre_texto, codigo, estado) VALUES (?, ?, ?, ?)",
                [
                    (i + 1, nombre, codigo, "pendiente" if codigo else "no_encontrada")
                    for i, (nombre, codigo) in enumerate(elementos)
                ],
            )

    def listar(self):
        filas = self.db.conn.execute(
            "SELECT p.posicion, p.nombre_texto, p.codigo, p.estado, n.nombre_cancion "
            "FROM PROGRAMA p LEFT JOIN NOMBRES n ON n.codigo = p.codigo ORDER BY p.posicion"
        ).fetchall()
        return [dict(f) for f in filas]

    def siguiente_pendiente(self):
        fila = self.db.conn.execute(
            "SELECT p.posicion, p.codigo, n.nombre_cancion FROM PROGRAMA p "
            "JOIN NOMBRES n ON n.codigo = p.codigo "
            "WHERE p.estado = 'pendiente' ORDER BY p.posicion LIMIT 1"
        ).fetchone()
        return dict(fila) if fila else None

    def marcar(self, posicion, estado):
        with self.db.transaccion() as c:
            c.execute("UPDATE PROGRAMA SET estado = ? WHERE posicion = ?", (estado, posicion))

    def marcar_cantada(self, codigo):
        """Marca como cantada la primera aparición pendiente de esa canción.
        Si no estaba en el programa (o ya se cantó), no hace nada: el orden no es
        estricto y se puede repetir o cantar canciones fuera del programa."""
        with self.db.transaccion() as c:
            fila = c.execute(
                "SELECT posicion FROM PROGRAMA WHERE codigo = ? AND estado = 'pendiente' "
                "ORDER BY posicion LIMIT 1",
                (codigo,),
            ).fetchone()
            if fila:
                c.execute(
                    "UPDATE PROGRAMA SET estado = 'cantada' WHERE posicion = ?", (fila["posicion"],)
                )

    def reiniciar(self):
        with self.db.transaccion() as c:
            c.execute(
                "UPDATE PROGRAMA SET estado = 'pendiente' "
                "WHERE estado IN ('cantada', 'saltada') AND codigo IS NOT NULL"
            )

    def vaciar(self):
        with self.db.transaccion() as c:
            c.execute("DELETE FROM PROGRAMA")

    def resumen(self):
        total = pendientes = 0
        for f in self.listar():
            total += 1
            pendientes += f["estado"] == "pendiente"
        return total, pendientes
