from fastapi import FastAPI, Depends, HTTPException, Response
from sqlalchemy import text
from sqlalchemy.orm import Session
# import models # Si no usas los modelos de SQLAlchemy para crear tablas o para ORM, puedes comentarlo.
from database import engine # Asegúrate que tu database.py esté configurado correctamente
from dependencies import get_db
from decimal import Decimal # Para manejar los resultados de SUM

# models.Base.metadata.create_all(bind=engine) # Considera comentar o eliminar esta línea si la BD ya está creada y no usas los modelos para crear tablas.

app = FastAPI()

# Tu endpoint /ping-db (ya lo tienes, asegúrate que funcione con tu config)
@app.get("/ping-db")
def ping_db(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "Conexion exitosa"}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": {"code": "DATABASE_CONNECTION_ERROR", "message": f"Error de conexión a la base de datos: {str(e)}"}})

# --- ENDPOINTS REQUERIDOS (CORREGIDOS SEGÚN ERD) ---

@app.get("/users/count")
def get_users_count(db: Session = Depends(get_db)):
    try:
        # Usando 'usuarios' en minúsculas según convención de PostgreSQL para identificadores no citados
        result = db.execute(text("SELECT COUNT(*) AS total_users FROM usuarios;")).scalar_one_or_none()
        return {"total_users": result if result is not None else 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": {"code": "DATABASE_ERROR", "message": f"Error al consultar la base de datos: {str(e)}"}})

@app.get("/users/active/count")
def get_active_users_count(db: Session = Depends(get_db)):
    # Asumiendo que TARJETAS.estado = 'activa' para tarjetas activas. ¡Verifica este valor!
    query = text("""
        SELECT COUNT(DISTINCT u.usuario_id) AS active_users_count
        FROM usuarios u
        JOIN tarjetas t ON u.usuario_id = t.usuario_id
        WHERE t.estado = 'Activa'; 
    """)
    try:
        result = db.execute(query).scalar_one_or_none()
        return {"active_users_count": result if result is not None else 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": {"code": "DATABASE_ERROR", "message": f"Error al consultar la base de datos: {str(e)}"}})

@app.get("/users/latest")
def get_latest_user(db: Session = Depends(get_db)):
    query = text("""
        SELECT usuario_id, nombre, apellido
        FROM usuarios
        ORDER BY fecha_registro DESC
        LIMIT 1;
    """)
    try:
        result = db.execute(query).mappings().first()
        if result:
            full_name = f"{result['nombre']} {result['apellido']}"
            return {"latest_user": {"usuario_id": result['usuario_id'], "full_name": full_name}}
        else:
            return Response(status_code=204) # No Content
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": {"code": "DATABASE_ERROR", "message": f"Error al consultar la base de datos: {str(e)}"}})

@app.get("/trips/total")
def get_total_trips(db: Session = Depends(get_db)):
    try:
        result = db.execute(text("SELECT COUNT(*) AS total_trips FROM viajes;")).scalar_one_or_none()
        return {"total_trips": result if result is not None else 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": {"code": "DATABASE_ERROR", "message": f"Error al consultar la base de datos: {str(e)}"}})

@app.get("/finance/revenue")
def get_total_revenue(db: Session = Depends(get_db)):
    # Se requiere JOIN con la tabla TARIFAS para obtener el 'valor' (costo) del viaje.
    query = text("""
        SELECT SUM(tf.valor) AS total_revenue
        FROM viajes v
        JOIN tarifas tf ON v.tarifa_id = tf.tarifa_id;
    """)
    try:
        result = db.execute(query).scalar_one_or_none()
        total_revenue = result if result is not None else Decimal('0.00')
        return {"total_revenue": float(total_revenue), "currency": "COP"}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": {"code": "CALCULATION_ERROR", "message": f"Error al calcular los ingresos totales: {str(e)}"}})