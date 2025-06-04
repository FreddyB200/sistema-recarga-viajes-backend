import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from unittest.mock import Mock
from app.main import app
from app.dependencies import get_db, get_redis_client

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_cards.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={
                       "check_same_thread": False})
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


def override_get_redis_client():
    return Mock()


app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_redis_client] = override_get_redis_client

client = TestClient(app)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    # Create tables
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS cards (
            card_id INTEGER PRIMARY KEY,
            status TEXT DEFAULT 'active',
            balance REAL DEFAULT 0.0,
            last_used_date TIMESTAMP,
            update_date DATE DEFAULT CURRENT_DATE
        )
    """))

    db.execute(text("""
        CREATE TABLE IF NOT EXISTS recharges (
            recharge_id INTEGER PRIMARY KEY,
            card_id INTEGER,
            amount REAL,
            recharge_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))

    # Insert test data
    db.execute(
        text("INSERT INTO cards (card_id, status, balance) VALUES (1, 'active', 50.0)"))
    db.execute(
        text("INSERT INTO cards (card_id, status, balance) VALUES (2, 'inactive', 0.0)"))
    db.commit()

    yield db

    # Cleanup
    db.execute(text("DROP TABLE IF EXISTS cards"))
    db.execute(text("DROP TABLE IF EXISTS recharges"))
    db.commit()
    db.close()


def test_recharge_card_success(client, db_session):
    response = client.post("/api/v1/cards/recharge", json={
        "card_id": 1,
        "amount": 25.0
    })

    assert response.status_code == 200
    data = response.json()
    assert data["card_id"] == 1
    assert data["amount"] == 25.0
    assert data["new_balance"] == 75.0
    assert "recharge_timestamp" in data


def test_recharge_card_not_found(client, db_session):
    response = client.post("/api/v1/cards/recharge", json={
        "card_id": 999,
        "amount": 25.0
    })

    assert response.status_code == 404
    assert "Card not found" in response.json()["detail"]


def test_recharge_inactive_card(client, db_session):
    response = client.post("/api/v1/cards/recharge", json={
        "card_id": 2,
        "amount": 25.0
    })

    assert response.status_code == 400
    assert "Card is not active" in response.json()["detail"]


def test_get_card_balance_success(client, db_session):
    response = client.get("/api/v1/cards/1/balance")

    assert response.status_code == 200
    data = response.json()
    assert data["card_id"] == 1
    assert data["balance"] == 50.0
    assert data["status"] == "active"


def test_get_card_balance_not_found(client, db_session):
    response = client.get("/api/v1/cards/999/balance")

    assert response.status_code == 404
    assert "Card not found" in response.json()["detail"]


def test_get_card_history_empty(client, db_session):
    response = client.get("/api/v1/cards/1/history")

    assert response.status_code == 200
    data = response.json()
    assert data["history"] == []


def test_get_card_history_with_data(client, db_session):
    # Add some recharge history
    db_session.execute(text("""
        INSERT INTO recharges (card_id, amount, recharge_timestamp)
        VALUES (1, 20.0, '2023-01-01 10:00:00')
    """))
    db_session.execute(text("""
        INSERT INTO recharges (card_id, amount, recharge_timestamp)
        VALUES (1, 30.0, '2023-01-01 11:00:00')
    """))
    db_session.commit()

    response = client.get("/api/v1/cards/1/history")

    assert response.status_code == 200
    data = response.json()
    assert len(data["history"]) == 2

    # Should be ordered by timestamp DESC
    first_recharge = data["history"][0]
    assert first_recharge["amount"] == 30.0
    assert "recharge_timestamp" in first_recharge

    second_recharge = data["history"][1]
    assert second_recharge["amount"] == 20.0


def test_get_card_history_not_found(client, db_session):
    response = client.get("/api/v1/cards/999/history")

    assert response.status_code == 200
    data = response.json()
    assert data["history"] == []
