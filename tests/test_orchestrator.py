"""Tests for the Orchestrator."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.orchestrator import ConversionOrchestrator, ConversionResult


@pytest.fixture
def mock_config():
    """Mock configuration."""
    with patch('src.orchestrator.load_config') as mock:
        config = MagicMock()
        config.settings.anthropic_api_key = "test_key"
        config.settings.enable_validation = False
        mock.return_value = config
        yield config


@pytest.fixture
def orchestrator(mock_config):
    """Create orchestrator with mocked dependencies."""
    with patch('src.orchestrator.ConnectionConverterAgent'), \
         patch('src.orchestrator.QueryConverter'), \
         patch('src.orchestrator.DebuggingAgent'), \
         patch('src.orchestrator.ScriptValidator'):
        return ConversionOrchestrator()


class TestConversionResult:
    """Test ConversionResult class."""
    
    def test_successful_result(self):
        result = ConversionResult(
            success=True,
            converted_script="converted",
            original_script="original"
        )
        
        assert result.success == True
        assert result.converted_script == "converted"
        assert result.iterations == 0
        assert result.needs_manual_review == False
    
    def test_failed_result(self):
        result = ConversionResult(
            success=False,
            converted_script="converted",
            original_script="original",
            error_message="Error",
            iterations=2,
            needs_manual_review=True
        )
        
        assert result.success == False
        assert result.error_message == "Error"
        assert result.iterations == 2
        assert result.needs_manual_review == True


class TestOrchestrator:
    """Test ConversionOrchestrator."""
    
    def test_extract_connection(self, orchestrator):
        script = """
import snowflake.connector

conn = snowflake.connector.connect(
    user='test',
    password='pass',
    account='account'
)
"""
        connection = orchestrator._extract_connection(script)
        
        assert "snowflake.connector" in connection
        assert "connect" in connection
    
    def test_extract_connection_not_found(self, orchestrator):
        script = "print('Hello World')"
        connection = orchestrator._extract_connection(script)
        
        assert connection == ""
    
    def test_assemble_script(self, orchestrator):
        original = "import snowflake.connector\nconn = snowflake.connector.connect()\nquery = 'SELECT 1'"
        orig_conn = "import snowflake.connector\nconn = snowflake.connector.connect()"
        conv_conn = "import pymysql\nconn = pymysql.connect()"
        orig_queries = [("SELECT 1", 1)]
        conv_queries = [("SELECT 1", 1)]
        
        result = orchestrator._assemble_script(
            original, orig_conn, conv_conn, orig_queries, conv_queries
        )
        
        assert "Converted from Snowflake to StarRocks" in result
        assert "pymysql" in result
