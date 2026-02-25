from flask import Flask, request, jsonify # Importa Flask para la API y herramientas para leer/responder JSON
import sqlite3 # base de datos
import requests # Importa para que este servicio pueda HACER llamadas a otros microservicios
import logging # Importa para registrar eventos y errores en un archivo o consola
import time

app = Flask(__name__)

TOKEN = "supertoken123"

PRODUCTOS_URL = "http://localhost:5001"
INVENTARIO_URL = "http://localhost:5002"

logging.basicConfig(filename="pedido.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s") #registrar eventos, mostrar mensaje de info o superior

fallos_consecutivos = 0 #ver cuantas  veces fallo la comunicacion
CIRCUIT_BREAKER_LIMITE = 3 # limite de veces
CIRCUIT_OPEN = False # cambia a true y deja de llamar a los otros servicios 
tiempo_apertura = None # guarda el momento exacto en que se abrió el circuito
CIRCUIT_RESET_TIMEOUT = 5 # NUEVA CONSTANTE: tiempo en segundos que el circuito permanecerá abierto

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
    global fallos_consecutivos, CIRCUIT_OPEN, tiempo_apertura #modificar variable globales de estado de circuito, contador de cantida de fallos

    # NUEVA LÓGICA: verificar si el circuito estaba abierto y ya pasó el tiempo de espera
    if CIRCUIT_OPEN:
        if tiempo_apertura and (time.time() - tiempo_apertura >= CIRCUIT_RESET_TIMEOUT): #se resta tiempo de apertura con time
            # Se permite reintentar después de 5 segundos
            CIRCUIT_OPEN = False
            fallos_consecutivos = 0
            tiempo_apertura = None
            logging.info("Circuit Breaker RESETEADO automáticamente")
        else:
            return None #devolver repuesta o indicar el fallo 

    for i in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=2) #esperar repuesta de otro microservicio, espera max 2 segundos
            fallos_consecutivos = 0
            return response
        except Exception as e:
            fallos_consecutivos += 1
            logging.error(f"Error en comunicación: {str(e)}")
            time.sleep(1)

            if fallos_consecutivos >= CIRCUIT_BREAKER_LIMITE:
                CIRCUIT_OPEN = True 
                tiempo_apertura = time.time()  # NUEVA LÍNEA: guardar momento de apertura
                logging.error("Circuit Breaker ACTIVADO")
                return None

@app.route("/pedido", methods=["POST"]) #ruta exacta 
def crear_pedido():
    global CIRCUIT_OPEN, tiempo_apertura, fallos_consecutivos

    if not verificar_token():
        return jsonify({"error": "No autorizado"}), 401 # codigo de estado

    # NUEVA LÓGICA: permitir reapertura automática también aquí antes de bloquear
    if CIRCUIT_OPEN:
        if tiempo_apertura and (time.time() - tiempo_apertura >= CIRCUIT_RESET_TIMEOUT):
            CIRCUIT_OPEN = False
            fallos_consecutivos = 0
            tiempo_apertura = None
            logging.info("Circuit Breaker RESETEADO automáticamente")
        else:
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
    #llama a microservicio producto
    try:
        producto_resp = request_con_retry(
            f"{PRODUCTOS_URL}/productos/{producto_id}",
            headers
        )

        if not producto_resp or producto_resp.status_code != 200: #servicio respondio, pero con error
            return jsonify({"error": "Producto no disponible"}), 400 # producto no disponible

        #llama al microservicio inventario
        stock_resp = request_con_retry(
            f"{INVENTARIO_URL}/inventario/{producto_id}",
            headers
        )

        if not stock_resp or stock_resp.status_code != 200:   #servicio respondio, pero con error
            return jsonify({"error": "Stock no disponible"}), 400 #producto no disponible

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