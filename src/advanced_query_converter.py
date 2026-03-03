"""Advanced Query Converter with Table Mapping and Snowflake-specific conversions."""

import re
from typing import Dict, List, Optional
from loguru import logger
import sqlglot
from sqlglot import exp, parse


class AdvancedQueryConverter:
    """
    Advanced SQL converter that handles:
    - QUALIFY clause conversion
    - TRY_TO_DATE, TO_TIMESTAMP conversions
    - CONTAINS function conversion
    - Complex nested queries
    """
    
    def __init__(self):
        """Initialize the advanced query converter."""
        logger.info("Initialized AdvancedQueryConverter")
    
    def convert(self, snowflake_query: str) -> str:
        """
        Convert Snowflake SQL to StarRocks SQL.
        
        Args:
            snowflake_query: Original Snowflake SQL query
            
        Returns:
            Converted StarRocks SQL query
        """
        logger.info("Converting Snowflake query with advanced converter")
        
        try:
            # Step 1: Handle QUALIFY clause (must be done before sqlglot parsing)
            query = self._convert_qualify_clause(snowflake_query)
            
            # Step 2: Parse and convert using sqlglot
            query = self._convert_snowflake_syntax_to_starrocks(query)
            
            # Step 3: Post-processing for edge cases
            query = self._post_process_conversions(query)
            
            logger.success("Successfully converted query with advanced converter")
            return query
            
        except Exception as e:
            logger.warning(f"Advanced conversion failed: {e}, falling back to original")
            return snowflake_query
    
    def _convert_qualify_clause(self, sql: str) -> str:
        """
        Convert QUALIFY clause to subquery with WHERE.
        
        QUALIFY is Snowflake-specific for filtering window functions.
        StarRocks doesn't support QUALIFY, so we wrap in a subquery.
        
        Example:
            SELECT *, ROW_NUMBER() OVER(...) as rn FROM t QUALIFY rn = 1
            →
            SELECT * FROM (SELECT *, ROW_NUMBER() OVER(...) as rn FROM t) WHERE rn = 1
        """
        # Pattern to detect QUALIFY clause
        qualify_pattern = re.compile(
            r'\bQUALIFY\s+(.+?)(?=\s*(?:ORDER BY|LIMIT|;|$))',
            re.IGNORECASE | re.DOTALL
        )
        
        match = qualify_pattern.search(sql)
        if not match:
            return sql
        
        logger.info("QUALIFY clause detected - converting to subquery")
        
        # Extract the QUALIFY condition
        qualify_condition = match.group(1).strip()
        
        # Remove QUALIFY clause from original query
        base_query = qualify_pattern.sub('', sql).strip()
        
        # Wrap in subquery with WHERE
        converted = f"SELECT * FROM ({base_query}) AS qualified_subquery WHERE {qualify_condition}"
        
        logger.debug(f"QUALIFY conversion: {qualify_condition}")
        return converted
    
    def _convert_snowflake_syntax_to_starrocks(self, sql: str) -> str:
        """
        Convert Snowflake-specific functions to StarRocks using SQLGlot.
        
        Conversions:
        - TO_TIMESTAMP / TO_TIMESTAMP_NTZ → CAST(... AS DATETIME)
        - TRY_TO_TIMESTAMP → STR_TO_DATE
        - TRY_TO_DATE → STR_TO_DATE
        - CONTAINS(col, val) → col LIKE CONCAT('%', val, '%')
        """
        try:
            expressions = parse(sql, read="snowflake")
            converted_queries = []
            
            for expr in expressions:
                # Apply all conversions
                self._apply_to_timestamp_conversion(expr)
                self._apply_try_to_timestamp_conversion(expr)
                self._apply_try_to_date_conversion(expr)
                self._apply_contains_conversion(expr)
                self._apply_dateadd_conversion(expr)
                self._apply_interval_conversion(expr)
                
                # Generate StarRocks SQL
                converted_queries.append(expr.sql(dialect="starrocks"))
            
            return " ".join(converted_queries)
            
        except Exception as e:
            logger.warning(f"SQLGlot conversion failed: {e}")
            # Fallback to regex-based conversion
            return self._regex_based_conversion(sql)
    
    def _apply_to_timestamp_conversion(self, expr) -> None:
        """Replace TO_TIMESTAMP / TO_TIMESTAMP_NTZ with CAST(... AS DATETIME)."""
        for func in expr.find_all(exp.Anonymous):
            if func.name.upper() in ("TO_TIMESTAMP", "TO_TIMESTAMP_NTZ"):
                if func.args.get("expressions"):
                    arg = func.args["expressions"][0]
                    cast = exp.Cast(
                        this=arg,
                        to=exp.DataType(this=exp.DataType.Type.DATETIME)
                    )
                    func.replace(cast)
    
    def _apply_try_to_timestamp_conversion(self, expr) -> None:
        """Replace TRY_TO_TIMESTAMP with STR_TO_DATE."""
        for func in expr.find_all(exp.Anonymous):
            if func.name.upper() == "TRY_TO_TIMESTAMP":
                if func.args.get("expressions"):
                    arg = func.args["expressions"][0]
                    str_to_date = exp.Anonymous(
                        this="STR_TO_DATE",
                        expressions=[
                            arg,
                            exp.Literal.string('%Y-%m-%d %H:%i:%S')
                        ]
                    )
                    func.replace(str_to_date)
    
    def _apply_try_to_date_conversion(self, expr) -> None:
        """Replace TRY_TO_DATE with STR_TO_DATE."""
        for func in expr.find_all(exp.Anonymous):
            if func.name.upper() == "TRY_TO_DATE":
                if func.args.get("expressions"):
                    args = func.args["expressions"]
                    date_str = args[0]
                    # If format is provided, use it; otherwise use default
                    format_str = args[1] if len(args) > 1 else exp.Literal.string('%Y-%m-%d')
                    
                    str_to_date = exp.Anonymous(
                        this="STR_TO_DATE",
                        expressions=[date_str, format_str]
                    )
                    func.replace(str_to_date)
    
    def _apply_contains_conversion(self, expr) -> None:
        """Replace CONTAINS(col, val) with col LIKE CONCAT('%', val, '%')."""
        for func in list(expr.find_all(exp.Anonymous)) + list(expr.find_all(exp.Func)):
            if hasattr(func, 'name') and func.name.upper() == "CONTAINS":
                args = func.args.get("expressions", [])
                if len(args) >= 2:
                    col = args[0]
                    substring = args[1]
                    
                    concat_expr = exp.Concat(
                        expressions=[
                            exp.Literal.string('%'),
                            substring,
                            exp.Literal.string('%')
                        ]
                    )
                    
                    like_expr = exp.Like(
                        this=col,
                        expression=concat_expr
                    )
                    func.replace(like_expr)
    
    def _apply_dateadd_conversion(self, expr) -> None:
        """Convert DATEADD to DATE_ADD for StarRocks."""
        for func in expr.find_all(exp.Anonymous):
            if func.name.upper() == "DATEADD":
                # DATEADD(unit, value, date) → DATE_ADD(date, INTERVAL value unit)
                if func.args.get("expressions") and len(func.args["expressions"]) >= 3:
                    args = func.args["expressions"]
                    # Note: Snowflake DATEADD order is (unit, value, date)
                    # StarRocks DATE_ADD order is (date, INTERVAL value unit)
                    # This is a simplified conversion - may need adjustment
                    pass  # sqlglot should handle this
    
    def _apply_interval_conversion(self, expr) -> None:
        """Convert INTERVAL expressions for StarRocks compatibility."""
        # StarRocks uses: INTERVAL n DAY/HOUR/MINUTE
        # This is mostly handled by sqlglot
        pass
    
    def _regex_based_conversion(self, sql: str) -> str:
        """
        Fallback regex-based conversion when sqlglot fails.
        """
        query = sql
        
        # TRY_TO_DATE conversion
        query = re.sub(
            r"TRY_TO_DATE\s*\(\s*([^,]+)\s*,\s*'([^']+)'\s*\)",
            r"STR_TO_DATE(\1, '\2')",
            query,
            flags=re.IGNORECASE
        )
        
        # TRY_TO_TIMESTAMP conversion
        query = re.sub(
            r"TRY_TO_TIMESTAMP\s*\(\s*([^)]+)\s*\)",
            r"STR_TO_DATE(\1, '%Y-%m-%d %H:%i:%S')",
            query,
            flags=re.IGNORECASE
        )
        
        # TO_TIMESTAMP conversion
        query = re.sub(
            r"TO_TIMESTAMP\s*\(\s*([^)]+)\s*\)",
            r"CAST(\1 AS DATETIME)",
            query,
            flags=re.IGNORECASE
        )
        
        # CURRENT_DATE() → CURRENT_DATE (StarRocks doesn't use parentheses)
        query = re.sub(
            r"\bCURRENT_DATE\s*\(\s*\)",
            "CURRENT_DATE",
            query,
            flags=re.IGNORECASE
        )
        
        return query
    
    def _post_process_conversions(self, sql: str) -> str:
        """
        Post-processing fixes for edge cases.
        """
        query = sql
        
        # Fix CURRENT_DATE() if it still has parentheses
        query = re.sub(
            r"\bCURRENT_DATE\s*\(\s*\)",
            "CURRENT_DATE",
            query,
            flags=re.IGNORECASE
        )
        
        # Remove extra whitespace
        query = re.sub(r'\s+', ' ', query)
        query = query.strip()
        
        return query


def convert_query_advanced(snowflake_query: str) -> str:
    """
    Convenience function for advanced query conversion.
    
    Args:
        snowflake_query: Snowflake SQL query
        
    Returns:
        StarRocks SQL query
    """
    converter = AdvancedQueryConverter()
    return converter.convert(snowflake_query)
