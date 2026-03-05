# Snowflake to StarRocks Migration Tool

An AI-powered tool that automatically converts Snowflake code and configurations to StarRocks using Claude Agent SDK. This tool intelligently handles Python scripts, SQL queries, and configuration files with minimal manual intervention.

## 🎯 Overview

This tool automates the migration from Snowflake to StarRocks by:
- Converting Python connection code from `snowflake.connector` to `helios-python-sdk`
- Translating Snowflake SQL syntax to StarRocks-compatible SQL
- Updating configuration files (removing Snowflake settings, updating dependencies)
- Generating detailed change logs documenting all modifications

## ✨ Key Features

### 🤖 AI-Powered Conversion
- Uses Claude (Anthropic) for intelligent code analysis and conversion
- Context-aware transformations that preserve business logic
- Handles edge cases and complex code patterns automatically

### 📁 Multi-File Processing
- Processes entire directories of files in one run
- Supports Python (`.py`), SQL (`.sql`), and config files (`.ini`, `.txt`, `.json`, `.yaml`, `.yml`, `.toml`)
- Automatically skips Snowflake credentials files

### 🔍 Smart Detection
- Identifies file types and applies appropriate conversion strategies
- Detects when no changes are needed and copies files as-is
- Removes duplicate content and cleans up responses

### 📝 Automatic Documentation
- Generates `UPDATES.md` with detailed change logs
- Documents every modification made during conversion
- Provides before/after code comparisons

## 🚀 Quick Start

### Prerequisites

1. **Python 3.8+**
2. **Anthropic API Key** - Get one from [Anthropic Console](https://console.anthropic.com/)
3. **Required packages**:
   ```bash
   pip install claude-agent-sdk anthropic
   ```

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd helios-script-converter

# Set your API key
export ANTHROPIC_API_KEY="your-api-key-here"
```

### Basic Usage

1. **Place your files in `input_files/`**:
   ```bash
   input_files/
   ├── python_script.py          # Your Python scripts
   ├── query.sql                 # Your SQL queries
   ├── config.ini                # Configuration files
   ├── requirements.txt          # Dependencies
   └── ...                       # Any other files
   ```

2. **Run the conversion**:
   ```bash
   python main.py
   ```

3. **Review the output in `output_files/`**:
   ```bash
   output_files/
   ├── converted_python_script.py    # Converted Python
   ├── converted_query.sql           # Converted SQL
   ├── config.ini                    # Updated config
   ├── requirements.txt              # Updated dependencies
   └── UPDATES.md                    # Detailed change log
   ```

## 📂 Project Structure

```
helios-script-converter/
├── main.py                      # Main orchestrator and conversion logic
├── prompt.md                    # Python conversion prompt
├── sql_prompt.md                # SQL conversion prompt
├── config_prompt.md             # Config file conversion prompt
├── input_files/                 # Place your files here
│   ├── python_script.py
│   ├── query.sql
│   ├── config.ini
│   ├── requirements.txt
│   └── cfspl_snf_creds_admin_v1.json
├── output_files/                # Converted files appear here
│   ├── converted_python_script.py
│   ├── converted_query.sql
│   ├── config.ini
│   ├── requirements.txt
│   └── UPDATES.md
├── README.md                    # This file
├── CONVERSION_APPROACH.md       # Technical details on conversion approach
└── USAGE_UPDATED.md            # Detailed usage guide
```

## 🔧 How It Works

### Architecture

The tool consists of several key components:

#### 1. **FileManager** (`main.py`)
- Scans directories for files
- Reads and writes files
- Handles file type detection

#### 2. **Step1ConnectionConverter** (`main.py`)
- Sends files to Claude with appropriate prompts
- Extracts converted code from Claude's response
- Handles different file types (Python, SQL, Config)

#### 3. **Step2QueryConverter** (`main.py`)
- Extracts embedded SQL queries from Python scripts
- Converts Snowflake SQL syntax to StarRocks
- Uses Snowflake query parser for accurate extraction

#### 4. **ConversionOrchestrator** (`main.py`)
- Manages the complete conversion pipeline
- Processes all files in sequence
- Generates UPDATES.md documentation
- Provides summary and error reporting

### Conversion Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. SCAN INPUT FOLDER                                        │
│    - Find .py, .sql, .ini, .txt, .json, .yaml files       │
│    - Skip credentials files                                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. CONVERT PYTHON FILES                                     │
│    - Send to Claude with prompt.md                         │
│    - Replace snowflake.connector → StarRocksClient        │
│    - Extract and convert embedded SQL queries              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. CONVERT SQL FILES                                        │
│    - Send to Claude with sql_prompt.md                     │
│    - Convert Snowflake syntax to StarRocks                 │
│    - Fix dates, intervals, QUALIFY, identifiers            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. CONVERT CONFIG FILES                                     │
│    - Send to Claude with config_prompt.md                  │
│    - Remove Snowflake settings                             │
│    - Update dependencies                                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. GENERATE UPDATES.MD                                      │
│    - Document all changes made                             │
│    - Provide before/after comparisons                      │
│    - List migration impact                                  │
└─────────────────────────────────────────────────────────────┘
```

## 📋 What Gets Converted

### Python Files (`.py`)

**Removed:**
- ❌ `import snowflake.connector`
- ❌ `from cryptography.hazmat.primitives import serialization`
- ❌ JSON credentials loading logic
- ❌ RSA key handling
- ❌ Snowflake connection parameters (~80 lines)

**Added:**
- ✅ `from helios_python_sdk.services.starrocks_client import StarRocksClient`
- ✅ `client = StarRocksClient()` (2 lines!)

**Preserved:**
- ✅ All business logic
- ✅ Data processing code
- ✅ Error handling
- ✅ Email sending
- ✅ File operations

### SQL Files (`.sql`)

**Conversions:**
- `"DATABASE"."SCHEMA"."TABLE"` → `DATABASE.SCHEMA.TABLE`
- `TRY_TO_DATE('2024-01-01', 'YYYY-MM-DD')` → `STR_TO_DATE('2024-01-01', '%Y-%m-%d')`
- `CURRENT_DATE()` → `CURRENT_DATE`
- `INTERVAL '1 DAY'` → `INTERVAL 1 DAY`
- `QUALIFY ROW_NUMBER() OVER (...) = 1` → Subquery with `WHERE`

### Configuration Files

#### `config.ini`
- ❌ Removes: `SNOWFLAKE_CREDS_FILE`
- ❌ Removes: Snowflake connection parameters
- ✅ Keeps: All application settings

#### `requirements.txt`
- ❌ Removes: `snowflake-connector-python`
- ❌ Removes: `cryptography`
- ❌ Removes: `google-cloud-secret-manager`
- ✅ Adds: `helios-python-sdk`
- ✅ Keeps: All other dependencies

## 🎛️ Configuration

### Environment Variables

```bash
# Required
export ANTHROPIC_API_KEY="your-api-key-here"
```

### Customizing Prompts

You can customize the conversion behavior by editing the prompt files:

- **`prompt.md`** - Controls Python connection conversion
- **`sql_prompt.md`** - Controls SQL syntax conversion
- **`config_prompt.md`** - Controls configuration file conversion

## 📊 Example Conversion

### Before (Snowflake)

```python
import snowflake.connector
import json
from cryptography.hazmat.primitives import serialization

# Load credentials
with open('creds.json') as f:
    creds = json.load(f)

# Connect to Snowflake
connection = snowflake.connector.connect(
    account=creds['account'],
    user=creds['user'],
    password=creds['password'],
    warehouse=creds['warehouse'],
    database=creds['database'],
    schema=creds['schema']
)

# Execute query
cursor = connection.cursor()
cursor.execute('SELECT * FROM "DB"."SCHEMA"."TABLE"')
results = cursor.fetch_pandas_all()
```

### After (StarRocks)

```python
from helios_python_sdk.services.starrocks_client import StarRocksClient

# Connect to StarRocks
client = StarRocksClient()

# Execute query
results = client.execute_query('SELECT * FROM DB.SCHEMA.TABLE')
```

**Result:** ~80 lines → 2 lines for connection! 🎉

## 🧪 Testing

After conversion, follow these steps:

1. **Review converted files**
   ```bash
   cd output_files
   cat UPDATES.md  # Read the change log
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Test Python scripts**
   ```bash
   python converted_python_script.py
   ```

4. **Test SQL queries**
   - Run in StarRocks client
   - Or use `StarRocksClient().execute_query()`

5. **Verify data accuracy**
   - Compare results with Snowflake
   - Check for any data discrepancies

## 🔍 Troubleshooting

### Issue: "No .py or .sql files found"
**Solution:** Ensure files are in the `input_files/` directory

### Issue: "Conversion failed for file X"
**Solution:** Check the error message in console. The file might have syntax errors or unsupported patterns.

### Issue: "API key not set"
**Solution:** Set the `ANTHROPIC_API_KEY` environment variable

### Issue: "Duplicate content in config files"
**Solution:** The tool now automatically removes duplicates. If you see this, re-run the conversion with the latest version.

### Issue: "SQL syntax not converted correctly"
**Solution:** Review the `sql_prompt.md` and adjust the conversion rules if needed

## 📚 Additional Documentation

- **`CONVERSION_APPROACH.md`** - Technical details on the generic AI-powered approach
- **`USAGE_UPDATED.md`** - Detailed usage guide with examples
- **`output_files/UPDATES.md`** - Generated after each conversion with specific changes made

## 🛠️ Advanced Usage

### Adding New File Types

To support additional file types, edit `main.py`:

```python
other_files = FileManager.scan_directory(
    input_folder, 
    ['.ini', '.txt', '.json', '.yaml', '.yml', '.toml', '.NEW_EXTENSION']
)
```

### Custom Conversion Logic

Create a new prompt file (e.g., `custom_prompt.md`) and update the `convert_file` method:

```python
elif file_type == "CustomType":
    custom_prompt = "custom_prompt.md"
    if Path(custom_prompt).exists():
        prompt_file = custom_prompt
```

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

[Add your license information here]

## 🙏 Acknowledgments

- Built with [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk)
- Powered by [Anthropic Claude](https://www.anthropic.com/)
- Uses [Snowflake Connector](https://github.com/snowflakedb/snowflake-connector-python) for query parsing

## 📞 Support

For issues or questions:
- **Conversion errors:** Check console output and `UPDATES.md`
- **SQL syntax:** Review StarRocks documentation
- **Helios SDK:** Contact your platform team

## 🎯 Summary

This tool provides a **fully automated, AI-powered migration** from Snowflake to StarRocks:

- ✅ Converts Python, SQL, and configuration files
- ✅ Intelligent, context-aware conversions
- ✅ Automatic documentation generation
- ✅ Preserves business logic
- ✅ No manual editing required

**Just place your files in `input_files/`, run `python main.py`, and review the results in `output_files/`!**

---

**Version:** 1.0  
**Last Updated:** March 2026