# Docker Setup Guide - Travel Recharge API

This guide provides instructions for running the entire Travel Recharge API stack using Docker Compose (single-host deployment).

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/FreddyB200/travel-recharge-api.git
cd travel-recharge-api
```

### 2. Setup Database Schema
```bash
# Clone the database repository to get the schema and data
git clone https://github.com/FreddyB200/travel-recharge-database.git temp-db

# Copy the database files to the correct location
# The database repository contains:
# - Schema files in db/data/
# - 18 data insertion files in db/data/
# - Stored procedures in db/data/
# - Roles and permissions
cp -r temp-db/db/data/* database/

# Clean up
rm -rf temp-db
```

### 3. Start All Services
```bash
# Start all services (PostgreSQL, Redis, API)
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
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