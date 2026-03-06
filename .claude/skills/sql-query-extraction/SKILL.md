# SQL Query Extraction from Python Scripts

Extract embedded SQL strings from Python source files, convert them, and replace in-place.
Apply this skill after `python-connection-conversion` when processing `.py` files.

---

## Step 1: Identify SQL Strings

Look for strings containing SQL keywords: `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `WITH`, `MERGE`, `CREATE`, `DROP`, `TRUNCATE`.

Priority order for detection:
1. Triple double-quoted strings: `"""..."""`
2. Triple single-quoted strings: `'''...'''`
3. Double-quoted strings: `"..."`
4. Single-quoted strings: `'...'`

Also check for variable assignment context:
```python
query = """SELECT ..."""     # variable_name = "query"
sql = "SELECT ..."           # variable_name = "sql"
```

---

## Step 2: Extract and Convert Each Query

For each identified SQL string:
1. Extract the raw query text (without surrounding quotes)
2. Apply the `sql-syntax-conversion` skill to convert Snowflake syntax → StarRocks
3. Track whether the conversion changed the query

---

## Step 3: Replace in Script

Replace in **reverse order** (bottom to top) to preserve character positions for earlier replacements.

Build the replacement string preserving the original quote style:
```python
# Original: triple double-quoted
"""SELECT * FROM CSPL_DB.ORDERS"""
# Replaced with same quote style
"""SELECT * FROM CSPL_DB.ORDERS"""
```

---

## Step 4: Failure Handling

If conversion of a query fails:
- Keep the original query unchanged
- Log a warning with the query number and line number
- Continue processing remaining queries
- Never corrupt the surrounding Python syntax

---

## Rules

1. Never change variable names, indentation, or surrounding Python code
2. Never combine or split queries
3. Preserve the exact quote type (`"""`, `'''`, `"`, `'`)
4. If a string contains both SQL and non-SQL content (e.g. a docstring), skip it
5. Replace only the first occurrence when the same string appears multiple times
6. After all replacements, verify the script is still syntactically valid Python

---

## Output

Return:
- The converted script (string)
- A summary: total queries found, successfully converted, failed
- For failures: query number, line number, error message