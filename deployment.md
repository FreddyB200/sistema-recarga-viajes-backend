# Deployment and Setup Guide for Travel Recharge API

This guide provides detailed instructions to set up the necessary environment, install dependencies, configure, and run the Travel Recharge API project.

## 📖 Table of Contents

1.  [Prerequisites](#prerequisites)
2.  [Setup Order Overview](#setup-order-overview)
3.  [Step 1: Setup the PostgreSQL Database (External Repository)](#step-1-setup-the-postgresql-database-external-repository)
4.  [Step 2: Setup Redis](#step-2-setup-redis)
    * [Option A: Install Redis Natively](#option-a-install-redis-natively)
    * [Option B: Run Redis with Docker](#option-b-run-redis-with-docker)
5.  [Step 3: Setup the API Application](#step-3-setup-the-api-application)
    * [Clone the API Repository](#clone-the-api-repository)
    * [Configure Environment Variables](#configure-environment-variables)
    * [Install Python Dependencies](#install-python-dependencies)
6.  [Step 4: Run the API Application](#step-4-run-the-api-application)
7.  [Troubleshooting Common Issues](#troubleshooting-common-issues)

---

## 1. Prerequisites

Before you begin, ensure your system meets the following requirements:

* **General Development Tools:**
    * Git & a GitHub account
    * Python 3.8 or higher
    * `pip` (Python package manager) and `venv` (for virtual environments)
* **For the PostgreSQL Database (managed in a separate repository):**
    * Docker and Docker Compose (as per the database repository's instructions)
* **For Redis:**
    * Either Docker (if using the Docker option for Redis) OR package management tools for your OS (like `apt` for Debian/Ubuntu or `apk` for Alpine).
* **For the full distributed setup (as originally designed in a multi-VM environment):**
    * VirtualBox (or your preferred virtualization software)
    * Ability to create and manage Linux VMs (Ubuntu/Alpine recommended)
    * Docker & Docker Compose installed *on each respective VM* for its service
    * SSH keys configured for password-less login to VMs (recommended)

---

## 2. Setup Order Overview

For the API to function correctly, services must be set up in the following order:
1.  **PostgreSQL Database:** This is the primary data store.
2.  **Redis:** This is used for caching.
3.  **Travel Recharge API:** This application connects to both PostgreSQL and Redis.

---

## 3. Step 1: Setup the PostgreSQL Database (External Repository)

The PostgreSQL database for this project is managed in a **separate repository**. It **must be set up and running before proceeding with the API setup.**

➡️ **Go to the [Travel Recharge Database Repository](https://github.com/FreddyB200/travel-recharge-database.git) and follow the setup instructions provided in its `README.md` or `DEPLOYMENT.md` file.**

This external repository contains the Docker Compose configuration to launch PostgreSQL with the required schema and (optionally) initial data. After following its instructions, ensure your PostgreSQL container is running and accessible from the environment where you plan to run the API.

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

This is a simple way to get Redis running if you have Docker installed on the machine/VM where the API will run (or on a machine accessible by the API).
```bash
docker run -d --name redis-cache -p 6379:6379 redis:latest
```
* **Verify Installation:**
```bash
docker exec redis-cache redis-cli ping
```
This command should respond with PONG.
## 5. Step 3: Setup the API Application
Once the database and Redis are running and accessible:

### Clone the API Repository
Clone this repository (Travel Recharge API) to your local machine or VM:
```bash
git clone [https://github.com/FreddyB200/travel-recharge-api.git](https://github.com/FreddyB200/travel-recharge-api.git) # Or your fork's URL
cd travel-recharge-api
```
### Configure Environment Variables
This API requires environment variables to connect to your PostgreSQL and Redis instances.

1.  **Copy the example environment files:**
    ```bash
    cp .env.postgres.example .env.postgres
    cp .env.redis.example .env.redis
    ```
    _Note: Your application logic (e.g., in `app/core/config.py` or `app/database.py`) will need to be set up to correctly load these variables. Consider consolidating into a single `.env` loaded by `python-dotenv` if preferred._

2.  **Edit `.env.postgres` and `.env.redis`:**
    Update these files with the correct connection details for your running PostgreSQL (from Step 1 of `DEPLOYMENT.md` - setting up the database) and Redis (from Step 2 of `DEPLOYMENT.md` - setting up Redis) instances.
    * **`POSTGRES_HOST`**: IP address or hostname of your PostgreSQL server. If running PostgreSQL in Docker on the same machine as the API (but not Dockerized API), this might be `localhost`. If both are Docker containers on the same custom Docker network, it would be the PostgreSQL service name.
    * **`POSTGRES_PORT`**: Port for PostgreSQL (default `5432`).
    * **`POSTGRES_USER`**: Username for PostgreSQL.
    * **`POSTGRES_PASSWORD`**: Password for PostgreSQL.
    * **`POSTGRES_DB`**: Database name.
    * **`REDIS_HOST`**: IP address or hostname of your Redis server.
    * **`REDIS_PORT`**: Port for Redis (default `6379`).

### Install Python Dependencies
Create a Python virtual environment and install the required packages:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 6. Step 4: Run the API Application
With dependencies installed and environment variables configured, you can run the FastAPI application.

- Development Mode (with auto-reload, recommended for development):

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Alternatively, using the FastAPI CLI (if installed and preferred):
```bash
# fastapi dev app/main.py --host 0.0.0.0 --port 8000
Production-like Mode (without auto-reload):
```
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Alternatively, using the FastAPI CLI:
```bash
# fastapi run app/main.py --host 0.0.0.0 --port 8000
```

The application should now be available at `http://127.0.0.1:8000.` You can access the interactive API documentation at `http://127.0.0.1:8000/docs` and `http://127.0.0.1:8000/redoc.`

## 7. Troubleshooting Common Issues
- **Connection Refused (PostgreSQL or Redis):**
  - Verify the service (PostgreSQL/Redis) is running.
  - Check that the `HOST` and `PORT` in your `.env` files are correct and that the service is accessible from where the API is running (firewalls, Docker networking).
  - If using Docker, ensure ports are correctly mapped or containers are on the same network.
- **Authentication Failed (PostgreSQL):**
  - Double-check `USER`, `PASSWORD`, and `DB` names in `.env.postgres.`

- **API Errors on Startup:**
  - Check the console output for specific error messages. Often related to incorrect environment variable settings or inability to connect to database/cache.
- `ModuleNotFoundError:`
  - Ensure your virtual environment is activated and `pip install -r requirements.txt` was successful.
    
This guide should help you get the Travel Recharge API up and running. For details about the API's features, architecture, and how to run tests, please refer to the main [README](README.md) file of this repository.
