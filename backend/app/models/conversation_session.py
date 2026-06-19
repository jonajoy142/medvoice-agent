from sqlalchemy import Column, DateTime, String, Text, func

from app.db.base import Base


class ConversationSession(Base):
    __tablename__ = "conversation_sessions"

    id = Column(String(64), primary_key=True, index=True)
    opid = Column(String(32), nullable=True, index=True)
    patient_name = Column(String(120), nullable=True)
    last_doctor_list = Column(Text, nullable=True)
    conversation = Column(Text, nullable=True)
    recording_consent = Column(String(8), nullable=True)
    selected_receptionist_id = Column(String(64), nullable=True, index=True)
    hospital_id = Column(String(64), nullable=True, index=True)
    current_intent = Column(String(64), nullable=True)
    slots = Column(Text, nullable=True)
    missing_slots = Column(Text, nullable=True)
    last_assistant_question = Column(Text, nullable=True)
    workflow_state = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
