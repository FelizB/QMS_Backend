from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Import all models here so Alembic sees them
import backend_app.db.models  # noqa