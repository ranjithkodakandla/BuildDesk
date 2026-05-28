import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
# Import models so Base metadata is populated
from app.db.models import TenantRecord, ProjectRecord, GeometryRecord

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./builddesk.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
