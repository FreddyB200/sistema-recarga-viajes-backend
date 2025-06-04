from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.dependencies import get_db

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("/count")
def get_users_count(db: Session = Depends(get_db)):
    try:
        result = db.execute(
            text("SELECT COUNT(*) AS total_users FROM users;")).scalar_one_or_none()
        return {"total_users": result if result is not None else 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": {
                            "code": "DATABASE_ERROR", "message": f"Error querying the database: {str(e)}"}})


@router.get("/active/count")
def get_active_users_count(db: Session = Depends(get_db)):
    # We assume an "active user" is a user with at least one 'active' card.
    # Replaced stored procedure call with direct query.
    query = text("""
        SELECT COUNT(DISTINCT u.user_id) AS active_users_count
        FROM users u
        JOIN cards c ON u.user_id = c.user_id
        WHERE c.status = 'active';
    """)
    try:
        result = db.execute(query).scalar_one_or_none()
        return {"active_users_count": result if result is not None else 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": {
                            "code": "DATABASE_ERROR", "message": f"Error querying the database: {str(e)}"}})


@router.get("/latest")
def get_latest_user(db: Session = Depends(get_db)):
    query = text("""
        SELECT user_id, first_name, last_name
        FROM users
        ORDER BY registration_date DESC, user_id DESC
        LIMIT 1;
    """)  # Added user_id DESC for deterministic tie-breaker
    try:
        result = db.execute(query).mappings().first()
        if result:
            full_name = f"{result['first_name']} {result['last_name']}"
            return {"latest_user": {"user_id": result['user_id'], "full_name": full_name}}
        else:
            return Response(status_code=204)  # No Content
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": {
                            "code": "DATABASE_ERROR", "message": f"Error querying the database: {str(e)}"}})
