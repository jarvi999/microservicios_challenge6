# 🐧 Penguin Challenge - Microservicios

## Arquitectura

Sistema dividido en 3 microservicios independientes:

- Productos (5001)
- Inventario (5002)
- Pedidos (5003)

Cada uno tiene:
- Base de datos SQLite propia
- API REST
- Autenticación con token estático
- Logs
- Manejo de errores
- Comunicación HTTP

## Seguridad

Todos los endpoints requieren:

Authorization: Bearer supertoken123

## Resiliencia

El servicio de pedidos implementa:

- Retry automático (3 intentos)
- Circuit Breaker (se activa tras 3 fallos consecutivos)
- Logging de errores

## Ejecución

Ejecutar cada servicio en terminal diferente:

python app.py

## Flujo de pedido

1. Cliente llama a /pedido
2. Pedidos consulta Productos
3. Pedidos consulta Inventario
4. Si todo es válido, guarda en su base de datos
