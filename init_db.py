# init_db.py
import os
from sqlalchemy import create_engine
# ваша декларация моделей
from models import Base, User, engine, SessionLocal
  

DATABASE_URL = os.environ['DATABASE_URL']
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, echo=True, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL, echo=True)
Base.metadata.create_all(bind=engine)
print("База данных и таблицы созданы/проверены.")

