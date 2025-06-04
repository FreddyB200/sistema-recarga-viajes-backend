from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.dependencies import get_db, get_redis_client
import redis
import json
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/api/v1/cards", tags=["cards"])


class CardRecharge(BaseModel):
    card_id: int
    amount: float


class CardBalance(BaseModel):
    card_id: int
    balance: float
    last_used_date: Optional[datetime]
    status: str


class RechargeHistory(BaseModel):
    recharge_id: int
    card_id: int
    amount: float
    recharge_timestamp: datetime


# Cache TTL
CACHE_TTL_SECONDS = 300  # 5 minutes for card data


@router.post("/recharge")
def recharge_card(
    recharge: CardRecharge,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    try:
        # Check if card exists and is active
        card_query = text("""
            SELECT status FROM cards WHERE card_id = :card_id
        """)
        card = db.execute(card_query, {"card_id": recharge.card_id}).first()

        if not card:
            raise HTTPException(status_code=404, detail="Card not found")
        if card.status != "active":
            raise HTTPException(status_code=400, detail="Card is not active")

        # Insert recharge record (matching schema: no payment_method, use recharge_timestamp)
        recharge_query = text("""
            INSERT INTO recharges (card_id, amount, recharge_timestamp)
            VALUES (:card_id, :amount, CURRENT_TIMESTAMP)
            RETURNING recharge_id, recharge_timestamp
        """)
        result = db.execute(
            recharge_query,
            {
                "card_id": recharge.card_id,
                "amount": recharge.amount
            }
        ).first()

        # Update card balance and last_used_date
        update_query = text("""
            UPDATE cards 
            SET balance = balance + :amount,
                last_used_date = CURRENT_TIMESTAMP,
                update_date = CURRENT_DATE
            WHERE card_id = :card_id
            RETURNING balance
        """)
        new_balance = db.execute(
            update_query,
            {
                "card_id": recharge.card_id,
                "amount": recharge.amount
            }
        ).scalar_one()

        db.commit()

        # Invalidate cache
        redis_client.delete(f"card:{recharge.card_id}:balance")
        redis_client.delete(f"card:{recharge.card_id}:history")

        return {
            "recharge_id": result.recharge_id,
            "card_id": recharge.card_id,
            "amount": recharge.amount,
            "new_balance": new_balance,
            "recharge_timestamp": result.recharge_timestamp.isoformat()
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{card_id}/balance")
def get_card_balance(
    card_id: int,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    cache_key = f"card:{card_id}:balance"

    try:
        # Try to get from cache
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)

        # Query database (matching schema fields)
        query = text("""
            SELECT card_id, balance, last_used_date, status
            FROM cards
            WHERE card_id = :card_id
        """)
        result = db.execute(query, {"card_id": card_id}).first()

        if not result:
            raise HTTPException(status_code=404, detail="Card not found")

        response = {
            "card_id": result.card_id,
            "balance": float(result.balance),
            "last_used_date": result.last_used_date.isoformat() if result.last_used_date else None,
            "status": result.status
        }

        # Cache the result
        redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(response))

        return response

    except redis.exceptions.RedisError as e:
        # If Redis fails, just serve from database
        query = text("""
            SELECT card_id, balance, last_used_date, status
            FROM cards
            WHERE card_id = :card_id
        """)
        result = db.execute(query, {"card_id": card_id}).first()

        if not result:
            raise HTTPException(status_code=404, detail="Card not found")

        return {
            "card_id": result.card_id,
            "balance": float(result.balance),
            "last_used_date": result.last_used_date.isoformat() if result.last_used_date else None,
            "status": result.status
        }


@router.get("/{card_id}/history")
def get_card_history(
    card_id: int,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    cache_key = f"card:{card_id}:history"

    try:
        # Try to get from cache
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)

        # Query database (matching schema: use recharge_timestamp, no payment_method)
        query = text("""
            SELECT recharge_id, card_id, amount, recharge_timestamp
            FROM recharges
            WHERE card_id = :card_id
            ORDER BY recharge_timestamp DESC
            LIMIT 10
        """)
        results = db.execute(query, {"card_id": card_id}).fetchall()

        if not results:
            return {"history": []}

        history = [
            {
                "recharge_id": r.recharge_id,
                "card_id": r.card_id,
                "amount": float(r.amount),
                "recharge_timestamp": r.recharge_timestamp.isoformat()
            }
            for r in results
        ]

        response = {"history": history}

        # Cache the result
        redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(response))

        return response

    except redis.exceptions.RedisError as e:
        # If Redis fails, just serve from database
        query = text("""
            SELECT recharge_id, card_id, amount, recharge_timestamp
            FROM recharges
            WHERE card_id = :card_id
            ORDER BY recharge_timestamp DESC
            LIMIT 10
        """)
        results = db.execute(query, {"card_id": card_id}).fetchall()

        if not results:
            return {"history": []}

        history = [
            {
                "recharge_id": r.recharge_id,
                "card_id": r.card_id,
                "amount": float(r.amount),
                "recharge_timestamp": r.recharge_timestamp.isoformat()
            }
            for r in results
        ]

        return {"history": history}
