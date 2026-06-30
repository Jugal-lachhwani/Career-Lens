# create_tables.py
from src.Postres.postres import engine
from src.Postres.models import Base

Base.metadata.create_all(bind=engine)
print("Tables created successfully")