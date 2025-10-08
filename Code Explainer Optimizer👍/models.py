from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'app.db')
DB_URI = f"sqlite:///{DB_PATH}"

engine = create_engine(DB_URI, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class UsageRecord(Base):
    __tablename__ = 'usage_records'
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    language = Column(String, default='python')
    code_size = Column(Integer, default=0)
    action = Column(String, default='explain')  # explain | optimize
    success = Column(Boolean, default=True)
    latency_ms = Column(Integer, default=0)

def db_init():
    os.makedirs(os.path.join(os.path.dirname(__file__), 'instance'), exist_ok=True)
    Base.metadata.create_all(bind=engine)
    return engine