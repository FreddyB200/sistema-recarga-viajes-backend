from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import engine
from app.dependencies import get_db, get_redis_client
from app.routers import users, trips, finance

app = FastAPI(title="Travel Recharge API", version="1.0.0")

# Include routers
app.include_router(users.router)
app.include_router(trips.router)
app.include_router(finance.router)


@app.get("/api/v1/health")
def health_check():
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/api/v1/health/db")
def ping_db(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "Database connection successful"}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": {
                            "code": "DATABASE_CONNECTION_ERROR", "message": f"Database connection error: {str(e)}"}})


@app.get("/api/v1/health/cache")
def ping_cache(redis_client=Depends(get_redis_client)):
    try:
        redis_client.ping()
        return {"status": "Cache connection successful"}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": {
                            "code": "CACHE_CONNECTION_ERROR", "message": f"Cache connection error: {str(e)}"}})


@app.get("/")
def root():
    return {"message": "Travel Recharge API", "version": "1.0.0", "docs": "/docs"}
