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
2. [Architecture Diagrams](#architecture)  
   - [Network Topology](#network-topology)  
   - [Container](#container)  
   - [Request flow](#request-flow)
3. [Prerequisites](#prerequisites)  
4. [Installation](#installation)   
5. [License](#license)  
6. [Pending Tasks](#pending-tasks)

---

## Context

Modern systems need low-latency, high-throughput data access.  
- **PostgreSQL** provides durability, consistency and complex queries.  
- **Redis** sits as a cache layer, speeding up repeated reads (e.g. stats, aggregates).  
- **FastAPI** ties it all together with async endpoints.

## Architecture
### Network Topology Diagram
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
### Request Flow Diagram
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

### Installation

For installation guide, refer to the [Deployment Guide](DEPLOYMENT.md).

---

## See the API Documentation at

- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/redoc

---

## Database Repository

The database for this project is managed in a separate repository. You can find it here:

[Database Repository](https://github.com/FreddyB200/travel-recharge-database.git)

---
## Latency Testing Results

### Cacheable Endpoints

#### Endpoint: `/trips/total` MISS=postgres, HIT=redis
- **First Request (Cache MISS)**: 57.34 ms
- **Second Request (Cache HIT)**: 3.2 ms
- **Third Request**: 6 ms

#### Endpoint: `/trips/finance/revenue`
- **First Request (Cache MISS)**: 62.23 ms
- **Second Request (Cache HIT)**: 2.55 ms

### Non-Cacheable Endpoints

#### Endpoint: `/users/count`
- **Average Latency**: 8.11 ms

#### Endpoint: `/users/active/count`
- **Average Latency**: 9.11 ms

#### Endpoint: `/users/latest`
- **Average Latency**: 6.69 ms

---

## Scripts for Latency Testing

### Cached Endpoints
Use the `latency_test.py` script to test the latency of cached endpoints. You can specify the number of iterations to simulate multiple requests.

#### Usage:
```bash
python scripts/latency_test.py
```

Follow the prompts to select an endpoint and specify the number of iterations.

### Non-Cached Endpoints
Use the `latency_non_cacheable.py` script to test the latency of non-cached endpoints. Similar to the cached script, you can specify the number of iterations.

#### Usage:
```bash
python scripts/latency_non_cacheable.py
```

Follow the prompts to select an endpoint and specify the number of iterations.

---

### Cached Endpoint Example: `/finance/revenue`
The `/finance/revenue` endpoint now uses Redis for caching. This significantly reduces latency for repeated requests. The cache is automatically invalidated after a specified TTL.

#### Example:
Install curl if not available:
```bash
sudo apt update && sudo apt install curl -y
```

For Alpine Linux:
```bash
apk update && apk add curl apache2-utils
```

Test the endpoint with curl:
```bash
curl -X GET http://localhost:8000/finance/revenue
```

Test the endpoint with ab (Apache Benchmark):
```bash
ab -n 100 -c 10 http://localhost:8000/finance/revenue
```

#### Explanation of `ab` parameters:
- `-n 100`: Specifies the total number of requests to send to the server. In this case, 100 requests will be sent.
- `-c 10`: Specifies the number of concurrent requests to send at the same time. In this case, 10 requests will be sent simultaneously.

This command simulates a load test to measure the server's performance under concurrent requests.
---

## Pending Tasks

Here are some ideas and tasks to expand and improve the project:

1. **New Repository: Spring Boot Version**
   - Create a new repository for the API implemented in Spring Boot.
   - Apply security with Spring Security and aim for a more robust codebase.

2. **Version in Go**
   - Develop a version of the API in Go to compare performance with Python.

3. **CI/CD Pipeline**
   - Implement continuous integration and deployment pipelines using GitHub Actions or similar tools.

4. **Dockerization**
   - Containerize the application using Docker for easier deployment and scalability.

5. **Database Backups**
   - Set up automated backups of the database to another server.
   - Decide whether to document this in the README of this repository or the API repository.

6. **Cloud Integration**
   - Integrate the application with cloud services like AWS, Google Cloud, or Azure.

7. **Automated Tests**
   - Write unit, integration, and end-to-end tests to ensure the reliability of the API.

8. **Logging**
   - Implement structured logging to monitor and debug the application effectively.

9. **Performance Testing**
   - Use tools like Locust to simulate user load and measure the performance of the API.

---

## Acknowledgments
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Docker Documentation](https://docs.docker.com/)
- [Redis Documentation](https://redis.io/docs/latest/)

---
## License
This project is licensed under the MIT License. See the LICENSE file for details.

