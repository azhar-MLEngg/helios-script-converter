# Configuration File Conversion for Snowflake to StarRocks Migration

## Purpose
Review and update configuration files to remove Snowflake-specific settings and add StarRocks/Helios SDK requirements.

## Instructions

**Analyze the provided file and make ONLY the necessary changes for StarRocks migration:**

### For `config.ini` or `.ini` files:
1. **Remove** any Snowflake-specific settings:
   - `SNOWFLAKE_CREDS_FILE`
   - `SNOWFLAKE_USER`
   - `SNOWFLAKE_PASSWORD`
   - `SNOWFLAKE_ACCOUNT`
   - `SNOWFLAKE_WAREHOUSE`
   - `SNOWFLAKE_DATABASE`
   - `SNOWFLAKE_SCHEMA`
   - Any other Snowflake connection parameters

2. **Keep** all other application settings unchanged:
   - Email settings
   - File paths (except Snowflake credentials)
   - Application-specific configurations
   - API keys for other services

### For `requirements.txt` or dependency files:
1. **Remove** Snowflake-related packages:
   - `snowflake-connector-python`
   - `cryptography` (if only used for Snowflake authentication)
   - `google-cloud-secret-manager` (if only used for Snowflake credentials)

2. **Add** StarRocks package:
   - `helios-python-sdk`

3. **Keep** all other dependencies unchanged:
   - `pandas`, `numpy`, `pyarrow`
   - Email libraries (sendgrid, etc.)
   - Other application dependencies

### For other configuration files (`.json`, `.yaml`, `.toml`):
1. Remove Snowflake connection configurations
2. Remove Snowflake credential references
3. Keep all other configurations intact

## Output Format

**CRITICAL: Return ONLY the converted file content, nothing else.**
- No explanations before or after
- No markdown code blocks (```)
- No comments about what was changed
- No duplicate content
- No extra text at the beginning or end
- Just the clean, converted file content ONCE

**DO NOT duplicate any lines or sections. Return the file content exactly once.**

## Important Rules

1. **If no changes are needed**, return the file exactly as-is
2. **Preserve formatting**: Keep the same structure, indentation, and style
3. **Preserve comments**: Keep all comments in the file
4. **Minimal changes**: Only remove/add what's necessary for the migration
5. **No additions**: Don't add new settings unless they're required for StarRocks

## Example: config.ini

**Input:**
```ini
[SETTINGS]
APIKEY = SG.xyz123
FROM_EMAIL = data@company.com
TO_EMAILS = user@company.com
QUERY_FILE = query.sql
SNOWFLAKE_CREDS_FILE = /path/to/snowflake_creds.json
FILENAME = output.csv
```

**Output:**
```ini
[SETTINGS]
APIKEY = SG.xyz123
FROM_EMAIL = data@company.com
TO_EMAILS = user@company.com
QUERY_FILE = query.sql
FILENAME = output.csv
```

## Example: requirements.txt

**Input:**
```
sendgrid
pandas>=0.25.2
snowflake-connector-python>=3.17.0
cryptography==41.0.7
numpy==1.26.4
```

**Output:**
```
sendgrid
pandas>=0.25.2
helios-python-sdk
numpy==1.26.4
```

## Now Convert the Following File

Return ONLY the converted content, nothing else.
