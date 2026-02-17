from flask import Flask, request, jsonify
import sqlite3
import logging

app = Flask(__name__)

TOKEN = "supertoken123"

logging.basicConfig(level=logging.INFO)

def verificar_token():
    auth = request.headers.get("Authorization")
    if not auth or auth != f"Bearer {TOKEN}":
        return False
    return True

def init_db():
    conn = sqlite3.connect("productos.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            precio REAL
        )
    """)
    conn.commit()
    conn.close()

@app.route("/productos", methods=["POST"])
def crear_producto():
    if not verificar_token():
        return jsonify({"error": "No autorizado"}), 401

    data = request.json
    conn = sqlite3.connect("productos.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO productos (nombre, precio) VALUES (?, ?)",
                   (data["nombre"], data["precio"]))
    conn.commit()
    conn.close()

    logging.info("Producto creado correctamente")
    return jsonify({"mensaje": "Producto creado"}), 201

@app.route("/productos/<int:id>", methods=["GET"])
def obtener_producto(id):
    if not verificar_token():
        return jsonify({"error": "No autorizado"}), 401

    conn = sqlite3.connect("productos.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM productos WHERE id=?", (id,))
    producto = cursor.fetchone()
    conn.close()

    if not producto:
        return jsonify({"error": "Producto no encontrado"}), 404

    return jsonify({
        "id": producto[0],
        "nombre": producto[1],
        "precio": producto[2]
    })

if __name__ == "__main__":
    init_db()
    app.run(port=5001)
