"""Query Converter - Deterministic Rule-Based Conversion."""

import re
from typing import Any, Dict, List, Tuple

import sqlglot
from loguru import logger
from sqlparse import format as sql_format
from sqlparse import parse as sql_parse

from .config_loader import ConfigLoader


class QueryConverter:
    """Deterministic rule-based SQL query converter."""
    
    def __init__(self, config: ConfigLoader):
        """Initialize the Query Converter.
        
        Args:
            config: Configuration loader instance.
        """
        self.config = config
        self.rules = config.get_conversion_rules()
        logger.info("Initialized QueryConverter with conversion rules")
    
    def convert(self, snowflake_query: str) -> str:
        """Convert Snowflake SQL query to StarRocks format.
        
        Args:
            snowflake_query: SQL query in Snowflake dialect.
            
        Returns:
            SQL query in StarRocks dialect.
        """
        logger.info("Converting Snowflake query to StarRocks format")
        
        query = snowflake_query
        
        # Step 1: Apply data type conversions
        query = self._convert_data_types(query)
        
        # Step 2: Apply function conversions
        query = self._convert_functions(query)
        
        # Step 3: Apply syntax transformations
        query = self._convert_syntax(query)
        
        # Step 4: Apply DDL conversions
        query = self._convert_ddl(query)
        
        # Step 5: Use sqlglot for advanced transpilation
        query = self._transpile_with_sqlglot(query)
        
        # Step 6: Format the final query
        query = self._format_query(query)
        
        logger.success("Successfully converted query to StarRocks format")
        logger.debug(f"Converted query:\n{query}")
        
        return query
    
    def _convert_data_types(self, query: str) -> str:
        """Convert Snowflake data types to StarRocks equivalents.
        
        Args:
            query: SQL query.
            
        Returns:
            Query with converted data types.
        """
        data_types = self.rules.get("data_types", {})
        
        for snowflake_type, starrocks_type in data_types.items():
            # Handle parameterized types like NUMBER(38,0)
            if "(" in snowflake_type:
                pattern = re.escape(snowflake_type)
                query = re.sub(pattern, starrocks_type, query, flags=re.IGNORECASE)
            else:
                # Word boundary matching for simple types
                pattern = r'\b' + re.escape(snowflake_type) + r'\b'
                query = re.sub(pattern, starrocks_type, query, flags=re.IGNORECASE)
        
        return query
    
    def _convert_functions(self, query: str) -> str:
        """Convert Snowflake functions to StarRocks equivalents.
        
        Args:
            query: SQL query.
            
        Returns:
            Query with converted functions.
        """
        functions = self.rules.get("functions", {})
        
        for snowflake_func, starrocks_func in functions.items():
            # Match function calls with parentheses
            pattern = r'\b' + re.escape(snowflake_func) + r'\s*\('
            replacement = starrocks_func + '('
            query = re.sub(pattern, replacement, query, flags=re.IGNORECASE)
        
        return query
    
    def _convert_syntax(self, query: str) -> str:
        """Apply syntax pattern transformations.
        
        Args:
            query: SQL query.
            
        Returns:
            Query with converted syntax.
        """
        syntax_patterns = self.rules.get("syntax_patterns", [])
        
        for rule in syntax_patterns:
            pattern = rule.get("pattern")
            replacement = rule.get("replacement")
            description = rule.get("description", "")
            
            if not pattern or not replacement:
                continue
            
            # Special handling for different patterns
            if replacement == "CAST_AS":
                query = self._convert_double_colon_cast(query)
            elif replacement == "CONCAT":
                query = self._convert_pipe_concat(query)
            elif replacement == "NAMED_COLUMN":
                query = self._convert_positional_params(query)
            elif replacement == "SUBQUERY_WITH_ROW_NUMBER":
                query = self._convert_qualify_clause(query)
            else:
                query = re.sub(pattern, replacement, query, flags=re.IGNORECASE)
        
        return query
    
    def _convert_ddl(self, query: str) -> str:
        """Convert DDL statements.
        
        Args:
            query: SQL query.
            
        Returns:
            Query with converted DDL.
        """
        ddl_conversions = self.rules.get("ddl_conversions", [])
        
        for rule in ddl_conversions:
            pattern = rule.get("pattern")
            replacement = rule.get("replacement")
            
            if pattern and replacement:
                query = re.sub(pattern, replacement, query, flags=re.IGNORECASE)
        
        return query
    
    def _convert_double_colon_cast(self, query: str) -> str:
        """Convert :: casting to CAST(... AS ...).
        
        Args:
            query: SQL query.
            
        Returns:
            Query with converted casting.
        """
        # Pattern: column_name::data_type
        pattern = r'(\w+)\s*::\s*(\w+(?:\([^)]+\))?)'
        replacement = r'CAST(\1 AS \2)'
        
        return re.sub(pattern, replacement, query)
    
    def _convert_pipe_concat(self, query: str) -> str:
        """Convert || concatenation to CONCAT().
        
        Args:
            query: SQL query.
            
        Returns:
            Query with converted concatenation.
        """
        # This is complex - for now, simple replacement
        # TODO: Implement proper expression parsing
        parts = query.split('||')
        if len(parts) > 1:
            # Simple case: a || b || c -> CONCAT(a, b, c)
            concatenated = ', '.join(part.strip() for part in parts)
            return f'CONCAT({concatenated})'
        
        return query
    
    def _convert_positional_params(self, query: str) -> str:
        """Convert positional parameters ($1, $2) to named columns.
        
        Args:
            query: SQL query.
            
        Returns:
            Query with named columns.
        """
        # Pattern: $1, $2, etc.
        # Replace with col1, col2, etc. (generic names)
        pattern = r'\$(\d+)'
        replacement = r'col\1'
        
        return re.sub(pattern, replacement, query)
    
    def _convert_qualify_clause(self, query: str) -> str:
        """Convert QUALIFY clause to subquery with ROW_NUMBER().
        
        Args:
            query: SQL query.
            
        Returns:
            Query with converted QUALIFY.
        """
        # Check if QUALIFY exists
        if not re.search(r'\bQUALIFY\b', query, re.IGNORECASE):
            return query
        
        # This is complex - simplified implementation
        # TODO: Implement full QUALIFY conversion with proper parsing
        logger.warning("QUALIFY clause detected - manual review recommended")
        
        return query
    
    def _transpile_with_sqlglot(self, query: str) -> str:
        """Use sqlglot for advanced SQL transpilation.
        
        Args:
            query: SQL query.
            
        Returns:
            Transpiled query.
        """
        try:
            # Transpile from Snowflake to MySQL (StarRocks uses MySQL protocol)
            transpiled = sqlglot.transpile(
                query,
                read="snowflake",
                write="mysql",
                pretty=True
            )
            
            if transpiled:
                return transpiled[0]
            
        except Exception as e:
            logger.warning(f"sqlglot transpilation failed: {str(e)}, using rule-based conversion")
        
        return query
    
    def _format_query(self, query: str) -> str:
        """Format SQL query for readability.
        
        Args:
            query: SQL query.
            
        Returns:
            Formatted query.
        """
        return sql_format(query, reindent=True, keyword_case='upper')
    
    def extract_queries_from_script(self, script: str) -> List[Tuple[str, int]]:
        """Extract SQL queries from Python script.
        
        Args:
            script: Python script content.
            
        Returns:
            List of tuples (query, line_number).
        """
        queries = []
        
        # Pattern 1: Multi-line strings with SQL
        triple_quote_pattern = r'("""|\'\'\')(.*?)\1'
        matches = re.finditer(triple_quote_pattern, script, re.DOTALL)
        
        for match in matches:
            content = match.group(2).strip()
            # Check if it looks like SQL
            if self._is_sql(content):
                line_num = script[:match.start()].count('\n') + 1
                queries.append((content, line_num))
        
        # Pattern 2: Single-line strings with SQL
        single_quote_pattern = r'["\']([^"\']*(?:SELECT|INSERT|UPDATE|DELETE|CREATE)[^"\']*)["\']'
        matches = re.finditer(single_quote_pattern, script, re.IGNORECASE)
        
        for match in matches:
            content = match.group(1).strip()
            if self._is_sql(content):
                line_num = script[:match.start()].count('\n') + 1
                queries.append((content, line_num))
        
        return queries
    
    def _is_sql(self, text: str) -> bool:
        """Check if text looks like SQL.
        
        Args:
            text: Text to check.
            
        Returns:
            True if text appears to be SQL.
        """
        sql_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER', 'FROM', 'WHERE']
        text_upper = text.upper()
        
        return any(keyword in text_upper for keyword in sql_keywords)
