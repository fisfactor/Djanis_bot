# models.py
import os
from datetime import datetime

from sqlalchemy import create_engine, Column, BigInteger, Integer, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

# URL к БД (sqlite-файл в корне проекта)
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///usage.db')

# Движок и сессия
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

# Базовый класс моделей
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    user_id  = Column(BigInteger, primary_key=True, index=True)
    first_ts = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    count    = Column(Integer, default=0, nullable=False)
    blocked  = Column(Boolean, default=False, nullable=False)
