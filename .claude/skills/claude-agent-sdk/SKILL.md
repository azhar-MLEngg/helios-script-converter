---
name: claude-agent-sdk
description: Best practices for building applications with the Claude Agent SDK. Auto-load when writing agent loops, subagents, custom tools, hooks, or any code using @anthropic-ai/claude-agent-sdk or claude_agent_sdk.
---
# Claude Agent SDK Best Practices
## Core Concept
The Agent SDK is the infrastructure behind Claude Code, exposed as a library.
It handles the agent loop, tool execution, context compaction, and session management.
You do not manage stop reasons or tool result feeding -- the SDK does that.
```python
# SDK handles the loop
async for message in query(
    prompt="Fix the bug in auth.py",
    options=ClaudeAgentOptions(allowed_tools=["Read", "Edit", "Bash"])
):
    if hasattr(message, "result"):
        print(message.result)
# Don't roll your own loop against the raw API
while response.stop_reason == "tool_use":
    # manually feeding tool results back... don't do this
```
---
## Project Structure
```
my_agent/
├── src/
│   └── my_agent/
│       ├── __init__.py
│       ├── agent.py          # Main query() entry points
│       ├── agents/           # Subagent definitions (.md files)
│       ├── tools/            # Custom tool implementations
│       ├── hooks/            # Hook handlers
│       └── config.py         # AgentOptions config
├── .claude/
│   └── agents/               # Filesystem-based subagent definitions
├── tests/
└── pyproject.toml
```
---
## query() -- The Entry Point
Always use `async for` -- it streams messages as the agent works.
```python
from claude_agent_sdk import query, ClaudeAgentOptions
async def run():
    async for message in query(
        prompt="Analyse the schema in schema.sql and suggest optimisations",
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Bash", "Grep"],
            max_turns=10,
        )
    ):
        if hasattr(message, "type"):
            if message.type == "assistant":
                print(message.content)
            elif message.type == "result":
                print("Final result:", message.result)
```
### Key options
| Option | Use |
|---|---|
| `allowed_tools` | Always restrict to only what the agent needs |
| `max_turns` | Always set -- never let an agent run unbounded |
| `system_prompt` | Define the agent's role and constraints |
| `model` | Default is sonnet; use `opus` only for high-stakes tasks |
| `permission_mode` | `"default"` prompts user; `"acceptEdits"` auto-approves file edits |
---
## Tool Access -- Principle of Least Privilege
Only give an agent the tools it actually needs. Never use `"*"`.
```python
# Scoped tools
ClaudeAgentOptions(allowed_tools=["Read", "Grep", "Glob"])
# Too permissive -- don't do this
ClaudeAgentOptions(allowed_tools=["*"])
```
Built-in tools available:
`Read`, `Write`, `Edit`, `Bash`, `Glob`, `Grep`, `WebSearch`, `WebFetch`, `Task`
---
## Building Blocks of an Agentic Application
An agentic application is composed from five primitives. When helping write agent code,
use this guide to determine which primitive to reach for based on what the application needs.
---
### Subagents -- when the task needs isolation or parallelism
Write a subagent definition when the application needs to:
- Run multiple tasks simultaneously without them interfering with each other
- Offload heavy exploration (reading files, searching codebases) without bloating the main context
- Enforce strict tool restrictions on a specific job (e.g. a reviewer that can only Read, never Write)
- Keep intermediate work out of the main context -- the main agent only sees the final result
```python
# Define in code when building SDK applications
agents={
    "sql-reviewer": AgentDefinition(
        description="Reviews SQL for Iceberg compatibility and performance issues.",
        prompt="""You are a SQL review specialist for Snowflake-to-Iceberg migrations.
Check for: LATERAL FLATTEN usage, Snowflake-specific functions, unsupported syntax.
Return a structured list of issues with severity and suggested fixes.""",
        tools=["Read", "Grep"],  # read-only -- cannot modify files
        model="sonnet",
    ),
    "schema-analyser": AgentDefinition(
        description="Analyses table schemas and identifies partitioning opportunities.",
        prompt="You are a schema design expert...",
        tools=["Read"],
        model="sonnet",
    ),
}
# Main agent needs Task in allowedTools to spawn subagents
allowed_tools=["Read", "Bash", "Task"]
```
Do NOT write a subagent just to give the agent a different persona or tone.
A system prompt or skill handles that with far less overhead.
---
### Custom Tools -- when the application needs to call something external
Write a custom tool (via MCP server) when the application needs deterministic,
code-driven interaction with an external system -- not AI-generated output.
```python
# The tool does the work; Claude decides when to call it
async def run_iceberg_query(catalog: str, sql: str) -> str:
    """Execute a SQL query against the Iceberg catalog."""
    return execute_query(catalog, sql)
async def get_table_schema(database: str, table: str) -> dict:
    """Fetch schema metadata for a given table."""
    return fetch_schema(database, table)
server = create_sdk_mcp_server(
    name="data-tools",
    tools=[run_iceberg_query, get_table_schema]
)
options = ClaudeAgentOptions(
    mcp_servers=[server],
    allowed_tools=["Read", "data-tools/run_iceberg_query", "data-tools/get_table_schema"]
)
```
Write a custom tool when the application needs to:
- Query Snowflake, Iceberg, StarRocks, or DuckDB
- Trigger Airflow DAGs or call internal APIs
- Read from a data catalog or metadata store
- Do anything where the result must be deterministic, not generated
Do NOT write a custom tool for logic that is just instructions or reasoning.
That belongs in the system prompt or a skill.
---
### Skills -- when the agent needs a reusable methodology
Write a skill (`SKILL.md`) when the application involves a type of work that has
a consistent, repeatable approach worth encoding -- so Claude follows the same
methodology every time without being re-instructed.
```
.claude/skills/sql-migration/SKILL.md
.claude/skills/code-review/SKILL.md
.claude/skills/iac-authoring/SKILL.md
```
Write a skill when the application involves:
- A migration workflow with defined steps and syntax rules
- A code review standard the agent should always follow
- A documentation pattern or template approach
- Any repeating workflow where consistency matters across sessions
Skills auto-load when Claude detects relevant context, or are triggered via `/skill-name`.
They keep the system prompt lean -- load depth when needed, not always.
Do NOT write a skill for one-off tasks. Just prompt inline or use a slash command.
---
### Slash Commands -- when the user needs a fast, consistent trigger
Write a slash command (`.claude/commands/<name>.md`) when the application
exposes a specific workflow step that is always user-initiated with optional arguments.
```markdown
# .claude/commands/convert-script.md
---
description: Convert a Snowflake SQL script to Iceberg syntax
argument-hint: [script-path]
---
Convert the SQL script at $1 from Snowflake syntax to Apache Iceberg.
Follow the sql-migration skill. Validate the output before returning.
```
Write a slash command when:
- The trigger is always explicit -- the user decides when to run it
- The workflow takes arguments (file paths, IDs, options)
- You want a standardised entry point: `/convert-script src/pipeline.sql`
Do NOT use a slash command when Claude should decide when to invoke it. Use a skill.
---
### Plugins -- when the setup needs to be distributed
Write a plugin when the application packages multiple extensions together
for distribution -- to teammates, across repos, or as a shared workflow.
```
my-data-platform-plugin/
├── .claude-plugin/
│   └── plugin.json          # manifest
├── agents/
│   └── sql-reviewer.md
├── skills/
│   └── sql-migration/
│       └── SKILL.md
├── commands/
│   └── convert-script.md
└── .mcp.json                # MCP server definitions
```
Write a plugin when:
- The agent application ships as a team tool others will install
- Multiple extension types (agents + skills + commands) work together as a system
- You want `/plugin install` to set up everything in one command
For personal use only -- keep extensions directly in `.claude/`. No plugin needed.
---
### Decision Table
| What the application needs | Build |
|---|---|
| Parallel or isolated subtasks | Subagent |
| Call an external system (DB, API, service) | Custom Tool |
| Consistent methodology across sessions | Skill |
| User-initiated workflow with arguments | Slash Command |
| Distributable multi-extension setup | Plugin |
---
## Session Management -- Stateful Agents
Every `query()` without a `session_id` starts a fresh session.
Capture the session ID from the init message to resume.
```python
session_id = None
async for message in query(prompt="Start the migration analysis"):
    if message.type == "system" and message.subtype == "init":
        session_id = message.session_id
    if hasattr(message, "result"):
        print(message.result)
# Resume the same session later
async for message in query(
    prompt="Now generate the conversion report",
    options=ClaudeAgentOptions(resume=session_id)
):
    if hasattr(message, "result"):
        print(message.result)
```
---
## Hooks -- Deterministic Control Points
Use hooks to intercept agent behaviour at key points without modifying the agent loop.
```python
async def validate_bash_command(tool_input: dict, tool_use_id: str, context: dict) -> dict:
    command = tool_input.get("command", "")
    if any(danger in command for danger in ["rm -rf", "DROP TABLE", "truncate"]):
        return {"decision": "block", "reason": f"Blocked dangerous command: {command}"}
    return {}
options = ClaudeAgentOptions(
    hooks={
        "PreToolUse": [
            HookMatcher(matcher="Bash", hooks=[validate_bash_command])
        ]
    }
)
```
Hook types:
- `PreToolUse` -- intercept before a tool runs; can block or modify input
- `PostToolUse` -- observe tool results; useful for logging and metrics
- `Stop` -- trigger on agent completion
---
## Structured Output
When you need structured data back, prompt for JSON explicitly and parse the result block:
```python
prompt = """
Analyse the SQL file at scripts/pipeline.sql.
Respond ONLY with a JSON object -- no preamble, no markdown fences:
{
  "total_queries": int,
  "convertible": int,
  "issues": [{"query_id": str, "issue": str, "severity": "high|medium|low"}]
}
"""
async for message in query(prompt=prompt, options=options):
    if message.type == "result":
        try:
            report = json.loads(message.result)
        except json.JSONDecodeError:
            clean = message.result.strip().removeprefix("```json").removesuffix("```").strip()
            report = json.loads(clean)
```
---
## Error Handling
```python
from claude_agent_sdk import CLINotFoundError, AgentError
async def safe_run(prompt: str):
    try:
        async for message in query(prompt=prompt, options=options):
            yield message
    except CLINotFoundError:
        raise RuntimeError("Claude Code CLI not installed. Run: pip install claude-agent-sdk")
    except AgentError as e:
        logger.error("Agent failed: %s", e)
        raise
    except Exception as e:
        logger.exception("Unexpected error in agent execution")
        raise
```
---
## Cost and Turn Management
- Always set `max_turns` -- a runaway agent is expensive
- Use `sonnet` by default; only use `opus` for subagents doing high-stakes review
- For long-running pipelines, use session checkpointing to resume rather than restart
```python
async for message in query(prompt=prompt, options=ClaudeAgentOptions(max_turns=15)):
    if message.type == "system" and message.subtype == "init":
        logger.info("Session: %s", message.session_id)
    if message.type == "result":
        logger.info("Turns used: %s | Cost: %s", message.num_turns, message.usage)
```
---
## What Not to Do
- Don't include `Task` in a subagent's tools -- subagents cannot spawn subagents
- Don't use `permission_mode="bypassPermissions"` in production
- Don't give agents write access to files they only need to read
- Don't build your own agent loop against the raw Anthropic API when the SDK handles it
- Don't use unbounded `max_turns` -- always set a ceiling
- Don't ignore the `result` message type -- it is the agent's final answer
