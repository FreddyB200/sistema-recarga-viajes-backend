from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DB = os.getenv("DB_NAME")
USER = os.getenv("DB_USER")
PASSWORD = os.getenv("DB_PASSWORD")
HOST = os.getenv("DB_HOST", "localhost")
PORT = os.getenv("DB_PORT", 5432)

SQLALCHEMY_DATABASE_URL = f"postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DB}"


# CONNECTION ENGINE
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# DATABASE SESSION
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
