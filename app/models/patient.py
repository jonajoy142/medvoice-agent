from sqlalchemy import Column, DateTime, String, Text, func

from app.db.base import Base


class Patient(Base):
    __tablename__ = "patients"

    opid = Column(String(32), primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    phone = Column(String(32), nullable=True)
    email = Column(String(255), nullable=True)
    dob = Column(String(16), nullable=True)
    history = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
