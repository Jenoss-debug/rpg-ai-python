from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.db_config import app_database_url


engine = create_engine(
    app_database_url(),
    pool_pre_ping=True,
    hide_parameters=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
