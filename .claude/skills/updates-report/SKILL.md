# Updates Report Generation

Generate a UPDATES.md file summarising the Snowflake → StarRocks conversion run.

---

## Output

Write to: `{output_folder}/UPDATES.md`

---

## Format

```markdown
# Conversion Updates - Snowflake to StarRocks

**Conversion Date:** YYYY-MM-DD HH:MM:SS
**Input:** `{zip_path}`
**Total Files Processed:** N
**Successfully Converted:** N
**Failed:** N

---

## Changes Made

### {output_filename}
**Original:** `{input_file_path}`
**Type:** Python | SQL | Config

**Changes:**
- {change 1}
- {change 2}

### {output_filename}
...

---

## Failed Conversions

- **{filename}** ({type}): {error message}
```

---

## Rules

1. One `### {filename}` section per successfully converted file — use the output filename, not the full path
2. List every item in the `changes` array as a bullet point under **Changes:**
3. Only include the **Failed Conversions** section if there are failures; omit it entirely otherwise
4. Date format: `YYYY-MM-DD HH:MM:SS` (local time at time of writing)
5. Do not add any content beyond what the results contain — no summaries, no recommendations
