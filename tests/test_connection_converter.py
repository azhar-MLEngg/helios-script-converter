"""Tests for the Connection Converter Agent."""

import pytest
from unittest.mock import Mock, patch
from src.connection_converter import ConnectionConverterAgent
from src.config_loader import AgentConfig


@pytest.fixture
def agent_config():
    """Create test agent configuration."""
    return AgentConfig(
        model="claude-3-5-sonnet-20241022",
        temperature=0.1,
        max_tokens=4096
    )


@pytest.fixture
def mock_anthropic():
    """Mock Anthropic client."""
    with patch('src.connection_converter.Anthropic') as mock:
        yield mock


class TestConnectionConverterAgent:
    """Test Connection Converter Agent."""
    
    def test_initialization(self, agent_config, mock_anthropic):
        agent = ConnectionConverterAgent("test_api_key", agent_config)
        assert agent.config == agent_config
        mock_anthropic.assert_called_once_with(api_key="test_api_key")
    
    def test_clean_code_blocks(self, agent_config, mock_anthropic):
        agent = ConnectionConverterAgent("test_api_key", agent_config)
        
        code_with_markers = "```python\nimport pymysql\n```"
        cleaned = agent._clean_code_blocks(code_with_markers)
        assert "```" not in cleaned
        assert "import pymysql" in cleaned
    
    def test_build_prompt(self, agent_config, mock_anthropic):
        agent = ConnectionConverterAgent("test_api_key", agent_config)
        
        snowflake_conn = "import snowflake.connector\nconn = snowflake.connector.connect(...)"
        prompt = agent._build_prompt(snowflake_conn)
        
        assert "Snowflake Connection" in prompt
        assert "StarRocks" in prompt
        assert "pymysql" in prompt
        assert snowflake_conn in prompt
    
    def test_extract_connection_params(self, agent_config, mock_anthropic):
        agent = ConnectionConverterAgent("test_api_key", agent_config)
        
        connection_code = """
conn = pymysql.connect(
    host='localhost',
    port=9030,
    user='root',
    database='test_db'
)
"""
        params = agent.extract_connection_params(connection_code)
        
        assert params is not None
        assert 'host' in params
        assert 'port' in params
        assert params['host'] == 'localhost'
