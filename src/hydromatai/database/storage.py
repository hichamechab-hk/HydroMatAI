from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base


DATABASE_URL = "sqlite:///hydromatai.db"


engine = create_engine(
    DATABASE_URL,
    echo=False
)


SessionLocal = sessionmaker(
    bind=engine
)


def create_database():
    Base.metadata.create_all(engine)


def get_session():
    return SessionLocal()
