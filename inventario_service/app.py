from flask import Flask, request, jsonify
import sqlite3
import logging  #registrar eventos, y clasificar importancia

app = Flask(__name__)

TOKEN = "supertoken123"

logging.basicConfig(filename="inventario.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s") #registrar eventos, mostrar mensaje de info o superior

def verificar_token():
    auth = request.headers.get("Authorization") #buscar etiqueta que llame authorization
    if not auth or auth != f"Bearer {TOKEN}": # que cumpla coon auth y tenga el token, portador
        return False
    return True

def init_db():
    conn = sqlite3.connect("inventario.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventario (
            producto_id INTEGER PRIMARY KEY,
            stock INTEGER
        )
    """)
    conn.commit()
    conn.close()

@app.route("/inventario", methods=["POST"])
def agregar_stock():
    if not verificar_token():
        return jsonify({"error": "No autorizado"}), 401

    # Validar que venga JSON
    if not request.is_json:
        return jsonify({"error": "El cuerpo debe ser JSON"}), 400

    data = request.get_json()

    # Validar campos obligatorios
    if "producto_id" not in data or "stock" not in data:
        return jsonify({"error": "Faltan campos obligatorios (producto_id, stock)"}), 400

    # Validar producto_id
    try:
        producto_id = int(data["producto_id"])
        if producto_id <= 0:
            return jsonify({"error": "producto_id debe ser mayor a 0"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "producto_id debe ser numerico entero"}), 400

    # Validar stock
    try:
        stock = int(data["stock"])
        if stock < 0:
            return jsonify({"error": "El stock no puede ser negativo"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "El stock debe ser numerico entero"}), 400

    try:
        conn = sqlite3.connect("inventario.db")
        cursor = conn.cursor()

        cursor.execute("INSERT OR REPLACE INTO inventario (producto_id, stock) VALUES (?, ?)",
                       (producto_id, stock))

        conn.commit()
        conn.close()

        logging.info("Stock actualizado")
        return jsonify({"mensaje": "Stock actualizado"}), 200

    except Exception as e:
        logging.error(f"Error interno: {str(e)}")
        return jsonify({"error": "Error interno del servidor"}), 500


@app.route("/inventario/<int:producto_id>", methods=["GET"]) # buscar informacion mas exacta en la direccion URL
def verificar_stock(producto_id):
    if not verificar_token():
        return jsonify({"error": "No autorizado"}), 401

    if producto_id <= 0:
        return jsonify({"error": "producto_id invalido"}), 400

    try:
        conn = sqlite3.connect("inventario.db")
        cursor = conn.cursor()
        cursor.execute("SELECT stock FROM inventario WHERE producto_id=?", (producto_id,))
        stock = cursor.fetchone()
        conn.close()

        if not stock:
            return jsonify({"error": "Producto sin stock registrado"}), 404

        return jsonify({"producto_id": producto_id, "stock": stock[0]})

    except Exception as e:
        logging.error(f"Error interno: {str(e)}")
        return jsonify({"error": "Error interno del servidor"}), 500


if __name__ == "__main__":
    init_db()
    app.run(port=5002)
