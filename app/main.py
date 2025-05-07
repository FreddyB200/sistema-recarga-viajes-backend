from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
import models
from database import engine
from dependencies import get_db


models.Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.get("/ping-db")
def ping_db(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "Conexion exitosa"}
    except Exception as e:
        return {"status": "Error", "detail": str(e)}


@app.get("/users/")
def read_users(db: Session = Depends(get_db)):
    try:
        result = db.execute(text("select * from usuarios limit 10")).mappings().all()
        users = [dict(row) for row in result]

        return {"status": "success", "data": users}
    except Exception as e:
        return {"status": "Error", "detail": str(e)}
    
@app.get("/localidades/")
def read_localidades(db: Session = Depends(get_db)):
    try:
        result = db.execute(text("select * from localidades where nombre = 'Usme'")).mappings().all()
        localidades = [dict(row) for row in result]

        return {"status": "success", "data": localidades}
    except Exception as e:
        return {"status": "Error", "detail": str(e)}
