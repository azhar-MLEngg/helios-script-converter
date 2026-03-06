# Config File Conversion: Snowflake → StarRocks

Convert configuration and dependency files from Snowflake-specific settings to StarRocks.
Apply this skill when processing `.txt`, `.ini`, `.json`, `.yaml`, `.yml`, or `.toml` files.

---

## requirements.txt

Remove Snowflake-specific packages, add Helios SDK:

```diff
- snowflake-connector-python
- cryptography          # only if used solely for Snowflake RSA auth
- google-cloud-secret-manager  # only if used solely for Snowflake secrets

+ helios-python-sdk
```

Keep all other packages unchanged.

Rules:
- Only remove `cryptography` if it is used exclusively for Snowflake RSA key handling
- Only remove `google-cloud-secret-manager` if it is used exclusively to fetch Snowflake credentials
- Preserve version pins for all packages you keep
- Deduplicate any repeated lines
- Fix any concatenated package names (e.g. `pandas>=1.0requests` → two separate lines)

---

## config.ini

Remove Snowflake-specific settings, keep everything else:

```diff
[SETTINGS]
- SNOWFLAKE_CREDS_FILE = /path/to/creds.json
- SNOWFLAKE_ACCOUNT    = CQ31887-CARS24CSPL
- SNOWFLAKE_USER       = user@example.com
  EMAIL_SENDER         = sender@example.com   # keep
  OUTPUT_DIR           = /data/output          # keep
```

Rules:
- Remove any key that references Snowflake connection parameters
- Keep application settings: emails, file paths, feature flags, timeouts, etc.
- Preserve section headers (`[SETTINGS]`, `[APP]`, etc.)
- Do not duplicate sections — if `[SETTINGS]` appears only once, keep it once

---

## JSON Config Files

Skip files that match: name contains `"cred"` AND extension is `.json`.
These are Snowflake credential files and are not needed for StarRocks.

For other JSON config files, remove Snowflake keys:
```json
// Remove keys like:
"snowflake_account": "...",
"snowflake_user": "...",
"snowflake_creds_file": "...",
"rsa_key": "..."
```

---

## YAML / TOML Config Files

Same pattern — remove Snowflake-specific keys, preserve everything else:

```yaml
# Remove
snowflake:
  account: CQ31887-CARS24CSPL
  user: user@example.com

# Keep
app:
  output_dir: /data/output
  email: sender@example.com
```

---

## Rules

1. Never remove application-level settings (output paths, emails, feature flags)
2. Never add new Helios/StarRocks config unless you know the required keys
3. Do not reformat or re-order the file beyond what is needed
4. If unsure whether a key is Snowflake-only, keep it and add a `# TODO: verify` comment
