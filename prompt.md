# Snowflake to StarRocks Connection Conversion Guide

## Purpose
Transform Snowflake connection code to StarRocks by replacing the Snowflake connector with Helios Python SDK. The StarRocksClient handles all connection parameters internally, so only the import and instantiation are needed.

---

## Critical Output Pattern

**ALL conversions MUST output ONLY:**
```python
from helios_python_sdk.services.starrocks_client import StarRocksClient

client = StarRocksClient()
```

This is the ONLY acceptable final output format. Nothing else.

---

## Input: Three Credential Source Formats

### Format 1: Hardcoded Credentials

**Snowflake Input:**
```python
import snowflake.connector

conn_params = {
    "account": "xy12345.us-east-1",
    "user": "user@company.com",
    "private_key": private_key_bytes,
    "role": "ANALYST_ROLE",
    "warehouse": "COMPUTE_WH",
    "database": "ANALYTICS_DB",
    "schema": "PUBLIC",
    "arrow_number_to_decimal": True
}

connection = snowflake.connector.connect(**conn_params)
```

**ALWAYS OUTPUT THIS FORMAT:**
```python
from helios_python_sdk.services.starrocks_client import StarRocksClient

client = StarRocksClient()
```

---

### Format 2: Credentials from JSON File

**Snowflake Input:**
```python
import os
import json
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import snowflake.connector

creds_file = SNOWFLAKE_CREDS_FILE

if os.path.exists(creds_file):
    with open(creds_file, 'r') as f:
        sf_account = json.load(f)
else:
    sf_secret = os.getenv('SNOWFLAKE_SECRET')
    sf_account = json.loads(sf_secret)

creds = {
    "SF_ACCOUNT": sf_account["SF_ACCOUNT"],
    "SF_USER": sf_account["SF_USER"],
    "rsa_key": sf_account["rsa_key"]
}

p_key = serialization.load_pem_private_key(str.encode(creds["rsa_key"]), ...)
pkb = p_key.private_bytes(...)

connection = snowflake.connector.connect(...)
```

**ALWAYS OUTPUT THIS FORMAT:**
```python
from helios_python_sdk.services.starrocks_client import StarRocksClient

client = StarRocksClient()
```

---

### Format 3: Credentials from Secret Manager / Parameter Store

**Snowflake Input:**
```python
import os
import json
import boto3
from botocore.exceptions import ClientError
import snowflake.connector

secret_path = os.getenv('SECRET_MANAGER_PATH', 'snowflake/prod/creds')
region_name = 'us-east-1'

try:
    secret_client = boto3.client('secretsmanager', region_name=region_name)
    secret = secret_client.get_secret_value(SecretId=secret_path)
    sf_account = json.loads(secret['SecretString'])
except ClientError as e:
    raise ValueError(f"Failed to retrieve secret: {str(e)}")

conn_params = {
    "account": sf_account["account"],
    "user": sf_account["user"],
    "password": sf_account["password"],
    "warehouse": "COMPUTE_WH",
    "database": "ANALYTICS_DB"
}

connection = snowflake.connector.connect(**conn_params)
```

**ALWAYS OUTPUT THIS FORMAT:**
```python
from helios_python_sdk.services.starrocks_client import StarRocksClient

client = StarRocksClient()
```

---

## Conversion Rules

### Simple Rule: Replace Snowflake with Helios SDK

**What to do:**
1. ❌ Delete ONLY Snowflake connection-related code
2. ❌ Delete ONLY parameter dictionaries (conn_params)
3. ❌ Delete ONLY credential handling
4. ❌ Delete ONLY RSA key processing
5. ❌ Delete ONLY Snowflake imports
6. ✅ Keep ALL comments
7. ✅ Keep ALL other code
8. ✅ Add ONLY: `from helios_python_sdk.services.starrocks_client import StarRocksClient`
9. ✅ Add ONLY: `client = StarRocksClient()`

### What Gets Removed

**Remove ONLY these:**
- ❌ `import snowflake.connector`
- ❌ `from cryptography.hazmat.primitives import serialization`
- ❌ `from cryptography.hazmat.backends import default_backend`
- ❌ `import boto3` (if ONLY used for Snowflake creds)
- ❌ `from botocore.exceptions import ClientError` (if ONLY used for Snowflake)
- ❌ All `conn_params` dictionaries
- ❌ All credential loading code (json.load, os.getenv for Snowflake creds)
- ❌ All RSA key processing (serialization.load_pem_private_key, etc.)
- ❌ All `snowflake.connector.connect()` calls
- ❌ Any parameter mapping logic for Snowflake

### What Gets Preserved

**Keep ALL of these:**
- ✅ ALL comments (lines starting with #)
- ✅ ALL docstrings
- ✅ ALL function/class definitions
- ✅ ALL non-connection-related imports
- ✅ ALL non-connection-related code
- ✅ ALL logging statements
- ✅ ALL error handling (try/except blocks)
- ✅ ALL print statements
- ✅ ALL other logic outside of connection setup

### What Gets Added

**Add ONLY these TWO lines:**
```python
from helios_python_sdk.services.starrocks_client import StarRocksClient

client = StarRocksClient()
```

---

## Why This Works

The Helios Python SDK (`helios_python_sdk.services.starrocks_client`) is a custom SDK that:
- Handles all connection parameters internally
- Doesn't accept parameters in the constructor
- Manages all credential sources automatically
- Handles authentication internally
- Requires NO configuration

Therefore, conversion is simply: **Replace Snowflake client with StarRocks client.**

---

## Conversion Checklist

Before returning converted code, verify:

- [ ] Import: `from helios_python_sdk.services.starrocks_client import StarRocksClient`
- [ ] Instantiation: `client = StarRocksClient()`
- [ ] ALL comments preserved (no comments removed)
- [ ] ALL docstrings preserved
- [ ] ALL non-connection code preserved
- [ ] NO `conn_params` dictionary
- [ ] NO credential handling code
- [ ] NO RSA key processing
- [ ] NO Snowflake imports remaining
- [ ] NO boto3, cryptography, or other credential-related imports (only if used for Snowflake)
- [ ] Code is syntactically valid Python

---

## Examples

### Example 1: Hardcoded Credentials with Comments

**Input:**
```python
import snowflake.connector

# Configure Snowflake connection parameters
conn_params = {
    "account": "xy12345.us-east-1",
    "user": "analyst@company.com",
    "password": "MyPassword123!",
    "warehouse": "COMPUTE_WH",
    "database": "ANALYTICS_DB",
    "schema": "RAW",
    "role": "ANALYST_ROLE",
    "arrow_number_to_decimal": True
}

# Establish connection to Snowflake
connection = snowflake.connector.connect(**conn_params)
print("Connected to Snowflake")
```

**Output (Comments Preserved):**
```python
from helios_python_sdk.services.starrocks_client import StarRocksClient

# Establish connection to StarRocks
client = StarRocksClient()
print("Connected to StarRocks")
```

### Example 2: JSON File with Comments and Logging

**Input:**
```python
import json
import os
import logging
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import snowflake.connector

logger = logging.getLogger(__name__)

# Load credentials from file or environment
creds_file = "/app/secrets/snowflake_creds.json"

if os.path.exists(creds_file):
    logger.info(f"Loading Snowflake credentials from {creds_file}")
    with open(creds_file, 'r') as f:
        sf_account = json.load(f)
else:
    logger.info("Loading Snowflake credentials from environment")
    sf_secret = os.getenv('SNOWFLAKE_SECRET')
    sf_account = json.loads(sf_secret)

# Process RSA private key
creds = {
    "SF_ACCOUNT": sf_account["SF_ACCOUNT"],
    "SF_USER": sf_account["SF_USER"],
    "rsa_key": sf_account["rsa_key"]
}

p_key = serialization.load_pem_private_key(
    str.encode(creds["rsa_key"]),
    password=None,
    backend=default_backend(),
)
pkb = p_key.private_bytes(
    encoding=serialization.Encoding.DER,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)

conn_params = {
    "account": creds["SF_ACCOUNT"],
    "user": creds["SF_USER"],
    "private_key": pkb,
    "warehouse": "COMPUTE_WH",
    "database": "ANALYTICS_DB",
    "schema": "PUBLIC"
}

connection = snowflake.connector.connect(**conn_params)
logger.info("Successfully connected to Snowflake")
print("Connected to Snowflake")
```

**Output (Comments and Logging Preserved):**
```python
import logging
from helios_python_sdk.services.starrocks_client import StarRocksClient

logger = logging.getLogger(__name__)

# Establish connection to StarRocks
client = StarRocksClient()
logger.info("Successfully connected to StarRocks")
print("Connected to StarRocks")
```

### Example 3: AWS Secrets Manager with Error Handling

**Input:**
```python
import os
import json
import boto3
from botocore.exceptions import ClientError
import snowflake.connector

# AWS Secrets Manager configuration
secret_path = os.getenv('SECRET_MANAGER_PATH', 'snowflake/prod/creds')
region_name = 'us-east-1'

try:
    # Retrieve secrets from AWS
    secret_client = boto3.client('secretsmanager', region_name=region_name)
    secret = secret_client.get_secret_value(SecretId=secret_path)
    sf_account = json.loads(secret['SecretString'])
except ClientError as e:
    raise ValueError(f"Failed to retrieve secret: {str(e)}")

# Configure connection
conn_params = {
    "account": sf_account["account"],
    "user": sf_account["user"],
    "password": sf_account["password"],
    "warehouse": "COMPUTE_WH",
    "database": "ANALYTICS_DB"
}

# Connect to Snowflake
connection = snowflake.connector.connect(**conn_params)
print("Connected to Snowflake")
```

**Output (Comments and Error Handling Preserved):**
```python
from helios_python_sdk.services.starrocks_client import StarRocksClient

# Connect to StarRocks
client = StarRocksClient()
print("Connected to StarRocks")
```

---

## Key Point

**The Helios Python SDK manages ALL connection details internally.**

You don't need to:
- Pass hostnames
- Pass credentials
- Pass database names
- Handle authentication
- Process any parameters

Just instantiate it and it works.

---

## Now Convert the Following Code

(Paste the Snowflake connection code here)