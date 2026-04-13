from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///certificates.db')

if DATABASE_URL.startswith('sqlite'):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class ShareToken(Base):
    __tablename__ = "share_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(36), unique=True, index=True, nullable=False)
    student_name = Column(String(200))
    course_name = Column(String(200))
    student_data_json = Column(Text)

    period_type = Column(String(50))
    period_number = Column(Integer)
    period_year = Column(Integer)

    age_group = Column(String(20))
    grade = Column(Integer)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def is_valid(self):
        if not self.is_active:
            return False, "Ссылка отозвана"
        return True, "OK"

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()