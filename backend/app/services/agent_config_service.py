"""Agent configuration loading service for voice runtime."""

from __future__ import annotations

from typing import Dict, Any, Optional
from sqlalchemy import text
from fastapi import HTTPException, status

from app.db.session import check_db_connection, db_session
from app.core.rbac import CurrentUser


class AgentConfigService:
    """Service for loading and validating agent configuration."""
    
    @staticmethod
    def load_agent_config(
        agent_id: str,
        hospital_id: str,
        current_user: Optional[CurrentUser] = None
    ) -> Dict[str, Any]:
        """
        Load agent configuration from database with tenant validation.
        
        Args:
            agent_id: Agent UUID
            hospital_id: Hospital UUID for tenant validation
            current_user: Optional current user for additional validation
            
        Returns:
            Agent configuration dictionary
            
        Raises:
            HTTPException: If agent not found or tenant validation fails
        """
        if not check_db_connection():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        with db_session() as db:
            # Load agent with tenant validation
            row = db.execute(
                text(
                    """
                    SELECT 
                        id, hospital_id, name, description, status, language,
                        voice_provider, voice_name, tts_pace, greeting, system_prompt,
                        escalation_rules, working_hours, transfer_phone_number,
                        appointment_behavior, knowledge_source_ids, fallback_behavior,
                        stt_provider, llm_provider, tts_provider,
                        supported_languages, llm_model, stt_model, tts_model,
                        enabled_tools, business_config
                    FROM agents
                    WHERE id = :agent_id
                    LIMIT 1
                    """
                ),
                {"agent_id": agent_id},
            ).mappings().first()
            
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Agent not found: {agent_id}"
                )
            
            # Tenant validation - ensure agent belongs to the correct hospital
            agent_hospital_id = str(row["hospital_id"])
            if agent_hospital_id != hospital_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Agent does not belong to hospital {hospital_id}"
                )
            
            # Additional user validation if provided
            if current_user and not current_user.is_super_admin:
                if current_user.hospital_id != hospital_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Cannot access agent from another hospital"
                    )
            
            # Build configuration dictionary
            config = {
                "agent_id": str(row["id"]),
                "hospital_id": agent_hospital_id,
                "name": row["name"],
                "description": row["description"],
                "status": row["status"],
                "language": row["language"],
                "voice_provider": row["voice_provider"],
                "voice_name": row["voice_name"],
                "tts_pace": float(row["tts_pace"]) if row["tts_pace"] else 1.0,
                "greeting": row["greeting"],
                "system_prompt": row["system_prompt"],
                "escalation_rules": row["escalation_rules"] or {},
                "working_hours": row["working_hours"] or {},
                "transfer_phone_number": row["transfer_phone_number"],
                "appointment_behavior": row["appointment_behavior"] or {},
                "knowledge_source_ids": row["knowledge_source_ids"] or [],
                "fallback_behavior": row["fallback_behavior"],
                # Voice runtime providers
                "stt_provider": row.get("stt_provider", "openai"),
                "llm_provider": row.get("llm_provider", "openai"),
                "tts_provider": row.get("tts_provider", "openai"),
                # Language support
                "supported_languages": row.get("supported_languages", ["en-IN"]),
                # Model configuration
                "llm_model": row.get("llm_model"),
                "stt_model": row.get("stt_model"),
                "tts_model": row.get("tts_model"),
                # Tools
                "enabled_tools": row.get("enabled_tools", []),
                # Business configuration
                "business_config": row.get("business_config", {}),
            }
            
            # Validate required fields
            if not config["system_prompt"]:
                config["system_prompt"] = "You are a helpful AI assistant. Be concise and friendly."
            
            if not config["language"]:
                config["language"] = "en-IN"
            
            return config
    
    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """
        Get default agent configuration when no agent is specified.
        
        Returns:
            Default configuration dictionary
        """
        return {
            "agent_id": None,
            "hospital_id": None,
            "name": "Default Agent",
            "description": "Default voice agent",
            "status": "active",
            "language": "en-IN",
            "voice_provider": "openai",
            "voice_name": "alloy",
            "tts_pace": 1.0,
            "greeting": None,
            "system_prompt": "You are a helpful AI assistant. Be concise and friendly.",
            "escalation_rules": {},
            "working_hours": {},
            "transfer_phone_number": None,
            "appointment_behavior": {},
            "knowledge_source_ids": [],
            "fallback_behavior": None,
            "stt_provider": "openai",
            "llm_provider": "openai",
            "tts_provider": "openai",
            "supported_languages": ["en-IN"],
            "llm_model": None,
            "stt_model": None,
            "tts_model": None,
            "enabled_tools": [],
            "business_config": {},
        }


agent_config_service = AgentConfigService()
