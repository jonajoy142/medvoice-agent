from sqlalchemy import Column, DateTime, Integer, String, Text, func

from app.db.base import Base


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    specialization = Column(String(120), nullable=False, index=True)
    branch = Column(String(120), nullable=True)
    consultation_mode = Column(String(32), nullable=True)
    fee = Column(Integer, nullable=True)
    languages = Column(Text, nullable=True)
    slots = Column(Text, nullable=True)
    available_days = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
