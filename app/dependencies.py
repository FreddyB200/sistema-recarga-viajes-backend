
import redis.exceptions
from database import SessionLocal\

import redis
import os
from fastapi import HTTPException
from dotenv import load_dotenv

load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST", "192.168.100.2O") #redis vm IP
REDIS_PORT = int(os.getenv("REDIS_PORT", 6340))

redis_client_instance = None #every client's Global variable

try:
    #
    temp_redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=0,
        decode_responses=True #Very important: decodes reponses to string bytes
    )
    temp_redis_client.ping() #ping to verify the connection 
    redis_client_instance = temp_redis_client
    print(f"Succefully connected to Redis in {REDIS_HOST}:{REDIS_PORT}")
except redis.exceptions.ConnectionError as e:
    print(f"ALERT: cannot connect to Redis at starting the application: {e}")
    # App contnues but redis_client_instance would be None
    # The enpoints that depends on redis would be able o handle this.
except Exception as e:
    print(f"ALERT: An unexpected error has happenend at configuring redis: {e}")

def get_redis_client():
    """Dpendecia de FastAPI para obtener el cliente de Redis.
    Laanza una excepcion si e cliente no esta disponible."""

    if redis_client_instance is None:
        raise HTTPException(status_code=503, detail="Cache service (Redis) not avaliable, the connection has failed starting.")
    
    return redis_client_instance

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
