# SQL Syntax Conversion: Snowflake → StarRocks

Convert Snowflake-specific SQL syntax to StarRocks-compatible SQL.
Apply this skill whenever converting `.sql` files or embedded SQL strings in Python scripts.

---

## Transformation Rules

### Identifiers
Remove double-quotes from database/schema/table identifiers:
```sql
-- Before
SELECT * FROM "CSPL_DB"."PROD"."ORDERS"

-- After
SELECT * FROM CSPL_DB.PROD.ORDERS
```

---

### Date Functions

| Snowflake | StarRocks |
|-----------|-----------|
| `TRY_TO_DATE(x)` | `STR_TO_DATE(x, '%Y-%m-%d')` |
| `TO_DATE(x)` | `DATE(x)` |
| `CURRENT_DATE()` | `CURRENT_DATE` (no parentheses) |
| `TO_TIMESTAMP_NTZ(x)` | `CAST(x AS DATETIME)` |
| `TRY_TO_TIMESTAMP(x)` | `STR_TO_DATE(x, '%Y-%m-%d %H:%i:%S')` |
| `TO_TIMESTAMP(x)` | `CAST(x AS DATETIME)` |

---

### Interval Syntax
```sql
-- Before
DATEADD(DAY, -7, CURRENT_DATE())
INTERVAL '1 DAY'
INTERVAL '330 minutes'

-- After
DATE_SUB(CURRENT_DATE, INTERVAL 7 DAY)
INTERVAL 1 DAY
INTERVAL 330 MINUTE
```

### DATEDIFF — argument order is flipped
```sql
-- Before (Snowflake): DATEDIFF('day', start, end)
DATEDIFF('day', created_date, CURRENT_DATE())

-- After (StarRocks): DATEDIFF(end, start) — no unit string
DATEDIFF(CURRENT_DATE, created_date)
```

---

### QUALIFY Clause
StarRocks does not support `QUALIFY`. Convert to a subquery:

```sql
-- Before
SELECT appointment_id, ROW_NUMBER() OVER (PARTITION BY id ORDER BY ts DESC) AS rn
FROM my_table
QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY ts DESC) = 1

-- After
SELECT appointment_id FROM (
    SELECT appointment_id, ROW_NUMBER() OVER (PARTITION BY id ORDER BY ts DESC) AS rn
    FROM my_table
) t
WHERE rn = 1
```

---

### String / Type Functions

| Snowflake | StarRocks |
|-----------|-----------|
| `TO_VARCHAR(x)` | `CAST(x AS VARCHAR)` |
| `TRY_CAST(x AS NUMBER)` | `CAST(x AS DECIMAL)` |
| `CONTAINS(col, val)` | `col LIKE CONCAT('%', val, '%')` |
| `IFF(cond, a, b)` | `IF(cond, a, b)` |
| `NVL(x, y)` | `IFNULL(x, y)` |
| `ZEROIFNULL(x)` | `IFNULL(x, 0)` |

---

### JSON / Semi-structured
```sql
-- Before (Snowflake)
TRY_PARSE_JSON(col):field::int

-- After (StarRocks — use JSON_EXTRACT or rewrite as needed)
CAST(JSON_EXTRACT(col, '$.field') AS INT)
```

---

### Generator / Sequence (Snowflake-specific, no direct equivalent)
```sql
-- Before
SELECT TO_DATE(DATEADD(DAY, -SEQ4(), CURRENT_DATE())) AS DATE
FROM TABLE(GENERATOR(ROWCOUNT => 900))

-- After: replace with a numbers/calendar table or CTE approach
-- Flag for manual review if a suitable table is not available
```

---

### Snowflake Comments in SQL
```sql
-- Before (Snowflake uses // as inline comment in some contexts)
left join table1 // some comment

-- After: replace // with --
left join table1 -- some comment
```

---

## Rules

1. Apply all transformations — do not skip any rule
2. Preserve all logic — do not change WHERE conditions, JOINs, or aggregations
3. Preserve aliases and CTE names exactly
4. Flag any construct you cannot automatically convert with a `-- TODO: manual review` comment
5. Do not reformat or re-indent the SQL — preserve original structure
