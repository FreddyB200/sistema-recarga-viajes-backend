import pytest
from fastapi.testclient import TestClient


def test_get_total_revenue_empty(client, db_session):
    response = client.get("/api/v1/finance/revenue")
    assert response.status_code == 200
    assert response.json() == {"total_revenue": 0.0, "currency": "COP"}


def test_get_total_revenue_with_data(client, db_session):
    # Insert test data
    db_session.execute("""
        INSERT INTO fares (fare_id, value)
        VALUES (1, 2500.0)
    """)
    db_session.execute("""
        INSERT INTO trips (trip_id, user_id, boarding_station_id, fare_id)
        VALUES (1, 1, 1, 1)
    """)
    db_session.commit()

    response = client.get("/api/v1/finance/revenue")
    assert response.status_code == 200
    assert response.json() == {"total_revenue": 2500.0, "currency": "COP"}


def test_get_revenue_by_localities_empty(client, db_session):
    response = client.get("/api/v1/finance/revenue/localities")
    assert response.status_code == 200
    assert response.json() == {"data": [], "currency": "COP"}


def test_get_revenue_by_localities_with_data(client, db_session):
    # Insert test data
    db_session.execute("""
        INSERT INTO locations (location_id, name)
        VALUES (1, 'Test Locality')
    """)
    db_session.execute("""
        INSERT INTO stations (station_id, location_id)
        VALUES (1, 1)
    """)
    db_session.execute("""
        INSERT INTO fares (fare_id, value)
        VALUES (1, 2500.0)
    """)
    db_session.execute("""
        INSERT INTO trips (trip_id, user_id, boarding_station_id, fare_id)
        VALUES (1, 1, 1, 1)
    """)
    db_session.commit()

    response = client.get("/api/v1/finance/revenue/localities")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["locality"] == "Test Locality"
    assert data[0]["total_revenue"] == 2500.0


def test_redis_cache_revenue(client, db_session):
    # First request should hit the database
    response1 = client.get("/api/v1/finance/revenue")
    assert response1.status_code == 200

    # Insert new data
    db_session.execute("""
        INSERT INTO fares (fare_id, value)
        VALUES (1, 2500.0)
    """)
    db_session.execute("""
        INSERT INTO trips (trip_id, user_id, boarding_station_id, fare_id)
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

    # Insert new data
    db_session.execute("""
        INSERT INTO locations (location_id, name)
        VALUES (1, 'Test Locality')
    """)
    db_session.execute("""
        INSERT INTO stations (station_id, location_id)
        VALUES (1, 1)
    """)
    db_session.execute("""
        INSERT INTO fares (fare_id, value)
        VALUES (1, 2500.0)
    """)
    db_session.execute("""
        INSERT INTO trips (trip_id, user_id, boarding_station_id, fare_id)
        VALUES (1, 1, 1, 1)
    """)
    db_session.commit()

    # Second request should still return cached data
    response2 = client.get("/api/v1/finance/revenue/localities")
    assert response2.status_code == 200
    assert response1.json() == response2.json()  # Should be equal due to caching
