import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.database import Base, get_db
from app.dependencies import get_redis_client
import json

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine)

# Mock Redis client


class MockRedis:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def setex(self, key, ttl, value):
        self.data[key] = value
        return True

    def ping(self):
        return True


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()

    def override_get_redis():
        return MockRedis()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis_client] = override_get_redis

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_get_total_revenue_empty(client, db_session):
    response = client.get("/api/v1/finance/revenue")
    assert response.status_code == 200
    assert response.json() == {"total_revenue": 0.0}


def test_get_total_revenue_with_data(client, db_session):
    # Insert test data - Fixed: using card_id instead of user_id
    db_session.execute("""
        INSERT INTO fares (fare_id, value, fare_type, start_date)
        VALUES (1, 2.50, 'STANDARD', '2023-01-01')
    """)
    db_session.execute("""
        INSERT INTO trips (trip_id, card_id, boarding_station_id, fare_id)
        VALUES (1, 1, 1, 1)
    """)
    db_session.commit()

    response = client.get("/api/v1/finance/revenue")
    assert response.status_code == 200
    assert response.json() == {"total_revenue": 2.5}


def test_get_revenue_by_localities_empty(client, db_session):
    response = client.get("/api/v1/finance/revenue/localities")
    assert response.status_code == 200
    assert response.json() == {"data": []}


def test_get_revenue_by_localities_with_data(client, db_session):
    # Insert test data - Fixed: using card_id instead of user_id
    db_session.execute("""
        INSERT INTO locations (location_id, name)
        VALUES (1, 'Test Locality')
    """)
    db_session.execute("""
        INSERT INTO stations (station_id, location_id)
        VALUES (1, 1)
    """)
    db_session.execute("""
        INSERT INTO fares (fare_id, value, fare_type, start_date)
        VALUES (1, 2.50, 'STANDARD', '2023-01-01')
    """)
    db_session.execute("""
        INSERT INTO trips (trip_id, card_id, boarding_station_id, fare_id)
        VALUES (1, 1, 1, 1)
    """)
    db_session.commit()

    response = client.get("/api/v1/finance/revenue/localities")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["locality"] == "Test Locality"
    assert data[0]["total_revenue"] == 2.5


def test_redis_cache_revenue(client, db_session):
    # First request should hit the database
    response1 = client.get("/api/v1/finance/revenue")
    assert response1.status_code == 200

    # Insert new data - Fixed: using card_id instead of user_id
    db_session.execute("""
        INSERT INTO fares (fare_id, value, fare_type, start_date)
        VALUES (1, 2.50, 'STANDARD', '2023-01-01')
    """)
    db_session.execute("""
        INSERT INTO trips (trip_id, card_id, boarding_station_id, fare_id)
        VALUES (1, 1, 1, 1)
    """)
    db_session.commit()

    # Second request should still return cached data
    response2 = client.get("/api/v1/finance/revenue")
    assert response2.status_code == 200
    assert response1.json() == response2.json()  # Should be equal due to caching


def test_redis_cache_revenue_localities(client, db_session):
    # First request should hit the database
    response1 = client.get("/api/v1/finance/revenue/localities")
    assert response1.status_code == 200

    # Insert new data - Fixed: using card_id instead of user_id
    db_session.execute("""
        INSERT INTO locations (location_id, name)
        VALUES (1, 'Test Locality')
    """)
    db_session.execute("""
        INSERT INTO stations (station_id, location_id)
        VALUES (1, 1)
    """)
    db_session.execute("""
        INSERT INTO fares (fare_id, value, fare_type, start_date)
        VALUES (1, 2.50, 'STANDARD', '2023-01-01')
    """)
    db_session.execute("""
        INSERT INTO trips (trip_id, card_id, boarding_station_id, fare_id)
        VALUES (1, 1, 1, 1)
    """)
    db_session.commit()

    # Second request should still return cached data
    response2 = client.get("/api/v1/finance/revenue/localities")
    assert response2.status_code == 200
    assert response1.json() == response2.json()  # Should be equal due to caching
