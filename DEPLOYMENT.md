# Deployment Guide

This document provides a step-by-step guide to deploy and run the project on any machine.

---

## Prerequisites

Before starting, ensure you have the following installed on your system:

- Python 3.8 or higher
- pip (Python package manager)
- Git
- PostgreSQL (or the database system used by the project)
- Redis (optional, for caching)

---

## Local Setup

Follow these steps to set up and run the project locally:

### Step 1: Clone the Repository

Clone the project repository to your local machine:

```bash
git clone https://github.com/FreddyB200/travel-recharge-api.git
cd travel-recharge-database
```

### Step 2: Configure Environment Variables

Copy the example files to their respective `.env` files:

```bash
cp .env.postgres.example .env.postgres
cp .env.redis.example .env.redis
```

Edit the `.env` files to configure your database and Redis credentials.

### Step 3: Create a Virtual Environment and Install Dependencies

Create a virtual environment:

```bash
python3 -m venv env
```

Activate the virtual environment:

- On Linux/MacOS:
  ```bash
  source env/bin/activate
  ```
- On Windows:
  ```bash
  env\Scripts\activate
  ```

Install the required dependencies:

```bash
pip install -r requirements.txt
```

### Step 4: Run the Application

#### Method 1: FastAPI CLI (Recommended)

Use the FastAPI CLI for development:

```bash
fastapi dev app/main.py --host 0.0.0.0 --port 8000
```

#### Method 2: FastAPI Run

Run the application using FastAPI:

```bash
fastapi run app/main.py --host 0.0.0.0 --port 8000
```

#### Method 3: Uvicorn

Alternatively, you can use Uvicorn:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The application will be available at `http://127.0.0.1:8000`.

---

## Redis Setup

If you are using Redis for caching, ensure Redis is running:

### Option 1: Run Redis Locally

Install Redis on your machine and start the service:

```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis
```

### Option 2: Run Redis in Docker

Run Redis in a Docker container:

```bash
docker run -d --name redis -p 6379:6379 redis:latest
```

---

## Testing the Application

### Cacheable Endpoints
Test the cacheable endpoints using the `latency_test.py` script:

```bash
python latency_test.py
```

### Non-Cacheable Endpoints
Test the non-cacheable endpoints using the `latency_non_cacheable.py` script:

```bash
python latency_non_cacheable.py
```

---

## Documentation

- [API Documentation (Swagger UI)](http://127.0.0.1:8000/docs)
- [API Documentation (ReDoc)](http://127.0.0.1:8000/redoc)

---

## Additional Notes

- Ensure your database is running and accessible with the credentials provided in the `.env` file.
- Use the FastAPI interactive documentation at `http://127.0.0.1:8000/docs` to test the API endpoints.
- If you encounter issues, check the logs for detailed error messages.

---
