# Snowflake to StarRocks SQL Conversion Guide

## Purpose
Convert Snowflake SQL queries to StarRocks-compatible SQL syntax.

## Critical Instructions

1. **Output the COMPLETE converted SQL query**
2. **Do NOT abbreviate or truncate the query**
3. **Do NOT add explanations before or after the SQL**
4. **Output ONLY the converted SQL code**

## Conversion Rules

### Database/Schema References
- Snowflake: `"DATABASE"."SCHEMA"."TABLE"`
- StarRocks: `DATABASE.SCHEMA.TABLE` (remove quotes)

### Date Functions
- `TRY_TO_DATE()` → `STR_TO_DATE()` or `DATE()`
- `CURRENT_DATE()` → `CURRENT_DATE` (remove parentheses)
- `DATEADD()` → `DATE_ADD()` or `DATE_SUB()`
- `DATEDIFF()` → `DATEDIFF()`

### String Functions
- `CONCAT()` → `CONCAT()`
- `SUBSTR()` → `SUBSTRING()`
- `LENGTH()` → `LENGTH()`

### Window Functions
- `ROW_NUMBER() OVER()` → `ROW_NUMBER() OVER()`
- `QUALIFY` → Convert to subquery with WHERE

### Interval Syntax
- `INTERVAL '1 DAY'` → `INTERVAL 1 DAY`
- `INTERVAL '1 MONTH'` → `INTERVAL 1 MONTH`

### Case Sensitivity
- Remove double quotes from identifiers
- Keep single quotes for string literals

### QUALIFY Clause
Snowflake's `QUALIFY` must be converted to a subquery:

**Snowflake:**
```sql
SELECT * FROM table
QUALIFY ROW_NUMBER() OVER(PARTITION BY id ORDER BY date DESC) = 1
```

**StarRocks:**
```sql
SELECT * FROM (
  SELECT *, ROW_NUMBER() OVER(PARTITION BY id ORDER BY date DESC) as rn
  FROM table
) WHERE rn = 1
```

## Important Notes

- Preserve ALL column names and aliases
- Preserve ALL table names and aliases
- Preserve ALL JOIN conditions
- Preserve ALL WHERE clauses
- Preserve ALL GROUP BY clauses
- Preserve ALL ORDER BY clauses
- Preserve the complete query structure

## Now Convert the Following SQL Query

Return ONLY the converted SQL code, nothing else.
