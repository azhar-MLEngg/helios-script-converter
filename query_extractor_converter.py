#!/usr/bin/env python3
"""
Query Extraction and Conversion Tool
=====================================

Integrates with query_converter.py to:
1. Extract all SQL queries from Python scripts
2. Convert each query using convert_snowflake_to_starrocks()
3. Replace converted queries in the script
4. Generate detailed conversion report

Usage:
------
from query_extractor_converter import process_python_script

# Read your Python script
with open('snowflake_script.py', 'r') as f:
    script = f.read()

# Process and convert all queries
converted_script, details = process_python_script(script)

# Save results
with open('converted_starrocks_script.py', 'w') as f:
    f.write(converted_script)
"""

import re
import logging
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass

# Import your query converter
try:
    from query_converter import convert_snowflake_to_starrocks
    logger = logging.getLogger(__name__)
    logger.info("✓ Successfully imported convert_snowflake_to_starrocks from query_converter")
except ImportError as e:
    logger.error(f"✗ Failed to import query_converter: {str(e)}")
    raise

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class QueryMatch:
    """Represents a found SQL query with metadata"""
    query_text: str
    line_number: int
    column_start: int
    column_end: int
    quote_type: str  # 'single', 'double', 'triple_single', 'triple_double'
    variable_name: Optional[str] = None
    converted_query: Optional[str] = None
    conversion_successful: bool = False
    conversion_error: Optional[str] = None


class SnowflakeQueryExtractor:
    """
    Extracts SQL queries embedded in Python source code
    
    APPROACH:
    1. Find all string literals (single, double, triple-quoted)
    2. Check if they contain SQL keywords (SELECT, INSERT, WITH, etc.)
    3. Extract full query text with multi-line support
    4. Track position, line number, and variable assignment
    """
    
    # SQL keywords that indicate start of a query
    SQL_KEYWORDS = [
        r'SELECT\s', r'WITH\s', r'INSERT\s', r'UPDATE\s', 
        r'DELETE\s', r'CREATE\s', r'DROP\s', r'ALTER\s',
        r'MERGE\s', r'TRUNCATE\s'
    ]
    
    def __init__(self):
        """Initialize the extractor"""
        self.queries: List[QueryMatch] = []
    
    def extract_queries(self, script_content: str) -> List[QueryMatch]:
        """
        Extract all SQL queries from Python script
        
        Args:
            script_content: Python source code as string
            
        Returns:
            List of QueryMatch objects
        """
        self.queries = []
        lines = script_content.split('\n')
        
        # Pattern 1: Triple double-quoted strings (highest priority)
        self._extract_by_pattern(script_content, lines, r'"""((?:.*?)?)"""', 'triple_double', re.DOTALL)
        
        # Pattern 2: Triple single-quoted strings
        self._extract_by_pattern(script_content, lines, r"'''((?:.*?)?)'''", 'triple_single', re.DOTALL)
        
        # Pattern 3: Double-quoted strings
        self._extract_by_pattern(script_content, lines, r'\"((?:[^"\\]|\\.)*)\"', 'double')
        
        # Pattern 4: Single-quoted strings
        self._extract_by_pattern(script_content, lines, r"'((?:[^'\\]|\\.)*)'", 'single')
        
        # Filter to keep only SQL queries
        self.queries = self._filter_sql_queries(self.queries)
        
        # Sort by line number
        self.queries.sort(key=lambda x: x.line_number)
        
        return self.queries
    
    def _extract_by_pattern(self, content: str, lines: List[str], pattern: str, 
                            quote_type: str, flags=0):
        """Extract queries matching a specific string pattern"""
        for match in re.finditer(pattern, content, flags):
            query_text = match.group(1)
            
            # Skip empty queries
            if not query_text.strip():
                continue
            
            # Find line number
            line_num = content[:match.start()].count('\n') + 1
            
            # Check if this matches a variable assignment
            var_name = self._get_variable_name(content, match.start())
            
            query_match = QueryMatch(
                query_text=query_text,
                line_number=line_num,
                column_start=match.start(),
                column_end=match.end(),
                quote_type=quote_type,
                variable_name=var_name
            )
            
            self.queries.append(query_match)
    
    def _filter_sql_queries(self, queries: List[QueryMatch]) -> List[QueryMatch]:
        """Filter to keep only strings that contain SQL keywords"""
        sql_queries = []
        
        for query in queries:
            text_upper = query.query_text.upper()
            
            # Check if any SQL keyword is present
            is_sql = any(re.search(keyword, text_upper) for keyword in self.SQL_KEYWORDS)
            
            if is_sql:
                sql_queries.append(query)
        
        return sql_queries
    
    def _get_variable_name(self, content: str, string_pos: int) -> Optional[str]:
        """
        Try to find variable name if query is assigned to a variable
        
        Example: query = "SELECT ..." -> returns "query"
        """
        # Look backwards from the string to find variable assignment
        before_text = content[:string_pos]
        
        # Pattern: variable_name = "string"
        match = re.search(r'(\w+)\s*=\s*["\']?$', before_text)
        
        if match:
            return match.group(1)
        
        return None


class QueryConverterProcessor:
    """
    Main processor that:
    1. Extracts queries from Python script
    2. Converts each query using your converter logic
    3. Replaces queries in the script
    4. Returns updated script and conversion details
    
    APPROACH:
    - Phase 1: Extract all embedded SQL queries
    - Phase 2: Convert each using convert_snowflake_to_starrocks()
    - Phase 3: Replace in script (preserving quotes and formatting)
    - Phase 4: Generate detailed report
    """
    
    def __init__(self):
        """Initialize processor"""
        self.extractor = SnowflakeQueryExtractor()
    
    def process_script(self, script_content: str, verbose: bool = True) -> Tuple[str, List[Dict]]:
        """
        Process a Python script and convert all embedded Snowflake queries
        
        Args:
            script_content: Python source code
            verbose: Print detailed conversion info
            
        Returns:
            Tuple of (converted_script, conversion_details)
        """
        # Step 1: Extract queries
        queries = self.extractor.extract_queries(script_content)
        
        if verbose:
            print(f"\n{'='*80}")
            print(f"[STEP 1] QUERY EXTRACTION")
            print(f"{'='*80}")
            print(f"\n✓ Found {len(queries)} SQL queries in script\n")
        
        if not queries:
            return script_content, []
        
        # Step 2: Convert queries using your converter
        if verbose:
            print(f"{'='*80}")
            print(f"[STEP 2] QUERY CONVERSION")
            print(f"{'='*80}\n")
        
        conversion_details = []
        updated_script = script_content
        
        for i, query_match in enumerate(queries):
            query_num = i + 1
            
            if verbose:
                print(f"[Query {query_num}] Line {query_match.line_number}")
                if query_match.variable_name:
                    print(f"  Variable: {query_match.variable_name}")
                print(f"  Quote Type: {query_match.quote_type}")
            
            try:
                # Convert using your converter
                converted = convert_snowflake_to_starrocks(query_match.query_text)
                
                query_match.converted_query = converted
                query_match.conversion_successful = True
                
                if verbose:
                    print(f"  Status: ✓ CONVERTED")
                    original_preview = query_match.query_text[:60].replace('\n', ' ')
                    converted_preview = converted[:60].replace('\n', ' ')
                    print(f"  Original:  {original_preview}...")
                    print(f"  Converted: {converted_preview}...\n")
                
            except Exception as e:
                query_match.conversion_successful = False
                query_match.conversion_error = str(e)
                
                if verbose:
                    print(f"  Status: ✗ FAILED")
                    print(f"  Error: {str(e)}\n")
            
            # Prepare conversion detail
            detail = {
                "query_number": query_num,
                "line_number": query_match.line_number,
                "variable_name": query_match.variable_name,
                "quote_type": query_match.quote_type,
                "original_query": query_match.query_text,
                "converted_query": query_match.converted_query,
                "conversion_successful": query_match.conversion_successful,
                "conversion_error": query_match.conversion_error,
                "changed": converted != query_match.query_text if converted else False
            }
            conversion_details.append(detail)
        
        # Step 3: Replace queries in script (in reverse order to preserve positions)
        if verbose:
            print(f"{'='*80}")
            print(f"[STEP 3] SCRIPT REPLACEMENT")
            print(f"{'='*80}\n")
        
        successful_replacements = 0
        
        for query_match in reversed(queries):
            if query_match.conversion_successful and query_match.converted_query:
                # Get quote characters
                quote_map = {
                    'single': "'",
                    'double': '"',
                    'triple_single': "'''",
                    'triple_double': '"""'
                }
                quote_char = quote_map.get(query_match.quote_type, '"')
                
                # Build original and replacement strings
                original_string = f"{quote_char}{query_match.query_text}{quote_char}"
                converted_string = f"{quote_char}{query_match.converted_query}{quote_char}"
                
                # Replace in script (using exact position to avoid duplicates)
                # We'll use a simple string replace for now
                updated_script = updated_script.replace(
                    original_string,
                    converted_string,
                    1  # Replace only first occurrence
                )
                successful_replacements += 1
                
                if verbose:
                    print(f"✓ Replaced query {query_match.variable_name or 'at line ' + str(query_match.line_number)}")
        
        if verbose:
            print(f"\n✓ Successfully replaced {successful_replacements} out of {len(queries)} queries\n")
        
        return updated_script, conversion_details


def process_python_script(script_content: str, verbose: bool = True) -> Tuple[str, List[Dict]]:
    """
    Convenience function to process a Python script
    
    Args:
        script_content: Python source code containing Snowflake queries
        verbose: Print detailed information
        
    Returns:
        Tuple of (converted_script, conversion_details)
    """
    processor = QueryConverterProcessor()
    return processor.process_script(script_content, verbose=verbose)


def print_summary(conversion_details: List[Dict]):
    """Print conversion summary"""
    if not conversion_details:
        print("No queries found to convert")
        return
    
    print(f"\n{'='*80}")
    print("CONVERSION SUMMARY")
    print(f"{'='*80}\n")
    
    successful = sum(1 for d in conversion_details if d['conversion_successful'])
    failed = len(conversion_details) - successful
    changed = sum(1 for d in conversion_details if d['changed'])
    
    print(f"Total Queries Found:       {len(conversion_details)}")
    print(f"Successfully Converted:    {successful}")
    print(f"Conversion Errors:         {failed}")
    print(f"Queries with Changes:      {changed}")
    
    if failed > 0:
        print(f"\n{'='*80}")
        print("FAILED CONVERSIONS")
        print(f"{'='*80}\n")
        for detail in conversion_details:
            if not detail['conversion_successful']:
                print(f"Query #{detail['query_number']} (Line {detail['line_number']})")
                print(f"  Variable: {detail['variable_name'] or 'Not assigned'}")
                print(f"  Error: {detail['conversion_error']}\n")


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def main():
    """Example: Process a Python script with Snowflake queries"""
    
    # Example Python script with Snowflake queries
    example_script = '''#!/usr/bin/env python3
from helios_python_sdk.services.starrocks_client import StarRocksClient

client = StarRocksClient()

# Query 1: Simple SELECT with DATEDIFF
query1 = """
SELECT 
    customer_id,
    DATEDIFF('day', created_date, current_date) as days_since_creation,
    CAST(amount as DECIMAL(10,2)) as amount
FROM CSPL_DB.SCHEMA.CUSTOMERS
WHERE status = 'active'
"""

# Query 2: Query with TO_TIMESTAMP_NTZ
query2 = 'SELECT * FROM CSPL_DB.ADMIN.ORDERS WHERE created_at > TO_TIMESTAMP_NTZ(\\\'2023-01-01\\\')'

# Query 3: Complex query with multiple tables
insert_query = """
INSERT INTO CSPL_DB.PROD.AUDIT_LOG
SELECT 
    appointment_id,
    TO_TIMESTAMP_NTZ(event_time) as event_timestamp,
    action_type
FROM CSPL_DB.STAGING.EVENTS
WHERE processed = FALSE
"""

# Execute queries
print("Processing queries...")
result1 = execute_query(query1)
result2 = execute_query(query2)
'''
    
    print("\n" + "#"*80)
    print("# SNOWFLAKE QUERY EXTRACTION AND CONVERSION")
    print("#"*80)
    
    # Process the script
    converted_script, details = process_python_script(example_script, verbose=True)
    
    # Display summary
    print_summary(details)
    
    # Display converted script
    print(f"\n{'='*80}")
    print("CONVERTED SCRIPT")
    print(f"{'='*80}\n")
    print(converted_script)
    
    # Display detailed results
    if details:
        print(f"\n{'='*80}")
        print("DETAILED CONVERSIONS")
        print(f"{'='*80}")
        
        for detail in details:
            print(f"\n[Query #{detail['query_number']}] Line {detail['line_number']}")
            if detail['variable_name']:
                print(f"  Variable: {detail['variable_name']}")
            print(f"  Status: {'✓ SUCCESS' if detail['conversion_successful'] else '✗ FAILED'}")
            if detail['conversion_error']:
                print(f"  Error: {detail['conversion_error']}")


if __name__ == "__main__":
    main()