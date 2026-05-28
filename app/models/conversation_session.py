from sqlalchemy import Column, DateTime, String, Text, func

from app.db.base import Base


class ConversationSession(Base):
    __tablename__ = "conversation_sessions"

    id = Column(String(64), primary_key=True, index=True)
    opid = Column(String(32), nullable=True, index=True)
    patient_name = Column(String(120), nullable=True)
    last_doctor_list = Column(Text, nullable=True)
    conversation = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
