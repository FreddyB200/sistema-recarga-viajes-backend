# Deployment Guide

This document provides a step-by-step guide to deploy and run the project on any machine.

---

## 1. Prerequisites

Before starting, ensure you have the following installed on your system:

- Python 3.8 or higher
- pip (Python package manager)
- Git
- PostgreSQL (or the database system used by the project)

---

## 2. Local Setup

Follow these steps to set up and run the project locally:

### 2.1 Clone the Repository

Clone the project repository to your local machine:

```bash
git clone https://github.com/your-repo-url.git
cd SISTEMA-RECARGA-VIAJES-BACKEND
```

### 2.2 Copy `.env.example` and Configure Environment Variables

Copy the `.env.example` file to `.env`:

```bash
cp .env.example .env
```

Edit the `.env` file and configure the environment variables as needed (e.g., database connection details, secret keys, etc.).

### 2.3 Create a Virtual Environment and Install Dependencies

Create a virtual environment:

```bash
python3 -m venv venv
```

Activate the virtual environment:

- On Linux/MacOS:
  ```bash
  source venv/bin/activate
  ```
- On Windows:
  ```bash
  venv\Scripts\activate
  ```

Install the required dependencies:

```bash
pip install -r requirements.txt
```

### 2.4 Run the Application with FastAPI

Start the FastAPI application:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
with FastAPI:
   ```bash
   fastapi dev app/main.py --host 0.0.0.0 --port 8000
   ```

The application will be available at `http://127.0.0.1:8000`.

---

## Additional Notes

- Ensure your database is running and accessible with the credentials provided in the `.env` file.
- Use the FastAPI interactive documentation at `http://127.0.0.1:8000/docs` to test the API endpoints.
- If you encounter issues, check the logs for detailed error messages.

---