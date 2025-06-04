from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.dependencies import get_db, get_redis_client
import json
import redis

router = APIRouter(prefix="/api/v1/finance", tags=["finance"])

# Constant for cache TTL
CACHE_TTL_SECONDS = 60  # 1 minute cache


@router.get("/revenue")
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

        redis_client.setex(cache_key, CACHE_TTL_SECONDS,
                           json.dumps(total_revenue_float))
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
        raise HTTPException(status_code=500, detail={"error": {
                            "code": "CALCULATION_ERROR", "message": f"Error calculating total incomes: {str(e)}"}})


@router.get("/revenue/localities")
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
            {"locality": row["locality"], "total_revenue": float(
                row["total_revenue"]) if row["total_revenue"] is not None else 0.0}
            for row in rows
        ]

        redis_client.setex(cache_key, CACHE_TTL_SECONDS,
                           json.dumps(response_data_list))
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
            {"locality": row["locality"], "total_revenue": float(
                row["total_revenue"]) if row["total_revenue"] is not None else 0.0}
            for row in rows
        ]
        return {"data": response_data_list, "currency": "COP"}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": {
                            "code": "CALCULATION_ERROR", "message": f"Error calculating total incomes: {str(e)}"}})
