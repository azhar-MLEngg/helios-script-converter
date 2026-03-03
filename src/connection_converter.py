"""Connection Converter Agent - AI Layer 1."""

import json
import re
from typing import Dict, Optional

from anthropic import Anthropic
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from .config_loader import AgentConfig


class ConnectionConverterAgent:
    """AI-powered agent to convert Snowflake connections to StarRocks format."""
    
    def __init__(self, api_key: str, config: AgentConfig):
        """Initialize the Connection Converter Agent.
        
        Args:
            api_key: Anthropic API key.
            config: Agent configuration.
        """
        self.client = Anthropic(api_key=api_key)
        self.config = config
        logger.info(f"Initialized ConnectionConverterAgent with model: {config.model}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def convert(self, snowflake_connection: str) -> str:
        """Convert Snowflake connection code to StarRocks format.
        
        Args:
            snowflake_connection: Python code containing Snowflake connection.
            
        Returns:
            Python code with StarRocks connection.
            
        Raises:
            Exception: If conversion fails after retries.
        """
        logger.info("Converting Snowflake connection to StarRocks format")
        
        prompt = self._build_prompt(snowflake_connection)
        
        try:
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            
            converted_code = response.content[0].text.strip()
            
            # Clean up code blocks if present
            converted_code = self._clean_code_blocks(converted_code)
            
            logger.success("Successfully converted Snowflake connection to StarRocks")
            logger.debug(f"Converted connection:\n{converted_code}")
            
            return converted_code
            
        except Exception as e:
            logger.error(f"Failed to convert connection: {str(e)}")
            raise
    
    def _build_prompt(self, snowflake_connection: str) -> str:
        """Build the prompt for the AI agent.
        
        Args:
            snowflake_connection: Snowflake connection code.
            
        Returns:
            Formatted prompt string.
        """
        return f"""Convert this Snowflake connection code to StarRocks format.

Snowflake Connection:
```python
{snowflake_connection}
```

Requirements:
1. Use pymysql for StarRocks connection (import pymysql)
2. Map Snowflake parameters to StarRocks equivalents:
   - account, warehouse, schema → not needed in StarRocks
   - database → database (keep same)
   - user → user (keep same)
   - password → password (keep same)
   - Add: host (default: 'localhost')
   - Add: port (default: 9030)
3. Preserve variable names (e.g., if Snowflake uses 'conn', StarRocks should too)
4. Include error handling if present in original
5. Return ONLY the Python connection code, no explanations

Output the converted connection code:"""
    
    def _clean_code_blocks(self, code: str) -> str:
        """Remove markdown code block markers if present.
        
        Args:
            code: Code potentially wrapped in markdown blocks.
            
        Returns:
            Clean code without markdown markers.
        """
        # Remove ```python or ``` markers
        code = re.sub(r'^```python\s*\n', '', code, flags=re.MULTILINE)
        code = re.sub(r'^```\s*\n', '', code, flags=re.MULTILINE)
        code = re.sub(r'\n```\s*$', '', code, flags=re.MULTILINE)
        
        return code.strip()
    
    def extract_connection_params(self, connection_code: str) -> Optional[Dict[str, str]]:
        """Extract connection parameters from Python code.
        
        Args:
            connection_code: Python code containing connection.
            
        Returns:
            Dictionary of connection parameters or None if extraction fails.
        """
        params = {}
        
        # Extract parameters from snowflake.connector.connect() or pymysql.connect()
        patterns = [
            r"(\w+)\s*=\s*['\"]([^'\"]+)['\"]",
            r"(\w+)\s*=\s*(\d+)",
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, connection_code)
            for key, value in matches:
                params[key] = value
        
        return params if params else None
