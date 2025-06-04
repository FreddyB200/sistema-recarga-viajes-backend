from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.dependencies import get_db, get_redis_client
import json
import redis

router = APIRouter(prefix="/api/v1/trips", tags=["trips"])

# Constant for cache TTL
CACHE_TTL_SECONDS = 60  # 1 minute cache


@router.get("/total")
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
        result = db.execute(
            text("SELECT COUNT(*) AS total_trips FROM trips;")).scalar_one_or_none()
        total_trips = result if result is not None else 0

        redis_client.setex(cache_key, CACHE_TTL_SECONDS,
                           json.dumps(total_trips))
        print(f"'{cache_key}' saved to Redis with TTL of {CACHE_TTL_SECONDS}s.")

        return {"total_trips": total_trips}

    except redis.exceptions.RedisError as e:
        print(f"ALERT: Redis error during operation: {e}. Serving from DB.")
        result = db.execute(
            text("SELECT COUNT(*) AS total_trips FROM trips;")).scalar_one_or_none()
        total_trips = result if result is not None else 0
        return {"total_trips": total_trips}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": {
                            "code": "DATABASE_ERROR", "message": f"Error querying the database: {str(e)}"}})


@router.get("/total/localities")
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
            {"locality": row["locality"], "total_trips": int(
                row["total_trips"]) if row["total_trips"] is not None else 0}
            for row in rows
        ]

        redis_client.setex(cache_key, CACHE_TTL_SECONDS,
                           json.dumps(response_data_list))
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
            {"locality": row["locality"], "total_trips": int(
                row["total_trips"]) if row["total_trips"] is not None else 0}
            for row in rows
        ]
        return {"data": response_data_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": {
                            "code": "DATABASE_ERROR", "message": f"Error querying the database: {str(e)}"}})
