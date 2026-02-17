from flask import Flask, request, jsonify
import sqlite3
import requests
import logging
import time

app = Flask(__name__)

TOKEN = "supertoken123"

PRODUCTOS_URL = "http://localhost:5001"
INVENTARIO_URL = "http://localhost:5002"

logging.basicConfig(filename="inventario.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s") #registrar eventos, mostrar mensaje de info o superior

fallos_consecutivos = 0 #ver cuantas  veces fallo la comunicacion
CIRCUIT_BREAKER_LIMITE = 3 # limite de veces
CIRCUIT_OPEN = False # cambia a true y deja de llamar a los otros servicios 

def verificar_token():
    auth = request.headers.get("Authorization") #buscar etiqueta que llame authorization
    if not auth or auth != f"Bearer {TOKEN}": #que cumpla con auth y tenga el token, portador
        return False
    return True

def init_db():
    conn = sqlite3.connect("pedidos.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER,
            cantidad INTEGER
        )
    """)
    conn.commit()
    conn.close()

def request_con_retry(url, headers, retries=3): #datos para hacer peticiones HTTP
    global fallos_consecutivos, CIRCUIT_OPEN #modificar variable global, contador de cantida de fallos

    if CIRCUIT_OPEN:
        return None

    for i in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=2)
            fallos_consecutivos = 0
            return response
        except Exception as e:
            fallos_consecutivos += 1
            logging.error(f"Error en comunicación: {str(e)}")
            time.sleep(1)

            if fallos_consecutivos >= CIRCUIT_BREAKER_LIMITE:
                CIRCUIT_OPEN = True
                logging.error("Circuit Breaker ACTIVADO")
                return None

@app.route("/pedido", methods=["POST"]) #ruta exacta 
def crear_pedido():
    if not verificar_token():
        return jsonify({"error": "No autorizado"}), 401

    if CIRCUIT_OPEN: #intentando ingresar al servidor
        return jsonify({"error": "Servicio temporalmente no disponible"}), 503

    # Validar que venga JSON
    if not request.is_json:
        return jsonify({"error": "El cuerpo debe ser JSON"}), 400

    data = request.get_json() #recibiendo informacion en formato json

    # Validar campos obligatorios
    if "producto_id" not in data or "cantidad" not in data:
        return jsonify({"error": "Faltan campos obligatorios (producto_id, cantidad)"}), 400

    # Validar producto_id
    try:
        producto_id = int(data["producto_id"])
        if producto_id <= 0:
            return jsonify({"error": "producto_id debe ser mayor a 0"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "producto_id debe ser numérico entero"}), 400

    # Validar cantidad
    try:
        cantidad = int(data["cantidad"])
        if cantidad <= 0:
            return jsonify({"error": "La cantidad debe ser mayor a 0"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "La cantidad debe ser numérica entera"}), 400

    headers = {"Authorization": f"Bearer {TOKEN}"} # 

    try:
        producto_resp = request_con_retry(
            f"{PRODUCTOS_URL}/productos/{producto_id}",
            headers
        )

        if not producto_resp or producto_resp.status_code != 200:
            return jsonify({"error": "Producto no disponible"}), 400

        stock_resp = request_con_retry(
            f"{INVENTARIO_URL}/inventario/{producto_id}",
            headers
        )

        if not stock_resp or stock_resp.status_code != 200:
            return jsonify({"error": "Stock no disponible"}), 400

        stock = stock_resp.json()["stock"]

        if stock < cantidad:
            return jsonify({"error": "Stock insuficiente"}), 400

        conn = sqlite3.connect("pedidos.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO pedidos (producto_id, cantidad) VALUES (?, ?)",
                       (producto_id, cantidad))
        conn.commit()
        conn.close()

        logging.info("Pedido creado correctamente")
        return jsonify({"mensaje": "Pedido creado con éxito"}), 201

    except Exception as e:
        logging.error(f"Error interno: {str(e)}")
        return jsonify({"error": "Error interno del servidor"}), 500


if __name__ == "__main__":
    init_db()
    app.run(port=5003)
