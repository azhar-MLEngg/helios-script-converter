# Python Connection Conversion: Snowflake → StarRocks

Convert Snowflake Python connection boilerplate to the Helios StarRocksClient.
Apply this skill whenever you are converting a `.py` file in this repo.

---

## What to Remove

Remove all of the following — completely, not commented out:

```python
# Imports to remove
import snowflake.connector
from snowflake.connector import SnowflakeConnection
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import json

# Credential loading to remove
with open(creds_file) as f:
    creds = json.load(f)

# RSA key loading to remove
p_key = serialization.load_pem_private_key(
    creds["RSA_KEY"].encode(),
    password=None,
    backend=default_backend(),
)
pkb = p_key.private_bytes(...)

# Connection setup to remove
connection = snowflake.connector.connect(
    account=...,
    user=...,
    private_key=pkb,
    ...
)

# Cursor pattern to remove
cursor = connection.cursor()
cursor.execute(sql)
results = cursor.fetchall()
cursor.close()
connection.close()
```

---

## What to Add

```python
# Add this import at the top
from helios_python_sdk.services.starrocks_client import StarRocksClient

# Replace connection setup with
client = StarRocksClient()

# Replace cursor.execute / fetch with StarRocks client calls
# (check existing usages in the script for the right client API)
```

---

## Rules

1. Keep all business logic, data processing, scheduling, and error handling intact
2. Keep all non-Snowflake imports (pandas, datetime, logging, etc.)
3. Remove config settings that reference Snowflake only (`SNOWFLAKE_CREDS_FILE`, etc.)
4. Do not add comments explaining what was removed — just remove it cleanly
5. If the script uses both a connection and embedded SQL queries, handle both:
   - Replace the connection boilerplate (this skill)
   - Convert the embedded SQL separately (use `sql-syntax-conversion` skill)

---

## Before / After Example

### Before
```python
import snowflake.connector
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import json

with open("creds.json") as f:
    creds = json.load(f)

p_key = serialization.load_pem_private_key(creds["RSA_KEY"].encode(), password=None, backend=default_backend())
pkb = p_key.private_bytes(encoding=serialization.Encoding.DER, format=serialization.PrivateFormat.PKCS8, encryption_algorithm=serialization.NoEncryption())

connection = snowflake.connector.connect(account=creds["ACCOUNT"], user=creds["USERNAME"], private_key=pkb)
cursor = connection.cursor()
cursor.execute(sql)
rows = cursor.fetchall()
cursor.close()
connection.close()
```

### After
```python
from helios_python_sdk.services.starrocks_client import StarRocksClient

client = StarRocksClient()
rows = client.execute(sql)
```
