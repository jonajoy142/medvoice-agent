"""Tests for agent configuration service."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from app.services.agent_config_service import AgentConfigService


class TestAgentConfigService:
    """Tests for agent configuration loading."""
    
    @patch('app.services.agent_config_service.check_db_connection')
    @patch('app.services.agent_config_service.db_session')
    def test_load_agent_config_success(self, mock_db_session, mock_check_db):
        """Test successful agent configuration loading."""
        mock_check_db.return_value = True
        
        # Mock database response
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db
        
        mock_row = {
            "id": "agent-uuid-1",
            "hospital_id": "hospital-uuid-1",
            "name": "Test Agent",
            "description": "Test description",
            "status": "active",
            "language": "en-IN",
            "voice_provider": "openai",
            "voice_name": "alloy",
            "tts_pace": 1.0,
            "greeting": "Hello",
            "system_prompt": "You are helpful",
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
            "llm_model": "gpt-4o-mini",
            "stt_model": None,
            "tts_model": None,
            "enabled_tools": [],
            "business_config": {},
        }
        mock_db.execute.return_value.mappings.return_value.first.return_value = mock_row
        
        service = AgentConfigService()
        config = service.load_agent_config("agent-uuid-1", "hospital-uuid-1")
        
        assert config["agent_id"] == "agent-uuid-1"
        assert config["hospital_id"] == "hospital-uuid-1"
        assert config["name"] == "Test Agent"
        assert config["stt_provider"] == "openai"
        assert config["llm_provider"] == "openai"
        assert config["tts_provider"] == "openai"
    
    @patch('app.services.agent_config_service.check_db_connection')
    @patch('app.services.agent_config_service.db_session')
    def test_load_agent_config_not_found(self, mock_db_session, mock_check_db):
        """Test loading non-existent agent raises 404."""
        mock_check_db.return_value = True
        
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db
        mock_db.execute.return_value.mappings.return_value.first.return_value = None
        
        service = AgentConfigService()
        
        with pytest.raises(HTTPException) as exc_info:
            service.load_agent_config("non-existent", "hospital-uuid-1")
        assert exc_info.value.status_code == 404
    
    @patch('app.services.agent_config_service.check_db_connection')
    @patch('app.services.agent_config_service.db_session')
    def test_load_agent_config_tenant_mismatch(self, mock_db_session, mock_check_db):
        """Test loading agent from different hospital raises 403."""
        mock_check_db.return_value = True
        
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db
        
        mock_row = {
            "id": "agent-uuid-1",
            "hospital_id": "different-hospital",
            "name": "Test Agent",
            "description": None,
            "status": "active",
            "language": "en-IN",
            "voice_provider": "openai",
            "voice_name": "alloy",
            "tts_pace": 1.0,
            "greeting": None,
            "system_prompt": "You are helpful",
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
        mock_db.execute.return_value.mappings.return_value.first.return_value = mock_row
        
        service = AgentConfigService()
        
        with pytest.raises(HTTPException) as exc_info:
            service.load_agent_config("agent-uuid-1", "hospital-uuid-1")
        assert exc_info.value.status_code == 403
    
    @patch('app.services.agent_config_service.check_db_connection')
    def test_load_agent_config_db_unavailable(self, mock_check_db):
        """Test loading agent when database unavailable raises 503."""
        mock_check_db.return_value = False
        
        service = AgentConfigService()
        
        with pytest.raises(HTTPException) as exc_info:
            service.load_agent_config("agent-uuid-1", "hospital-uuid-1")
        assert exc_info.value.status_code == 503
    
    def test_get_default_config(self):
        """Test getting default agent configuration."""
        service = AgentConfigService()
        config = service.get_default_config()
        
        assert config["agent_id"] is None
        assert config["hospital_id"] is None
        assert config["name"] == "Default Agent"
        assert config["stt_provider"] == "openai"
        assert config["llm_provider"] == "openai"
        assert config["tts_provider"] == "openai"
        assert config["language"] == "en-IN"
        assert config["system_prompt"] is not None
