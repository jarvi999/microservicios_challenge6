from flask import Flask, request, jsonify  # Importa Flask para la API yjsonify para respuestas JSON
import sqlite3  # Importa para manejar la base de datos local de productos
import logging  # Importa para llevar un registro (log) de lo que sucede

app = Flask(__name__) # Creamos la instancia del servidor Flask

TOKEN = "supertoken123"

logging.basicConfig(filename="producto.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def verificar_token():
    auth = request.headers.get("Authorization") #etiqueta
    if not auth or auth != f"Bearer {TOKEN}": # que cumpla coon auth y tenga el token, portador
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

# RUTA PARA ACTUALIZAR STOCK: Se usa POST para enviar datos de creación o actualización
@app.route("/productos", methods=["POST"])
def crear_producto():
    if not verificar_token():
        return jsonify({"error": "No autorizado"}), 401 # no autorizacion

    # Validar que venga JSON
    if not request.is_json:
        return jsonify({"error": "El cuerpo debe ser JSON"}), 400 #no se pudo procesar solicitud por error de cliente

    data = request.get_json()

    # Validar campos obligatorios
    if "nombre" not in data or "precio" not in data:
        return jsonify({"error": "Faltan campos obligatorios (nombre, precio)"}), 400  #no se pudo procesar solicitud por error de cliente

    # Validación de nombre: Verifica que sea texto y que no esté vacío (strip quita espacios)
    if not isinstance(data["nombre"], str) or not data["nombre"].strip():
        return jsonify({"error": "El nombre debe ser un texto válido"}), 400  #no se pudo procesar solicitud por error de cliente

    # Validar precio
    try:
        precio = float(data["precio"])
        if precio <= 0:
            return jsonify({"error": "El precio debe ser mayor a cero"}), 400 #no se pudo procesar solicitud por error de cliente
    except (ValueError, TypeError):
        return jsonify({"error": "El precio debe ser numérico"}), 400  

    try:
        conn = sqlite3.connect("productos.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO productos (nombre, precio) VALUES (?, ?)",
                       (data["nombre"], precio))
        conn.commit()
        conn.close()

        logging.info("Producto creado correctamente")
        return jsonify({"mensaje": "Producto creado"}), 201
    # Si algo falla con la base de datos, registra el error y responde al cliente
    except Exception as e:
        logging.error(f"Error interno: {str(e)}")
        return jsonify({"error": "Error interno del servidor"}), 500

# RUTA PARA OBTENER UN PRODUCTO: Busca por ID en la URL, query param
@app.route("/productos/<int:id>", methods=["GET"])
def obtener_producto(id):
    if not verificar_token():
        return jsonify({"error": "No autorizado"}), 401

    try:
        conn = sqlite3.connect("productos.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM productos WHERE id=?", (id,))
        producto = cursor.fetchone()
        conn.close()
    # Si el producto no existe en la base de datos
        if not producto:
            return jsonify({"error": "Producto no encontrado"}), 404
    # Construye la respuesta JSON con los datos de la fila (0=id, 1=nombre, 2=precio)
        return jsonify({
            "id": producto[0],
            "nombre": producto[1],
            "precio": producto[2]
        })

    except Exception as e:
        logging.error(f"Error interno: {str(e)}")
        return jsonify({"error": "Error interno del servidor"}), 500


if __name__ == "__main__":
    init_db()
    app.run(port=5001)
