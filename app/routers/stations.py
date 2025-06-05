from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.dependencies import get_db, get_redis_client
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import json
import redis

router = APIRouter(prefix="/api/v1/stations", tags=["stations"])

# Pydantic models for request/response


class Station(BaseModel):
    station_id: int
    name: str
    locality: str
    status: str
    capacity: int
    current_occupancy: int


class StationArrival(BaseModel):
    station_id: int
    line: str
    destination: str
    estimated_arrival: datetime
    status: str


class StationAlert(BaseModel):
    alert_id: int
    station_id: int
    type: str
    message: str
    severity: str
    start_time: datetime
    end_time: Optional[datetime]


# Cache TTL
CACHE_TTL_SECONDS = 60  # 1 minute for station data


@router.get("/")
def list_stations(
    locality: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    cache_key = f"stations:list:{locality}:{status}"

    try:
        # Try to get from cache
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)

        # Build query
        query = text("""
            SELECT station_id, name, locality, status, capacity, current_occupancy
            FROM stations
            WHERE 1=1
        """)
        params = {}

        if locality:
            query = text(str(query) + " AND locality = :locality")
            params["locality"] = locality

        if status:
            query = text(str(query) + " AND status = :status")
            params["status"] = status

        query = text(str(query) + " ORDER BY name")

        results = db.execute(query, params).fetchall()

        stations = [
            {
                "station_id": r.station_id,
                "name": r.name,
                "locality": r.locality,
                "status": r.status,
                "capacity": r.capacity,
                "current_occupancy": r.current_occupancy
            }
            for r in results
        ]

        response = {"stations": stations}

        # Cache the result
        redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(response))

        return response

    except redis.exceptions.RedisError as e:
        # If Redis fails, just serve from database
        query = text("""
            SELECT station_id, name, locality, status, capacity, current_occupancy
            FROM stations
            WHERE 1=1
        """)
        params = {}

        if locality:
            query = text(str(query) + " AND locality = :locality")
            params["locality"] = locality

        if status:
            query = text(str(query) + " AND status = :status")
            params["status"] = status

        query = text(str(query) + " ORDER BY name")

        results = db.execute(query, params).fetchall()

        stations = [
            {
                "station_id": r.station_id,
                "name": r.name,
                "locality": r.locality,
                "status": r.status,
                "capacity": r.capacity,
                "current_occupancy": r.current_occupancy
            }
            for r in results
        ]

        return {"stations": stations}


@router.get("/{station_id}/arrivals")
def get_station_arrivals(
    station_id: int,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    cache_key = f"station:{station_id}:arrivals"

    try:
        # Try to get from cache
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)

        # Check if station exists
        station_query = text("""
            SELECT station_id FROM stations WHERE station_id = :station_id
        """)
        station = db.execute(station_query, {"station_id": station_id}).first()

        if not station:
            raise HTTPException(status_code=404, detail="Station not found")

        # Get arrivals
        query = text("""
            SELECT station_id, line, destination, estimated_arrival, status
            FROM arrivals
            WHERE station_id = :station_id
            AND estimated_arrival > CURRENT_TIMESTAMP
            ORDER BY estimated_arrival
            LIMIT 10
        """)
        results = db.execute(query, {"station_id": station_id}).fetchall()

        arrivals = [
            {
                "station_id": r.station_id,
                "line": r.line,
                "destination": r.destination,
                "estimated_arrival": r.estimated_arrival.isoformat(),
                "status": r.status
            }
            for r in results
        ]

        response = {"arrivals": arrivals}

        # Cache the result
        redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(response))

        return response

    except redis.exceptions.RedisError as e:
        # If Redis fails, just serve from database
        # Check if station exists
        station_query = text("""
            SELECT station_id FROM stations WHERE station_id = :station_id
        """)
        station = db.execute(station_query, {"station_id": station_id}).first()

        if not station:
            raise HTTPException(status_code=404, detail="Station not found")

        # Get arrivals
        query = text("""
            SELECT station_id, line, destination, estimated_arrival, status
            FROM arrivals
            WHERE station_id = :station_id
            AND estimated_arrival > CURRENT_TIMESTAMP
            ORDER BY estimated_arrival
            LIMIT 10
        """)
        results = db.execute(query, {"station_id": station_id}).fetchall()

        arrivals = [
            {
                "station_id": r.station_id,
                "line": r.line,
                "destination": r.destination,
                "estimated_arrival": r.estimated_arrival.isoformat(),
                "status": r.status
            }
            for r in results
        ]

        return {"arrivals": arrivals}


@router.get("/{station_id}/alerts")
def get_station_alerts(
    station_id: int,
    active_only: bool = True,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    cache_key = f"station:{station_id}:alerts:{active_only}"

    try:
        # Try to get from cache
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)

        # Check if station exists
        station_query = text("""
            SELECT station_id FROM stations WHERE station_id = :station_id
        """)
        station = db.execute(station_query, {"station_id": station_id}).first()

        if not station:
            raise HTTPException(status_code=404, detail="Station not found")

        # Build query
        query = text("""
            SELECT alert_id, station_id, type, message, severity, start_time, end_time
            FROM alerts
            WHERE station_id = :station_id
        """)
        params = {"station_id": station_id}

        if active_only:
            query = text(
                str(query) + " AND (end_time IS NULL OR end_time > CURRENT_TIMESTAMP)")

        query = text(str(query) + " ORDER BY start_time DESC")

        results = db.execute(query, params).fetchall()

        alerts = [
            {
                "alert_id": r.alert_id,
                "station_id": r.station_id,
                "type": r.type,
                "message": r.message,
                "severity": r.severity,
                "start_time": r.start_time.isoformat(),
                "end_time": r.end_time.isoformat() if r.end_time else None
            }
            for r in results
        ]

        response = {"alerts": alerts}

        # Cache the result
        redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(response))

        return response

    except redis.exceptions.RedisError as e:
        # If Redis fails, just serve from database
        # Check if station exists
        station_query = text("""
            SELECT station_id FROM stations WHERE station_id = :station_id
        """)
        station = db.execute(station_query, {"station_id": station_id}).first()

        if not station:
            raise HTTPException(status_code=404, detail="Station not found")

        # Build query
        query = text("""
            SELECT alert_id, station_id, type, message, severity, start_time, end_time
            FROM alerts
            WHERE station_id = :station_id
        """)
        params = {"station_id": station_id}

        if active_only:
            query = text(
                str(query) + " AND (end_time IS NULL OR end_time > CURRENT_TIMESTAMP)")

        query = text(str(query) + " ORDER BY start_time DESC")

        results = db.execute(query, params).fetchall()

        alerts = [
            {
                "alert_id": r.alert_id,
                "station_id": r.station_id,
                "type": r.type,
                "message": r.message,
                "severity": r.severity,
                "start_time": r.start_time.isoformat(),
                "end_time": r.end_time.isoformat() if r.end_time else None
            }
            for r in results
        ]

        return {"alerts": alerts}


@router.get("/identifiers")
def get_station_identifiers(
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    """
    Get all station identifiers (code and name) for selectors
    """
    cache_key = "stations:identifiers"

    try:
        # Try to get from cache
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)

        # Get all stations
        query = text("""
            SELECT station_code, name
            FROM stations
            WHERE station_code IS NOT NULL
            AND is_active = true
            ORDER BY name ASC
        """)
        
        results = db.execute(query).fetchall()

        stations = [
            {
                "code": r.station_code,
                "name": r.name
            }
            for r in results
        ]

        response = {"stations": stations}

        # Cache the result for 5 minutes
        redis_client.setex(cache_key, 300, json.dumps(response))

        return response

    except redis.exceptions.RedisError as e:
        # If Redis fails, just serve from database
        query = text("""
            SELECT station_code, name
            FROM stations
            WHERE station_code IS NOT NULL
            AND is_active = true
            ORDER BY name ASC
        """)
        
        results = db.execute(query).fetchall()

        stations = [
            {
                "code": r.station_code,
                "name": r.name
            }
            for r in results
        ]

        return {"stations": stations}


@router.get("/{station_code}/details")
def get_station_details(
    station_code: str,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    """
    Get station details including routes that serve it
    """
    cache_key = f"station:{station_code}:details"

    try:
        # Try to get from cache
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)

        # Get station details
        station_query = text("""
            SELECT station_code, name, station_type, address, latitude, longitude
            FROM stations
            WHERE station_code = :station_code
            AND is_active = true
        """)
        
        station = db.execute(station_query, {"station_code": station_code}).first()

        if not station:
            raise HTTPException(status_code=404, detail="Station not found")

        # Get routes serving this station
        routes_query = text("""
            SELECT r.route_code, r.route_name, r.route_type
            FROM intermediate_stations ist
            JOIN routes r ON ist.route_id = r.route_id
            WHERE ist.station_id = (SELECT station_id FROM stations WHERE station_code = :station_code)
            AND r.is_active = true
            ORDER BY r.route_code ASC
        """)
        
        routes_results = db.execute(routes_query, {"station_code": station_code}).fetchall()

        routes_serving = [
            {
                "route_code": r.route_code,
                "route_name": r.route_name or "",
                "route_type": r.route_type
            }
            for r in routes_results
        ]

        response = {
            "station_code": station.station_code,
            "station_name": station.name,
            "station_type": station.station_type,
            "address": station.address or "",
            "latitude": float(station.latitude) if station.latitude else None,
            "longitude": float(station.longitude) if station.longitude else None,
            "routes_serving": routes_serving
        }

        # Cache the result for 5 minutes
        redis_client.setex(cache_key, 300, json.dumps(response))

        return response

    except redis.exceptions.RedisError as e:
        # If Redis fails, just serve from database
        # Get station details
        station_query = text("""
            SELECT station_code, name, station_type, address, latitude, longitude
            FROM stations
            WHERE station_code = :station_code
            AND is_active = true
        """)
        
        station = db.execute(station_query, {"station_code": station_code}).first()

        if not station:
            raise HTTPException(status_code=404, detail="Station not found")

        # Get routes serving this station
        routes_query = text("""
            SELECT r.route_code, r.route_name, r.route_type
            FROM intermediate_stations ist
            JOIN routes r ON ist.route_id = r.route_id
            WHERE ist.station_id = (SELECT station_id FROM stations WHERE station_code = :station_code)
            AND r.is_active = true
            ORDER BY r.route_code ASC
        """)
        
        routes_results = db.execute(routes_query, {"station_code": station_code}).fetchall()

        routes_serving = [
            {
                "route_code": r.route_code,
                "route_name": r.route_name or "",
                "route_type": r.route_type
            }
            for r in routes_results
        ]

        response = {
            "station_code": station.station_code,
            "station_name": station.name,
            "station_type": station.station_type,
            "address": station.address or "",
            "latitude": float(station.latitude) if station.latitude else None,
            "longitude": float(station.longitude) if station.longitude else None,
            "routes_serving": routes_serving
        }

        return response
