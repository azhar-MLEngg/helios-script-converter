"""Main orchestrator for the conversion workflow."""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config_loader import ConfigLoader, load_config
from .connection_converter import ConnectionConverterAgent
from .debugging_agent import DebuggingAgent
from .query_converter import QueryConverter
from .validator import ScriptValidator


class ConversionResult:
    """Result of a conversion operation."""
    
    def __init__(
        self,
        success: bool,
        converted_script: str,
        original_script: str,
        error_message: Optional[str] = None,
        iterations: int = 0,
        needs_manual_review: bool = False
    ):
        self.success = success
        self.converted_script = converted_script
        self.original_script = original_script
        self.error_message = error_message
        self.iterations = iterations
        self.needs_manual_review = needs_manual_review


class ConversionOrchestrator:
    """Orchestrates the entire conversion workflow."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the orchestrator.
        
        Args:
            config_path: Optional path to config.yaml file.
        """
        self.config = load_config(config_path)
        self.console = Console()
        
        # Initialize components
        api_key = self.config.settings.anthropic_api_key
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in environment")
        
        self.connection_converter = ConnectionConverterAgent(api_key, self.config.connection_converter)
        self.query_converter = QueryConverter(self.config)
        self.debugging_agent = DebuggingAgent(api_key, self.config.debugging_agent)
        self.validator = ScriptValidator(self.config)
        
        logger.info("Initialized ConversionOrchestrator")
    
    def convert_script(self, input_file: Path) -> ConversionResult:
        """Convert a Snowflake Python script to StarRocks format.
        
        Args:
            input_file: Path to input Snowflake script.
            
        Returns:
            ConversionResult object.
        """
        logger.info(f"Starting conversion of: {input_file}")
        
        # Read input script
        with open(input_file, 'r') as f:
            original_script = f.read()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            
            # Stage 1: Input Processing
            task = progress.add_task("Processing input script...", total=None)
            connection_code, queries = self._extract_components(original_script)
            progress.update(task, completed=True)
            
            # Stage 2: Parallel Conversion
            task = progress.add_task("Converting connection (AI Layer 1)...", total=None)
            converted_connection = self._convert_connection(connection_code)
            progress.update(task, completed=True)
            
            task = progress.add_task("Converting queries (Deterministic)...", total=None)
            converted_queries = self._convert_queries(queries)
            progress.update(task, completed=True)
            
            # Stage 3: Assembly
            task = progress.add_task("Assembling converted script...", total=None)
            converted_script = self._assemble_script(
                original_script,
                connection_code,
                converted_connection,
                queries,
                converted_queries
            )
            progress.update(task, completed=True)
            
            # Stage 4: Validation
            if self.config.settings.enable_validation:
                task = progress.add_task("Validating converted script...", total=None)
                success, error_message, error_details = self.validator.validate_script(converted_script)
                progress.update(task, completed=True)
                
                # Stage 5: Error Resolution Loop
                if not success and error_message:
                    logger.warning("Validation failed, entering debugging loop")
                    converted_script, iterations, needs_manual = self._debug_and_fix(
                        original_script,
                        converted_script,
                        queries,
                        converted_queries,
                        error_message,
                        error_details or {},
                        progress
                    )
                    
                    # Re-validate after fixes
                    success, error_message, _ = self.validator.validate_script(converted_script)
                    
                    return ConversionResult(
                        success=success,
                        converted_script=converted_script,
                        original_script=original_script,
                        error_message=error_message,
                        iterations=iterations,
                        needs_manual_review=needs_manual or not success
                    )
            else:
                success = True
                error_message = None
        
        logger.success("Conversion completed successfully")
        return ConversionResult(
            success=success,
            converted_script=converted_script,
            original_script=original_script,
            error_message=error_message,
            iterations=0,
            needs_manual_review=False
        )
    
    def _extract_components(self, script: str) -> Tuple[str, List[Tuple[str, int]]]:
        """Extract connection code and queries from script.
        
        Args:
            script: Python script content.
            
        Returns:
            Tuple of (connection_code, queries).
        """
        logger.info("Extracting connection and queries from script")
        
        # Extract connection code
        connection_code = self._extract_connection(script)
        
        # Extract queries
        queries = self.query_converter.extract_queries_from_script(script)
        
        logger.info(f"Extracted connection and {len(queries)} queries")
        return connection_code, queries
    
    def _extract_connection(self, script: str) -> str:
        """Extract Snowflake connection code from script.
        
        Args:
            script: Python script content.
            
        Returns:
            Connection code string.
        """
        # Pattern to match snowflake.connector.connect()
        pattern = r'(import\s+snowflake\.connector.*?)((?:conn|connection)\s*=\s*snowflake\.connector\.connect\s*\([^)]*\))'
        match = re.search(pattern, script, re.DOTALL | re.IGNORECASE)
        
        if match:
            return match.group(0)
        
        # Fallback: look for any connection-related code
        lines = script.split('\n')
        connection_lines = []
        in_connection = False
        
        for line in lines:
            if 'snowflake.connector' in line.lower() or 'import snowflake' in line.lower():
                in_connection = True
            
            if in_connection:
                connection_lines.append(line)
                
                if 'connect(' in line and ')' in line:
                    break
        
        return '\n'.join(connection_lines) if connection_lines else ""
    
    def _convert_connection(self, connection_code: str) -> str:
        """Convert connection code using AI agent.
        
        Args:
            connection_code: Snowflake connection code.
            
        Returns:
            StarRocks connection code.
        """
        if not connection_code:
            logger.warning("No connection code found, using default")
            return """import pymysql

conn = pymysql.connect(
    host='localhost',
    port=9030,
    user='root',
    password='',
    database='test_db'
)"""
        
        return self.connection_converter.convert(connection_code)
    
    def _convert_queries(self, queries: List[Tuple[str, int]]) -> List[Tuple[str, int]]:
        """Convert queries using deterministic rules.
        
        Args:
            queries: List of (query, line_number) tuples.
            
        Returns:
            List of (converted_query, line_number) tuples.
        """
        converted = []
        
        for query, line_num in queries:
            converted_query = self.query_converter.convert(query)
            converted.append((converted_query, line_num))
        
        return converted
    
    def _assemble_script(
        self,
        original_script: str,
        original_connection: str,
        converted_connection: str,
        original_queries: List[Tuple[str, int]],
        converted_queries: List[Tuple[str, int]]
    ) -> str:
        """Assemble the final converted script.
        
        Args:
            original_script: Original script content.
            original_connection: Original connection code.
            converted_connection: Converted connection code.
            original_queries: Original queries with line numbers.
            converted_queries: Converted queries with line numbers.
            
        Returns:
            Assembled converted script.
        """
        script = original_script
        
        # Replace connection code
        if original_connection:
            script = script.replace(original_connection, converted_connection)
        
        # Replace queries
        for (orig_query, _), (conv_query, _) in zip(original_queries, converted_queries):
            script = script.replace(orig_query, conv_query)
        
        # Add header comment
        header = """# Converted from Snowflake to StarRocks
# Generated by Snowflake-to-StarRocks Conversion System
# Please review and test before production use

"""
        
        return header + script
    
    def _debug_and_fix(
        self,
        original_script: str,
        converted_script: str,
        original_queries: List[Tuple[str, int]],
        converted_queries: List[Tuple[str, int]],
        error_message: str,
        error_details: Dict[str, Any],
        progress: Progress
    ) -> Tuple[str, int, bool]:
        """Debug and fix validation errors using AI agent.
        
        Args:
            original_script: Original Snowflake script.
            converted_script: Current converted script.
            original_queries: Original queries.
            converted_queries: Converted queries.
            error_message: Validation error message.
            error_details: Error details dictionary.
            progress: Progress bar instance.
            
        Returns:
            Tuple of (fixed_script, iterations, needs_manual_review).
        """
        max_iterations = self.config.debugging_agent.max_iterations
        previous_fixes = []
        current_script = converted_script
        
        for iteration in range(1, max_iterations + 1):
            task = progress.add_task(f"Debugging (iteration {iteration}/{max_iterations})...", total=None)
            
            # For simplicity, debug the first query (can be extended)
            if converted_queries:
                original_query = original_queries[0][0] if original_queries else ""
                converted_query = converted_queries[0][0]
                
                fix_result = self.debugging_agent.debug_and_fix(
                    original_query=original_query,
                    converted_query=converted_query,
                    error_message=error_message,
                    error_details=error_details,
                    iteration=iteration,
                    previous_fixes=previous_fixes
                )
                
                previous_fixes.append(fix_result)
                
                # Apply the fix
                if fix_result.get("fixed_query"):
                    current_script = current_script.replace(
                        converted_query,
                        fix_result["fixed_query"]
                    )
                
                progress.update(task, completed=True)
                
                # Check if we should continue
                confidence = fix_result.get("confidence", 0.0)
                if not self.debugging_agent.should_continue(iteration, confidence):
                    logger.warning("Stopping debugging loop - low confidence or max iterations")
                    return current_script, iteration, True
                
                # Re-validate
                success, new_error, new_details = self.validator.validate_script(current_script)
                
                if success:
                    logger.success(f"Validation passed after {iteration} iteration(s)")
                    return current_script, iteration, False
                
                # Update error for next iteration
                error_message = new_error or error_message
                error_details = new_details or error_details
            else:
                break
        
        logger.warning(f"Max iterations ({max_iterations}) reached, manual review required")
        return current_script, max_iterations, True
    
    def save_result(self, result: ConversionResult, output_file: Path) -> None:
        """Save conversion result to file.
        
        Args:
            result: ConversionResult object.
            output_file: Path to output file.
        """
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            f.write(result.converted_script)
        
        logger.info(f"Saved converted script to: {output_file}")
        
        # Save error log if needed
        if result.needs_manual_review and result.error_message:
            error_file = output_file.with_suffix('.error.log')
            with open(error_file, 'w') as f:
                f.write(f"Conversion completed with errors\n")
                f.write(f"Iterations: {result.iterations}\n")
                f.write(f"Needs manual review: {result.needs_manual_review}\n\n")
                f.write(f"Error Message:\n{result.error_message}\n")
            
            logger.warning(f"Saved error log to: {error_file}")
