"""Validation module for testing converted scripts."""

import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pymysql
from loguru import logger

from .config_loader import ConfigLoader


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


class ScriptValidator:
    """Validates converted Python scripts by executing them."""
    
    def __init__(self, config: ConfigLoader):
        """Initialize the validator.
        
        Args:
            config: Configuration loader instance.
        """
        self.config = config
        self.timeout = config.settings.validation_timeout
        self.enabled = config.settings.enable_validation
        logger.info(f"Initialized ScriptValidator (enabled: {self.enabled}, timeout: {self.timeout}s)")
    
    def validate_script(self, script_content: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Validate a converted Python script by executing it.
        
        Args:
            script_content: Python script content to validate.
            
        Returns:
            Tuple of (success, error_message, error_details).
        """
        if not self.enabled:
            logger.info("Validation disabled, skipping")
            return True, None, None
        
        logger.info("Validating converted script")
        
        try:
            # Create temporary file with the script
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(script_content)
                temp_file = f.name
            
            temp_path = Path(temp_file)
            
            try:
                # Execute the script
                result = subprocess.run(
                    ['python', str(temp_path)],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout
                )
                
                if result.returncode == 0:
                    logger.success("Script validation passed")
                    return True, None, None
                else:
                    error_message = result.stderr or result.stdout
                    error_details = self._parse_error(error_message, result.returncode)
                    
                    logger.error(f"Script validation failed: {error_message}")
                    return False, error_message, error_details
                    
            finally:
                # Clean up temp file
                temp_path.unlink(missing_ok=True)
                
        except subprocess.TimeoutExpired:
            error_message = f"Script execution timed out after {self.timeout} seconds"
            logger.error(error_message)
            return False, error_message, {"error_type": "TimeoutError"}
            
        except Exception as e:
            error_message = f"Validation error: {str(e)}"
            logger.error(error_message)
            return False, error_message, {"error_type": type(e).__name__}
    
    def validate_connection(self) -> Tuple[bool, Optional[str]]:
        """Validate StarRocks connection.
        
        Returns:
            Tuple of (success, error_message).
        """
        logger.info("Validating StarRocks connection")
        
        try:
            conn = pymysql.connect(
                host=self.config.starrocks.host,
                port=self.config.starrocks.port,
                user=self.config.starrocks.user,
                password=self.config.starrocks.password,
                database=self.config.starrocks.database,
                connect_timeout=5
            )
            
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
            
            conn.close()
            
            logger.success("StarRocks connection validated")
            return True, None
            
        except Exception as e:
            error_message = f"Connection validation failed: {str(e)}"
            logger.error(error_message)
            return False, error_message
    
    def validate_query(self, query: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Validate a SQL query by executing it on StarRocks.
        
        Args:
            query: SQL query to validate.
            
        Returns:
            Tuple of (success, error_message, error_details).
        """
        logger.info("Validating SQL query")
        
        try:
            conn = pymysql.connect(
                host=self.config.starrocks.host,
                port=self.config.starrocks.port,
                user=self.config.starrocks.user,
                password=self.config.starrocks.password,
                database=self.config.starrocks.database
            )
            
            with conn.cursor() as cursor:
                # Use EXPLAIN to validate without executing
                cursor.execute(f"EXPLAIN {query}")
                result = cursor.fetchall()
            
            conn.close()
            
            logger.success("Query validation passed")
            return True, None, None
            
        except pymysql.Error as e:
            error_message = str(e)
            error_details = {
                "error_type": "SQLError",
                "error_code": e.args[0] if e.args else None,
                "sql_state": getattr(e, 'sqlstate', None)
            }
            
            logger.error(f"Query validation failed: {error_message}")
            return False, error_message, error_details
            
        except Exception as e:
            error_message = f"Query validation error: {str(e)}"
            error_details = {"error_type": type(e).__name__}
            
            logger.error(error_message)
            return False, error_message, error_details
    
    def _parse_error(self, error_message: str, return_code: int) -> Dict[str, Any]:
        """Parse error message to extract details.
        
        Args:
            error_message: Error message from script execution.
            return_code: Process return code.
            
        Returns:
            Dictionary with error details.
        """
        error_details = {
            "return_code": return_code,
            "error_type": "UnknownError"
        }
        
        # Try to extract error type
        if "SyntaxError" in error_message:
            error_details["error_type"] = "SyntaxError"
        elif "ImportError" in error_message or "ModuleNotFoundError" in error_message:
            error_details["error_type"] = "ImportError"
        elif "NameError" in error_message:
            error_details["error_type"] = "NameError"
        elif "TypeError" in error_message:
            error_details["error_type"] = "TypeError"
        elif "ValueError" in error_message:
            error_details["error_type"] = "ValueError"
        elif "pymysql" in error_message.lower():
            error_details["error_type"] = "DatabaseError"
        
        # Try to extract line number
        import re
        line_match = re.search(r'line (\d+)', error_message)
        if line_match:
            error_details["line_number"] = int(line_match.group(1))
        
        return error_details
