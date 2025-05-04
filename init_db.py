# init_db.py
from sqlalchemy import create_engine
# ваша декларация моделей
from models import Base  

engine = create_engine("sqlite:///usage.db", echo=True)
Base.metadata.create_all(engine)
print("База данных и таблицы созданы/проверены.")

