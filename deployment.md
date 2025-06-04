# Deployment and Setup Guide for Travel Recharge API

This guide provides detailed instructions for deploying the Travel Recharge API in two different ways:

1. **Single Host Deployment (Docker Compose)**
   - All services run on one machine
   - Perfect for development and testing
   - See [DOCKER_SETUP.md](DOCKER_SETUP.md) for detailed instructions

2. **Distributed Deployment (Multiple VMs)**
   - Services run on separate virtual machines
   - Simulates a real distributed environment
   - Instructions below

## 📖 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Setup Order Overview](#setup-order-overview)
3. [Step 1: Setup the PostgreSQL Database](#step-1-setup-the-postgresql-database)
4. [Step 2: Setup Redis](#step-2-setup-redis)
5. [Step 3: Setup the API Application](#step-3-setup-the-api-application)
6. [Step 4: Run the API Application](#step-4-run-the-api-application)
7. [Troubleshooting Common Issues](#troubleshooting-common-issues)

---

## 1. Prerequisites

Before you begin, ensure your system meets the following requirements:

* **General Development Tools:**
    * Git & a GitHub account
    * Python 3.8 or higher
    * `pip` (Python package manager) and `venv` (for virtual environments)
* **For the PostgreSQL Database:**
    * Docker and Docker Compose
* **For Redis:**
    * Docker (recommended) or native installation
* **For the distributed setup:**
    * VirtualBox (or your preferred virtualization software)
    * Ability to create and manage Linux VMs (Ubuntu/Alpine recommended)
    * Docker & Docker Compose installed on each VM
    * SSH keys configured for password-less login to VMs (recommended)

---

## 2. Setup Order Overview

For the API to function correctly, services must be set up in the following order:
1. **PostgreSQL Database:** This is the primary data store.
2. **Redis:** This is used for caching.
3. **Travel Recharge API:** This application connects to both PostgreSQL and Redis.

---

## 3. Step 1: Setup the PostgreSQL Database

The PostgreSQL database for this project is managed in a **separate repository**. It **must be set up and running before proceeding with the API setup.**

```bash
# Clone the database repository
git clone https://github.com/FreddyB200/travel-recharge-database.git
cd travel-recharge-database

# Configure environment variables
cp .env.template .env
# Edit .env with correct values

# Start the database
docker-compose up -d
```

Verify the database is running:
```bash
docker-compose ps
```

---

## 4. Step 2: Setup Redis

You need a Redis instance running and accessible to the API. Choose one of the following options:

### Option A: Install Redis Natively

* **Debian/Ubuntu:**
    ```bash
    sudo apt update
    sudo apt install redis-server -y
    sudo systemctl enable redis-server --now
    ```
* **Alpine Linux:**
    ```bash
    apk update
    apk add redis
    rc-update add redis
    rc-service redis start
    ```
* **Verify Installation:**
    ```bash
    redis-cli ping
    ```
    This command should respond with `PONG`.

### Option B: Run Redis with Docker

```bash
docker run -d --name redis-cache -p 6379:6379 redis:latest
```
* **Verify Installation:**
```bash
docker exec redis-cache redis-cli ping
```
This command should respond with PONG.

## 5. Step 3: Setup the API Application

### Clone the API Repository
```bash
git clone https://github.com/FreddyB200/travel-recharge-api.git
cd travel-recharge-api
```

### Configure Environment Variables
1. **Copy the example environment file:**
    ```bash
    cp docker.env.example docker.env
    ```

2. **Edit `docker.env` with your settings:**
    * **`DB_HOST`**: IP address or hostname of your PostgreSQL server
    * **`DB_PORT`**: Port for PostgreSQL (default `5432`)
    * **`DB_NAME`**: Database name
    * **`DB_USER`**: Username for PostgreSQL
    * **`DB_PASSWORD`**: Password for PostgreSQL
    * **`REDIS_HOST`**: IP address or hostname of your Redis server
    * **`REDIS_PORT`**: Port for Redis (default `6379`)

### Install Python Dependencies
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 6. Step 4: Run the API Application

### Development Mode (with auto-reload)
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The application should now be available at `http://127.0.0.1:8000`. You can access the interactive API documentation at:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## 7. Troubleshooting Common Issues

### Connection Issues
- **PostgreSQL Connection Refused:**
  - Verify PostgreSQL is running
  - Check host and port in `docker.env`
  - Ensure network connectivity between services

- **Redis Connection Refused:**
  - Verify Redis is running
  - Check host and port in `docker.env`
  - Test connection with `redis-cli ping`

### Authentication Issues
- **PostgreSQL Authentication Failed:**
  - Double-check credentials in `docker.env`
  - Verify database name and user permissions

### API Startup Issues
- **ModuleNotFoundError:**
  - Ensure virtual environment is activated
  - Verify all dependencies are installed
  - Check Python version compatibility

### Docker-specific Issues
- **Container Networking:**
  - Ensure containers are on the same network
  - Check port mappings
  - Verify service names in environment variables

For more detailed troubleshooting, refer to the [DOCKER_SETUP.md](DOCKER_SETUP.md) guide.
