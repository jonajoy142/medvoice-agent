from sqlalchemy import Column, DateTime, Integer, String, func

from app.db.base import Base

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    patient_opid = Column(String(32), index=True, nullable=False)
    patient_name = Column(String(120), nullable=False)
    specialization = Column(String(120), nullable=False)
    doctor_name = Column(String(120), nullable=True)
    requested_time = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)