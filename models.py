# models.py
import os
from datetime import datetime

from sqlalchemy import create_engine, Column, BigInteger, Integer, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

DATABASE_URL = os.environ['DATABASE_URL']
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, unique=True, nullable=False)
    usage_count = Column(Integer, default=0, nullable=False)
    is_admin = Column(Boolean, default=False)
    last_request = Column(DateTime, default=datetime.utcnow)

