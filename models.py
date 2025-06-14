# models.py

import os
from datetime import datetime
from sqlalchemy import create_engine, Column, BigInteger, Integer, Boolean, DateTime, String, JSON, text   
from sqlalchemy.orm import declarative_base, sessionmaker
from dateutil.relativedelta import relativedelta


DATABASE_URL = os.environ['DATABASE_URL']
engine = create_engine(DATABASE_URL, echo=True)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id           = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True
        )
    user_id      = Column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True
        )
    usage_count  = Column(
        Integer,
        default=0,
        server_default=text('0'),
        nullable=False
        )
    is_admin     = Column(
        Boolean,
        default=False,
        server_default=text('false'),
        nullable=False
        )
    first_request  = Column(
        DateTime,
        default=datetime.utcnow,
        server_default=text('CURRENT_TIMESTAMP'),
        nullable=False
        )
    last_request = Column(
        DateTime,
        default=datetime.utcnow,
        server_default=text('CURRENT_TIMESTAMP'),
        nullable=False
        )
    tariff        = Column(
        String,
        default='',
        server_default=text("''"),
        nullable=False
        )     
    tariff_paid   = Column(
        Boolean,
        default=False,
        server_default=text('false'),
        nullable=False
        )
    advisors      = Column(
        JSON,
        default=list,
        server_default=text("'[]'"),
        nullable=False
        )  

    def tariff_expires(self) -> datetime:
        """Дата начала тарифа берётся из first_request, длительность — по типу."""
        dur = {
          'БМ': relativedelta(months=+1),
          'БГ': relativedelta(years=+1),
          'РМ': relativedelta(months=+1),
          'РГ': relativedelta(years=+1),
        }.get(self.tariff, None)
        if not self.tariff_paid or not dur:
            return None
        return self.first_request + dur
