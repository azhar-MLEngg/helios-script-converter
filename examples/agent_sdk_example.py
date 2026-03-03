"""Example of using Claude Agent SDK for conversion tasks."""

import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions


async def convert_with_agent_sdk():
    """Example: Convert Snowflake connection using Agent SDK."""
    
    snowflake_code = """
import snowflake.connector

conn = snowflake.connector.connect(
    user='myuser',
    password='mypass',
    account='myaccount',
    warehouse='mywarehouse',
    database='mydb'
)
"""
    
    prompt = f"""Convert this Snowflake connection code to StarRocks format using pymysql.

Snowflake code:
{snowflake_code}

Requirements:
- Use pymysql library
- Map parameters appropriately (host, port, user, password, database)
- Default port is 9030
- Return only the converted Python code
"""
    
    print("Converting with Claude Agent SDK...\n")
    
    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            model="claude-3-haiku-20240307",
            max_tokens=4096,
            temperature=0.1
        ),
    ):
        if hasattr(message, "result"):
            print("Converted code:")
            print(message.result)


async def debug_with_agent_sdk():
    """Example: Debug SQL query using Agent SDK."""
    
    error_context = """
Original Snowflake query:
SELECT id::VARCHAR, created_at::TIMESTAMP_NTZ FROM users

Converted StarRocks query (with error):
SELECT id::VARCHAR, created_at::TIMESTAMP_NTZ FROM users

Error: Unknown data type TIMESTAMP_NTZ

Fix this query for StarRocks compatibility.
"""
    
    print("\nDebugging with Claude Agent SDK...\n")
    
    async for message in query(
        prompt=error_context,
        options=ClaudeAgentOptions(
            model="claude-3-haiku-20240307",
            max_tokens=4096,
            temperature=0.2
        ),
    ):
        if hasattr(message, "result"):
            print("Fixed query:")
            print(message.result)


if __name__ == "__main__":
    # Run examples
    asyncio.run(convert_with_agent_sdk())
    asyncio.run(debug_with_agent_sdk())
