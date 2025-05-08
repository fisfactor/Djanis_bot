# init_db.py

from models import Base, engine

# Создаст таблицы, если их ещё нет:
Base.metadata.create_all(bind=engine)
print("База данных и таблицы созданы/проверены.")


