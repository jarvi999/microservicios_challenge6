from flask import Flask, request, jsonify
import sqlite3
import logging  #registrar eventos, y clasificar importancia

app = Flask(__name__)

TOKEN = "supertoken123"

logging.basicConfig(level=logging.INFO) #registrar eventos, mostrar mensaje de info o superior

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

    data = request.json
    conn = sqlite3.connect("inventario.db")
    cursor = conn.cursor()

    cursor.execute("INSERT OR REPLACE INTO inventario (producto_id, stock) VALUES (?, ?)",
                   (data["producto_id"], data["stock"]))

    conn.commit()
    conn.close()

    logging.info("Stock actualizado")
    return jsonify({"mensaje": "Stock actualizado"}), 200

@app.route("/inventario/<int:producto_id>", methods=["GET"]) # buscar informacion mas exacta en la direccion URL
def verificar_stock(producto_id):
    if not verificar_token():
        return jsonify({"error": "No autorizado"}), 401

    conn = sqlite3.connect("inventario.db")
    cursor = conn.cursor()
    cursor.execute("SELECT stock FROM inventario WHERE producto_id=?", (producto_id,))
    stock = cursor.fetchone()
    conn.close()

    if not stock:
        return jsonify({"error": "Producto sin stock registrado"}), 404

    return jsonify({"producto_id": producto_id, "stock": stock[0]})

if __name__ == "__main__":
    init_db()
    app.run(port=5002)
