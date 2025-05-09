# init_db.py

from models import Base, engine


# Удаляем старую схему (если есть)
Base.metadata.drop_all(bind=engine)

# Создаём заново
Base.metadata.create_all(bind=engine)
print("✅ База и таблицы пересозданы.")


