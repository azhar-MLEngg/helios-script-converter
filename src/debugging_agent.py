"""Debugging Agent - AI Layer 2."""

import json
from typing import Any, Dict, List, Optional

from anthropic import Anthropic
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from .config_loader import DebuggingAgentConfig


class DebuggingAgent:
    """AI-powered agent to debug and fix validation errors in converted queries."""
    
    def __init__(self, api_key: str, config: DebuggingAgentConfig):
        """Initialize the Debugging Agent.
        
        Args:
            api_key: Anthropic API key.
            config: Agent configuration.
        """
        self.client = Anthropic(api_key=api_key)
        self.config = config
        self.max_iterations = config.max_iterations
        logger.info(f"Initialized DebuggingAgent with model: {config.model}, max_iterations: {self.max_iterations}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def debug_and_fix(
        self,
        original_query: str,
        converted_query: str,
        error_message: str,
        error_details: Dict[str, Any],
        iteration: int,
        previous_fixes: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Debug and fix a validation error.
        
        Args:
            original_query: Original Snowflake query.
            converted_query: Current StarRocks query with errors.
            error_message: Error message from validation.
            error_details: Additional error context.
            iteration: Current iteration number (1-indexed).
            previous_fixes: List of previous fix attempts.
            
        Returns:
            Dictionary containing:
                - analysis: Root cause analysis
                - fixed_query: Corrected StarRocks query
                - changes: List of changes made
                - confidence: Confidence score (0-1)
                - should_retry: Whether to retry validation
        """
        logger.info(f"Debugging query (iteration {iteration}/{self.max_iterations})")
        
        if iteration > self.max_iterations:
            logger.error(f"Max iterations ({self.max_iterations}) exceeded")
            return {
                "analysis": "Max iterations exceeded",
                "fixed_query": converted_query,
                "changes": [],
                "confidence": 0.0,
                "should_retry": False
            }
        
        error_context = {
            "original_query": original_query,
            "converted_query": converted_query,
            "error_message": error_message,
            "error_details": error_details,
            "previous_fixes": previous_fixes or []
        }
        
        prompt = self._build_prompt(error_context, iteration)
        
        try:
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result_text = response.content[0].text.strip()
            result = self._parse_response(result_text)
            
            logger.success(f"Generated fix with confidence: {result.get('confidence', 0.0)}")
            logger.debug(f"Analysis: {result.get('analysis', 'N/A')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to debug query: {str(e)}")
            raise
    
    def _build_prompt(self, error_context: Dict[str, Any], iteration: int) -> str:
        """Build the prompt for the debugging agent.
        
        Args:
            error_context: Context about the error.
            iteration: Current iteration number.
            
        Returns:
            Formatted prompt string.
        """
        previous_fixes_text = "None"
        if error_context.get("previous_fixes"):
            previous_fixes_text = "\n".join([
                f"Attempt {i+1}: {fix.get('analysis', 'N/A')}"
                for i, fix in enumerate(error_context["previous_fixes"])
            ])
        
        return f"""You are a SQL debugging expert specializing in Snowflake to StarRocks conversions.

**Original Snowflake Query:**
```sql
{error_context['original_query']}
```

**Current StarRocks Query (with errors):**
```sql
{error_context['converted_query']}
```

**Error Message:**
{error_context['error_message']}

**Error Details:**
{json.dumps(error_context['error_details'], indent=2)}

**Iteration:** {iteration}/{self.max_iterations}

**Previous Fix Attempts:**
{previous_fixes_text}

**Your Task:**
1. Analyze the root cause of the error
2. Identify what needs to be fixed in the StarRocks query
3. Provide the corrected query
4. List specific changes made
5. Assess your confidence in the fix (0.0 to 1.0)

**Important StarRocks Differences:**
- Use JSON instead of VARIANT
- Use UNNEST instead of FLATTEN
- Use JSON_EXTRACT instead of GET_PATH
- Use CAST(x AS type) instead of x::type
- Use CONCAT() instead of ||
- QUALIFY clause not supported (use subquery with ROW_NUMBER)
- Use DATETIME instead of TIMESTAMP_NTZ/LTZ/TZ

**Response Format (JSON):**
```json
{{
  "analysis": "Detailed explanation of the root cause",
  "fixed_query": "The complete corrected StarRocks SQL query",
  "changes": [
    "Change 1: Description",
    "Change 2: Description"
  ],
  "confidence": 0.95
}}
```

Provide ONLY the JSON response, no additional text:"""
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the agent's JSON response.
        
        Args:
            response_text: Raw response from the agent.
            
        Returns:
            Parsed response dictionary.
        """
        try:
            # Try to extract JSON from code blocks
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1)
            
            result = json.loads(response_text)
            
            # Validate required fields
            required_fields = ["analysis", "fixed_query", "changes", "confidence"]
            for field in required_fields:
                if field not in result:
                    logger.warning(f"Missing field in response: {field}")
                    result[field] = "" if field != "confidence" else 0.5
            
            # Ensure confidence is a float between 0 and 1
            try:
                result["confidence"] = float(result["confidence"])
                result["confidence"] = max(0.0, min(1.0, result["confidence"]))
            except (ValueError, TypeError):
                result["confidence"] = 0.5
            
            # Determine if we should retry
            result["should_retry"] = result["confidence"] >= 0.7
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            logger.debug(f"Raw response: {response_text}")
            
            # Return a fallback response
            return {
                "analysis": "Failed to parse agent response",
                "fixed_query": "",
                "changes": [],
                "confidence": 0.0,
                "should_retry": False
            }
    
    def should_continue(self, iteration: int, confidence: float) -> bool:
        """Determine if debugging should continue.
        
        Args:
            iteration: Current iteration number.
            confidence: Confidence score of the last fix.
            
        Returns:
            True if should continue debugging.
        """
        if iteration >= self.max_iterations:
            logger.warning(f"Reached max iterations ({self.max_iterations})")
            return False
        
        if confidence < 0.7:
            logger.warning(f"Low confidence ({confidence}), may need manual review")
        
        return True
