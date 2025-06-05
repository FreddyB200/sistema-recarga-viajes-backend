from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.dependencies import get_db, get_redis_client
from pydantic import BaseModel
from typing import List, Optional
import json
import redis

router = APIRouter(prefix="/api/v1/routes", tags=["routes"])

# Pydantic models for response


class RouteStation(BaseModel):
    sequence: int
    station_code: str
    station_name: str
    station_type: str


class RouteDetails(BaseModel):
    route_code: str
    route_name: Optional[str]
    route_type: str
    stations: List[RouteStation]


# Cache TTL
CACHE_TTL_SECONDS = 300  # 5 minutes for route data


@router.get("/codes")
def get_route_codes(
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    """
    Get all route codes for selectors
    """
    cache_key = "routes:codes"

    try:
        # Try to get from cache
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)

        # Get all route codes
        query = text("""
            SELECT DISTINCT route_code 
            FROM routes 
            WHERE is_active = true
            ORDER BY route_code ASC
        """)
        
        results = db.execute(query).fetchall()

        route_codes = [r.route_code for r in results]

        response = {"route_codes": route_codes}

        # Cache the result for 5 minutes
        redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(response))

        return response

    except redis.exceptions.RedisError as e:
        # If Redis fails, just serve from database
        query = text("""
            SELECT DISTINCT route_code 
            FROM routes 
            WHERE is_active = true
            ORDER BY route_code ASC
        """)
        
        results = db.execute(query).fetchall()

        route_codes = [r.route_code for r in results]

        return {"route_codes": route_codes}


@router.get("/{route_code}/details")
def get_route_details(
    route_code: str,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    """
    Get route details including stations in order
    """
    cache_key = f"route:{route_code}:details"

    try:
        # Try to get from cache
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)

        # Get route details
        route_query = text("""
            SELECT route_id, route_code, route_name, route_type 
            FROM routes 
            WHERE route_code = :route_code
            AND is_active = true
        """)
        
        route = db.execute(route_query, {"route_code": route_code}).first()

        if not route:
            raise HTTPException(status_code=404, detail="Route not found")

        # Get stations for this route
        stations_query = text("""
            SELECT s.station_code, s.name as station_name, s.station_type, ist.sequence_order
            FROM intermediate_stations ist
            JOIN stations s ON ist.station_id = s.station_id
            WHERE ist.route_id = :route_id
            ORDER BY ist.sequence_order ASC
        """)
        
        stations_results = db.execute(stations_query, {"route_id": route.route_id}).fetchall()

        stations = [
            {
                "sequence": r.sequence_order,
                "station_code": r.station_code,
                "station_name": r.station_name,
                "station_type": r.station_type
            }
            for r in stations_results
        ]

        response = {
            "route_code": route.route_code,
            "route_name": route.route_name or "",
            "route_type": route.route_type,
            "stations": stations
        }

        # Cache the result for 5 minutes
        redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(response))

        return response

    except redis.exceptions.RedisError as e:
        # If Redis fails, just serve from database
        # Get route details
        route_query = text("""
            SELECT route_id, route_code, route_name, route_type 
            FROM routes 
            WHERE route_code = :route_code
            AND is_active = true
        """)
        
        route = db.execute(route_query, {"route_code": route_code}).first()

        if not route:
            raise HTTPException(status_code=404, detail="Route not found")

        # Get stations for this route
        stations_query = text("""
            SELECT s.station_code, s.name as station_name, s.station_type, ist.sequence_order
            FROM intermediate_stations ist
            JOIN stations s ON ist.station_id = s.station_id
            WHERE ist.route_id = :route_id
            ORDER BY ist.sequence_order ASC
        """)
        
        stations_results = db.execute(stations_query, {"route_id": route.route_id}).fetchall()

        stations = [
            {
                "sequence": r.sequence_order,
                "station_code": r.station_code,
                "station_name": r.station_name,
                "station_type": r.station_type
            }
            for r in stations_results
        ]

        response = {
            "route_code": route.route_code,
            "route_name": route.route_name or "",
            "route_type": route.route_type,
            "stations": stations
        }

        return response 