from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import engine
from app.dependencies import get_db
from app.routers import users, trips, finance

app = FastAPI(title="Travel Recharge API", version="1.0.0")

# Include routers
app.include_router(users.router)
app.include_router(trips.router)
app.include_router(finance.router)


@app.get("/ping-db")
def ping_db(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "Successful connection"}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": {
                            "code": "DATABASE_CONNECTION_ERROR", "message": f"Database connection error: {str(e)}"}})


@app.get("/")
def root():
    return {"message": "Travel Recharge API", "version": "1.0.0", "docs": "/docs"}
