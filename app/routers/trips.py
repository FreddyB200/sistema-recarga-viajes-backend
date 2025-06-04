from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.dependencies import get_db, get_redis_client
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import json
import redis

router = APIRouter(prefix="/api/v1/trips", tags=["trips"])

# Pydantic models for request/response


class TripStart(BaseModel):
    card_id: int
    station_id: int


class TripEnd(BaseModel):
    trip_id: int
    station_id: int


class Trip(BaseModel):
    trip_id: int
    card_id: int
    start_station_id: int
    end_station_id: Optional[int]
    start_time: datetime
    end_time: Optional[datetime]
    status: str
    fare: Optional[float]


# Cache TTL
CACHE_TTL_SECONDS = 300  # 5 minutes for trip data


@router.post("/start")
def start_trip(
    trip: TripStart,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    try:
        # Check if card exists and has sufficient balance
        card_query = text("""
            SELECT status, balance FROM cards WHERE card_id = :card_id
        """)
        card = db.execute(card_query, {"card_id": trip.card_id}).first()

        if not card:
            raise HTTPException(status_code=404, detail="Card not found")
        if card.status != "active":
            raise HTTPException(status_code=400, detail="Card is not active")
        if card.balance < 1.0:  # Minimum balance required
            raise HTTPException(status_code=400, detail="Insufficient balance")

        # Check if station exists and is active
        station_query = text("""
            SELECT station_id, name, locality, status, capacity, current_occupancy 
            FROM stations WHERE station_id = :station_id
        """)
        station = db.execute(
            station_query, {"station_id": trip.station_id}).first()

        if not station:
            raise HTTPException(status_code=404, detail="Station not found")
        if station.status != "active":
            raise HTTPException(
                status_code=400, detail="Station is not active")

        # Check if card has an active trip
        active_trip_query = text("""
            SELECT trip_id FROM trips 
            WHERE card_id = :card_id AND status = 'in_progress'
        """)
        active_trip = db.execute(
            active_trip_query, {"card_id": trip.card_id}).first()

        if active_trip:
            raise HTTPException(
                status_code=400, detail="Card has an active trip")

        # Create new trip
        trip_query = text("""
            INSERT INTO trips (card_id, start_station_id, start_time, status)
            VALUES (:card_id, :station_id, CURRENT_TIMESTAMP, 'in_progress')
            RETURNING trip_id, start_time
        """)
        result = db.execute(
            trip_query,
            {
                "card_id": trip.card_id,
                "station_id": trip.station_id
            }
        ).first()

        db.commit()

        # Invalidate cache
        redis_client.delete("trips:total")
        redis_client.delete(f"trips:card:{trip.card_id}")

        return {
            "trip_id": result.trip_id,
            "card_id": trip.card_id,
            "start_station_id": trip.station_id,
            "start_time": result.start_time.isoformat(),
            "status": "in_progress"
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/end")
def end_trip(
    trip: TripEnd,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    try:
        # Check if trip exists and is in progress
        trip_query = text("""
            SELECT t.trip_id, t.card_id, t.start_station_id, t.start_time, c.balance
            FROM trips t
            JOIN cards c ON t.card_id = c.card_id
            WHERE t.trip_id = :trip_id AND t.status = 'in_progress'
        """)
        trip_data = db.execute(trip_query, {"trip_id": trip.trip_id}).first()

        if not trip_data:
            raise HTTPException(
                status_code=404, detail="Active trip not found")

        # Check if end station exists and is active
        station_query = text("""
            SELECT status FROM stations WHERE station_id = :station_id
        """)
        station = db.execute(
            station_query, {"station_id": trip.station_id}).first()

        if not station:
            raise HTTPException(status_code=404, detail="Station not found")
        if station.status != "active":
            raise HTTPException(
                status_code=400, detail="Station is not active")

        # Calculate fare based on distance/time
        # This is a simplified calculation - in reality, it would be more complex
        fare = 2.50  # Base fare

        # Check if card has sufficient balance
        if trip_data.balance < fare:
            raise HTTPException(
                status_code=400, detail="Insufficient balance for fare")

        # Update trip and card balance
        update_query = text("""
            WITH trip_update AS (
                UPDATE trips 
                SET end_station_id = :station_id,
                    end_time = CURRENT_TIMESTAMP,
                    status = 'completed',
                    fare = :fare
                WHERE trip_id = :trip_id
                RETURNING trip_id, end_time
            )
            UPDATE cards
            SET balance = balance - :fare
            WHERE card_id = :card_id
            RETURNING balance
        """)
        result = db.execute(
            update_query,
            {
                "trip_id": trip.trip_id,
                "station_id": trip.station_id,
                "fare": fare,
                "card_id": trip_data.card_id
            }
        ).first()

        db.commit()

        # Invalidate cache
        redis_client.delete("trips:total")
        redis_client.delete(f"trips:card:{trip_data.card_id}")
        redis_client.delete(f"card:{trip_data.card_id}:balance")

        return {
            "trip_id": trip.trip_id,
            "card_id": trip_data.card_id,
            "start_station_id": trip_data.start_station_id,
            "end_station_id": trip.station_id,
            "start_time": trip_data.start_time.isoformat(),
            "end_time": result.end_time.isoformat(),
            "status": "completed",
            "fare": fare,
            "new_balance": result.balance
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/total")
def get_total_trips(
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    cache_key = "trips:total"

    try:
        # Try to get from cache
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)

        # Query database
        query = text("""
            SELECT 
                COUNT(*) as total_trips,
                COUNT(CASE WHEN end_time IS NOT NULL THEN 1 END) as completed_trips,
                COUNT(CASE WHEN end_time IS NULL THEN 1 END) as active_trips,
                SUM(CASE WHEN end_time IS NOT NULL THEN fare ELSE 0 END) as total_revenue
            FROM trips
        """)
        result = db.execute(query).first()

        response = {
            "total_trips": result.total_trips,
            "completed_trips": result.completed_trips,
            "active_trips": result.active_trips,
            "total_revenue": float(result.total_revenue) if result.total_revenue else 0.0
        }

        # Cache the result
        redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(response))

        return response

    except redis.exceptions.RedisError as e:
        # If Redis fails, just serve from database
        query = text("""
            SELECT 
                COUNT(*) as total_trips,
                COUNT(CASE WHEN end_time IS NOT NULL THEN 1 END) as completed_trips,
                COUNT(CASE WHEN end_time IS NULL THEN 1 END) as active_trips,
                SUM(CASE WHEN end_time IS NOT NULL THEN fare ELSE 0 END) as total_revenue
            FROM trips
        """)
        result = db.execute(query).first()

        return {
            "total_trips": result.total_trips,
            "completed_trips": result.completed_trips,
            "active_trips": result.active_trips,
            "total_revenue": float(result.total_revenue) if result.total_revenue else 0.0
        }


@router.get("/total/localities")
def get_total_trips_by_localities(
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    cache_key = "trips:total:localities"

    try:
        # Try to get from cache
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)

        # Query database
        query = text("""
            WITH trip_stats AS (
                SELECT 
                    s.locality,
                    COUNT(*) as total_trips,
                    COUNT(CASE WHEN t.end_time IS NOT NULL THEN 1 END) as completed_trips,
                    COUNT(CASE WHEN t.end_time IS NULL THEN 1 END) as active_trips,
                    SUM(CASE WHEN t.end_time IS NOT NULL THEN t.fare ELSE 0 END) as total_revenue
                FROM trips t
                JOIN stations s ON t.start_station_id = s.station_id
                GROUP BY s.locality
            )
            SELECT 
                locality,
                total_trips,
                completed_trips,
                active_trips,
                total_revenue
            FROM trip_stats
            ORDER BY total_trips DESC
        """)
        results = db.execute(query).fetchall()

        localities = [
            {
                "locality": r.locality,
                "total_trips": r.total_trips,
                "completed_trips": r.completed_trips,
                "active_trips": r.active_trips,
                "total_revenue": float(r.total_revenue) if r.total_revenue else 0.0
            }
            for r in results
        ]

        response = {"localities": localities}

        # Cache the result
        redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(response))

        return response

    except redis.exceptions.RedisError as e:
        # If Redis fails, just serve from database
        query = text("""
            WITH trip_stats AS (
                SELECT 
                    s.locality,
                    COUNT(*) as total_trips,
                    COUNT(CASE WHEN t.end_time IS NOT NULL THEN 1 END) as completed_trips,
                    COUNT(CASE WHEN t.end_time IS NULL THEN 1 END) as active_trips,
                    SUM(CASE WHEN t.end_time IS NOT NULL THEN t.fare ELSE 0 END) as total_revenue
                FROM trips t
                JOIN stations s ON t.start_station_id = s.station_id
                GROUP BY s.locality
            )
            SELECT 
                locality,
                total_trips,
                completed_trips,
                active_trips,
                total_revenue
            FROM trip_stats
            ORDER BY total_trips DESC
        """)
        results = db.execute(query).fetchall()

        localities = [
            {
                "locality": r.locality,
                "total_trips": r.total_trips,
                "completed_trips": r.completed_trips,
                "active_trips": r.active_trips,
                "total_revenue": float(r.total_revenue) if r.total_revenue else 0.0
            }
            for r in results
        ]

        return {"localities": localities}


@router.get("/card/{card_id}")
def get_card_trips(
    card_id: int,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    cache_key = f"trips:card:{card_id}"

    try:
        # Try to get from cache
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)

        # Check if card exists
        card_query = text("""
            SELECT card_id FROM cards WHERE card_id = :card_id
        """)
        card = db.execute(card_query, {"card_id": card_id}).first()

        if not card:
            raise HTTPException(status_code=404, detail="Card not found")

        # Get trips
        query = text("""
            SELECT 
                t.trip_id,
                t.card_id,
                t.start_station_id,
                t.end_station_id,
                t.start_time,
                t.end_time,
                t.status,
                t.fare,
                s1.name as start_station_name,
                s2.name as end_station_name
            FROM trips t
            LEFT JOIN stations s1 ON t.start_station_id = s1.station_id
            LEFT JOIN stations s2 ON t.end_station_id = s2.station_id
            WHERE t.card_id = :card_id
            ORDER BY t.start_time DESC
            LIMIT 10
        """)
        results = db.execute(query, {"card_id": card_id}).fetchall()

        trips = [
            {
                "trip_id": r.trip_id,
                "card_id": r.card_id,
                "start_station_id": r.start_station_id,
                "end_station_id": r.end_station_id,
                "start_station_name": r.start_station_name,
                "end_station_name": r.end_station_name,
                "start_time": r.start_time.isoformat(),
                "end_time": r.end_time.isoformat() if r.end_time else None,
                "status": r.status,
                "fare": float(r.fare) if r.fare else None
            }
            for r in results
        ]

        response = {"trips": trips}

        # Cache the result
        redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(response))

        return response

    except redis.exceptions.RedisError as e:
        # If Redis fails, just serve from database
        # Check if card exists
        card_query = text("""
            SELECT card_id FROM cards WHERE card_id = :card_id
        """)
        card = db.execute(card_query, {"card_id": card_id}).first()

        if not card:
            raise HTTPException(status_code=404, detail="Card not found")

        # Get trips
        query = text("""
            SELECT 
                t.trip_id,
                t.card_id,
                t.start_station_id,
                t.end_station_id,
                t.start_time,
                t.end_time,
                t.status,
                t.fare,
                s1.name as start_station_name,
                s2.name as end_station_name
            FROM trips t
            LEFT JOIN stations s1 ON t.start_station_id = s1.station_id
            LEFT JOIN stations s2 ON t.end_station_id = s2.station_id
            WHERE t.card_id = :card_id
            ORDER BY t.start_time DESC
            LIMIT 10
        """)
        results = db.execute(query, {"card_id": card_id}).fetchall()

        trips = [
            {
                "trip_id": r.trip_id,
                "card_id": r.card_id,
                "start_station_id": r.start_station_id,
                "end_station_id": r.end_station_id,
                "start_station_name": r.start_station_name,
                "end_station_name": r.end_station_name,
                "start_time": r.start_time.isoformat(),
                "end_time": r.end_time.isoformat() if r.end_time else None,
                "status": r.status,
                "fare": float(r.fare) if r.fare else None
            }
            for r in results
        ]

        return {"trips": trips}
