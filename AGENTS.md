# Agent Architecture for Snowflake-to-StarRocks Conversion System

## Overview

This document outlines the multi-agent architecture for converting Snowflake Python scripts (connections + queries) to StarRocks-compatible Python scripts. The system uses Claude Agent SDK to implement two specialized AI agents that handle different aspects of the conversion process.

## System Architecture

```
Input: Python Script (Snowflake Connection + Query)
                    |
        +-----------+-----------+
        |                       |
   AI Layer 1              AI Layer 2
Connection Converter    Query Converter
  (Claude Agent)      (Deterministic Rules)
        |                       |
        v                       v
Converted Connection      Converted Query
(StarRocks Config)        (StarRocks SQL)
        |                       |
        +----------+------------+
                   |
                   v
        Assemble Converted Script
        (Python with StarRocks)
                   |
                   v
          Validation Script
          (Test Execution)
                   |
        +----------+----------+
        |          |          |
    Passes      Fails    Still Failing
        |          |          |
        v          v          v
    Valid    Error Details  Max Iterations?
   Output    + Context         |
                |          +---+---+
                |          |       |
                |         No      Yes
                |          |       |
                |          v       v
                |    AI Layer 2  Manual Review
                |    Debugging   (Error Log)
                |    (Claude Agent SDK)
                |          |
                |          v
                |    Propose Query Fix
                |          |
                +----------+
                           |
                           v
                  Apply Fix to Query
                           |
                           v
                  (Loop back to Validation)
```

## Agent Definitions

### Agent 1: Connection Converter (AI-Powered)

**Purpose**: Convert Snowflake connection configurations to StarRocks connection configurations.

**Technology**: Claude Agent SDK with Claude API

**Responsibilities**:
- Parse Snowflake connection parameters (account, warehouse, database, schema, role, user, password)
- Map to StarRocks connection parameters (host, port, database, user, password)
- Generate StarRocks connection configuration in Python format
- Handle authentication differences between platforms
- Preserve connection pooling and timeout settings where applicable

**Input Format**:
```python
# Snowflake connection example
import snowflake.connector
conn = snowflake.connector.connect(
    user='USER',
    password='PASSWORD',
    account='ACCOUNT',
    warehouse='WAREHOUSE',
    database='DATABASE',
    schema='SCHEMA'
)
```

**Output Format**:
```python
# StarRocks connection example
import pymysql
conn = pymysql.connect(
    host='HOST',
    port=9030,
    user='USER',
    password='PASSWORD',
    database='DATABASE'
)
```

**Agent Configuration**:
- Model: Claude 3.5 Sonnet (or latest)
- Temperature: 0.1 (low for consistency)
- Max tokens: 4096
- Tools: None (pure text transformation)

---

### Agent 2: Debugging & Fixing Agent (AI-Powered)

**Purpose**: Debug and fix validation errors in converted queries through iterative refinement.

**Technology**: Claude Agent SDK with Claude API

**Responsibilities**:
- Analyze validation error messages and context
- Identify root causes of conversion failures
- Propose targeted fixes for SQL syntax/semantic issues
- Handle StarRocks-specific SQL dialect differences
- Iterate on fixes until validation passes or max iterations reached

**Input Format**:
```json
{
  "original_snowflake_query": "SELECT ...",
  "converted_starrocks_query": "SELECT ...",
  "error_message": "SQL syntax error: ...",
  "error_context": {
    "line_number": 5,
    "error_type": "SyntaxError",
    "failed_statement": "..."
  },
  "iteration_count": 1
}
```

**Output Format**:
```json
{
  "analysis": "The error is caused by...",
  "proposed_fix": "SELECT ... (corrected query)",
  "changes_made": [
    "Replaced VARIANT with JSON",
    "Changed FLATTEN to UNNEST"
  ],
  "confidence": 0.95
}
```

**Agent Configuration**:
- Model: Claude 3.5 Sonnet (or latest)
- Temperature: 0.2 (slightly higher for creative problem-solving)
- Max tokens: 8192
- Tools: 
  - SQL syntax validator
  - StarRocks documentation lookup
  - Error pattern matcher

**Iteration Logic**:
- Max iterations: 3
- If validation fails after 3 iterations → Manual review required
- Each iteration includes full error context and previous fix attempts

---

## Deterministic Components

### Query Converter (Logic-Based)

**Purpose**: Convert Snowflake SQL queries to StarRocks SQL using deterministic rules.

**Technology**: Python with rule-based transformations (no AI)

**Key Conversion Rules**:

1. **Data Type Mappings**:
   - `VARIANT` → `JSON`
   - `TIMESTAMP_NTZ` → `DATETIME`
   - `TIMESTAMP_LTZ` → `DATETIME`
   - `TIMESTAMP_TZ` → `DATETIME`
   - `NUMBER(38,0)` → `BIGINT`
   - `VARCHAR` → `VARCHAR` (same)
   - `ARRAY` → `ARRAY<JSON>`

2. **Function Mappings**:
   - `FLATTEN()` → `UNNEST()`
   - `PARSE_JSON()` → `PARSE_JSON()` (same)
   - `GET_PATH()` → `JSON_EXTRACT()`
   - `TO_TIMESTAMP()` → `STR_TO_DATE()`
   - `DATEADD()` → `DATE_ADD()`
   - `DATEDIFF()` → `DATEDIFF()`
   - `IFF()` → `IF()`
   - `LISTAGG()` → `GROUP_CONCAT()`

3. **Syntax Transformations**:
   - `QUALIFY` clause → Subquery with `ROW_NUMBER()`
   - `$1, $2` (positional) → Named columns
   - `::` casting → `CAST(... AS ...)`
   - `||` concatenation → `CONCAT()`
   - Lateral joins → Preserved (StarRocks supports)

4. **DDL Conversions**:
   - `CREATE TABLE ... CLUSTER BY` → `CREATE TABLE ... DISTRIBUTED BY HASH`
   - `TRANSIENT TABLE` → Regular table (no transient in StarRocks)
   - `STAGE` references → External table or file path

**Implementation**: Rule engine with regex patterns and AST parsing

---

## Workflow Stages

### Stage 1: Input Processing
- Parse input Python script
- Extract connection configuration
- Extract SQL queries
- Identify Snowflake-specific constructs

### Stage 2: Parallel Conversion
- **Track A**: Connection Converter Agent (AI Layer 1)
  - Convert connection config to StarRocks format
- **Track B**: Query Converter (Deterministic)
  - Apply rule-based SQL transformations

### Stage 3: Assembly
- Combine converted connection + converted query
- Generate complete Python script with StarRocks imports
- Add error handling and logging

### Stage 4: Validation
- Execute converted script in test environment
- Capture execution results and errors
- Generate validation report

### Stage 5: Error Resolution Loop
- **If validation passes**: Output valid converted script
- **If validation fails**: 
  - Send to Debugging Agent (AI Layer 2)
  - Agent analyzes error and proposes fix
  - Apply fix to query
  - Re-run validation
  - Repeat up to 3 iterations
- **If max iterations reached**: Flag for manual review with full error log

---

## Agent SDK Implementation Details

### Agent 1: Connection Converter

```python
from anthropic import Anthropic

class ConnectionConverterAgent:
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"
        
    def convert(self, snowflake_connection: str) -> str:
        prompt = f"""Convert this Snowflake connection to StarRocks format.

Snowflake Connection:
{snowflake_connection}

Requirements:
1. Use pymysql for StarRocks connection
2. Map Snowflake parameters to StarRocks equivalents
3. Default StarRocks port is 9030
4. Return only the Python connection code

Output the converted connection code:"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            temperature=0.1,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.content[0].text
```

### Agent 2: Debugging Agent

```python
from anthropic import Anthropic

class DebuggingAgent:
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"
        self.max_iterations = 3
        
    def debug_and_fix(self, error_context: dict, iteration: int) -> dict:
        prompt = f"""You are a SQL debugging expert. Fix this StarRocks query error.

Original Snowflake Query:
{error_context['original_query']}

Current StarRocks Query:
{error_context['converted_query']}

Error Message:
{error_context['error_message']}

Error Context:
{error_context['error_details']}

Iteration: {iteration}/{self.max_iterations}

Previous Attempts:
{error_context.get('previous_fixes', 'None')}

Analyze the error and provide:
1. Root cause analysis
2. Corrected StarRocks query
3. Explanation of changes

Return as JSON:
{{
  "analysis": "...",
  "fixed_query": "...",
  "changes": ["..."]
}}"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=8192,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return self.parse_response(response.content[0].text)
```

---

## Configuration

### Environment Variables
```bash
ANTHROPIC_API_KEY=your_api_key_here
STARROCKS_HOST=localhost
STARROCKS_PORT=9030
STARROCKS_USER=root
STARROCKS_PASSWORD=
MAX_DEBUG_ITERATIONS=3
VALIDATION_TIMEOUT=30
```

### Config File (config.yaml)
```yaml
agents:
  connection_converter:
    model: claude-3-5-sonnet-20241022
    temperature: 0.1
    max_tokens: 4096
    
  debugging_agent:
    model: claude-3-5-sonnet-20241022
    temperature: 0.2
    max_tokens: 8192
    max_iterations: 3

conversion:
  rules_file: rules/conversion_rules.yaml
  validation_enabled: true
  test_execution: true

starrocks:
  host: ${STARROCKS_HOST}
  port: ${STARROCKS_PORT}
  database: test_db
  user: ${STARROCKS_USER}
  password: ${STARROCKS_PASSWORD}
```

---

## Error Handling Strategy

### Validation Errors
1. **Syntax Errors**: Debugging agent fixes SQL syntax
2. **Semantic Errors**: Debugging agent adjusts logic
3. **Connection Errors**: Logged for manual review (not agent-fixable)
4. **Timeout Errors**: Increase timeout or flag for optimization

### Agent Failures
1. **API Errors**: Retry with exponential backoff (3 attempts)
2. **Invalid Output**: Fallback to manual review
3. **Rate Limits**: Queue requests and process sequentially

### Manual Review Triggers
- Max debugging iterations exceeded
- Agent confidence < 0.7
- Critical syntax errors persist
- Connection configuration issues

---

## Success Metrics

1. **Conversion Accuracy**: % of scripts that validate successfully
2. **First-Pass Success Rate**: % passing without debugging iterations
3. **Average Iterations**: Mean number of debugging cycles needed
4. **Manual Review Rate**: % requiring human intervention
5. **Conversion Time**: Average time per script conversion

---

## Future Enhancements

1. **Agent 3: Optimization Agent** - Optimize converted queries for StarRocks performance
2. **Learning System**: Train on successful conversions to improve rules
3. **Multi-file Support**: Handle complex projects with multiple scripts
4. **Interactive Mode**: Allow user to guide agent decisions
5. **Rollback Mechanism**: Version control for conversion attempts

---

## Dependencies

```
anthropic>=0.18.0
pymysql>=1.1.0
pyyaml>=6.0
sqlparse>=0.4.4
pytest>=7.4.0
```

---

## Getting Started

1. Install dependencies: `pip install -r requirements.txt`
2. Set up environment variables in `.env`
3. Configure `config.yaml` with your settings
4. Run: `python main.py --input snowflake_script.py --output starrocks_script.py`

---

## References

- [Claude Agent SDK Documentation](https://platform.claude.com/docs/en/agent-sdk/overview)
- [StarRocks SQL Reference](https://docs.starrocks.io/docs/sql-reference/)
- [Snowflake to StarRocks Migration Guide](https://docs.starrocks.io/)
