# Distributed Deployment Guide for Travel Recharge API

This guide provides detailed instructions for deploying the Travel Recharge API services (PostgreSQL, Redis, API) across multiple Virtual Machines (VMs) to simulate a distributed environment. For a simpler single-host setup using Docker Compose, please refer to [DOCKER_SETUP.md](DOCKER_SETUP.md).

## 📖 Table of Contents

1.  [Prerequisites for Distributed Setup](#prerequisites-for-distributed-setup)
2.  [Architecture Overview (Distributed)](#architecture-overview-distributed)
3.  [Step 1: Prepare Virtual Machines](#step-1-prepare-virtual-machines)
4.  [Step 2: Deploy PostgreSQL on its VM](#step-2-deploy-postgresql-on-its-vm)
5.  [Step 3: Deploy Redis on its VM](#step-3-deploy-redis-on-its-vm)
6.  [Step 4: Deploy the API Application on its VM](#step-4-deploy-the-api-application-on-its-vm)
7.  [Step 5: Configure and Run the API](#step-5-configure-and-run-the-api)
8.  [Troubleshooting Distributed Setup](#troubleshooting-distributed-setup)

---

## 1. Prerequisites for Distributed Setup

*   **Virtualization Software:** VirtualBox, VMware, or similar.
*   **Linux VMs:** At least three VMs (e.g., Ubuntu Server, Alpine Linux). One for each service: PostgreSQL, Redis, API.
*   **Networking:** VMs must be able to communicate with each other over the network (e.g., using a NAT Network or Bridged Adapter in VirtualBox, properly configured).
*   **Basic Linux & Networking Skills:** SSH, package management, IP configuration.
*   **Docker & Docker Compose:** Required on the PostgreSQL VM (if using the DB repository's Docker setup) and optionally on the Redis VM.
*   **Git:** For cloning repositories.
*   **Python 3.8+ & pip:** On the API VM.

---

## 2. Architecture Overview (Distributed)

*   **VM 1 (Database VM):** Runs PostgreSQL.
*   **VM 2 (Cache VM):** Runs Redis.
*   **VM 3 (API VM):** Runs the FastAPI application.
*   Each VM will have its own IP address. The API VM will be configured to connect to the Database VM and Cache VM using their respective IP addresses and ports.

---

## 3. Step 1: Prepare Virtual Machines

1.  Create and configure three Linux VMs.
2.  Install necessary base packages (e.g., `git`, `curl`, `build-essential` for Python if needed).
3.  Ensure network connectivity between all VMs. Note down the IP address of each VM.
4.  Install Docker and Docker Compose on the VM designated for PostgreSQL, and optionally on the VM for Redis if you plan to run Redis in Docker.

---

## 4. Step 2: Deploy PostgreSQL on its VM

This assumes you are using the `travel-recharge-database` repository to run PostgreSQL in Docker on its dedicated VM.

1.  **On the Database VM:**
    ```bash
    # Clone the database repository
    git clone https://github.com/FreddyB200/travel-recharge-database.git
    cd travel-recharge-database

    # Configure environment variables (e.g., in .env)
    cp .env.template .env
    # Edit .env with your desired database name (POSTGRES_DB),
    # user (POSTGRES_USER), password (POSTGRES_PASSWORD),
    # and the host port you want PostgreSQL to listen on (POSTGRES_LISTEN_PORT, e.g., 5432).
    # The PostgreSQL container will be accessible on this port on the Database VM's IP.

    # Start the database
    docker-compose up -d
    ```
2.  **Verify PostgreSQL Accessibility:**
    *   Ensure the PostgreSQL container is running on the Database VM: `docker-compose ps`
    *   **Crucially, ensure the Database VM's firewall allows incoming connections on the `POSTGRES_LISTEN_PORT` (e.g., 5432) from the API VM's IP address.**
    *   From the API VM, test connectivity to the PostgreSQL port on the Database VM:
        ```bash
        # Replace DB_VM_IP with the Database VM's IP and DB_PORT with the POSTGRES_LISTEN_PORT
        nc -zv DB_VM_IP DB_PORT
        ```
        A successful connection will indicate that the network path is open. The official PostgreSQL Docker image, when configured with `POSTGRES_USER` and `POSTGRES_PASSWORD`, is generally set up to allow connections from other hosts using these credentials without needing to modify internal PostgreSQL configuration files like `pg_hba.conf` for typical use cases.

---

## 5. Step 3: Deploy Redis on its VM

1.  **On the Cache VM:**
    *   **Option A: Install Redis Natively**
        ```bash
        # Debian/Ubuntu
        sudo apt update && sudo apt install redis-server -y
        sudo systemctl enable redis-server --now
        # Edit /etc/redis/redis.conf, change 'bind 127.0.0.1' to 'bind 0.0.0.0' or the Cache VM's IP
        sudo systemctl restart redis-server
        ```
        ```bash
        # Alpine Linux
        apk update && apk add redis
        # Edit /etc/redis.conf, change 'bind 127.0.0.1' to 'bind 0.0.0.0' or the Cache VM's IP
        rc-update add redis && rc-service redis start
        ```
    *   **Option B: Run Redis with Docker**
        ```bash
        docker run -d --name redis-cache -p 6379:6379 redis:latest redis-server --bind 0.0.0.0
        ```
2.  **Verify:** Ensure Redis is running and accessible on its port (6379) from the API VM.
    ```bash
    # From API VM (replace CACHE_VM_IP and REDIS_PORT)
    # nc -zv CACHE_VM_IP REDIS_PORT
    # Or try redis-cli
    # redis-cli -h CACHE_VM_IP -p REDIS_PORT ping 
    ```

---

## 6. Step 4: Deploy the API Application on its VM

1.  **On the API VM:**
    ```bash
    # Clone the API repository
    git clone https://github.com/FreddyB200/travel-recharge-api.git
    cd travel-recharge-api

    # Create a Python virtual environment and install dependencies
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

---

## 7. Step 5: Configure and Run the API

1.  **On the API VM (in `travel-recharge-api` directory):**
    1.  Create an environment file for the API. You can copy `docker.env.example` to a new file, e.g., `.env.distributed` (to avoid confusion with `docker.env` used by Docker Compose setup).
        ```bash
        cp docker.env.example .env.distributed 
        ```
    2.  Edit `.env.distributed` (or your chosen env file name):
        *   `DB_HOST`: Set to the **IP address of your Database VM**.
        *   `DB_PORT`: Set to the port PostgreSQL is listening on in the Database VM (e.g., `5432`).
        *   `DB_NAME`, `DB_USER`, `DB_PASSWORD`: Match the credentials for your PostgreSQL database.
        *   `REDIS_HOST`: Set to the **IP address of your Cache VM**.
        *   `REDIS_PORT`: Set to the port Redis is listening on in the Cache VM (e.g., `6379`).
        *   `API_HOST=0.0.0.0` (to make the API accessible externally on the API VM).
        *   `API_PORT=8000`.

2.  **Load Environment Variables and Run the API:**
    The `app.main` likely uses a library like `python-dotenv` to load a `.env` file by default, or you might need to source it or use a tool like `honcho` or `uvicorn --env-file`.

    If `python-dotenv` is used and loads `.env` by default, you can rename your `.env.distributed` to `.env` before running:
    ```bash
    mv .env.distributed .env 
    ```
    Then run Uvicorn:
    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload 
    ```
    Alternatively, if your Uvicorn version supports `--env-file`:
    ```bash
    uvicorn app.main:app --env-file .env.distributed --host 0.0.0.0 --port 8000 --reload
    ```

3.  **Access the API:** From your host machine or another machine that can reach the API VM, use `http://API_VM_IP:8000`.

---

## 8. Troubleshooting Distributed Setup

*   **Connection Refused/Timeout:**
    *   Verify VM network connectivity (ping between VMs).
    *   Check firewalls on each VM (e.g., `ufw` on Ubuntu). Ensure ports 5432 (PostgreSQL), 6379 (Redis), and 8000 (API) are open for connections from the respective source IPs.
    *   Ensure PostgreSQL and Redis services are configured to `bind` to `0.0.0.0` or their specific VM IP, not just `127.0.0.1`.
    *   Double-check IP addresses and ports in the API's environment file.
*   **Authentication Failed (PostgreSQL):**
    *   Ensure `pg_hba.conf` on the Database VM allows connections from the API VM's IP for the specified user and database.
    *   Verify credentials.

This guide focuses on the distributed setup. For single-host Docker Compose, see [DOCKER_SETUP.md](DOCKER_SETUP.md).
