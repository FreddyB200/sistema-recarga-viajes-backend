import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.database import Base, get_db
from app.dependencies import get_redis_client
import redis

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


def test_get_users_count_empty(client, db_session):
    response = client.get("/api/v1/users/count")
    assert response.status_code == 200
    assert response.json() == {"total_users": 0}


def test_get_users_count_with_data(client, db_session):
    # Insert test data
    db_session.execute("""
        INSERT INTO users (user_id, first_name, last_name, registration_date)
        VALUES (1, 'John', 'Doe', CURRENT_TIMESTAMP)
    """)
    db_session.commit()

    response = client.get("/api/v1/users/count")
    assert response.status_code == 200
    assert response.json() == {"total_users": 1}


def test_get_active_users_count_empty(client, db_session):
    response = client.get("/api/v1/users/active/count")
    assert response.status_code == 200
    assert response.json() == {"active_users_count": 0}


def test_get_active_users_count_with_data(client, db_session):
    # Insert test data
    db_session.execute("""
        INSERT INTO users (user_id, first_name, last_name, registration_date)
        VALUES (1, 'John', 'Doe', CURRENT_TIMESTAMP)
    """)
    db_session.execute("""
        INSERT INTO cards (card_id, user_id, status)
        VALUES (1, 1, 'active')
    """)
    db_session.commit()

    response = client.get("/api/v1/users/active/count")
    assert response.status_code == 200
    assert response.json() == {"active_users_count": 1}


def test_get_latest_user_empty(client, db_session):
    response = client.get("/api/v1/users/latest")
    assert response.status_code == 204


def test_get_latest_user_with_data(client, db_session):
    # Insert test data
    db_session.execute("""
        INSERT INTO users (user_id, first_name, last_name, registration_date)
        VALUES (1, 'John', 'Doe', CURRENT_TIMESTAMP)
    """)
    db_session.commit()

    response = client.get("/api/v1/users/latest")
    assert response.status_code == 200
    assert response.json() == {
        "latest_user": {
            "user_id": 1,
            "full_name": "John Doe"
        }
    }
