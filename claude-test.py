#!/usr/bin/env python3
"""
Claude Agent SDK - Connection Conversion Test
Reads prompt.md and python_script.py, then converts using Claude Agent SDK
"""

import asyncio
import os
import sys
from pathlib import Path
from claude_agent_sdk import query


def read_file(filename: str) -> str:
    """
    Read file content
    
    Args:
        filename: Path to file
        
    Returns:
        File content as string
    """
    try:
        with open(filename, 'r') as f:
            return f.read()
    except FileNotFoundError:
        print(f"✗ Error: {filename} not found")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error reading {filename}: {str(e)}")
        sys.exit(1)


def extract_message_content(message) -> str:
    """
    Extract content from different message types
    
    Args:
        message: Message object from query()
        
    Returns:
        String representation of the message
    """
    message_type = type(message).__name__
    
    # Handle SystemMessage (initialization data)
    if message_type == "SystemMessage":
        return ""  # Skip system messages
    
    # Handle AssistantMessage (thinking and responses)
    elif message_type == "AssistantMessage":
        content_list = []
        
        if hasattr(message, 'content') and message.content:
            for block in message.content:
                block_type = type(block).__name__
                
                # Extract text content
                if block_type == "TextBlock":
                    if hasattr(block, 'text'):
                        content_list.append(block.text)
                
                # Skip thinking blocks in output
                elif block_type != "ThinkingBlock":
                    if hasattr(block, 'text'):
                        content_list.append(str(block.text))
        
        return "".join(content_list)
    
    # Handle ResultMessage (final result)
    elif message_type == "ResultMessage":
        if hasattr(message, 'result') and message.result:
            return str(message.result)
        return ""
    
    return ""


async def convert_connection_code(api_key: str, prompt_file: str, code_file: str) -> dict:
    """
    Convert Snowflake connection code to StarRocks using Claude Agent SDK
    
    Args:
        api_key: Anthropic API key
        prompt_file: Path to prompt.md
        code_file: Path to python_script.py
        
    Returns:
        Dictionary with conversion result
    """
    print("\n" + "="*80)
    print("READING FILES")
    print("="*80)
    
    # Read files
    print(f"\n[1] Reading {prompt_file}...")
    prompt_template = read_file(prompt_file)
    print(f"✓ Read {len(prompt_template)} characters from prompt.md")
    
    print(f"\n[2] Reading {code_file}...")
    snowflake_code = read_file(code_file)
    print(f"✓ Read {len(snowflake_code)} characters from python_script.py")
    
    # Combine prompt and code
    print("\n" + "="*80)
    print("PREPARING CONVERSION PROMPT")
    print("="*80)
    
    full_prompt = f"""{prompt_template}

```python
{snowflake_code}
```"""
    
    print(f"\n✓ Combined prompt: {len(full_prompt)} characters")
    print(f"✓ Ready to send to Claude Agent SDK")
    
    # Send to Claude Agent SDK
    print("\n" + "="*80)
    print("SENDING TO CLAUDE AGENT SDK")
    print("="*80)
    
    print(f"\nPrompt sent to Claude Agent SDK...\n")
    print("-"*80)
    print("CONVERSION OUTPUT:")
    print("-"*80 + "\n")
    
    messages = []
    converted_code = ""
    
    try:
        async for message in query(prompt=full_prompt):
            message_type = type(message).__name__
            messages.append(message)
            
            content = extract_message_content(message)
            
            if content:
                print(content, end="", flush=True)
                converted_code += content
        
        print("\n" + "-"*80)
        
        result = {
            "status": "success",
            "messages_received": len(messages),
            "converted_code": converted_code,
            "code_length": len(converted_code)
        }
        
        return result
        
    except Exception as e:
        import traceback
        print(f"\n✗ Error: {str(e)}")
        traceback.print_exc()
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e)
        }


def print_summary(result: dict):
    """Print conversion summary"""
    print("\n" + "="*80)
    print("CONVERSION SUMMARY")
    print("="*80)
    
    if result["status"] == "success":
        print("\n✓ CONVERSION SUCCESSFUL")
        print(f"\nMessages processed: {result['messages_received']}")
        print(f"Converted code length: {result['code_length']} characters")
        
        print("\n" + "="*80)
        print("CONVERTED CODE")
        print("="*80)
        print("\n" + result['converted_code'])
        
        # Save to file
        output_file = "converted_starrocks.py"
        with open(output_file, 'w') as f:
            f.write(result['converted_code'])
        print(f"\n✓ Converted code saved to: {output_file}")
        
    else:
        print(f"\n✗ CONVERSION FAILED")
        print(f"Error Type: {result['error_type']}")
        print(f"Error: {result['error_message']}")
    
    print("\n" + "="*80 + "\n")


async def main():
    """Main async function"""
    print("\n" + "#"*80)
    print("# CLAUDE AGENT SDK - CONNECTION CONVERTER")
    print("# Reads prompt.md and python_script.py")
    print("#"*80)
    
    os.environ["ANTHROPIC_API_KEY"] = api_key
    print("✓ API key set\n")
    
    # Check if files exist
    prompt_file = "prompt.md"
    code_file = "python_script.py"
    
    if not Path(prompt_file).exists():
        print(f"✗ {prompt_file} not found")
        sys.exit(1)
    
    if not Path(code_file).exists():
        print(f"✗ {code_file} not found")
        sys.exit(1)
    
    # Run conversion
    try:
        result = await convert_connection_code(api_key, prompt_file, code_file)
        # print_summary(result)
        
    except KeyboardInterrupt:
        print("\n\n✗ Conversion interrupted by user")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())