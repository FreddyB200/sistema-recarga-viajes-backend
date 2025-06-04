# Docker Setup Guide - Travel Recharge API

This guide provides instructions for running the entire Travel Recharge API stack using Docker Compose (single-host deployment).

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Git

### 1. Setup Database First
```bash
# Clone and setup the database repository
git clone https://github.com/FreddyB200/travel-recharge-database.git
cd travel-recharge-database

# Configure environment variables
cp .env.template .env
# Edit .env with correct values

# Start the database
docker-compose up -d
```

### 2. Setup API
```bash
# Clone the API repository
git clone https://github.com/FreddyB200/travel-recharge-api.git
cd travel-recharge-api

# Configure environment variables
cp docker.env.example docker.env
# Edit docker.env with correct values:
# - DB_HOST=postgres (from database docker-compose)
# - DB_PORT=5432
# - DB_NAME=travel_recharge_db
# - DB_USER=travel_user
# - DB_PASSWORD=travel_password
# - REDIS_HOST=redis
# - REDIS_PORT=6379

# Start the API and Redis
docker-compose up -d
```

### 3. Verify Installation
```bash
# Check all services are running
docker-compose ps

# View logs
docker-compose logs -f

# Test the API
curl http://localhost:8000/ping-db
```

### 4. Access the API
- **API Documentation (Swagger):** http://localhost:8000/docs
- **API Documentation (ReDoc):** http://localhost:8000/redoc
- **API Base URL:** http://localhost:8000

### 5. Test the API
```bash
# Test database connection
curl http://localhost:8000/ping-db

# Test user endpoints
curl http://localhost:8000/users/count

# Test trips endpoints
curl http://localhost:8000/trips/total

# Test finance endpoints
curl http://localhost:8000/finance/revenue
```

## 🛠️ Development

### Environment Variables
The docker-compose.yml includes default environment variables. For custom configuration:

1. Copy the example file:
   ```bash
   cp docker.env.example docker.env
   ```

2. Modify `docker.env` with your settings

3. Update docker-compose.yml to use the env file:
   ```yaml
   api:
     env_file:
       - docker.env
   ```

### Rebuilding the API
```bash
# Rebuild only the API service
docker-compose build api
docker-compose up -d api

# Or rebuild everything
docker-compose down
docker-compose build
docker-compose up -d
```

## 🔧 Troubleshooting

### Services Not Starting
```bash
# Check logs for specific service
docker-compose logs postgres
docker-compose logs redis
docker-compose logs api

# Restart services
docker-compose restart
```

### Database Issues
```bash
# Access PostgreSQL directly
docker-compose exec postgres psql -U travel_user -d travel_recharge_db

# Reset database
docker-compose down -v
docker-compose up -d
```

### Redis Issues
```bash
# Access Redis directly
docker-compose exec redis redis-cli

# Clear Redis cache
docker-compose exec redis redis-cli FLUSHALL
```

## 🧹 Cleanup

```bash
# Stop all services
docker-compose down

# Remove all data (volumes)
docker-compose down -v

# Remove all images
docker-compose down --rmi all
```

## 📊 Monitoring

### Check Resource Usage
```bash
# View container stats
docker stats

# View specific service logs
docker-compose logs --tail=50 api
```

### Health Checks
All services include health checks. Check status with:
```bash
docker-compose ps
```

## 🔄 Comparison with Distributed Setup

| Feature | Docker Compose (Single Host) | Distributed VMs |
|---------|------------------------------|-----------------|
| Setup Complexity | Low | High |
| Resource Usage | Shared host resources | Dedicated VM resources |
| Network Isolation | Docker networks | VM networks |
| Use Case | Development, testing | Production, learning |
| Startup Time | Fast | Slower |
| Scalability | Limited to host | Full distributed scaling |

For the original distributed VM setup, refer to the main [DEPLOYMENT.md](deployment.md) guide. 