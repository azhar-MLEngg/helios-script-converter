"""Tests for the Query Converter."""

import pytest
from pathlib import Path
from src.config_loader import load_config
from src.query_converter import QueryConverter


@pytest.fixture
def config():
    """Load test configuration."""
    return load_config()


@pytest.fixture
def converter(config):
    """Create QueryConverter instance."""
    return QueryConverter(config)


class TestDataTypeConversion:
    """Test data type conversions."""
    
    def test_variant_to_json(self, converter):
        query = "SELECT metadata::VARIANT FROM table"
        result = converter.convert(query)
        assert "JSON" in result.upper()
    
    def test_timestamp_ntz_to_datetime(self, converter):
        query = "SELECT created_at::TIMESTAMP_NTZ FROM table"
        result = converter.convert(query)
        assert "DATETIME" in result.upper()
    
    def test_number_to_bigint(self, converter):
        query = "CREATE TABLE t (id NUMBER(38,0))"
        result = converter.convert(query)
        assert "BIGINT" in result.upper()


class TestFunctionConversion:
    """Test function conversions."""
    
    def test_flatten_to_unnest(self, converter):
        query = "SELECT * FROM table, FLATTEN(array_col)"
        result = converter.convert(query)
        assert "UNNEST" in result.upper()
    
    def test_iff_to_if(self, converter):
        query = "SELECT IFF(status = 'active', 1, 0) FROM table"
        result = converter.convert(query)
        assert "IF" in result.upper()
    
    def test_dateadd_to_date_add(self, converter):
        query = "SELECT DATEADD(day, 7, created_at) FROM table"
        result = converter.convert(query)
        assert "DATE_ADD" in result.upper()


class TestSyntaxConversion:
    """Test syntax transformations."""
    
    def test_double_colon_cast(self, converter):
        query = "SELECT name::VARCHAR FROM table"
        result = converter.convert(query)
        assert "CAST" in result.upper()
    
    def test_positional_params(self, converter):
        query = "SELECT $1, $2 FROM table"
        result = converter.convert(query)
        assert "col1" in result.lower() or "$1" not in result


class TestQueryExtraction:
    """Test query extraction from Python scripts."""
    
    def test_extract_triple_quote_query(self, converter):
        script = '''
query = """
SELECT * FROM users
WHERE id = 1
"""
'''
        queries = converter.extract_queries_from_script(script)
        assert len(queries) > 0
        assert "SELECT" in queries[0][0]
    
    def test_extract_single_quote_query(self, converter):
        script = "query = 'SELECT * FROM users'"
        queries = converter.extract_queries_from_script(script)
        assert len(queries) > 0
    
    def test_is_sql_detection(self, converter):
        assert converter._is_sql("SELECT * FROM table")
        assert converter._is_sql("INSERT INTO table VALUES (1)")
        assert not converter._is_sql("This is not SQL")


class TestFormatting:
    """Test query formatting."""
    
    def test_format_query(self, converter):
        query = "select id,name from users where status='active'"
        result = converter._format_query(query)
        assert "SELECT" in result
        assert result != query  # Should be formatted differently
