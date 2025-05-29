# Travel Recharge API – Distributed Systems Lab
This project simulates a recharge system (like TransMilenio cards) using a distributed architecture with FastAPI, PostgreSQL, and Redis. It demonstrates caching, database logic optimization, and API development using modern Python tools.

> **Goal**  
> Build, deploy and test a simple distributed architecture:
> - **FastAPI** REST API  
> - **PostgreSQL** relational database (Docker)  
> - **Redis** in-memory cache (Docker) 

---

## 📖 Table of Contents

1. [Context](#context)  
2. [Architecture](#architecture)  
   - [Network Topology](#network-topology)  
   - [Container Diagram](#container-diagram)  
3. [Prerequisites](#prerequisites)  
4. [Installation & Setup](#installation--setup)  
5. [Usage](#usage)  
6. [Deployment](#deployment)  
   - [`DEPLOYMENT.md`](#deploymentmd)  
   - `DEPLOYMENT-REDIS.md` (proposed)  
7. [Future Improvements](#future-improvements)  
8. [License](#license)  

---

## Context

Modern systems need low-latency, high-throughput data access.  
- **PostgreSQL** provides durability, consistency and complex queries.  
- **Redis** sits as a cache layer, speeding up repeated reads (e.g. stats, aggregates).  
- **FastAPI** ties it all together with async endpoints.

## Architecture
### Network Topology
```mermaid
graph TB
  subgraph VirtualBox
    A[Host: Port Forwarding 127.0.0.1:2222 → VM1:22] --> VM1[VM FastAPI<br>eth0: NAT-DHCP<br>eth1: 192.168.100.10]
    B[Host: Port Forwarding 127.0.0.1:2223 → VM2:22] --> VM2[VM Redis<br>eth0: NAT-DHCP<br>eth1: 192.168.100.20]
    C[Host: Port Forwarding 127.0.0.1:2224 → VM3:22] --> VM3[VM PostgreSQL<br>eth0: NAT-DHCP<br>eth1: 192.168.100.30]
  end

  VM1 <-->|eth1 ↔ eth1<br>Direct Communication| VM2
  VM1 <-->|eth1 ↔ eth1<br>Direct Communication| VM3
```
### Container Diagram
```mermaid
%% C4 Container Diagram with Database Grouping
C4Container
title Container Diagram – Redis / FastAPI / PostgreSQL Lab

Person(Student, "Student", "Accesses via browser or HTTP client (Postman, curl, etc.)")

Container(FastAPI_App, "FastAPI App", "Python 3.9+, FastAPI", "Exposes REST endpoints; handles caching with Redis and persistence with PostgreSQL")

Container_Boundary(databases, "Databases") {
  Container(Redis, "Redis", "Redis 7.x (Docker)", "In-memory store for cached data (TTL, in-memory structures)")
  Container(PostgreSQL, "PostgreSQL", "PostgreSQL 13 (Docker)", "Relational database for persistent data")
}

Rel(Student, FastAPI_App, "HTTP / HTTPS API")
Rel(FastAPI_App, Redis, "GET / SET (redis-py)")
Rel(FastAPI_App, PostgreSQL, "INSERT / SELECT (psycopg2 or SQLAlchemy)")

```
---
### request flow
```mermaid
sequenceDiagram
    participant C as Client (Browser/Postman)
    participant F as FastAPI (VM)
    participant R as Redis (VM)
    participant P as PostgreSQL (VM)

    Note over C: Read Operation (GET /trips/{trip_id})
    C->>F: 1. HTTP GET /trips/123
    F->>R: 2. EXISTS trip:123
    alt Cache Hit
        R-->>F: true
        F->>R: 3. GET trip:123
        R-->>F: Trip data (JSON)
        F-->>C: 4. 200 OK (cached)
    else Cache Miss
        R-->>F: false
        F->>P: 5. SELECT * FROM trips WHERE trip_id=123
        P-->>F: Trip data
        F->>R: 6. SETEX trip:123 300
        F-->>C: 7. 200 OK
    end

    Note over C: Write Operation (POST /recharges)
    C->>F: 1. HTTP POST /recharges
    F->>P: 2. BEGIN TRANSACTION
    F->>P: 3. INSERT INTO recharges(...)
    P-->>F: Success
    F->>P: 4. UPDATE cards SET balance=balance+500
    P-->>F: Success
    F->>P: 5. COMMIT
    F->>R: 6. DEL card:789:balance
    F->>R: 7. DEL user:456:recharges
    F-->>C: 8. 201 Created

```
---
## Project Structure
```bash
SISTEMA-RECARGA-VIAJES-BACKEND/
├── app/
│   ├── database.py       # Database connection and setup
│   ├── dependencies.py   # Dependency injection for database sessions
│   ├── main.py           # FastAPI application and endpoints
│   ├── models.py         # Database models (if used)
│   └── __pycache__/      # Compiled Python files
├── requirements.txt      # Python dependencies
├── .gitignore            # Git ignore rules
├── DEPLOYMENT.md         # Deployment guide
└── README.md             # Project documentation
```

---

## Getting Started

### Prerequisites
- VirtualBox VMs with Ubuntu/Alpine or any linux OS
- Docker & Docker Compose installed on each VM
- SSH keys configured for password-less login
- Git & GitHub account
- Python 3.8 or higher
- pip (Python package manager)
- Git

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/FreddyB200/sistema-recarga-viajes-backend.git
   cd SISTEMA-RECARGA-VIAJES-BACKEND
   ```
---

2. Set up the environment variables:
   ```bash
   cp .env.example .env
   ```
   Configure the `.env` file with your database credentials and other settings.

3. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. Run the application:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   with FastAPI:
   ```bash
   fastapi dev app/main.py --host 0.0.0.0 --port 8000
   ```

5. Access the API documentation:
   - Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
   - ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## Database Repository

The database for this project is managed in a separate repository. You can find it here:

[Database Repository](https://github.com/FreddyB200/travel-recharge-api.git)

---

## License

This project is licensed under the MIT License. See the LICENSE file for details.

---

## Acknowledgments

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Docker Documentation](https://docs.docker.com/)
- [Redis Documentation] (https://redis.io/docs/latest/)
