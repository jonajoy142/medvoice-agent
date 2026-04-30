from sqlalchemy import Column, Integer, String
from app.db.session import Base

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    patient_name = Column(String)
    time_slot = Column(String)