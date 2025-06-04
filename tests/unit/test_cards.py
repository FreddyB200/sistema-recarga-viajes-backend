import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from datetime import datetime


def test_recharge_card_success(client: TestClient, db_session):
    # Insert test card
    db_session.execute(
        text("""
            INSERT INTO cards (card_id, balance, status)
            VALUES (1, 0.0, 'active')
        """)
    )
    db_session.commit()

    # Test recharge
    response = client.post(
        "/api/v1/cards/recharge",
        json={
            "card_id": 1,
            "amount": 50.0,
            "payment_method": "credit_card"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["card_id"] == 1
    assert data["amount"] == 50.0
    assert data["new_balance"] == 50.0
    assert "recharge_id" in data
    assert "timestamp" in data


def test_recharge_card_not_found(client: TestClient):
    response = client.post(
        "/api/v1/cards/recharge",
        json={
            "card_id": 999,
            "amount": 50.0,
            "payment_method": "credit_card"
        }
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Card not found"


def test_recharge_card_inactive(client: TestClient, db_session):
    # Insert inactive card
    db_session.execute(
        text("""
            INSERT INTO cards (card_id, balance, status)
            VALUES (2, 0.0, 'inactive')
        """)
    )
    db_session.commit()

    response = client.post(
        "/api/v1/cards/recharge",
        json={
            "card_id": 2,
            "amount": 50.0,
            "payment_method": "credit_card"
        }
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Card is not active"


def test_get_card_balance_success(client: TestClient, db_session):
    # Insert test card
    db_session.execute(
        text("""
            INSERT INTO cards (card_id, balance, status, last_recharge)
            VALUES (3, 100.0, 'active', CURRENT_TIMESTAMP)
        """)
    )
    db_session.commit()

    response = client.get("/api/v1/cards/3/balance")

    assert response.status_code == 200
    data = response.json()
    assert data["card_id"] == 3
    assert data["balance"] == 100.0
    assert data["status"] == "active"
    assert "last_recharge" in data


def test_get_card_balance_not_found(client: TestClient):
    response = client.get("/api/v1/cards/999/balance")

    assert response.status_code == 404
    assert response.json()["detail"] == "Card not found"


def test_get_card_history_success(client: TestClient, db_session):
    # Insert test card and recharges
    db_session.execute(
        text("""
            INSERT INTO cards (card_id, balance, status)
            VALUES (4, 150.0, 'active')
        """)
    )

    db_session.execute(
        text("""
            INSERT INTO recharges (card_id, amount, payment_method, timestamp)
            VALUES 
                (4, 50.0, 'credit_card', CURRENT_TIMESTAMP),
                (4, 100.0, 'debit_card', CURRENT_TIMESTAMP)
        """)
    )
    db_session.commit()

    response = client.get("/api/v1/cards/4/history")

    assert response.status_code == 200
    data = response.json()
    assert "history" in data
    assert len(data["history"]) == 2

    # Verify first recharge
    first_recharge = data["history"][0]
    assert first_recharge["card_id"] == 4
    assert first_recharge["amount"] == 100.0
    assert first_recharge["payment_method"] == "debit_card"
    assert "timestamp" in first_recharge


def test_get_card_history_empty(client: TestClient, db_session):
    # Insert test card without recharges
    db_session.execute(
        text("""
            INSERT INTO cards (card_id, balance, status)
            VALUES (5, 0.0, 'active')
        """)
    )
    db_session.commit()

    response = client.get("/api/v1/cards/5/history")

    assert response.status_code == 200
    data = response.json()
    assert "history" in data
    assert len(data["history"]) == 0


def test_redis_cache_card_balance(client: TestClient, db_session):
    # Insert test card
    db_session.execute(
        text("""
            INSERT INTO cards (card_id, balance, status)
            VALUES (6, 200.0, 'active')
        """)
    )
    db_session.commit()

    # First request - should hit database
    response1 = client.get("/api/v1/cards/6/balance")
    assert response1.status_code == 200

    # Update balance in database
    db_session.execute(
        text("""
            UPDATE cards SET balance = 300.0 WHERE card_id = 6
        """)
    )
    db_session.commit()

    # Second request - should return cached data
    response2 = client.get("/api/v1/cards/6/balance")
    assert response2.status_code == 200
    assert response2.json()["balance"] == 200.0  # Still old value from cache


def test_redis_cache_card_history(client: TestClient, db_session):
    # Insert test card and recharge
    db_session.execute(
        text("""
            INSERT INTO cards (card_id, balance, status)
            VALUES (7, 100.0, 'active')
        """)
    )

    db_session.execute(
        text("""
            INSERT INTO recharges (card_id, amount, payment_method, timestamp)
            VALUES (7, 100.0, 'credit_card', CURRENT_TIMESTAMP)
        """)
    )
    db_session.commit()

    # First request - should hit database
    response1 = client.get("/api/v1/cards/7/history")
    assert response1.status_code == 200
    assert len(response1.json()["history"]) == 1

    # Add new recharge
    db_session.execute(
        text("""
            INSERT INTO recharges (card_id, amount, payment_method, timestamp)
            VALUES (7, 50.0, 'debit_card', CURRENT_TIMESTAMP)
        """)
    )
    db_session.commit()

    # Second request - should return cached data
    response2 = client.get("/api/v1/cards/7/history")
    assert response2.status_code == 200
    assert len(response2.json()["history"]) == 1  # Still old data from cache
