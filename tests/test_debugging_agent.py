"""Tests for the Debugging Agent."""

import pytest
from unittest.mock import Mock, patch
from src.debugging_agent import DebuggingAgent
from src.config_loader import DebuggingAgentConfig


@pytest.fixture
def agent_config():
    """Create test agent configuration."""
    return DebuggingAgentConfig(
        model="claude-3-5-sonnet-20241022",
        temperature=0.2,
        max_tokens=8192,
        max_iterations=3
    )


@pytest.fixture
def mock_anthropic():
    """Mock Anthropic client."""
    with patch('src.debugging_agent.Anthropic') as mock:
        yield mock


class TestDebuggingAgent:
    """Test Debugging Agent."""
    
    def test_initialization(self, agent_config, mock_anthropic):
        agent = DebuggingAgent("test_api_key", agent_config)
        assert agent.config == agent_config
        assert agent.max_iterations == 3
        mock_anthropic.assert_called_once_with(api_key="test_api_key")
    
    def test_build_prompt(self, agent_config, mock_anthropic):
        agent = DebuggingAgent("test_api_key", agent_config)
        
        error_context = {
            "original_query": "SELECT * FROM table",
            "converted_query": "SELECT * FROM table",
            "error_message": "Syntax error",
            "error_details": {"line": 1},
            "previous_fixes": []
        }
        
        prompt = agent._build_prompt(error_context, 1)
        
        assert "Original Snowflake Query" in prompt
        assert "Current StarRocks Query" in prompt
        assert "Error Message" in prompt
        assert "Syntax error" in prompt
    
    def test_parse_valid_json_response(self, agent_config, mock_anthropic):
        agent = DebuggingAgent("test_api_key", agent_config)
        
        response_text = """```json
{
  "analysis": "Test analysis",
  "fixed_query": "SELECT * FROM table",
  "changes": ["Change 1"],
  "confidence": 0.95
}
```"""
        
        result = agent._parse_response(response_text)
        
        assert result["analysis"] == "Test analysis"
        assert result["fixed_query"] == "SELECT * FROM table"
        assert result["confidence"] == 0.95
        assert result["should_retry"] == True
    
    def test_parse_invalid_json_response(self, agent_config, mock_anthropic):
        agent = DebuggingAgent("test_api_key", agent_config)
        
        response_text = "This is not JSON"
        result = agent._parse_response(response_text)
        
        assert result["confidence"] == 0.0
        assert result["should_retry"] == False
    
    def test_should_continue_max_iterations(self, agent_config, mock_anthropic):
        agent = DebuggingAgent("test_api_key", agent_config)
        
        assert agent.should_continue(1, 0.9) == True
        assert agent.should_continue(3, 0.9) == False
        assert agent.should_continue(4, 0.9) == False
    
    def test_should_continue_low_confidence(self, agent_config, mock_anthropic):
        agent = DebuggingAgent("test_api_key", agent_config)
        
        # Should still continue even with low confidence (just warns)
        assert agent.should_continue(1, 0.5) == True
        assert agent.should_continue(2, 0.3) == True
