"""Drop and recreate all tables (development only)."""
from src.Postres.postres import engine
from src.Postres.models import Base

Base.metadata.drop_all(bind=engine)
print("🗑️  Dropped all tables")

Base.metadata.create_all(bind=engine)
print("✅ Tables recreated successfully")
