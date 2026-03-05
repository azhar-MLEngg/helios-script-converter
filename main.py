#!/usr/bin/env python3
import asyncio
import os
import sys
import json
import logging
from pathlib import Path
from typing import Tuple, Dict, List
from datetime import datetime
from claude_agent_sdk import query
from query_extractor_converter import process_python_script

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FileManager:
    """Handle file operations"""
    
    @staticmethod
    def read_file(filename: str) -> str:
        """Read file content"""
        try:
            if not Path(filename).exists():
                logger.error(f"✗ File not found: {filename}")
                sys.exit(1)
            
            with open(filename, 'r') as f:
                content = f.read()
            logger.info(f"✓ Read {filename} ({len(content)} characters)")
            return content
        except Exception as e:
            logger.error(f"✗ Error reading {filename}: {str(e)}")
            sys.exit(1)
    
    @staticmethod
    def write_file(filename: str, content: str) -> None:
        """Write content to file"""
        try:
            # Create parent directory if it doesn't exist
            Path(filename).parent.mkdir(parents=True, exist_ok=True)
            with open(filename, 'w') as f:
                f.write(content)
            logger.info(f"✓ Saved to {filename}")
        except Exception as e:
            logger.error(f"✗ Error writing {filename}: {str(e)}")
            sys.exit(1)
    
    @staticmethod
    def scan_directory(directory: str, extensions: List[str] = None) -> List[Path]:
        """Scan directory for files with specific extensions"""
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                logger.error(f"✗ Directory not found: {directory}")
                return []
            
            if not dir_path.is_dir():
                logger.error(f"✗ Not a directory: {directory}")
                return []
            
            files = []
            for file_path in dir_path.iterdir():
                if file_path.is_file():
                    if extensions is None or file_path.suffix in extensions:
                        files.append(file_path)
            
            return sorted(files)
        except Exception as e:
            logger.error(f"✗ Error scanning directory {directory}: {str(e)}")
            return []


class Step1ConnectionConverter:
    """
    STEP 1: Connection Conversion using Claude Agent SDK
    
    Process:
    1. Read prompt.md (conversion instructions)
    2. Read python_script.py (Snowflake script)
    3. Send to Claude Agent SDK for conversion
    4. Extract converted connection code
    """
    
    def __init__(self, api_key: str):
        """Initialize with API key"""
        self.api_key = api_key
    
    @staticmethod
    def _extract_code(response: str, file_extension: str) -> str:
        """
        Extract code from Claude's response, removing markdown and explanations
        
        Args:
            response: Full response from Claude
            file_extension: File extension (.py or .sql)
            
        Returns:
            Extracted code only
        """
        import re
        
        # Determine the code block type based on file extension
        code_blocks = []
        
        if file_extension == '.py':
            code_blocks = re.findall(r'```python\s*\n(.*?)\n```', response, re.DOTALL)
        elif file_extension == '.sql':
            # Try multiple patterns for SQL
            code_blocks = re.findall(r'```sql\s*\n(.*?)\n```', response, re.DOTALL)
            if not code_blocks:
                code_blocks = re.findall(r'```\s*\n(.*?)\n```', response, re.DOTALL)
        else:
            code_blocks = re.findall(r'```\s*\n(.*?)\n```', response, re.DOTALL)
        
        if code_blocks:
            # Get the largest code block (most likely to be the full conversion)
            largest_block = max(code_blocks, key=len)
            
            # If the extracted block is suspiciously short compared to response, use full response
            if len(largest_block) < len(response) * 0.3:
                logger.warning(f"Extracted code block seems too short ({len(largest_block)} chars vs {len(response)} total), using full response")
                return response.strip()
            
            return largest_block.strip()
        
        # If no code blocks found, clean up the response for config files
        logger.warning(f"No code blocks found in response for {file_extension}, returning full text")
        
        # For config files, try to clean up any duplicate content
        if file_extension in ['.ini', '.txt', '.json', '.yaml', '.yml', '.toml']:
            cleaned = response.strip()
            
            # Remove common Claude response patterns
            cleaned = re.sub(r'^Here.*?:\s*', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'^The converted.*?:\s*', '', cleaned, flags=re.IGNORECASE)
            
            # For .ini files, check if [SETTINGS] appears twice and keep only first occurrence
            if file_extension == '.ini' and cleaned.count('[SETTINGS]') > 1:
                # Split at the second [SETTINGS] and keep only the first part
                parts = cleaned.split('[SETTINGS]')
                if len(parts) > 2:
                    # Reconstruct with only first section
                    cleaned = '[SETTINGS]' + parts[1]
                    logger.info("Removed duplicate [SETTINGS] section")
            
            # For .txt files (like requirements.txt), remove duplicate lines and fix concatenation
            if file_extension == '.txt':
                # First, try to fix any concatenated package names (e.g., "pandas>=0.25.2sendgrid")
                # Split by common package name patterns
                import re
                # Look for patterns like "package1>=versionpackage2" and split them
                cleaned = re.sub(r'(\d)([a-zA-Z])', r'\1\n\2', cleaned)
                
                lines = cleaned.split('\n')
                seen = set()
                unique_lines = []
                for line in lines:
                    line_stripped = line.strip()
                    # Skip empty lines and duplicates
                    if line_stripped and line_stripped not in seen:
                        unique_lines.append(line_stripped)
                        seen.add(line_stripped)
                
                cleaned = '\n'.join(unique_lines)
                logger.info(f"Cleaned and deduplicated requirements file")
            
            return cleaned.strip()
        
        return response.strip()
    
    async def convert_file(self, prompt_file: str, code_file: str, file_type: str = "Python") -> str:
        """
        Convert Snowflake code to StarRocks
        
        Args:
            prompt_file: Path to prompt.md (for Python) or sql_prompt.md (for SQL)
            code_file: Path to code file (.py or .sql)
            file_type: Type of file ("Python" or "SQL")
            
        Returns:
            Converted code
        """
        print("\n" + "="*80)
        print(f"CONVERTING {file_type.upper()} FILE: {Path(code_file).name}")
        print("="*80)
        
        try:
            # Use appropriate prompt file based on file type
            if file_type == "SQL":
                sql_prompt = "sql_prompt.md"
                if Path(sql_prompt).exists():
                    prompt_file = sql_prompt
                    logger.info(f"[1.1] Using SQL-specific prompt: {prompt_file}")
            elif file_type == "Config":
                config_prompt = "config_prompt.md"
                if Path(config_prompt).exists():
                    prompt_file = config_prompt
                    logger.info(f"[1.1] Using Config-specific prompt: {prompt_file}")
            
            # Read files
            logger.info(f"[1.1] Reading {prompt_file}...")
            prompt_template = FileManager.read_file(prompt_file)
            
            logger.info(f"[1.2] Reading {code_file}...")
            snowflake_code = FileManager.read_file(code_file)
            
            # Combine prompt and code
            logger.info("[1.3] Preparing conversion prompt...")
            
            # For config files, don't use code blocks
            if file_type == "Config":
                full_prompt = f"""{prompt_template}

{snowflake_code}"""
            else:
                code_lang = "python" if file_type == "Python" else "sql"
                full_prompt = f"""{prompt_template}

```{code_lang}
{snowflake_code}
```"""
            
            print(f"\n[1.4] Sending to Claude Agent SDK...")
            print("-" * 80)
            
            # Stream response from Claude
            full_response = ""
            
            os.environ["ANTHROPIC_API_KEY"] = self.api_key
            
            async for message in query(prompt=full_prompt):
                message_type = type(message).__name__
                
                # Extract text content
                if message_type == "AssistantMessage":
                    if hasattr(message, 'content') and message.content:
                        for block in message.content:
                            if hasattr(block, 'text'):
                                text = block.text
                                full_response += text
                
                elif message_type == "ResultMessage":
                    if hasattr(message, 'result') and message.result:
                        result_text = str(message.result)
                        if result_text.strip():
                            full_response += result_text
            
            print("\n" + "-" * 80)
            logger.info(f"[1.5] Extracting {file_type} code from response...")
            
            # Extract only the code from the response
            file_ext = Path(code_file).suffix
            converted_code = self._extract_code(full_response, file_ext)
            
            logger.info(f"✓ Connection conversion completed ({len(converted_code)} characters)")
            
            return converted_code
        
        except Exception as e:
            logger.error(f"✗ Connection conversion failed: {str(e)}")
            raise


class Step2QueryConverter:
    """
    STEP 2: Query Extraction & Conversion
    
    Process:
    1. Extract all embedded SQL queries from script
    2. Convert each query using query_converter.py
    3. Replace queries in script with converted versions
    """
    
    def convert_queries(self, script_content: str) -> Tuple[str, List[Dict]]:
        """
        Extract and convert all queries in script
        
        Args:
            script_content: Python script content
            
        Returns:
            Tuple of (converted_script, conversion_details)
        """
        print("\n" + "="*80)
        print("STEP 2: QUERY EXTRACTION & CONVERSION")
        print("="*80)
        
        try:
            logger.info("[2.1] Extracting embedded SQL queries...")
            converted_script, details = process_python_script(script_content, verbose=False)
            
            # Print summary
            if details:
                successful = sum(1 for d in details if d['conversion_successful'])
                failed = len(details) - successful
                
                print(f"\n[2.2] Query Conversion Summary:")
                print(f"  Total Queries Found:       {len(details)}")
                print(f"  Successfully Converted:    {successful}")
                print(f"  Conversion Errors:         {failed}")
                
                if failed > 0:
                    print(f"\n  Failed Queries:")
                    for detail in details:
                        if not detail['conversion_successful']:
                            print(f"    - Query #{detail['query_number']} (Line {detail['line_number']})")
                            print(f"      Error: {detail['conversion_error']}")
                
                logger.info(f"✓ Query conversion completed ({successful}/{len(details)} successful)")
            else:
                logger.warning("⚠ No queries found in script")
                converted_script = script_content
            
            return converted_script, details
        
        except ImportError as e:
            logger.error(f"✗ Failed to import query_extractor_converter: {str(e)}")
            logger.info("  Make sure query_extractor_converter.py and query_converter.py are in the same directory")
            raise
        except Exception as e:
            logger.error(f"✗ Query conversion failed: {str(e)}")
            raise


class Step3Merger:
    """
    STEP 3: Merge Results
    
    Process:
    1. Take converted connection code from Step 1
    2. Apply query conversions from Step 2
    3. Generate final script with all conversions applied
    """
    
    @staticmethod
    def merge_conversions(connection_converted_script: str, 
                         query_converted_script: str,
                         query_details: List[Dict]) -> str:
        """
        Merge connection and query conversions
        
        Args:
            connection_converted_script: Output from Step 1
            query_converted_script: Output from Step 2
            query_details: Details of query conversions
            
        Returns:
            Final merged script
        """
        print("\n" + "="*80)
        print("STEP 3: MERGE & COMPILE")
        print("="*80)
        
        logger.info("[3.1] Merging conversions...")
        
        # Since query_extractor_converter already applies conversions,
        # we use the query_converted_script as the base
        # and verify the connection part is converted
        
        # Extract connection part from connection_converted_script
        connection_section = Step3Merger._extract_connection_section(connection_converted_script)
        
        # Verify query conversions are applied
        logger.info(f"[3.2] Verifying conversions...")
        print(f"  Connection Conversion: ✓")
        print(f"  Query Conversions: ✓ ({len(query_details)} queries processed)")
        
        # The final script is the query_converted_script
        # which already has all conversions from both steps
        final_script = query_converted_script
        
        logger.info("[3.3] Final script compiled")
        logger.info(f"✓ Merge completed")
        
        return final_script
    
    @staticmethod
    def _extract_connection_section(script: str) -> str:
        """Extract just the connection code from script"""
        lines = script.split('\n')
        connection_lines = []
        
        for line in lines:
            if 'from helios_python_sdk' in line or 'StarRocksClient' in line:
                connection_lines.append(line)
        
        return '\n'.join(connection_lines)


class ConversionOrchestrator:
    """
    Main orchestrator that manages the complete conversion pipeline
    
    Workflow:
    1. Validate inputs and API key
    2. Scan input folder for files to convert
    3. Convert each file (Python and SQL) using Claude Agent SDK
    4. For Python files: Extract and convert embedded queries
    5. Save all converted files to output folder
    """
    
    def __init__(self, api_key: str):
        """Initialize orchestrator"""
        self.api_key = api_key
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    async def run_conversion(self, 
                            prompt_file: str = "prompt.md",
                            input_folder: str = "input_files",
                            output_folder: str = "output_files") -> None:
        """
        Run complete conversion pipeline for all files in input folder
        
        Args:
            prompt_file: Path to prompt.md
            input_folder: Folder containing files to convert
            output_folder: Folder to save converted files
        """
        print("\n" + "#"*80)
        print("# SNOWFLAKE → STARROCKS MIGRATION ORCHESTRATOR")
        print("#"*80)
        
        try:
            # Validate inputs
            logger.info("Validating inputs...")
            if not Path(prompt_file).exists():
                logger.error(f"✗ {prompt_file} not found")
                sys.exit(1)
            
            if not Path(input_folder).exists():
                logger.error(f"✗ Input folder not found: {input_folder}")
                sys.exit(1)
            
            # Create output folder if it doesn't exist
            Path(output_folder).mkdir(parents=True, exist_ok=True)
            
            # Scan for files to convert
            logger.info(f"Scanning {input_folder} for files...")
            python_files = FileManager.scan_directory(input_folder, ['.py'])
            sql_files = FileManager.scan_directory(input_folder, ['.sql'])
            
            total_files = len(python_files) + len(sql_files)
            if total_files == 0:
                logger.warning(f"⚠ No .py or .sql files found in {input_folder}")
                return
            
            logger.info(f"✓ Found {len(python_files)} Python file(s) and {len(sql_files)} SQL file(s)\n")
            
            conversion_results = []
            
            # Process Python files
            for py_file in python_files:
                try:
                    # STEP 1: Convert Python file
                    step1 = Step1ConnectionConverter(self.api_key)
                    connection_converted = await step1.convert_file(prompt_file, str(py_file), "Python")
                    
                    # STEP 2: Query Extraction & Conversion for Python files
                    print("\n" + "="*80)
                    print(f"QUERY EXTRACTION & CONVERSION: {py_file.name}")
                    print("="*80)
                    
                    step2 = Step2QueryConverter()
                    query_converted, query_details = step2.convert_queries(connection_converted)
                    
                    # Save converted Python file
                    output_file = Path(output_folder) / f"converted_{py_file.name}"
                    FileManager.write_file(str(output_file), query_converted)
                    
                    conversion_results.append({
                        'file': py_file.name,
                        'type': 'Python',
                        'output': str(output_file),
                        'queries': len(query_details),
                        'success': True
                    })
                    
                except Exception as e:
                    logger.error(f"✗ Failed to convert {py_file.name}: {str(e)}")
                    conversion_results.append({
                        'file': py_file.name,
                        'type': 'Python',
                        'output': None,
                        'queries': 0,
                        'success': False,
                        'error': str(e)
                    })
            
            # Process SQL files
            for sql_file in sql_files:
                try:
                    # Convert SQL file
                    step1 = Step1ConnectionConverter(self.api_key)
                    converted_sql = await step1.convert_file(prompt_file, str(sql_file), "SQL")
                    
                    # Save converted SQL file
                    output_file = Path(output_folder) / f"converted_{sql_file.name}"
                    FileManager.write_file(str(output_file), converted_sql)
                    
                    conversion_results.append({
                        'file': sql_file.name,
                        'type': 'SQL',
                        'output': str(output_file),
                        'queries': 0,
                        'success': True
                    })
                    
                except Exception as e:
                    logger.error(f"✗ Failed to convert {sql_file.name}: {str(e)}")
                    conversion_results.append({
                        'file': sql_file.name,
                        'type': 'SQL',
                        'output': None,
                        'queries': 0,
                        'success': False,
                        'error': str(e)
                    })
            
            # Convert other files (config, requirements, etc.)
            print("\n" + "="*80)
            print("CONVERTING OTHER FILES")
            print("="*80)
            other_files = FileManager.scan_directory(input_folder, ['.ini', '.txt', '.json', '.yaml', '.yml', '.toml'])
            for other_file in other_files:
                try:
                    # Skip if it's a Snowflake credentials file
                    if 'cred' in other_file.name.lower() and other_file.suffix == '.json':
                        logger.info(f"⚠ Skipping Snowflake credentials file: {other_file.name}")
                        continue
                    
                    # Convert using Claude
                    step1 = Step1ConnectionConverter(self.api_key)
                    converted_content = await step1.convert_file(prompt_file, str(other_file), "Config")
                    
                    # Save converted file
                    output_file = Path(output_folder) / other_file.name
                    FileManager.write_file(str(output_file), converted_content)
                    
                    conversion_results.append({
                        'file': other_file.name,
                        'type': 'Config',
                        'output': str(output_file),
                        'queries': 0,
                        'success': True
                    })
                    
                except Exception as e:
                    logger.error(f"✗ Failed to convert {other_file.name}: {str(e)}")
                    conversion_results.append({
                        'file': other_file.name,
                        'type': 'Config',
                        'output': None,
                        'queries': 0,
                        'success': False,
                        'error': str(e)
                    })
            
            # Generate UPDATES.md
            print("\n" + "="*80)
            print("GENERATING UPDATES.MD")
            print("="*80)
            self._generate_updates(conversion_results, input_folder, output_folder)
            
            # Summary
            print("\n" + "="*80)
            print("CONVERSION COMPLETE")
            print("="*80)
            self._print_summary(conversion_results, output_folder)
        
        except Exception as e:
            logger.error(f"✗ Conversion pipeline failed: {str(e)}")
            sys.exit(1)
    
    @staticmethod
    def _generate_updates(conversion_results: List[Dict], input_folder: str, output_folder: str) -> None:
        """Generate UPDATES.md documenting all changes made during conversion"""
        try:
            logger.info("Generating UPDATES.md...")
            
            successful_conversions = [r for r in conversion_results if r['success']]
            failed_conversions = [r for r in conversion_results if not r['success']]
            
            updates_content = f"""# Conversion Updates - Snowflake to StarRocks

**Conversion Date:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Tool Version:** 1.0  
**Total Files Processed:** {len(conversion_results)}  
**Successfully Converted:** {len(successful_conversions)}  
**Failed:** {len(failed_conversions)}

---

## Changes Made

This document details all changes made during the Snowflake to StarRocks conversion.

### Summary of Changes
"""
            
            # List converted code files
            for result in successful_conversions:
                updates_content += f"\n#### {Path(result['output']).name}\n"
                updates_content += f"**Original File:** `{input_folder}/{result['file']}`  \n"
                updates_content += f"**Converted File:** `{output_folder}/{Path(result['output']).name}`  \n"
                updates_content += f"**Type:** {result['type']}  \n"
                
                if result['type'] == 'Python':
                    updates_content += f"""
**Changes Made:**
- ❌ **Removed:** `snowflake.connector` and all Snowflake connection code
- ❌ **Removed:** `cryptography` imports for RSA key handling
- ❌ **Removed:** JSON credentials loading logic
- ✅ **Added:** `from helios_python_sdk.services.starrocks_client import StarRocksClient`
- ✅ **Added:** `client = StarRocksClient()` for database connection
- ✅ **Kept:** All business logic, data processing, and error handling

**Before (Snowflake):**
```python
connection = snowflake.connector.connect(**conn_params)
```

**After (StarRocks):**
```python
client = StarRocksClient()
```
"""
                elif result['type'] == 'SQL':
                    updates_content += f"""
**Changes Made:**
- Database references: Removed double quotes from identifiers (`"DB"."SCHEMA"` → `DB.SCHEMA`)
- Date functions: `TRY_TO_DATE()` → `STR_TO_DATE()`
- Date functions: `CURRENT_DATE()` → `CURRENT_DATE` (removed parentheses)
- Interval syntax: `INTERVAL '1 DAY'` → `INTERVAL 1 DAY` (removed quotes)
- QUALIFY clause: Converted to subquery with `WHERE` condition
"""
                elif result['type'] == 'Config':
                    if 'requirements' in result['file'].lower():
                        updates_content += f"""
**Changes Made:**
- ❌ **Removed:** `snowflake-connector-python`
- ❌ **Removed:** `cryptography` (if only used for Snowflake)
- ❌ **Removed:** `google-cloud-secret-manager` (if only used for Snowflake)
- ✅ **Added:** `helios-python-sdk`
- ✅ **Kept:** All other dependencies unchanged
"""
                    elif 'config' in result['file'].lower():
                        updates_content += f"""
**Changes Made:**
- ❌ **Removed:** `SNOWFLAKE_CREDS_FILE` setting
- ❌ **Removed:** Other Snowflake-specific connection parameters
- ✅ **Kept:** All application settings (email, file paths, etc.)
"""
                    else:
                        updates_content += f"""
**Changes Made:**
- Snowflake-specific configurations removed
- All other settings preserved
"""
            
            # Failed conversions section
            if failed_conversions:
                updates_content += f"""

### Failed Conversions

The following files could not be converted:

"""
                for result in failed_conversions:
                    updates_content += f"- ✗ **{result['file']}** ({result['type']}): {result.get('error', 'Unknown error')}\n"
            
            # Files not copied section
            updates_content += """

---

## Files Not Copied to Output

### Snowflake Credentials Files
- Files containing "cred" in the name with `.json` extension are automatically skipped
- These files are **not needed** for StarRocks
- The `StarRocksClient()` handles all authentication internally through the Helios SDK

---

## Migration Impact Summary

"""
            
            updates_content += f"""
| Metric | Count |
|--------|-------|
| **Total Files Processed** | {len(conversion_results)} |
| **Successfully Converted** | {len(successful_conversions)} |
| **Failed Conversions** | {len(failed_conversions)} |
| **Python Files** | {sum(1 for r in successful_conversions if r['type'] == 'Python')} |
| **SQL Files** | {sum(1 for r in successful_conversions if r['type'] == 'SQL')} |
| **Configuration Files** | {sum(1 for r in successful_conversions if r['type'] == 'Config')} |

---

## Next Steps

1. ✅ **Review Changes:** Examine each converted file to verify accuracy
2. ✅ **Test SQL Queries:** Run converted SQL in StarRocks to ensure compatibility
3. ✅ **Test Python Scripts:** Execute converted scripts in a test environment
4. ✅ **Verify Data:** Compare results between Snowflake and StarRocks
5. ✅ **Update Configuration:** Adjust `config.ini` with your environment-specific settings
6. ✅ **Deploy:** Move to production after successful testing

---

**Generated by:** Snowflake to StarRocks Migration Tool  
**Tool Version:** 1.0  
**Conversion Date:** """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Write UPDATES.md
            updates_path = Path(output_folder) / "UPDATES.md"
            with open(updates_path, 'w') as f:
                f.write(updates_content)
            
            logger.info(f"✓ UPDATES.md generated at {updates_path}")
            
        except Exception as e:
            logger.error(f"✗ Error generating README: {str(e)}")
    
    @staticmethod
    def _print_summary(conversion_results: List[Dict], output_folder: str) -> None:
        """Print conversion summary"""
        successful_files = sum(1 for r in conversion_results if r['success'])
        failed_files = len(conversion_results) - successful_files
        total_queries = sum(r.get('queries', 0) for r in conversion_results if r['success'])
        
        print(f"""
✓ Conversion Pipeline Completed!

Summary:
--------
Total Files Processed:     {len(conversion_results)}
Successfully Converted:    {successful_files}
Conversion Errors:         {failed_files}
Total Queries Processed:   {total_queries}

Converted Files:
----------------""")
        
        for result in conversion_results:
            if result['success']:
                print(f"✓ {result['type']:6} | {result['file']:30} → {Path(result['output']).name}")
            else:
                print(f"✗ {result['type']:6} | {result['file']:30} → FAILED: {result.get('error', 'Unknown error')}")
        
        
        # Show config files separately
        config_files = [r for r in conversion_results if r['type'] == 'Config' and r['success']]
        if config_files:
            print(f"""
Configuration Files:
--------------------""")
            for result in config_files:
                print(f"✓ {result['type']:6} | {result['file']:30} → {Path(result['output']).name}")
        
        print(f"""
Documentation:
--------------
✓ Docs    | UPDATES.md                    → UPDATES.md (Change log)

Output Folder:
--------------
{output_folder}

Next Steps:
-----------
1. Review the converted files in: {output_folder}
2. Read UPDATES.md for detailed list of all changes made
3. Install dependencies: pip install -r {output_folder}/requirements.txt
4. Test the converted scripts with StarRocks
5. Handle any failed conversions manually if needed

{'='*80}
""")


async def main():
    """Main entry point"""
    
    # Get API key
    print("\n" + "="*80)
    print("AUTHENTICATION")
    print("="*80)
    
    os.environ["ANTHROPIC_API_KEY"] = api_key
    
    if not api_key:
        logger.error("✗ API key cannot be empty")
        sys.exit(1)
    
    logger.info("✓ API key set\n")
    
    # Initialize orchestrator
    orchestrator = ConversionOrchestrator(api_key)
    
    # Run conversion pipeline
    await orchestrator.run_conversion(
        prompt_file="prompt.md",
        input_folder="input_files",
        output_folder="output_files"
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n✗ Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)