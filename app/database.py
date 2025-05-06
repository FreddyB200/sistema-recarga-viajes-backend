from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DB = os.getenv("POSTGRES_DB")
USER = os.getenv("POSTGRES_USER")
PASSWORD = os.getenv("POSTGRES_PASSWORD")
HOST = "db"
PORT = 5532

# SQLALCHEMY_DATABASE_URL = f"postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DB}"


SQLALCHEMY_DATABASE_URL = "postgresql://admin:Pass%21__2025%21@149.130.169.172:33333/sistema_recargas_viajes"

# CONNECTION ENGINE
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# DATABASE SESSION
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
