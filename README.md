# Sistema de Recarga de Viajes API

This project is a FastAPI-based backend for a travel recharge system, inspired by systems like TransMilenio (Bogota). It is designed to interact with a Dockerized PostgreSQL database and provides endpoints for managing users, trips, and finances. The project is a learning exercise to improve skills in FastAPI and database management, with plans to evolve into a fully functional and comprehensive API.

---

## Features

- **User Management**: Endpoints to count users, retrieve the latest user, and count active users.
- **Trip Management**: Endpoints to count total trips.
- **Financial Insights**: Endpoints to calculate total revenue.
- **Database Health Check**: Endpoint to verify database connectivity.
- **Interactive API Documentation**: Available at `/docs` (Swagger UI) and `/redoc` (ReDoc).

---

## Project Structure

```
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

- Python 3.8 or higher
- pip (Python package manager)
- Git
- Docker (for the database)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/FreddyB200/sistema-recarga-viajes-backend.git
   cd SISTEMA-RECARGA-VIAJES-BACKEND
   ```

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

[Database Repository](https://github.com/FreddyB200/sistema-recargas-viajes-db.git)

---

## Future Improvements

- Add authentication and authorization.
- Implement more endpoints for advanced user and trip management.
- Add unit and integration tests.
- Improve error handling and logging.
- Deploy the application to a cloud platform.

---

## License

This project is licensed under the MIT License. See the LICENSE file for details.

---

## Acknowledgments

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Docker Documentation](https://docs.docker.com/)