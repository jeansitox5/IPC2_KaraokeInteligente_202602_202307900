"""
config_repo.py - Tabla CONFIGURACION (clave, valor, descripción).
"""


class ConfigRepo:
    def __init__(self, db):
        self.db = db

    def asegurar_defaults(self, defaults):
        """Inserta las claves que falten sin tocar las que el usuario ya cambió."""
        with self.db.transaccion() as c:
            c.executemany(
                "INSERT OR IGNORE INTO CONFIGURACION (clave, valor, descripcion) VALUES (?, ?, ?)",
                [(k, str(v), d) for k, (v, d) in defaults.items()],
            )

    def obtener_todos(self):
        return {
            f["clave"]: f["valor"]
            for f in self.db.conn.execute("SELECT clave, valor FROM CONFIGURACION")
        }

    def guardar(self, clave, valor, descripcion=None):
        with self.db.transaccion() as c:
            c.execute(
                "INSERT INTO CONFIGURACION (clave, valor, descripcion) VALUES (?, ?, ?) "
                "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
                (clave, valor, descripcion),
            )
