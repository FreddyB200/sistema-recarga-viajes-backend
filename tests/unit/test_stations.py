import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from datetime import datetime, timedelta


def test_list_stations_all(client: TestClient, db_session):
    # Insert test stations
    db_session.execute(
        text("""
            INSERT INTO stations (station_id, name, locality, status, capacity, current_occupancy)
            VALUES 
                (1, 'Station A', 'Locality 1', 'active', 100, 50),
                (2, 'Station B', 'Locality 1', 'active', 150, 75),
                (3, 'Station C', 'Locality 2', 'maintenance', 200, 0)
        """)
    )
    db_session.commit()

    response = client.get("/api/v1/stations/")

    assert response.status_code == 200
    data = response.json()
    assert "stations" in data
    assert len(data["stations"]) == 3

    # Verify first station
    first_station = data["stations"][0]
    assert first_station["name"] == "Station A"
    assert first_station["locality"] == "Locality 1"
    assert first_station["status"] == "active"
    assert first_station["capacity"] == 100
    assert first_station["current_occupancy"] == 50


def test_list_stations_by_locality(client: TestClient, db_session):
    # Insert test stations
    db_session.execute(
        text("""
            INSERT INTO stations (station_id, name, locality, status, capacity, current_occupancy)
            VALUES 
                (1, 'Station A', 'Locality 1', 'active', 100, 50),
                (2, 'Station B', 'Locality 1', 'active', 150, 75),
                (3, 'Station C', 'Locality 2', 'maintenance', 200, 0)
        """)
    )
    db_session.commit()

    response = client.get("/api/v1/stations/?locality=Locality 1")

    assert response.status_code == 200
    data = response.json()
    assert "stations" in data
    assert len(data["stations"]) == 2

    # Verify all stations are from Locality 1
    for station in data["stations"]:
        assert station["locality"] == "Locality 1"


def test_list_stations_by_status(client: TestClient, db_session):
    # Insert test stations
    db_session.execute(
        text("""
            INSERT INTO stations (station_id, name, locality, status, capacity, current_occupancy)
            VALUES 
                (1, 'Station A', 'Locality 1', 'active', 100, 50),
                (2, 'Station B', 'Locality 1', 'active', 150, 75),
                (3, 'Station C', 'Locality 2', 'maintenance', 200, 0)
        """)
    )
    db_session.commit()

    response = client.get("/api/v1/stations/?status=maintenance")

    assert response.status_code == 200
    data = response.json()
    assert "stations" in data
    assert len(data["stations"]) == 1

    # Verify station is in maintenance
    station = data["stations"][0]
    assert station["name"] == "Station C"
    assert station["status"] == "maintenance"


def test_get_station_arrivals_success(client: TestClient, db_session):
    # Insert test station
    db_session.execute(
        text("""
            INSERT INTO stations (station_id, name, locality, status, capacity, current_occupancy)
            VALUES (1, 'Station A', 'Locality 1', 'active', 100, 50)
        """)
    )

    # Insert test arrivals
    now = datetime.utcnow()
    db_session.execute(
        text("""
            INSERT INTO arrivals (station_id, line, destination, estimated_arrival, status)
            VALUES 
                (1, 'Line 1', 'Destination A', :time1, 'on_time'),
                (1, 'Line 2', 'Destination B', :time2, 'delayed')
        """),
        {
            "time1": now + timedelta(minutes=5),
            "time2": now + timedelta(minutes=10)
        }
    )
    db_session.commit()

    response = client.get("/api/v1/stations/1/arrivals")

    assert response.status_code == 200
    data = response.json()
    assert "arrivals" in data
    assert len(data["arrivals"]) == 2

    # Verify first arrival
    first_arrival = data["arrivals"][0]
    assert first_arrival["station_id"] == 1
    assert first_arrival["line"] == "Line 1"
    assert first_arrival["destination"] == "Destination A"
    assert first_arrival["status"] == "on_time"
    assert "estimated_arrival" in first_arrival


def test_get_station_arrivals_not_found(client: TestClient):
    response = client.get("/api/v1/stations/999/arrivals")

    assert response.status_code == 404
    assert response.json()["detail"] == "Station not found"


def test_get_station_alerts_success(client: TestClient, db_session):
    # Insert test station
    db_session.execute(
        text("""
            INSERT INTO stations (station_id, name, locality, status, capacity, current_occupancy)
            VALUES (1, 'Station A', 'Locality 1', 'active', 100, 50)
        """)
    )

    # Insert test alerts
    now = datetime.utcnow()
    db_session.execute(
        text("""
            INSERT INTO alerts (station_id, type, message, severity, start_time, end_time)
            VALUES 
                (1, 'maintenance', 'Scheduled maintenance', 'low', :time1, :time2),
                (1, 'incident', 'Technical issues', 'high', :time3, NULL)
        """),
        {
            "time1": now - timedelta(hours=1),
            "time2": now + timedelta(hours=1),
            "time3": now - timedelta(minutes=30)
        }
    )
    db_session.commit()

    response = client.get("/api/v1/stations/1/alerts")

    assert response.status_code == 200
    data = response.json()
    assert "alerts" in data
    assert len(data["alerts"]) == 2

    # Verify first alert
    first_alert = data["alerts"][0]
    assert first_alert["station_id"] == 1
    assert first_alert["type"] == "incident"
    assert first_alert["message"] == "Technical issues"
    assert first_alert["severity"] == "high"
    assert "start_time" in first_alert
    assert first_alert["end_time"] is None


def test_get_station_alerts_not_found(client: TestClient):
    response = client.get("/api/v1/stations/999/alerts")

    assert response.status_code == 404
    assert response.json()["detail"] == "Station not found"


def test_get_station_alerts_active_only(client: TestClient, db_session):
    # Insert test station
    db_session.execute(
        text("""
            INSERT INTO stations (station_id, name, locality, status, capacity, current_occupancy)
            VALUES (1, 'Station A', 'Locality 1', 'active', 100, 50)
        """)
    )

    # Insert test alerts
    now = datetime.utcnow()
    db_session.execute(
        text("""
            INSERT INTO alerts (station_id, type, message, severity, start_time, end_time)
            VALUES 
                (1, 'maintenance', 'Scheduled maintenance', 'low', :time1, :time2),
                (1, 'incident', 'Technical issues', 'high', :time3, NULL)
        """),
        {
            "time1": now - timedelta(hours=2),
            "time2": now - timedelta(hours=1),  # Expired alert
            "time3": now - timedelta(minutes=30)
        }
    )
    db_session.commit()

    response = client.get("/api/v1/stations/1/alerts?active_only=true")

    assert response.status_code == 200
    data = response.json()
    assert "alerts" in data
    assert len(data["alerts"]) == 1  # Only the active alert

    # Verify alert
    alert = data["alerts"][0]
    assert alert["type"] == "incident"
    assert alert["end_time"] is None


def test_redis_cache_stations_list(client: TestClient, db_session):
    # Insert test station
    db_session.execute(
        text("""
            INSERT INTO stations (station_id, name, locality, status, capacity, current_occupancy)
            VALUES (1, 'Station A', 'Locality 1', 'active', 100, 50)
        """)
    )
    db_session.commit()

    # First request - should hit database
    response1 = client.get("/api/v1/stations/")
    assert response1.status_code == 200
    assert len(response1.json()["stations"]) == 1

    # Add new station
    db_session.execute(
        text("""
            INSERT INTO stations (station_id, name, locality, status, capacity, current_occupancy)
            VALUES (2, 'Station B', 'Locality 1', 'active', 150, 75)
        """)
    )
    db_session.commit()

    # Second request - should return cached data
    response2 = client.get("/api/v1/stations/")
    assert response2.status_code == 200
    assert len(response2.json()["stations"]) == 1  # Still old data from cache


def test_redis_cache_station_arrivals(client: TestClient, db_session):
    # Insert test station
    db_session.execute(
        text("""
            INSERT INTO stations (station_id, name, locality, status, capacity, current_occupancy)
            VALUES (1, 'Station A', 'Locality 1', 'active', 100, 50)
        """)
    )

    # Insert test arrival
    now = datetime.utcnow()
    db_session.execute(
        text("""
            INSERT INTO arrivals (station_id, line, destination, estimated_arrival, status)
            VALUES (1, 'Line 1', 'Destination A', :time1, 'on_time')
        """),
        {"time1": now + timedelta(minutes=5)}
    )
    db_session.commit()

    # First request - should hit database
    response1 = client.get("/api/v1/stations/1/arrivals")
    assert response1.status_code == 200
    assert len(response1.json()["arrivals"]) == 1

    # Add new arrival
    db_session.execute(
        text("""
            INSERT INTO arrivals (station_id, line, destination, estimated_arrival, status)
            VALUES (1, 'Line 2', 'Destination B', :time1, 'delayed')
        """),
        {"time1": now + timedelta(minutes=10)}
    )
    db_session.commit()

    # Second request - should return cached data
    response2 = client.get("/api/v1/stations/1/arrivals")
    assert response2.status_code == 200
    assert len(response2.json()["arrivals"]) == 1  # Still old data from cache
