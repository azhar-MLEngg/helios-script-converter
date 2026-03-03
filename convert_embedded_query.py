"""
Script to convert embedded SQL queries in Python files.
This handles the QUERY variable conversion that was missing.
"""

import re
from src.advanced_query_converter import AdvancedQueryConverter

def extract_and_convert_embedded_queries(python_code: str) -> str:
    """
    Find embedded SQL queries in Python code and convert them.
    
    Looks for patterns like:
    QUERY = triple-quoted strings
    query = triple-quoted strings
    sql = triple-quoted strings
    """
    converter = AdvancedQueryConverter()
    
    # Pattern to match multi-line string assignments
    # Matches: VARIABLE = """...""" or VARIABLE = '''...'''
    pattern = r'(\b(?:QUERY|query|sql|SQL)\s*=\s*)("""|\'\'\')(.*?)\2'
    
    def convert_match(match):
        prefix = match.group(1)  # Variable assignment part
        quote = match.group(2)   # Triple quote type
        sql_content = match.group(3)  # SQL query content
        
        print(f"\n{'='*60}")
        print(f"Found embedded SQL query (length: {len(sql_content)} chars)")
        print(f"{'='*60}")
        
        # Convert the SQL
        try:
            converted_sql = converter.convert(sql_content)
            print(f"✓ Successfully converted SQL query")
            return f"{prefix}{quote}{converted_sql}{quote}"
        except Exception as e:
            print(f"✗ Conversion failed: {e}")
            print(f"Keeping original query")
            return match.group(0)
    
    # Apply conversion
    converted_code = re.sub(pattern, convert_match, python_code, flags=re.DOTALL)
    
    return converted_code


if __name__ == "__main__":
    # Read the input file
    with open('test_input.py', 'r') as f:
        original_code = f.read()
    
    print("Converting embedded SQL queries in test_input.py...")
    
    # Convert
    converted_code = extract_and_convert_embedded_queries(original_code)
    
    # Write to new file
    output_file = 'test_output_fixed.py'
    with open(output_file, 'w') as f:
        f.write(converted_code)
    
    print(f"\n{'='*60}")
    print(f"✓ Conversion complete!")
    print(f"Output saved to: {output_file}")
    print(f"{'='*60}")
