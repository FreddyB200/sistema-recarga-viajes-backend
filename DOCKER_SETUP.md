# Docker Setup Guide - Travel Recharge API

This guide provides instructions for running the entire Travel Recharge API stack (API, PostgreSQL, Redis) on a single host using Docker Compose. This is ideal for development and testing.

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Git

### 1. Clone the API Repository
```bash
git clone https://github.com/FreddyB200/travel-recharge-api.git
cd travel-recharge-api
```

### 2. Prepare Database Initialization Scripts
For this single-host setup, the PostgreSQL container will initialize itself using SQL scripts placed in the `./database` directory of this API repository.

**Action:**
1. Clone the `travel-recharge-database` repository to a temporary location:
    ```bash
    cd ..  # Go up one level from travel-recharge-api
    git clone https://github.com/FreddyB200/travel-recharge-database.git temp-db-repo
    ```
2. Copy all `.sql` files from the database repository to the API's database directory:
    ```bash
    cp temp-db-repo/db/data/*.sql travel-recharge-api/database/
    ```
3. Clean up the temporary repository:
    ```bash
    rm -rf temp-db-repo
    cd travel-recharge-api  # Return to the API directory
    ```

**Note:** The `docker-compose.yml` is configured to run any `.sql`, `.sh`, or `.sql.gz` files found in the `./database` directory when the PostgreSQL container starts.

### 3. Configure Environment Variables
1.  Copy the example environment file:
    ```bash
    cp docker.env.example docker.env
    ```
2.  Edit `docker.env` and ensure the following are set correctly:
    *   `DB_HOST=postgres` (this is the service name in `docker-compose.yml`)
    *   `DB_PORT=5432` (internal port for API to connect to DB container)
    *   `DB_NAME=travel_recharge_db`
    *   `DB_USER=travel_user`
    *   `DB_PASSWORD=travel_password` (this will also be used by the PostgreSQL container for initialization)
    *   `REDIS_HOST=redis`
    *   `REDIS_PORT=6379`
    *   You can also set `DB_PORT_HOST` if you want to expose PostgreSQL on a different host port (e.g., `DB_PORT_HOST=5433`).

### 4. Start All Services
```bash
# This will build the API image and start all services (PostgreSQL, Redis, API)
docker-compose up -d --build

# View logs to check for errors during startup
docker-compose logs -f

# Check service status
docker-compose ps
```

### 5. Access the API
- **API Documentation (Swagger):** http://localhost:8000/docs (or `http://localhost:${API_PORT_HOST}/docs` if you changed `API_PORT_HOST`)
- **API Documentation (ReDoc):** http://localhost:8000/redoc
- **API Base URL:** http://localhost:8000

### 6. Test the API
```bash
# Test database connection (should now work)
curl http://localhost:8000/ping-db

# Test other endpoints like:
curl http://localhost:8000/users/count
curl http://localhost:8000/finance/revenue
```

## 🛠️ Development

### Environment Variables
As configured in Step 3, all necessary variables are in `docker.env`. The `docker-compose.yml` uses these for both the API container and to set up the PostgreSQL container.

### Rebuilding the API
If you make changes to the API code in the `./app` directory:
```bash
# Rebuild and restart only the API service
docker-compose up -d --no-deps --build api

# Or to rebuild everything and restart all services:
docker-compose down
docker-compose up -d --build
```

## 🔧 Troubleshooting

### Database Initialization Issues
*   **Error: relation "xxx" does not exist:** This usually means the database schema was not created. Check the logs of the `travel_postgres` container (`docker-compose logs postgres`). Ensure your SQL scripts in the `./database` directory are correct and were executed.
*   **PostgreSQL container not starting:** Check `docker-compose logs postgres`. Common issues include problems with SQL files in `./database` or port conflicts if `DB_PORT_HOST` is already in use.

### API Connection Issues
*   Ensure `DB_HOST` in `docker.env` is `postgres`.
*   Ensure `DB_PASSWORD` in `docker.env` matches the password the PostgreSQL container is using (it also gets this from `docker.env`).

### General
```bash
# Check logs for specific service
docker-compose logs postgres
docker-compose logs redis
docker-compose logs api

# Restart services
docker-compose restart
```

## 🧹 Cleanup

```bash
# Stop all services
docker-compose down

# Remove all data (volumes)
docker-compose down -v

# Remove all images (optional)
# docker-compose down --rmi all
```

## 📊 Monitoring

### Check Resource Usage
```bash
docker stats
```

### Health Checks
All services include health checks. Check status with:
```bash
docker-compose ps
```

### Latency Tests
The repository includes two scripts to test API latency. Since these scripts need to be run on the host machine (not in Docker), we'll set up a Python virtual environment:

1. **Set up Python virtual environment:**
```bash
# Make sure you are in the travel-recharge-api directory
python3 -m venv venv

# Activate the virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows (WSL):
source venv/bin/activate
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Install test dependencies (only what's needed for latency tests)
pip install -r requirements-test.txt
```

2. **Run the tests:**
   - **Cacheable Endpoints Test** (`scripts/latency_test.py`):
     - Tests endpoints that use Redis caching
     - Available endpoints:
       - `/trips/total`
       - `/trips/total/localities`
       - `/finance/revenue`
       - `/finance/revenue/localities`

   - **Non-Cacheable Endpoints Test** (`scripts/latency_non_cacheable.py`):
     - Tests endpoints that don't use caching
     - Available endpoints:
       - `/users/count`
       - `/users/active/count`
       - `/users/latest`

```bash
# Make sure your virtual environment is activated
# Run cacheable endpoints test
python3 scripts/latency_test.py

# Run non-cacheable endpoints test
python3 scripts/latency_non_cacheable.py
```

Each test will:
1. Show available endpoints
2. Let you choose an endpoint or test all endpoints
3. Ask for the number of iterations
4. Show detailed statistics for each request:
   - Minimum, maximum, and average latency
   - Median latency and standard deviation
   - Success rate and HTTP status codes
   - Any errors that occurred
5. Option to save results to a JSON file

**Note:** 
- The first request to a cacheable endpoint will be slower as it needs to fetch from the database. Subsequent requests should be faster due to Redis caching.
- When you're done testing, you can deactivate the virtual environment by typing `deactivate`
- If you need to run the tests again later, just activate the virtual environment again with `source venv/bin/activate` (Linux/macOS/WSL) or `.\venv\Scripts\Activate.ps1` (Windows PowerShell)

## 🔄 Comparison with Distributed Setup

This `DOCKER_SETUP.md` guide focuses on a single-host setup. For deploying services across multiple Virtual Machines (a distributed setup), please refer to the [DEPLOYMENT.md](deployment.md) guide. This single-host setup is simpler and does **not** require running `docker-compose` in the `travel-recharge-database` repository separately. 