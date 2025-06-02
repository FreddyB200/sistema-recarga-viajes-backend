from fastapi import FastAPI, Depends, HTTPException, Response
from sqlalchemy import text
from sqlalchemy.orm import Session
# import models # Kept commented out since schema is managed externally
from app.database import engine # Ensure database.py is properly configured
from app.dependencies import get_db, get_redis_client # Ensure get_redis_client is imported
from decimal import Decimal # For handling SUM results

import json
import redis # For Redis dependency type hint


# Constant for cache TTL
CACHE_TTL_SECONDS = 60 # 1 minute cache

# models.Base.metadata.create_all(bind=engine) # Kept commented, schema is created externally

app = FastAPI()

@app.get("/ping-db")
def ping_db(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "Successful connection"}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": {"code": "DATABASE_CONNECTION_ERROR", "message": f"Database connection error: {str(e)}"}})

# --- REQUIRED ENDPOINTS (UPDATED FOR NEW SCHEMA) ---

@app.get("/users/count")
def get_users_count(db: Session = Depends(get_db)):
    try:
        result = db.execute(text("SELECT COUNT(*) AS total_users FROM users;")).scalar_one_or_none()
        return {"total_users": result if result is not None else 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": {"code": "DATABASE_ERROR", "message": f"Error querying the database: {str(e)}"}})

@app.get("/users/active/count")
def get_active_users_count(db: Session = Depends(get_db)):
    # We assume an "active user" is a user with at least one 'active' card.
    # Replaced stored procedure call with direct query.
    query = text("""
        SELECT COUNT(DISTINCT u.user_id) AS active_users_count
        FROM users u
        JOIN cards c ON u.user_id = c.user_id
        WHERE c.status = 'active';
    """)
    try:
        result = db.execute(query).scalar_one_or_none()
        return {"active_users_count": result if result is not None else 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": {"code": "DATABASE_ERROR", "message": f"Error querying the database: {str(e)}"}})

@app.get("/users/latest")
def get_latest_user(db: Session = Depends(get_db)):
    query = text("""
        SELECT user_id, first_name, last_name
        FROM users
        ORDER BY registration_date DESC, user_id DESC
        LIMIT 1;
    """) # Added user_id DESC for deterministic tie-breaker
    try:
        result = db.execute(query).mappings().first()
        if result:
            full_name = f"{result['first_name']} {result['last_name']}"
            return {"latest_user": {"user_id": result['user_id'], "full_name": full_name}}
        else:
            return Response(status_code=204) # No Content
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": {"code": "DATABASE_ERROR", "message": f"Error querying the database: {str(e)}"}})

@app.get("/trips/total")
def get_total_trips(
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    cache_key = "trips:total"

    try:
        cached_data_str = redis_client.get(cache_key)
        if cached_data_str:
            print(f"Cache HIT for '{cache_key}'")
            total_trips = json.loads(cached_data_str)
            return {"total_trips": total_trips}

        print(f"Cache MISS for '{cache_key}'. Querying database...")
        result = db.execute(text("SELECT COUNT(*) AS total_trips FROM trips;")).scalar_one_or_none()
        total_trips = result if result is not None else 0

        redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(total_trips))
        print(f"'{cache_key}' saved to Redis with TTL of {CACHE_TTL_SECONDS}s.")
        
        return {"total_trips": total_trips}

    except redis.exceptions.RedisError as e:
        print(f"ALERT: Redis error during operation: {e}. Serving from DB.")
        result = db.execute(text("SELECT COUNT(*) AS total_trips FROM trips;")).scalar_one_or_none()
        total_trips = result if result is not None else 0
        return {"total_trips": total_trips}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": {"code": "DATABASE_ERROR", "message": f"Error querying the database: {str(e)}"}})

@app.get("/finance/revenue")
def get_total_revenue(
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    cache_key = "finance:total_revenue"

    try:
        cached_data_str = redis_client.get(cache_key)
        if cached_data_str:
            print(f"Cache HIT for '{cache_key}'")
            total_revenue = json.loads(cached_data_str)
            return {"total_revenue": total_revenue, "currency": "COP"}

        print(f"Cache MISS for '{cache_key}'. Querying database...")
        query = text("""
            SELECT SUM(tf.value) AS total_revenue
            FROM trips t
            JOIN fares tf ON t.fare_id = tf.fare_id;
        """)
        result = db.execute(query).scalar_one_or_none()
        # total_revenue is Decimal if not None, or None.
        total_revenue_float = 0.0
        if result is not None:
            total_revenue_float = float(result)

        redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(total_revenue_float))
        print(f"'{cache_key}' saved to Redis with TTL of {CACHE_TTL_SECONDS}s.")

        return {"total_revenue": total_revenue_float, "currency": "COP"}

    except redis.exceptions.RedisError as e:
        print(f"ALERT: Redis error during operation: {e}. Serving from DB.")
        query = text("""
            SELECT SUM(tf.value) AS total_revenue
            FROM trips t
            JOIN fares tf ON t.fare_id = tf.fare_id;
        """)
        result = db.execute(query).scalar_one_or_none()
        total_revenue_float = 0.0
        if result is not None:
            total_revenue_float = float(result)
        return {"total_revenue": total_revenue_float, "currency": "COP"}
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
        # Replaced stored procedure call with direct query joining trips -> fares, trips -> stations -> locations
        query = text("""
            SELECT loc.name AS locality, SUM(f.value) AS total_revenue
            FROM trips t
            JOIN fares f ON t.fare_id = f.fare_id
            JOIN stations s ON t.boarding_station_id = s.station_id
            JOIN locations loc ON s.location_id = loc.location_id
            GROUP BY loc.name
            ORDER BY total_revenue DESC;
        """)
        result_proxy = db.execute(query)
        # Use .mappings().all() to get a list of dictionaries
        rows = result_proxy.mappings().all() 

        response_data_list = [
            # Access fields by column/alias name
            {"locality": row["locality"], "total_revenue": float(row["total_revenue"]) if row["total_revenue"] is not None else 0.0}
            for row in rows
        ]

        redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(response_data_list))
        print(f"'{cache_key}' saved to Redis with TTL of {CACHE_TTL_SECONDS}s.")

        return {"data": response_data_list, "currency": "COP"}

    except redis.exceptions.RedisError as e:
        print(f"ALERT: Redis error during operation: {e}. Serving from DB.")
        query = text("""
            SELECT loc.name AS locality, SUM(f.value) AS total_revenue
            FROM trips t
            JOIN fares f ON t.fare_id = f.fare_id
            JOIN stations s ON t.boarding_station_id = s.station_id
            JOIN locations loc ON s.location_id = loc.location_id
            GROUP BY loc.name
            ORDER BY total_revenue DESC;
        """)
        result_proxy = db.execute(query)
        rows = result_proxy.mappings().all()
        response_data_list = [
            {"locality": row["locality"], "total_revenue": float(row["total_revenue"]) if row["total_revenue"] is not None else 0.0}
            for row in rows
        ]
        return {"data": response_data_list, "currency": "COP"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "CALCULATION_ERROR", "message": f"Error calculating revenue by locality: {str(e)}"}})

@app.get("/trips/total/localities")
def get_total_trips_by_localities(
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    cache_key = "trips:total:by_localities"

    try:
        cached_data_str = redis_client.get(cache_key)
        if cached_data_str:
            print(f"Cache HIT for '{cache_key}'")
            response_data_list = json.loads(cached_data_str)
            return {"data": response_data_list}

        print(f"Cache MISS for '{cache_key}'. Querying database...")
        # Adjusted table and column names: localities -> locations, locality_id -> location_id
        query = text("""
            SELECT loc.name AS locality, COUNT(t.trip_id) AS total_trips
            FROM trips t
            JOIN stations s ON t.boarding_station_id = s.station_id
            JOIN locations loc ON s.location_id = loc.location_id 
            GROUP BY loc.name
            ORDER BY total_trips DESC;
        """)
        result_proxy = db.execute(query)
        rows = result_proxy.mappings().all() # Use .mappings().all()

        response_data_list = [
            # Access by column/alias name
            {"locality": row["locality"], "total_trips": row["total_trips"]}
            for row in rows
        ]

        redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(response_data_list))
        print(f"'{cache_key}' saved to Redis with TTL of {CACHE_TTL_SECONDS}s.")

        return {"data": response_data_list}

    except redis.exceptions.RedisError as e:
        print(f"ALERT: Redis error during operation: {e}. Serving from DB.")
        query = text("""
            SELECT loc.name AS locality, COUNT(t.trip_id) AS total_trips
            FROM trips t
            JOIN stations s ON t.boarding_station_id = s.station_id
            JOIN locations loc ON s.location_id = loc.location_id
            GROUP BY loc.name
            ORDER BY total_trips DESC;
        """)
        result_proxy = db.execute(query)
        rows = result_proxy.mappings().all()
        response_data_list = [
            {"locality": row["locality"], "total_trips": row["total_trips"]}
            for row in rows
        ]
        return {"data": response_data_list}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "DATABASE_ERROR", "message": f"Error querying the database: {str(e)}"}}
        )