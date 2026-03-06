# Azhar's Claude Context

## Who I Am
ML Platform Engineer at CARS24. I work across a broad stack — data infrastructure,
backend services, internal tooling, AI-powered applications, and frontend interfaces.
Currently focused on Snowflake → Iceberg migration and Claude Agent SDK development.

---

## My Stack

- **Languages**: Python (primary), Bash, TypeScript (occasional)
- **Data**: Snowflake, Apache Iceberg, StarRocks, DuckDB, Spark, dbt
- **Backend**: FastAPI, REST APIs
- **Infrastructure**: Terraform, Helm, Kubernetes
- **AI**: Anthropic Claude API, Claude Agent SDK, MCP
- **Notebooks**: JupyterHub
- **Frontend**: React (internal tooling)
- **CLI**: Python-based CLI tooling

---

## How I Work

- I value simple, practical solutions over clever or over-engineered ones
- Be concise — I don't need long explanations unless I ask for them
- Don't pad responses. Make your point and stop.
- When I ask for code, write the code. Don't narrate what you're about to do before doing it.
- Prefer explicit over implicit — no magic, no hidden behavior
- When there are tradeoffs, state them briefly. Don't hedge endlessly.
- If something is unclear, ask one focused question. Don't ask multiple at once.

---

## Code Preferences

- **Python**: type hints always, explicit error handling, no bare `except`, use `logging` not `print`
- **Structure**: flat over nested — avoid deep abstractions for their own sake
- **Functions**: do one thing, named clearly after what they do
- **Comments**: explain *why*, not *what*
- **Tests**: practical, not ceremonial — test behavior not implementation
- **Dependencies**: prefer stdlib or well-known libraries; avoid adding deps for trivial things

---

## What I Don't Want

- Don't suggest LangChain or LlamaIndex unless I ask
- Don't use ORMs when raw SQL is simpler and clearer
- Don't use pandas when DuckDB or plain Python can do the job
- Don't add complexity in the name of "best practices" if the simple version works
- Don't over-comment obvious code

---

## Active Work

- Snowflake → Iceberg SQL/Python/Shell script migration tool (with Gauri Bansal)
- Claude Agent SDK applications and internal AI tooling
- ML/data platform infrastructure at CARS24

---

## Skills Available

Load these automatically or invoke with `/skill-name`:

- `/python`          — general Python best practices
- `/sdk`             — Anthropic Messages API patterns
- `/claude-agent-sdk`— agent loops, subagents, sessions, hooks
- `/mcp`             — MCP server building, tool definitions
- `/cli`             — CLI design, arg parsing, UX patterns
- `/backend`         — service structure, API contracts
- `/scripts`         — bash/shell standards, logging
- `/jupyter`         — notebook structure, cell conventions
- `/iac`             — Terraform/Pulumi patterns, naming
- `/helm`            — chart structure, values, best practices
- `/frontend`        — React component patterns, styling, state

---

## Workspace

- OS: Linux
- Python: 3.11+
- Package manager: pip / uv
