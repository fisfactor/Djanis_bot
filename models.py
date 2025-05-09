# models.py

import os
from datetime import datetime
from sqlalchemy import create_engine, Column, BigInteger, Integer, Boolean, DateTime, String   
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.environ['DATABASE_URL']
engine = create_engine(DATABASE_URL, echo=True)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id           = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id      = Column(BigInteger, unique=True, nullable=False, index=True)
    usage_count  = Column(Integer, default=0, nullable=False)
    is_admin     = Column(Boolean, default=False, nullable=False)
    first_request  = Column(DateTime,  default=datetime.utcnow, nullable=False)
    last_request = Column(DateTime, default=datetime.utcnow, nullable=False)
    gender = Column(String, nullable=True)
