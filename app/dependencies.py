import redis.exceptions
from database import SessionLocal

import redis
import os
from fastapi import HTTPException
from dotenv import load_dotenv

load_dotenv(".env.redis")

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1") #redis vm IP
REDIS_PORT = int(os.getenv("REDIS_PORT", 6340))

redis_client_instance = None # Global variable for the Redis client instance

try:
    #
    temp_redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=0,
        decode_responses=True # Decodes responses from bytes to strings
    )
    temp_redis_client.ping() # Ping to verify the connection
    redis_client_instance = temp_redis_client
    print(f"Successfully connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
except redis.exceptions.ConnectionError as e:
    print(f"ALERT: Cannot connect to Redis during application startup: {e}")
    # App continues but redis_client_instance would be None
    # The endpoints that depend on Redis will handle this gracefully.
except Exception as e:
    print(f"ALERT: An unexpected error occurred while configuring Redis: {e}")

def get_redis_client():
    """FastAPI dependency to get the Redis client.
    Raises an exception if the client is not available."""

    if redis_client_instance is None:
        raise HTTPException(status_code=503, detail="Cache service (Redis) not available; the connection failed during startup.")

    return redis_client_instance

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
