from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.dependencies import get_db, get_redis_client
import json
import redis

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("/count")
def get_users_count(
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    cache_key = "users:count"
    
    try:
        # Try to get from cache
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)
        
        # Get from database
        result = db.execute(
            text("SELECT COUNT(*) AS total_users FROM users;")).scalar_one_or_none()
        
        response = {"total_users": result if result is not None else 0}
        
        # Cache for 5 minutes
        redis_client.setex(cache_key, 300, json.dumps(response))
        
        return response
    except redis.exceptions.RedisError as e:
        # If Redis fails, just serve from database
        result = db.execute(
            text("SELECT COUNT(*) AS total_users FROM users;")).scalar_one_or_none()
        return {"total_users": result if result is not None else 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": {
                            "code": "DATABASE_ERROR", "message": f"Error querying the database: {str(e)}"}})


@router.get("/active/count")
def get_active_users_count(
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    cache_key = "users:active:count"
    
    try:
        # Try to get from cache
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)
        
        # We assume an "active user" is a user with at least one 'active' card.
        # Replaced stored procedure call with direct query.
        query = text("""
            SELECT COUNT(DISTINCT u.user_id) AS active_users_count
            FROM users u
            JOIN cards c ON u.user_id = c.user_id
            WHERE c.status = 'active';
        """)
        
        result = db.execute(query).scalar_one_or_none()
        response = {"active_users_count": result if result is not None else 0}
        
        # Cache for 1 minute (more frequent updates for active users)
        redis_client.setex(cache_key, 60, json.dumps(response))
        
        return response
    except redis.exceptions.RedisError as e:
        # If Redis fails, just serve from database
        query = text("""
            SELECT COUNT(DISTINCT u.user_id) AS active_users_count
            FROM users u
            JOIN cards c ON u.user_id = c.user_id
            WHERE c.status = 'active';
        """)
        result = db.execute(query).scalar_one_or_none()
        return {"active_users_count": result if result is not None else 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": {
                            "code": "DATABASE_ERROR", "message": f"Error querying the database: {str(e)}"}})


@router.get("/latest")
def get_latest_user(
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    cache_key = "users:latest"
    
    try:
        # Try to get from cache
        cached_data = redis_client.get(cache_key)
        if cached_data:
            cached_response = json.loads(cached_data)
            if cached_response.get("status") == "no_content":
                return Response(status_code=204)
            return cached_response
        
        query = text("""
            SELECT user_id, first_name, last_name
            FROM users
            ORDER BY registration_date DESC, user_id DESC
            LIMIT 1;
        """)  # Added user_id DESC for deterministic tie-breaker
        
        result = db.execute(query).mappings().first()
        if result:
            full_name = f"{result['first_name']} {result['last_name']}"
            response = {"latest_user": {"user_id": result['user_id'], "full_name": full_name}}
            
            # Cache for 2 minutes
            redis_client.setex(cache_key, 120, json.dumps(response))
            
            return response
        else:
            # Cache the "no content" status too
            redis_client.setex(cache_key, 120, json.dumps({"status": "no_content"}))
            return Response(status_code=204)  # No Content
    except redis.exceptions.RedisError as e:
        # If Redis fails, just serve from database
        query = text("""
            SELECT user_id, first_name, last_name
            FROM users
            ORDER BY registration_date DESC, user_id DESC
            LIMIT 1;
        """)
        result = db.execute(query).mappings().first()
        if result:
            full_name = f"{result['first_name']} {result['last_name']}"
            return {"latest_user": {"user_id": result['user_id'], "full_name": full_name}}
        else:
            return Response(status_code=204)  # No Content
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": {
                            "code": "DATABASE_ERROR", "message": f"Error querying the database: {str(e)}"}})
