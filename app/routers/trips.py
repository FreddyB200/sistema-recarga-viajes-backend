from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.dependencies import get_db, get_redis_client
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import json
import redis
import uuid

router = APIRouter(prefix="/api/v1/trips", tags=["trips"])

# Pydantic models for request/response (Enhanced for realistic simulations)

class TripStart(BaseModel):
    """Enhanced trip start model with route integration"""
    card_id: int
    route_id: int                    # Route the user wants to board
    boarding_station_id: int         # Station where user boards
    vehicle_id: Optional[int] = None # Specific vehicle (auto-assigned if None)
    driver_id: Optional[int] = None  # Specific driver (auto-assigned if None)

class TripEnd(BaseModel):
    """Trip end model with validation"""
    trip_id: int
    disembarking_station_id: int     # Station where user disembarks

class CompleteTripSimulation(BaseModel):
    """Complete trip for simulation purposes"""
    card_id: int
    route_id: int
    boarding_station_id: int
    disembarking_station_id: int
    vehicle_id: Optional[int] = None
    driver_id: Optional[int] = None

class TripResponse(BaseModel):
    """Standardized trip response"""
    trip_id: int
    card_id: int
    route_id: Optional[int]
    boarding_station_id: int
    disembarking_station_id: Optional[int]
    boarding_time: datetime
    disembarking_time: Optional[datetime]
    fare_id: Optional[int]
    fare_amount: Optional[float]
    is_transfer: bool
    status: str
    remaining_balance: Optional[float]

# Cache TTL
CACHE_TTL_SECONDS = 300  # 5 minutes for trip data

# Transfer window in minutes
TRANSFER_WINDOW_MINUTES = 90

# Helper functions for enhanced trip management

def get_current_fare(route_type: str, is_transfer: bool, db: Session) -> dict:
    """
    Get current active fare based on route type and transfer status
    Returns: {"fare_id": int, "value": float, "fare_type": str}
    """
    if is_transfer:
        # Most transfers are free, some cost 200 COP
        fare_type = "TRANSFER_0_COST"  # Can be enhanced with logic for paid transfers
    elif route_type == "CABLE":
        fare_type = "STANDARD_CABLE"
    else:
        fare_type = "STANDARD_SITP"
    
    fare_query = text("""
        SELECT fare_id, value, fare_type 
        FROM fares 
        WHERE fare_type = :fare_type 
        AND (end_date IS NULL OR end_date >= CURRENT_DATE)
        ORDER BY start_date DESC 
        LIMIT 1
    """)
    
    fare = db.execute(fare_query, {"fare_type": fare_type}).first()
    
    if not fare:
        # Fallback to standard fare if specific type not found
        fare = db.execute(fare_query, {"fare_type": "STANDARD_SITP"}).first()
    
    return {
        "fare_id": fare.fare_id if fare else 1,
        "value": float(fare.value) if fare else 2950.0,
        "fare_type": fare.fare_type if fare else "STANDARD_SITP"
    }

def check_transfer_eligibility(card_id: int, current_route_id: int, db: Session) -> dict:
    """
    Check if a trip qualifies as a transfer
    Returns: {"is_transfer": bool, "transfer_group_id": str}
    """
    recent_trip_query = text("""
        SELECT t.transfer_group_id, t.route_id, r.route_type, t.boarding_time
        FROM trips t
        JOIN routes r ON t.route_id = r.route_id
        WHERE t.card_id = :card_id 
        AND t.disembarking_time IS NOT NULL
        AND t.boarding_time >= (CURRENT_TIMESTAMP - INTERVAL ':window minutes')
        ORDER BY t.disembarking_time DESC 
        LIMIT 1
    """)
    
    recent_trip = db.execute(recent_trip_query, {
        "card_id": card_id, 
        "window": TRANSFER_WINDOW_MINUTES
    }).first()
    
    if recent_trip:
        # Check if it's a valid transfer (different route, within time window)
        current_route_query = text("SELECT route_type FROM routes WHERE route_id = :route_id")
        current_route = db.execute(current_route_query, {"route_id": current_route_id}).first()
        
        if (recent_trip.route_id != current_route_id and 
            current_route and recent_trip.transfer_group_id):
            return {
                "is_transfer": True,
                "transfer_group_id": recent_trip.transfer_group_id
            }
    
    # Not a transfer, create new group
    return {
        "is_transfer": False,
        "transfer_group_id": str(uuid.uuid4())
    }

def validate_route_station(route_id: int, station_id: int, db: Session) -> bool:
    """
    Validate that a station is part of a route
    """
    validation_query = text("""
        SELECT 1 FROM intermediate_stations 
        WHERE route_id = :route_id AND station_id = :station_id
        UNION
        SELECT 1 FROM routes 
        WHERE route_id = :route_id 
        AND (origin_station_id = :station_id OR destination_station_id = :station_id)
    """)
    
    result = db.execute(validation_query, {
        "route_id": route_id, 
        "station_id": station_id
    }).first()
    
    return result is not None

def assign_vehicle_and_driver(route_id: int, db: Session) -> dict:
    """
    Auto-assign available vehicle and driver for a route
    """
    # Get route's concessionaire to match vehicles/drivers
    assignment_query = text("""
        SELECT 
            v.vehicle_id,
            d.driver_id,
            r.concessionaire_id
        FROM routes r
        LEFT JOIN vehicles v ON v.concessionaire_id = r.concessionaire_id 
            AND v.status = 'active'
        LEFT JOIN drivers d ON d.concessionaire_id = r.concessionaire_id 
            AND d.status = 'active'
        WHERE r.route_id = :route_id
        AND v.vehicle_id IS NOT NULL 
        AND d.driver_id IS NOT NULL
        ORDER BY RANDOM()
        LIMIT 1
    """)
    
    assignment = db.execute(assignment_query, {"route_id": route_id}).first()
    
    if assignment:
        return {
            "vehicle_id": assignment.vehicle_id,
            "driver_id": assignment.driver_id
        }
    else:
        # Fallback to any available vehicle/driver
        fallback_query = text("""
            SELECT 
                (SELECT vehicle_id FROM vehicles WHERE status = 'active' ORDER BY RANDOM() LIMIT 1) as vehicle_id,
                (SELECT driver_id FROM drivers WHERE status = 'active' ORDER BY RANDOM() LIMIT 1) as driver_id
        """)
        fallback = db.execute(fallback_query).first()
        return {
            "vehicle_id": fallback.vehicle_id if fallback else 1,
            "driver_id": fallback.driver_id if fallback else 1
        }


@router.post("/start")
def start_trip(
    trip: TripStart,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    """
    Enhanced trip start with route validation, dynamic fares, and transfer detection
    """
    try:
        # 1. Validate card exists and is active
        card_query = text("""
            SELECT status, balance FROM cards WHERE card_id = :card_id
        """)
        card = db.execute(card_query, {"card_id": trip.card_id}).first()

        if not card:
            raise HTTPException(status_code=404, detail="Card not found")
        if card.status != "active":
            raise HTTPException(status_code=400, detail="Card is not active")

        # 2. Validate route exists and is active
        route_query = text("""
            SELECT route_id, route_type, is_active 
            FROM routes WHERE route_id = :route_id
        """)
        route = db.execute(route_query, {"route_id": trip.route_id}).first()

        if not route:
            raise HTTPException(status_code=404, detail="Route not found")
        if not route.is_active:
            raise HTTPException(status_code=400, detail="Route is not active")

        # 3. Validate boarding station exists and is active
        station_query = text("""
            SELECT station_id, name, station_type, is_active 
            FROM stations WHERE station_id = :station_id
        """)
        station = db.execute(station_query, {"station_id": trip.boarding_station_id}).first()

        if not station:
            raise HTTPException(status_code=404, detail="Boarding station not found")
        if not station.is_active:
            raise HTTPException(status_code=400, detail="Boarding station is not active")

        # 4. Validate that the station is part of the route
        if not validate_route_station(trip.route_id, trip.boarding_station_id, db):
            raise HTTPException(
                status_code=400, 
                detail="Boarding station is not part of the specified route"
            )

        # 5. Check for active trips
        active_trip_query = text("""
            SELECT trip_id FROM trips 
            WHERE card_id = :card_id AND disembarking_time IS NULL
        """)
        active_trip = db.execute(active_trip_query, {"card_id": trip.card_id}).first()

        if active_trip:
            raise HTTPException(status_code=400, detail="Card has an active trip")

        # 6. Check transfer eligibility and get transfer info
        transfer_info = check_transfer_eligibility(trip.card_id, trip.route_id, db)

        # 7. Calculate fare based on route type and transfer status
        fare_info = get_current_fare(route.route_type, transfer_info["is_transfer"], db)

        # 8. Validate sufficient balance (CRITICAL for simulations)
        if card.balance < fare_info["value"]:
            raise HTTPException(
                status_code=402, 
                detail=f"Insufficient balance. Required: ${fare_info['value']:.2f}, Available: ${card.balance:.2f}"
            )

        # 9. Auto-assign vehicle and driver if not provided
        if not trip.vehicle_id or not trip.driver_id:
            assignment = assign_vehicle_and_driver(trip.route_id, db)
            vehicle_id = trip.vehicle_id or assignment["vehicle_id"]
            driver_id = trip.driver_id or assignment["driver_id"]
        else:
            vehicle_id = trip.vehicle_id
            driver_id = trip.driver_id

        # 10. Create new trip with complete information
        trip_insert_query = text("""
            INSERT INTO trips (
                card_id, route_id, vehicle_id, driver_id,
                boarding_station_id, boarding_time, 
                fare_id, is_transfer, transfer_group_id
            )
            VALUES (
                :card_id, :route_id, :vehicle_id, :driver_id,
                :boarding_station_id, CURRENT_TIMESTAMP,
                :fare_id, :is_transfer, :transfer_group_id
            )
            RETURNING trip_id, boarding_time
        """)
        
        result = db.execute(trip_insert_query, {
            "card_id": trip.card_id,
            "route_id": trip.route_id,
            "vehicle_id": vehicle_id,
            "driver_id": driver_id,
            "boarding_station_id": trip.boarding_station_id,
            "fare_id": fare_info["fare_id"],
            "is_transfer": transfer_info["is_transfer"],
            "transfer_group_id": transfer_info["transfer_group_id"]
        }).first()

        db.commit()

        # 11. Invalidate relevant caches
        redis_client.delete("trips:total")
        redis_client.delete(f"trips:card:{trip.card_id}")
        redis_client.delete("trips:total:localities")

        return {
            "trip_id": result.trip_id,
            "card_id": trip.card_id,
            "route_id": trip.route_id,
            "boarding_station_id": trip.boarding_station_id,
            "boarding_time": result.boarding_time.isoformat(),
            "vehicle_id": vehicle_id,
            "driver_id": driver_id,
            "fare_amount": fare_info["value"],
            "is_transfer": transfer_info["is_transfer"],
            "status": "in_progress",
            "message": "Trip started successfully"
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/end")
def end_trip(
    trip: TripEnd,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    """
    Enhanced trip end with route validation and proper fare deduction
    """
    try:
        # 1. Get trip details with route information
        trip_query = text("""
            SELECT 
                t.trip_id, t.card_id, t.route_id, t.boarding_station_id, 
                t.boarding_time, t.fare_id, t.is_transfer,
                c.balance, f.value as fare_amount,
                r.route_type
            FROM trips t
            JOIN cards c ON t.card_id = c.card_id
            JOIN fares f ON t.fare_id = f.fare_id
            JOIN routes r ON t.route_id = r.route_id
            WHERE t.trip_id = :trip_id AND t.disembarking_time IS NULL
        """)
        trip_data = db.execute(trip_query, {"trip_id": trip.trip_id}).first()

        if not trip_data:
            raise HTTPException(status_code=404, detail="Active trip not found")

        # 2. Validate disembarking station exists and is active
        station_query = text("""
            SELECT station_id, name, is_active 
            FROM stations WHERE station_id = :station_id
        """)
        station = db.execute(station_query, {"station_id": trip.disembarking_station_id}).first()

        if not station:
            raise HTTPException(status_code=404, detail="Disembarking station not found")
        if not station.is_active:
            raise HTTPException(status_code=400, detail="Disembarking station is not active")

        # 3. Validate that disembarking station is part of the route
        if not validate_route_station(trip_data.route_id, trip.disembarking_station_id, db):
            raise HTTPException(
                status_code=400, 
                detail="Disembarking station is not part of the route"
            )

        # 4. Final balance check (double-check for concurrency issues)
        if trip_data.balance < trip_data.fare_amount:
            raise HTTPException(
                status_code=402, 
                detail=f"Insufficient balance for fare: ${trip_data.fare_amount:.2f}"
            )

        # 5. Complete trip and deduct fare from card balance
        complete_trip_query = text("""
            WITH trip_update AS (
                UPDATE trips 
                SET disembarking_station_id = :disembarking_station_id,
                    disembarking_time = CURRENT_TIMESTAMP
                WHERE trip_id = :trip_id
                RETURNING trip_id, disembarking_time, boarding_time
            ),
            balance_update AS (
                UPDATE cards
                SET balance = balance - :fare_amount,
                    last_used_date = CURRENT_TIMESTAMP
                WHERE card_id = :card_id
                RETURNING balance
            )
            SELECT 
                t.trip_id, t.disembarking_time, t.boarding_time,
                b.balance as new_balance
            FROM trip_update t, balance_update b
        """)
        
        result = db.execute(complete_trip_query, {
            "trip_id": trip.trip_id,
            "disembarking_station_id": trip.disembarking_station_id,
            "fare_amount": trip_data.fare_amount,
            "card_id": trip_data.card_id
        }).first()

        db.commit()

        # 6. Invalidate relevant caches
        redis_client.delete("trips:total")
        redis_client.delete(f"trips:card:{trip_data.card_id}")
        redis_client.delete("trips:total:localities")
        redis_client.delete(f"card:{trip_data.card_id}:balance")

        return {
            "trip_id": trip.trip_id,
            "card_id": trip_data.card_id,
            "route_id": trip_data.route_id,
            "boarding_station_id": trip_data.boarding_station_id,
            "disembarking_station_id": trip.disembarking_station_id,
            "boarding_time": trip_data.boarding_time.isoformat(),
            "disembarking_time": result.disembarking_time.isoformat(),
            "fare_amount": float(trip_data.fare_amount),
            "is_transfer": trip_data.is_transfer,
            "status": "completed",
            "new_balance": float(result.new_balance),
            "message": "Trip completed successfully"
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


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
                COUNT(CASE WHEN disembarking_time IS NOT NULL THEN 1 END) as completed_trips,
                COUNT(CASE WHEN disembarking_time IS NULL THEN 1 END) as active_trips,
                SUM(CASE WHEN disembarking_time IS NOT NULL THEN f.value ELSE 0 END) as total_revenue
            FROM trips t
            LEFT JOIN fares f ON t.fare_id = f.fare_id
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
                COUNT(CASE WHEN disembarking_time IS NOT NULL THEN 1 END) as completed_trips,
                COUNT(CASE WHEN disembarking_time IS NULL THEN 1 END) as active_trips,
                SUM(CASE WHEN disembarking_time IS NOT NULL THEN f.value ELSE 0 END) as total_revenue
            FROM trips t
            LEFT JOIN fares f ON t.fare_id = f.fare_id
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
                    l.name as locality,
                    COUNT(*) as total_trips,
                    COUNT(CASE WHEN t.disembarking_time IS NOT NULL THEN 1 END) as completed_trips,
                    COUNT(CASE WHEN t.disembarking_time IS NULL THEN 1 END) as active_trips,
                    SUM(CASE WHEN t.disembarking_time IS NOT NULL THEN f.value ELSE 0 END) as total_revenue
                FROM trips t
                JOIN stations s ON t.boarding_station_id = s.station_id
                JOIN locations l ON s.location_id = l.location_id
                LEFT JOIN fares f ON t.fare_id = f.fare_id
                GROUP BY l.name
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
                    l.name as locality,
                    COUNT(*) as total_trips,
                    COUNT(CASE WHEN t.disembarking_time IS NOT NULL THEN 1 END) as completed_trips,
                    COUNT(CASE WHEN t.disembarking_time IS NULL THEN 1 END) as active_trips,
                    SUM(CASE WHEN t.disembarking_time IS NOT NULL THEN f.value ELSE 0 END) as total_revenue
                FROM trips t
                JOIN stations s ON t.boarding_station_id = s.station_id
                JOIN locations l ON s.location_id = l.location_id
                LEFT JOIN fares f ON t.fare_id = f.fare_id
                GROUP BY l.name
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
                t.boarding_station_id,
                t.disembarking_station_id,
                t.boarding_time,
                t.disembarking_time,
                t.is_transfer,
                f.value as fare,
                s1.name as boarding_station_name,
                s2.name as disembarking_station_name
            FROM trips t
            LEFT JOIN stations s1 ON t.boarding_station_id = s1.station_id
            LEFT JOIN stations s2 ON t.disembarking_station_id = s2.station_id
            LEFT JOIN fares f ON t.fare_id = f.fare_id
            WHERE t.card_id = :card_id
            ORDER BY t.boarding_time DESC
            LIMIT 10
        """)
        results = db.execute(query, {"card_id": card_id}).fetchall()

        trips = [
            {
                "trip_id": r.trip_id,
                "card_id": r.card_id,
                "boarding_station_id": r.boarding_station_id,
                "disembarking_station_id": r.disembarking_station_id,
                "boarding_station_name": r.boarding_station_name,
                "disembarking_station_name": r.disembarking_station_name,
                "boarding_time": r.boarding_time.isoformat(),
                "disembarking_time": r.disembarking_time.isoformat() if r.disembarking_time else None,
                "is_transfer": r.is_transfer,
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
                t.boarding_station_id,
                t.disembarking_station_id,
                t.boarding_time,
                t.disembarking_time,
                t.is_transfer,
                f.value as fare,
                s1.name as boarding_station_name,
                s2.name as disembarking_station_name
            FROM trips t
            LEFT JOIN stations s1 ON t.boarding_station_id = s1.station_id
            LEFT JOIN stations s2 ON t.disembarking_station_id = s2.station_id
            LEFT JOIN fares f ON t.fare_id = f.fare_id
            WHERE t.card_id = :card_id
            ORDER BY t.boarding_time DESC
            LIMIT 10
        """)
        results = db.execute(query, {"card_id": card_id}).fetchall()

        trips = [
            {
                "trip_id": r.trip_id,
                "card_id": r.card_id,
                "boarding_station_id": r.boarding_station_id,
                "disembarking_station_id": r.disembarking_station_id,
                "boarding_station_name": r.boarding_station_name,
                "disembarking_station_name": r.disembarking_station_name,
                "boarding_time": r.boarding_time.isoformat(),
                "disembarking_time": r.disembarking_time.isoformat() if r.disembarking_time else None,
                "is_transfer": r.is_transfer,
                "fare": float(r.fare) if r.fare else None
            }
            for r in results
        ]

        return {"trips": trips}


# Enhanced endpoints for realistic simulations

@router.post("/complete")
def create_complete_trip(
    trip: CompleteTripSimulation,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    """
    Create a complete trip (start to end) in one operation for simulation purposes
    """
    try:
        # 1. Validate card, route, and stations
        validation_query = text("""
            SELECT 
                c.card_id, c.status, c.balance,
                r.route_id, r.route_type, r.is_active as route_active,
                s1.station_id as boarding_station, s1.is_active as boarding_active,
                s2.station_id as disembarking_station, s2.is_active as disembarking_active
            FROM cards c,
                 routes r,
                 stations s1,
                 stations s2
            WHERE c.card_id = :card_id
            AND r.route_id = :route_id
            AND s1.station_id = :boarding_station_id
            AND s2.station_id = :disembarking_station_id
        """)
        
        validation = db.execute(validation_query, {
            "card_id": trip.card_id,
            "route_id": trip.route_id,
            "boarding_station_id": trip.boarding_station_id,
            "disembarking_station_id": trip.disembarking_station_id
        }).first()

        if not validation:
            raise HTTPException(status_code=404, detail="Invalid card, route, or stations")

        if validation.status != "active":
            raise HTTPException(status_code=400, detail="Card is not active")
        if not validation.route_active:
            raise HTTPException(status_code=400, detail="Route is not active")
        if not validation.boarding_active or not validation.disembarking_active:
            raise HTTPException(status_code=400, detail="One or more stations are not active")

        # 2. Validate route-station relationships
        if not validate_route_station(trip.route_id, trip.boarding_station_id, db):
            raise HTTPException(status_code=400, detail="Boarding station not part of route")
        if not validate_route_station(trip.route_id, trip.disembarking_station_id, db):
            raise HTTPException(status_code=400, detail="Disembarking station not part of route")

        # 3. Check for active trips
        active_trip_query = text("""
            SELECT trip_id FROM trips 
            WHERE card_id = :card_id AND disembarking_time IS NULL
        """)
        active_trip = db.execute(active_trip_query, {"card_id": trip.card_id}).first()
        if active_trip:
            raise HTTPException(status_code=400, detail="Card has an active trip")

        # 4. Calculate transfer status and fare
        transfer_info = check_transfer_eligibility(trip.card_id, trip.route_id, db)
        fare_info = get_current_fare(validation.route_type, transfer_info["is_transfer"], db)

        # 5. Check balance
        if validation.balance < fare_info["value"]:
            raise HTTPException(
                status_code=402, 
                detail=f"Insufficient balance: ${fare_info['value']:.2f} required"
            )

        # 6. Auto-assign vehicle/driver if needed
        if not trip.vehicle_id or not trip.driver_id:
            assignment = assign_vehicle_and_driver(trip.route_id, db)
            vehicle_id = trip.vehicle_id or assignment["vehicle_id"]
            driver_id = trip.driver_id or assignment["driver_id"]
        else:
            vehicle_id = trip.vehicle_id
            driver_id = trip.driver_id

        # 7. Create complete trip with realistic timing
        boarding_time = datetime.now()
        travel_duration = timedelta(minutes=15 + (abs(trip.disembarking_station_id - trip.boarding_station_id) * 2))
        disembarking_time = boarding_time + travel_duration

        complete_trip_query = text("""
            WITH trip_insert AS (
                INSERT INTO trips (
                    card_id, route_id, vehicle_id, driver_id,
                    boarding_station_id, disembarking_station_id,
                    boarding_time, disembarking_time,
                    fare_id, is_transfer, transfer_group_id
                )
                VALUES (
                    :card_id, :route_id, :vehicle_id, :driver_id,
                    :boarding_station_id, :disembarking_station_id,
                    :boarding_time, :disembarking_time,
                    :fare_id, :is_transfer, :transfer_group_id
                )
                RETURNING trip_id
            ),
            balance_update AS (
                UPDATE cards
                SET balance = balance - :fare_amount,
                    last_used_date = :disembarking_time
                WHERE card_id = :card_id
                RETURNING balance
            )
            SELECT t.trip_id, b.balance as new_balance
            FROM trip_insert t, balance_update b
        """)

        result = db.execute(complete_trip_query, {
            "card_id": trip.card_id,
            "route_id": trip.route_id,
            "vehicle_id": vehicle_id,
            "driver_id": driver_id,
            "boarding_station_id": trip.boarding_station_id,
            "disembarking_station_id": trip.disembarking_station_id,
            "boarding_time": boarding_time,
            "disembarking_time": disembarking_time,
            "fare_id": fare_info["fare_id"],
            "fare_amount": fare_info["value"],
            "is_transfer": transfer_info["is_transfer"],
            "transfer_group_id": transfer_info["transfer_group_id"]
        }).first()

        db.commit()

        # 8. Invalidate caches
        redis_client.delete("trips:total")
        redis_client.delete(f"trips:card:{trip.card_id}")
        redis_client.delete("trips:total:localities")

        return {
            "trip_id": result.trip_id,
            "card_id": trip.card_id,
            "route_id": trip.route_id,
            "boarding_station_id": trip.boarding_station_id,
            "disembarking_station_id": trip.disembarking_station_id,
            "boarding_time": boarding_time.isoformat(),
            "disembarking_time": disembarking_time.isoformat(),
            "vehicle_id": vehicle_id,
            "driver_id": driver_id,
            "fare_amount": fare_info["value"],
            "is_transfer": transfer_info["is_transfer"],
            "new_balance": float(result.new_balance),
            "status": "completed",
            "message": "Complete trip simulation successful"
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/simulate/revenue-test")
def simulate_revenue_increase(
    num_trips: int = 50,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    """
    Generate multiple random trips to test revenue increase in simulations
    """
    try:
        if num_trips > 200:
            raise HTTPException(status_code=400, detail="Maximum 200 trips per simulation")

        # Get active cards with sufficient balance
        active_cards_query = text("""
            SELECT card_id FROM cards 
            WHERE status = 'active' AND balance >= 2000
            ORDER BY RANDOM()
            LIMIT :num_trips
        """)
        active_cards = db.execute(active_cards_query, {"num_trips": num_trips}).fetchall()

        if len(active_cards) < num_trips:
            raise HTTPException(
                status_code=400, 
                detail=f"Only {len(active_cards)} cards available with sufficient balance"
            )

        # Get random routes and their stations
        routes_query = text("""
            SELECT DISTINCT r.route_id, r.route_type,
                   array_agg(DISTINCT s.station_id) as station_ids
            FROM routes r
            JOIN intermediate_stations i ON r.route_id = i.route_id
            JOIN stations s ON i.station_id = s.station_id
            WHERE r.is_active = true AND s.is_active = true
            GROUP BY r.route_id, r.route_type
            HAVING COUNT(DISTINCT s.station_id) >= 2
            ORDER BY RANDOM()
            LIMIT 20
        """)
        routes_data = db.execute(routes_query).fetchall()

        if not routes_data:
            raise HTTPException(status_code=400, detail="No suitable routes found")

        successful_trips = []
        total_revenue_generated = 0.0

        for i, card_row in enumerate(active_cards):
            try:
                # Select random route and stations
                route_data = routes_data[i % len(routes_data)]
                station_ids = route_data.station_ids
                
                if len(station_ids) < 2:
                    continue

                boarding_station = station_ids[0]
                disembarking_station = station_ids[-1]

                # Create trip simulation data
                trip_sim = CompleteTripSimulation(
                    card_id=card_row.card_id,
                    route_id=route_data.route_id,
                    boarding_station_id=boarding_station,
                    disembarking_station_id=disembarking_station
                )

                # Use the complete trip endpoint internally
                trip_result = create_complete_trip(trip_sim, db, redis_client)
                successful_trips.append({
                    "trip_id": trip_result["trip_id"],
                    "card_id": trip_result["card_id"],
                    "fare_amount": trip_result["fare_amount"]
                })
                total_revenue_generated += trip_result["fare_amount"]

            except Exception as trip_error:
                # Log individual trip errors but continue
                continue

        return {
            "simulation_summary": {
                "requested_trips": num_trips,
                "successful_trips": len(successful_trips),
                "total_revenue_generated": round(total_revenue_generated, 2),
                "average_fare": round(total_revenue_generated / len(successful_trips), 2) if successful_trips else 0
            },
            "trips": successful_trips,
            "message": f"Successfully simulated {len(successful_trips)} trips"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Simulation error: {str(e)}")


@router.get("/routes/{route_id}/stations")
def get_route_stations(
    route_id: int,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    """
    Get all stations for a specific route
    """
    cache_key = f"route:{route_id}:stations"
    
    try:
        # Try cache first
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)

        # Validate route exists
        route_query = text("""
            SELECT route_id, route_code, route_name, route_type, is_active
            FROM routes WHERE route_id = :route_id
        """)
        route = db.execute(route_query, {"route_id": route_id}).first()

        if not route:
            raise HTTPException(status_code=404, detail="Route not found")

        # Get all stations for this route with proper ordering
        stations_query = text("""
            WITH route_stations AS (
                SELECT 
                    s.station_id,
                    s.name,
                    s.station_type,
                    s.is_active,
                    i.sequence_order
                FROM stations s
                LEFT JOIN intermediate_stations i ON s.station_id = i.station_id AND i.route_id = :route_id
                WHERE s.station_id IN (
                    SELECT station_id FROM intermediate_stations WHERE route_id = :route_id
                    UNION
                    SELECT origin_station_id FROM routes WHERE route_id = :route_id
                    UNION  
                    SELECT destination_station_id FROM routes WHERE route_id = :route_id
                )
            )
            SELECT *
            FROM route_stations
            ORDER BY sequence_order NULLS LAST, station_id
        """)
        
        stations_result = db.execute(stations_query, {"route_id": route_id}).fetchall()

        stations = [
            {
                "station_id": s.station_id,
                "name": s.name,
                "station_type": s.station_type,
                "is_active": s.is_active,
                "sequence_order": s.sequence_order
            }
            for s in stations_result
        ]

        response = {
            "route": {
                "route_id": route.route_id,
                "route_code": route.route_code,
                "route_name": route.route_name,
                "route_type": route.route_type,
                "is_active": route.is_active
            },
            "stations": stations,
            "total_stations": len(stations)
        }

        # Cache for 10 minutes (routes don't change often)
        redis_client.setex(cache_key, 600, json.dumps(response))
        
        return response

    except HTTPException:
        raise
    except redis.exceptions.RedisError:
        # If Redis fails, serve from database directly
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving route stations: {str(e)}")
