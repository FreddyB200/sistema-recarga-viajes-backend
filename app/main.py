from fastapi import FastAPI, Depends, HTTPException, Response
from sqlalchemy import text
from sqlalchemy.orm import Session
# import models # If you don't use SQLAlchemy models to create tables or for ORM, you can comment this out.
from database import engine # Make sure your database.py is configured correctly
from dependencies import get_db
from decimal import Decimal # To handle SUM results

import json # For serialization/deserialization
import redis # For the type hint of the Redis dependency
from dependencies import get_db, get_redis_client # <-- MAKE SURE TO IMPORT get_redis_client


# Constant for cache TTL
CACHE_TTL_SECONDS = 60 # 1 minute cache

# models.Base.metadata.create_all(bind=engine) # Consider commenting or removing this line if the DB is already created and you don't use models to create tables.

app = FastAPI()

# Your /ping-db endpoint (make sure it works with your config)
@app.get("/ping-db")
def ping_db(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "Successful connection"}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": {"code": "DATABASE_CONNECTION_ERROR", "message": f"Database connection error: {str(e)}"}})

# --- REQUIRED ENDPOINTS (CORRECTED ACCORDING TO ERD) ---

@app.get("/users/count")
def get_users_count(db: Session = Depends(get_db)):
    try:
        # Using 'usuarios' in lowercase according to PostgreSQL convention for unquoted identifiers
        result = db.execute(text("SELECT COUNT(*) AS total_users FROM usuarios;")).scalar_one_or_none()
        return {"total_users": result if result is not None else 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": {"code": "DATABASE_ERROR", "message": f"Error querying the database: {str(e)}"}})

@app.get("/users/active/count")
def get_active_users_count(db: Session = Depends(get_db)):
    try:
        # Call the stored procedure for active users count
        query = text("CALL get_active_users_count();")
        result = db.execute(query).scalar_one_or_none()
        return {"active_users_count": result if result is not None else 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": {"code": "DATABASE_ERROR", "message": f"Error querying the database: {str(e)}"}})

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
        raise HTTPException(status_code=500, detail={"error": {"code": "DATABASE_ERROR", "message": f"Error querying the database: {str(e)}"}})

@app.get("/trips/total")
def get_total_trips(
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client) # Inject Redis client
):
    cache_key = "trips:total" # Redis key

    try:
        # 1. Try to read from Redis
        cached_data_str = redis_client.get(cache_key)
        if cached_data_str:
            print(f"Cache HIT for '{cache_key}'")
            total_trips = json.loads(cached_data_str) # Convert JSON string to number
            return {"total_trips": total_trips}

        # 2. Cache MISS: Query DB
        print(f"Cache MISS for '{cache_key}'. Querying database...")
        result = db.execute(text("SELECT COUNT(*) AS total_trips FROM viajes;")).scalar_one_or_none()
        total_trips = result if result is not None else 0

        # 3. Save to Redis before returning
        # Convert number to JSON string for storage
        redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(total_trips))
        print(f"'{cache_key}' saved to Redis with TTL of {CACHE_TTL_SECONDS}s.")
        
        return {"total_trips": total_trips}

    except redis.exceptions.RedisError as e:
        # Fallback if Redis fails (but initial connection in dependencies.py worked)
        print(f"ALERT: Redis error during operation: {e}. Serving from DB.")
        result = db.execute(text("SELECT COUNT(*) AS total_trips FROM viajes;")).scalar_one_or_none()
        total_trips = result if result is not None else 0
        return {"total_trips": total_trips}
    except Exception as e:
        # Handle database errors or others not directly related to Redis
        raise HTTPException(status_code=500, detail={"error": {"code": "DATABASE_ERROR", "message": f"Error querying the database: {str(e)}"}})

@app.get("/finance/revenue")
def get_total_revenue(db: Session = Depends(get_db)): # This one is fine
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
        raise HTTPException(status_code=500, detail={"error": {"code": "CALCULATION_ERROR", "message": f"Error calculating total incomes: {str(e)}"}})

@app.get("/finance/revenue/localities")
def get_revenue_by_localities(
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    cache_key = "finance:revenue:by_localities"

    try:
        cached_data_str = redis_client.get(cache_key)
        if cached_data_str:
            print(f"Cache HIT for '{cache_key}'")
            response_data_list = json.loads(cached_data_str)
            return {"data": response_data_list, "currency": "COP"}

        print(f"Cache MISS for '{cache_key}'. Querying database...")
        # Call the stored procedure for revenue by localities
        query = text("CALL get_revenue_by_localities();")
        result_proxy = db.execute(query)
        rows = result_proxy.fetchall()

        response_data_list = [
            {"localidad": row.localidad, "total_recaudado": float(row.total_recaudado)}
            for row in rows
        ]

        redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(response_data_list))
        print(f"'{cache_key}' saved to Redis with TTL of {CACHE_TTL_SECONDS}s.")

        return {"data": response_data_list, "currency": "COP"}

    except redis.exceptions.RedisError as e:
        print(f"ALERT: Redis error during operation: {e}. Serving from DB.")
        query = text("CALL get_revenue_by_localities();")
        result_proxy = db.execute(query)
        rows = result_proxy.fetchall()
        response_data_list = [
            {"localidad": row.localidad, "total_recaudado": float(row.total_recaudado)}
            for row in rows
        ]
        return {"data": response_data_list, "currency": "COP"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "CALCULATION_ERROR", "message": f"Error calculating revenue by locality: {str(e)}"}})











