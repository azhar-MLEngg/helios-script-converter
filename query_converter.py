# query_transform.py
"""
Query Transformation Module
===========================

Two main functions for users:

1. get_iceberg_table(snowflake_table_name: str) -> str
   Input:  Snowflake table name (e.g., "CSPL_DB.SCHEMA.TABLE")
   Output: Iceberg table name (e.g., "NEW_DB.NEW_SCHEMA.NEW_TABLE")

2. convert_snowflake_to_starrocks(snowflake_query: str) -> str
   Input:  Snowflake query with Snowflake table names
   Output: StarRocks query with Iceberg table names

Usage
-----
from query_transform import get_iceberg_table, convert_snowflake_to_starrocks

# Option 1: Get single table mapping
iceberg_table = get_iceberg_table("CSPL_DB.SCHEMA.TABLE")
print(iceberg_table)

# Option 2: Convert entire query
starrocks_query = convert_snowflake_to_starrocks(
    "SELECT * FROM CSPL_DB.SCHEMA.TABLE WHERE id > 100"
)
print(starrocks_query)
"""

import re
import logging
import pandas as pd
from typing import Dict, List, Optional, Tuple

import snowflake.connector as connector
from snowflake.connector import SnowflakeConnection
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

from sqlglot import parse

# ========== LOGGING CONFIGURATION ==========

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ========== SNOWFLAKE CLIENT ==========

class SnowflakeClient:
    """Manages Snowflake connections using RSA key-based authentication."""

    def __init__(self) -> None:
        """Initialize client and establish Snowflake connection."""
        self.entity = ""
        self.business_unit = ""
        self.platform = ""
        self.lob = ""

        self.helios_creds = {
            "USERNAME": "gauri.bansal@cars24.com",
            "RSA_KEY": """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCvEC7aMucP3a9K+S
NWIo5sfY5deFwloWgqIBAb8D0NlKOFx9x4KRr22OM9/bXMpjvDzmBHIFNbpEv+
RWGcbrMp64Kzg/697eE2W3Nq46tQGga92vy2ljyH7wVSfForoF0jOTvT3LfAtDTS
xtTye7mYtb/LY+XmP+QslRbPx+vAr1IN53AW9wv20oPfhtOR3hVLsB0Ivt63nIuM
LkFGed+uVLpkCUQtpyUJJBHnpaFdD+NQVP8Xqqi41wwfNqOp6IiIsiHr7ClyBVHj
TMnbETTicBuuKApl2B/D03SZqNoCRPAObnQSpxGHLRjPTVu3bGC0FO1L8wd/J0Tc
llPK1VYPAgMBAAECggEAEsIyqwniTYZtJqT8ntm0Fjb7/tMLWLLrdPwbjcrX1/Ex
9n9chfmtnH7QFs/tX6D+bXRbR7PUitDXncb0dy07gIXuaur9bH+lbsws2WrM7Bfl
2gkxpCUEFnLLyLNvfBZCdKhI22JexETrFhzdK6CLWiw7gYFSXLJC8m4FVD1xayOQ
v28yu4EM30s1HVDYpi3ocahsgb13kf8GJEJAS9saT4P11ZI23iQi9DG9mpMklQhg
QPR+/FOeMDUHvp0aTf0r7n07243PVzltRB4aLq0Qaeh4DuO7o0r7wuNz4YTu/94J
dBzK7PTmngKsjpVsJjOwxQqaVptcJ7p5vswNj7Wy4QKBgQDgIalOA6zn472zOYSp
fSugUCx7r6CnLXInqon13ezmiht6DQpovqhcsNOijoHPqhUrKLgaB0ZHy4lwu821
dXoBZK728xSCrOxx3AWbcnfdt9sjXGVc3ezSKou+xOeh2o7ggjYB4a6rwqFeevvo
45YYbuw0vhr/8tBFukSMFQwOrwKBgQDH9HJnBW07jofeNWcW2azyp/dB1P2UPoUC
qnQ1mtfOxwAPYXAawoeu3p9wTYCEPuRvc/Bgjy0dCYwXYdkRFpOa0fKkNVmwBy3R
hJzR0qdV7YsllR4H/cDLpN1hshfxfu04+PkIUa0UkbMh55zBKcP7udqRP63AUDjU
6Pv40pgGoQKBgBlaFWF6rvMn4oxEREo7m1St3Oo8qmpejJwKAULrUGGfW45JrVS9
xCN/6OBpSCuqLGzOVUy0Z/G1Bx3WUGVnHV7M+bF7O2Wwk6opXgUARKiypDnyuJBx
ldkL8PSqJx06sJCaietakLxi7ofWV2o3XAH1gghRPJKY75ADir9hnhSHAoGAWGA8
aDhHzTjz6EymIb1X6XA/ooMnCOyREVqRPlgP5j6iUin4yHsOSUXwJky67rh1cqVF
qwfdIqZjmroOnLTjzFva6KUD3P9vStlYDo0SlLIG/DdqLJIFMnzNtC5o0r4Mz0+L
khe3bg3vpJ6f8+gnzQyaA/SnMQbD96Z6J8G8m8ECgYEAhrjVUaL5DLFFVS0lOF/m
k2OpRiDk7bLk5m9+OgLffdAC8Ar6F0a0FbBnNN6D3nxybCskaDA7qOMNszGPNNTF
XzbdNqqGzqOM8P3Ne1aW505+jq3QYxJYQfkTZCXssvM01JY7I5oohyQ8FGCVnmf8
cVeDwEKmO06EUefhbQO+hLI=
-----END PRIVATE KEY-----""",
            "ACCOUNT": "CQ31887-CARS24CSPL",
        }

        logger.info("Loading Snowflake credentials")
        self.connection = self._get_snowflake_connection(
            self.helios_creds,
            self.business_unit,
            self.entity,
            self.platform,
            self.lob,
        )
        logger.info("SnowflakeClient initialized successfully")

    def _get_snowflake_connection(
        self,
        creds: Dict[str, str],
        business_unit: str,
        entity: str,
        platform: str,
        lob: str,
    ) -> SnowflakeConnection:
        """Establish RSA-authenticated connection to Snowflake."""
        try:
            p_key = serialization.load_pem_private_key(
                creds["RSA_KEY"].encode(),
                password=None,
                backend=default_backend(),
            )
            pkb = p_key.private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            connection_config = {
                "account": creds["ACCOUNT"],
                "user": creds["USERNAME"],
                "private_key": pkb,
                "arrow_number_to_decimal": True,
                "use_arrow_result_format": True,
                "session_parameters": {
                    "QUERY_TAG": (
                        f'{{"username": "{creds["USERNAME"]}", '
                        f'"business_unit": "{business_unit}", '
                        f'"entity": "{entity}", '
                        f'"platform": "{platform}", '
                        f'"lob": "{lob}"}}'
                    )
                },
            }
            connection = connector.connect(**connection_config)
            logger.info("Connection established successfully")
            return connection
        except Exception as error:
            logger.error(f"Failed to establish connection: {str(error)}")
            raise RuntimeError(f"Snowflake connection failed: {str(error)}")

    def execute_query(self, sql_query: str, params=None) -> pd.DataFrame:
        """Execute a SQL query and return the result as a Pandas DataFrame."""
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql_query, params)
            df = cursor.fetch_pandas_all()
            cursor.close()
            return df
        except Exception as e:
            logger.error(f"Query failed: {str(e)}")
            raise

    def close(self) -> None:
        """Close the Snowflake connection."""
        if self.connection:
            self.connection.close()
            logger.info("Snowflake connection closed")


# ========== HELPER FUNCTIONS ==========

def parse_fqn(fqn: str) -> Tuple[str, str, str]:
    """
    Parse a fully-qualified name 'db.schema.table' into its three parts.
    Strips surrounding double-quotes.

    Raises ValueError if the FQN does not contain exactly three dot-separated parts.
    """
    parts = [p.strip().strip('"') for p in fqn.split(".")]
    if len(parts) != 3:
        raise ValueError(f"Expected a 3-part FQN (db.schema.table), got: {fqn!r}")
    return parts[0], parts[1], parts[2]


ICEBERG_LOOKUP_QUERY = """
    SELECT DESTINATION_ACTUAL_CATALOG, DESTINATION_NAMESPACE, DESTINATION_TABLENAME
    FROM SNOWFLAKE_MANAGER.DATA_ENGG_JOBS.SNOWFLAKE_MIGRATED_TABLES_OVERALL
    WHERE DATABASE_NAME = %s
      AND SCHEMA_NAME   = %s
      AND TABLE_NAME    = %s
"""


def _get_iceberg_mapping(old_fqn: str, client: SnowflakeClient) -> Optional[str]:
    """
    Query the Iceberg migration mapping table and return the new FQN.

    Parameters
    ----------
    old_fqn : str
        The original Snowflake fully-qualified table name (db.schema.table).
    client : SnowflakeClient
        Active SnowflakeClient instance.

    Returns
    -------
    str or None
        - New FQN if mapping exists
        - 'TABLE MARKED AS NOT TO BE MIGRATED' if flagged as not migrated
        - None if no mapping row exists
    """
    try:
        old_db, old_schema, old_table = parse_fqn(old_fqn)
    except ValueError as exc:
        logger.warning(str(exc))
        return None

    try:
        result = client.execute_query(ICEBERG_LOOKUP_QUERY, (old_db, old_schema, old_table))

        if result.empty:
            return None

        row = result.iloc[0]
        new_db = str(row["DESTINATION_ACTUAL_CATALOG"]) if pd.notna(row["DESTINATION_ACTUAL_CATALOG"]) else ""
        new_schema = str(row["DESTINATION_NAMESPACE"]) if pd.notna(row["DESTINATION_NAMESPACE"]) else ""
        new_table = str(row["DESTINATION_TABLENAME"]) if pd.notna(row["DESTINATION_TABLENAME"]) else ""

        if not new_db or new_db.upper() == "NOT TO BE MIGRATED":
            return "TABLE MARKED AS NOT TO BE MIGRATED"

        return f"{new_db}.{new_schema}.{new_table}"
    except Exception as e:
        logger.error(f"Error looking up mapping for {old_fqn}: {str(e)}")
        return None


# ========== SQL PARSING REGEX PATTERNS ==========

_SQL_KEYWORDS = {
    "set", "where", "group", "order", "having", "limit", "offset",
    "union", "intersect", "except", "all", "distinct", "into",
    "values", "as", "on", "using", "with", "inner",
}

_FROM_RE = re.compile(r"FROM\s+([^\s();,]+)", re.IGNORECASE)
_JOIN_RE = re.compile(r"JOIN\s+([^\s();,]+)", re.IGNORECASE)
_INSERT_RE = re.compile(r"INSERT\s+INTO\s+([^\s();,]+)", re.IGNORECASE)
_UPDATE_RE = re.compile(r"UPDATE\s+(?!SET\s)([^\s();,]+)", re.IGNORECASE)
_MERGE_RE = re.compile(r"MERGE\s+INTO\s+([^\s();,]+)", re.IGNORECASE)
_DELETE_RE = re.compile(r"DELETE\s+FROM\s+([^\s();,]+)", re.IGNORECASE)
_ALTER_RE = re.compile(r"ALTER\s+TABLE\s+([^\s();,]+)", re.IGNORECASE)
_TRUNCATE_RE = re.compile(r"TRUNCATE\s+TABLE\s+([^\s();,]+)", re.IGNORECASE)
_OVERWRITE_RE = re.compile(r"OVERWRITE\s+INTO\s+([^\s();,]+)", re.IGNORECASE)
_CREATE_LIKE_RE = re.compile(
    r"CREATE\s+TABLE\s+[^\s();,]+\s+LIKE\s+([^\s();,]+)", re.IGNORECASE
)
_DROP_RE = re.compile(
    r"DROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?([^\s();,]+)", re.IGNORECASE
)
_TEMP_RE = re.compile(
    r"CREATE\s+(?:LOCAL\s+)?TEMP(?:ORARY)?\s+TABLE\s+([a-zA-Z0-9_\"]+)", re.IGNORECASE
)
_CTE_RE = re.compile(r"([a-zA-Z0-9_]+)\s+AS\s*\(", re.IGNORECASE)
_SUBQUERY_RE = re.compile(
    r"\(\s*SELECT.*?\)\s*(?:AS\s*)?([a-zA-Z0-9_\"]+)", re.IGNORECASE | re.DOTALL
)
_USE_DB_RE = re.compile(r"USE\s+DATABASE\s+([a-zA-Z0-9_\"]+)", re.IGNORECASE)
_USE_SCHEMA_RE = re.compile(r"USE\s+SCHEMA\s+([a-zA-Z0-9_\"]+)", re.IGNORECASE)
_USE_BOTH_RE = re.compile(
    r"USE\s+([a-zA-Z0-9_\"]+)\.([a-zA-Z0-9_\"]+)", re.IGNORECASE
)


def _split_statements(sql: str) -> List[str]:
    """Split SQL on ';', respecting quoted strings."""
    statements, current, in_quotes, qchar = [], "", False, None
    for ch in sql:
        if ch in ('"', "'"):
            if not in_quotes:
                in_quotes, qchar = True, ch
            elif ch == qchar:
                in_quotes, qchar = False, None
        current += ch
        if ch == ";" and not in_quotes:
            statements.append(current.strip())
            current = ""
    if current.strip():
        statements.append(current.strip())
    return statements


def _parse_dotted_identifier(ref: str) -> List[str]:
    """Split a (possibly double-quoted) dotted identifier into its parts."""
    parts, current, in_q = [], "", False
    for ch in ref:
        if ch == '"':
            in_q = not in_q
            current += ch
        elif ch == "." and not in_q:
            parts.append(current)
            current = ""
        else:
            current += ch
    if current:
        parts.append(current)
    return parts


def _extract_table_references(sql: str) -> List[Dict[str, str]]:
    """
    Parse SQL and return a list of unique table references.

    Returns
    -------
    List[Dict]
        [{"original_token": <str>, "fqn": <lowercase str>}, ...]
    """
    statements = _split_statements(sql)
    current_db = None
    current_schema = None
    temp_tables: List[str] = []
    cte_names: List[str] = []
    subq_aliases: List[str] = []
    seen_fqns: set = set()
    results: List[Dict] = []

    for stmt in statements:
        # --- USE DATABASE / USE SCHEMA context ---
        m = _USE_BOTH_RE.search(stmt)
        if m:
            current_db = m.group(1).strip('"')
            current_schema = m.group(2).strip('"')
            continue

        m = _USE_DB_RE.search(stmt)
        if m:
            current_db = m.group(1).strip('"')
            continue

        m = _USE_SCHEMA_RE.search(stmt)
        if m:
            current_schema = m.group(1).strip('"')
            continue

        # --- collect names to exclude ---
        for t in _TEMP_RE.findall(stmt):
            temp_tables.append(t.strip('"').lower())

        for section in _CTE_RE.findall(stmt):
            m2 = re.search(r"([a-zA-Z0-9_]+)", section.strip())
            if m2:
                cte_names.append(m2.group(1).lower())

        for m2 in _SUBQUERY_RE.finditer(stmt):
            subq_aliases.append(m2.group(1).strip('"').lower())

        # --- collect all raw table tokens ---
        raw_refs = (
            _FROM_RE.findall(stmt)
            + _JOIN_RE.findall(stmt)
            + _INSERT_RE.findall(stmt)
            + _UPDATE_RE.findall(stmt)
            + _MERGE_RE.findall(stmt)
            + _DELETE_RE.findall(stmt)
            + _ALTER_RE.findall(stmt)
            + _TRUNCATE_RE.findall(stmt)
            + _OVERWRITE_RE.findall(stmt)
            + _CREATE_LIKE_RE.findall(stmt)
            + _DROP_RE.findall(stmt)
        )

        exclusions = (
            _SQL_KEYWORDS
            | set(cte_names)
            | set(subq_aliases)
            | set(temp_tables)
        )

        for ref in raw_refs:
            bare = ref.strip('"').lower()
            if bare in exclusions:
                continue

            parts = _parse_dotted_identifier(ref)
            bare_parts = [p.strip('"') for p in parts]

            # Resolve to a 3-part FQN using USE context
            if len(bare_parts) == 3:
                fqn = ".".join(bare_parts)
            elif len(bare_parts) == 2 and current_db:
                fqn = f"{current_db}.{bare_parts[0]}.{bare_parts[1]}"
            elif len(bare_parts) == 1 and current_db and current_schema:
                fqn = f"{current_db}.{current_schema}.{bare_parts[0]}"
            else:
                logger.debug(f"Skipping unresolvable reference: {ref!r}")
                continue

            if fqn not in seen_fqns:
                seen_fqns.add(fqn)
                results.append({"original_token": ref, "fqn": fqn})

    return results


# ========== SQLGLOT CONVERSION FUNCTIONS ==========

from sqlglot import exp


def _apply_to_timestamp_conversion(expr) -> None:
    """Replace TO_TIMESTAMP / TO_TIMESTAMP_NTZ with CAST(... AS DATETIME)."""
    for func in expr.find_all(exp.Anonymous):
        if func.name.upper() in ("TO_TIMESTAMP", "TO_TIMESTAMP_NTZ"):
            arg = func.args["expressions"][0]
            cast = exp.Cast(
                this=arg,
                to=exp.DataType(this=exp.DataType.Type.DATETIME)
            )
            func.replace(cast)


def _apply_try_to_timestamp_conversion(expr) -> None:
    """Replace TRY_TO_TIMESTAMP with STR_TO_DATE."""
    for func in expr.find_all(exp.Anonymous):
        if func.name.upper() == "TRY_TO_TIMESTAMP":
            arg = func.args["expressions"][0]
            str_to_date = exp.Anonymous(
                this="STR_TO_DATE",
                expressions=[
                    arg,
                    exp.Literal.string('%Y-%m-%d %H:%i:%S')
                ]
            )
            func.replace(str_to_date)


def _apply_contains_conversion(expr) -> None:
    """Replace CONTAINS(col, val) with col LIKE CONCAT('%', val, '%')."""
    for func in list(expr.find_all(exp.Anonymous)) + list(expr.find_all(exp.Func)):
        if hasattr(func, 'name') and func.name.upper() == "CONTAINS":
            args = func.args.get("expressions", [])
            if len(args) >= 2:
                col = args[0]
                substring = args[1]
                
                concat_expr = exp.Concat(
                    expressions=[
                        exp.Literal.string('%'),
                        substring,
                        exp.Literal.string('%')
                    ]
                )
                
                like_expr = exp.Like(
                    this=col,
                    expression=concat_expr
                )
                func.replace(like_expr)


def _convert_snowflake_syntax_to_starrocks(sql: str) -> str:
    """Convert Snowflake-specific functions to StarRocks syntax using SQLGlot."""
    try:
        expressions = parse(sql, read="snowflake")
        converted_queries = []
        
        for expr in expressions:
            _apply_to_timestamp_conversion(expr)
            _apply_try_to_timestamp_conversion(expr)
            _apply_contains_conversion(expr)
            converted_queries.append(expr.sql(dialect="starrocks"))
        
        return " ".join(converted_queries)
    except Exception as e:
        logger.exception("SQL conversion failed")
        raise e


# ========== MAIN USER-FACING FUNCTIONS ==========

def get_iceberg_table(snowflake_table_name: str) -> str:
    """
    Convert a Snowflake table name to its Iceberg equivalent.

    Parameters
    ----------
    snowflake_table_name : str
        Fully-qualified Snowflake table name (e.g., "DB.SCHEMA.TABLE")

    Returns
    -------
    str
        Iceberg table name (e.g., "NEW_DB.NEW_SCHEMA.NEW_TABLE")

    Raises
    ------
    ValueError
        If the table name is not in db.schema.table format
    RuntimeError
        If Snowflake connection fails or mapping is not found
    """
    logger.info(f"Getting Iceberg mapping for: {snowflake_table_name}")
    
    client = SnowflakeClient()
    try:
        iceberg_table = _get_iceberg_mapping(snowflake_table_name, client)
        
        if iceberg_table is None:
            raise RuntimeError(f"No mapping found for table: {snowflake_table_name}")
        
        if iceberg_table == "TABLE MARKED AS NOT TO BE MIGRATED":
            raise RuntimeError(f"Table is marked as NOT TO BE MIGRATED: {snowflake_table_name}")
        
        logger.info(f"Successfully mapped to: {iceberg_table}")
        return iceberg_table
    finally:
        client.close()


def convert_snowflake_to_starrocks(snowflake_query: str) -> str:
    """
    Convert a Snowflake query to StarRocks query with Iceberg table names.

    This function:
    1. Extracts all table references from the Snowflake query
    2. Maps each Snowflake table to its Iceberg equivalent
    3. Replaces table names in the query
    4. Converts Snowflake-specific functions to StarRocks syntax

    Parameters
    ----------
    snowflake_query : str
        Original SQL query with Snowflake table names and functions

    Returns
    -------
    str
        StarRocks-executable SQL query with Iceberg table names

    Example
    -------
    >>> sql = "SELECT * FROM CSPL_DB.SCHEMA.TABLE WHERE id > 100"
    >>> result = convert_snowflake_to_starrocks(sql)
    >>> print(result)
    # SELECT * FROM ICEBERG_DB.SCHEMA.TABLE WHERE id > 100
    """
    logger.info("Starting Snowflake → StarRocks conversion")
    
    client = SnowflakeClient()
    try:
        # Step 1: Extract table references
        logger.info("Extracting table references from query...")
        table_refs = _extract_table_references(snowflake_query)
        
        if not table_refs:
            logger.warning("No table references found in query")
            updated_query = snowflake_query
        else:
            # Step 2: Map tables and replace in query
            logger.info(f"Found {len(table_refs)} unique table reference(s)")
            updated_query = snowflake_query
            
            for ref in table_refs:
                fqn = ref["fqn"]
                token = ref["original_token"]
                
                logger.info(f"Mapping table: {fqn}")
                iceberg_fqn = _get_iceberg_mapping(fqn, client)
                
                if iceberg_fqn is None:
                    logger.warning(f"No mapping found for: {fqn}, keeping original")
                    continue
                
                if iceberg_fqn == "TABLE MARKED AS NOT TO BE MIGRATED":
                    logger.warning(f"Table marked as NOT TO BE MIGRATED: {fqn}, keeping original")
                    continue
                
                # Replace the original token with iceberg FQN (case-insensitive)
                updated_query = re.sub(
                    re.escape(token), iceberg_fqn, updated_query, flags=re.IGNORECASE
                )
                logger.info(f"Replaced: {token} → {iceberg_fqn}")
        
        # Step 3: Convert Snowflake syntax to StarRocks
        logger.info("Converting Snowflake syntax to StarRocks...")
        starrocks_query = _convert_snowflake_syntax_to_starrocks(updated_query)
        
        logger.info("Conversion complete")
        return starrocks_query
    
    except Exception as e:
        logger.error(f"Conversion failed: {str(e)}")
        raise
    finally:
        client.close()


# ========== EXAMPLE USAGE ==========

if __name__ == "__main__":
    print("=" * 80)
    print("QUERY TRANSFORMATION MODULE")
    print("=" * 80)

    # Example 1: Get single Iceberg table
    print("\n[Example 1] Get Iceberg table name from Snowflake table name")
    print("-" * 80)
    try:
        snowflake_table = "CSPL_INSPARE_DB.FIVETRAN_METADATA.COLUMN_LINEAGE"
        iceberg_table = get_iceberg_table(snowflake_table)
        print(f"Input:  {snowflake_table}")
        print(f"Output: {iceberg_table}")
    except Exception as e:
        print(f"Error: {e}")

    # Example 2: Convert Snowflake query to StarRocks with Iceberg tables
    print("\n[Example 2] Convert Snowflake query to StarRocks (with Iceberg tables)")
    print("-" * 80)
    sample_query = """
    INSERT OVERWRITE INTO CSPL_C2B_DB.PROD.ELITE_INVENTORY
with waiver_conversion as(
SELECT * from ( select
    rc.appointment_id,ba.ORDERID ,
    MAX(CASE WHEN ebwd.SERVICE_TYPE_ID = '36' THEN ebwd.WAIVER END) AS WAIVER_Conversion_Discount
FROM CAPL_GS_DB.C2C_ADMIN_C2C_ADMIN_PANEL_PROD.C2C_RC_DETAILS rc
LEFT JOIN CAPL_GS_DB.C2C_LMS_C2C_LMS_PROD.DEAL d 
    ON rc.deal_id = d.deal_id
LEFT JOIN CAPL_GS_DB.ARANGO.ORDER_WH_VW ba 
    ON ba.ORDERID = d.booking_id 
    AND rc.appointment_id = ba.appointmentid
LEFT JOIN CAPL_GS_DB.C2C_ADMIN_C2C_ADMIN_PANEL_PROD.FINANCE_DEAL_DETAILS f 
    ON f.DEAL_ID = d.deal_id   
LEFT JOIN CAPL_GS_DB.C2C_ADMIN_C2C_ADMIN_PANEL_PROD.REMITTER r1 
    ON f.ID = r1.FK_FIN_DETAIL_ID 
    AND r1.CUSTOMER_TYPE = 'BUYER'
LEFT JOIN CAPL_GS_DB.C2C_ADMIN_C2C_ADMIN_PANEL_PROD.SERVICE_LOGS ebwd 
    ON r1.ID = ebwd.FK_REMITTER_ID
LEFT JOIN CAPL_GS_DB.C2C_ADMIN_C2C_ADMIN_PANEL_PROD.FINANCE_SERVICES_TYPE i 
    ON i.id = ebwd.SERVICE_TYPE_ID 
    and ebwd.SERVICE_TYPE_ID = '36'
GROUP BY 
    rc.appointment_id,ba.ORDERID ) vw
    where  vw.WAIVER_Conversion_Discount IS NOT NULL
  AND vw.WAIVER_Conversion_Discount != 0 ),

booking_data AS (
    -- Current active bookings
    SELECT 
        APPOINTMENTID AS lead_id,
        ORDERID AS booking_id,
        TO_DATE(BOOKINGCONFIRMDATE) AS booking_date,
        'BOOKED' AS booking_status,
        NULL AS token_date
    FROM 
        CAPL_GS_DB.ARANGO.ORDER_WH_VW
    WHERE 
        status in('PAYMENT','DONE') 
    QUALIFY 
        ROW_NUMBER() OVER (PARTITION BY APPOINTMENTID ORDER BY BOOKINGCONFIRMDATE DESC) = 1
    
    UNION ALL
    
    -- Completed sales bookings
    SELECT 
        appointment_id AS lead_id,
       d.booking_id,
        TO_DATE(token_date) AS booking_date,
        'SOLD' AS booking_status,
        token_date
    FROM 
    CAPL_GS_DB.PROD.C2C_SALES_DATA ac
    left join CAPL_GS_DB.C2C_LMS_C2C_LMS_PROD.DEAL d ON TO_VARCHAR(AC.DEAL_ID) = TO_VARCHAR(D.DEAL_ID)
    WHERE 
     booking_id IS NOT NULL
    QUALIFY 
        ROW_NUMBER() OVER (PARTITION BY appointment_id ORDER BY token_date DESC) = 1
),

latest_booking AS (
    SELECT 
        lead_id,
        booking_id AS latest_token_booking_id,
        booking_date AS latest_booking_date,
        booking_status,
        token_date,
        ROW_NUMBER() OVER (PARTITION BY lead_id ORDER BY 
            CASE 
                WHEN booking_status = 'SOLD' THEN 1 
                ELSE 2 
            END,
            booking_date DESC
        ) AS booking_rank
    FROM 
        booking_data
)
, price_changes AS (
    SELECT 
        APPOINTMENTID AS lead_id,
        TO_DATE(updatedAt) AS change_date,
        listingprice AS current_price,
        LAG(listingprice) OVER (PARTITION BY APPOINTMENTID ORDER BY updatedAt) AS previous_price,
        DATEDIFF('day', LAG(TO_DATE(updatedAt)) OVER (PARTITION BY APPOINTMENTID ORDER BY updatedAt), TO_DATE(updatedAt)) AS days_since_last_change
    FROM 
        CAPL_REFURB_DB.ARANGO.INVENTORY_LOG_WH_VW
    WHERE 
        (UPPER(TO_CHAR(PUBLISHED)) = 'TRUE' OR TO_CHAR(PUBLISHED) = '1')
        AND listingprice IS NOT NULL
),
price_drops AS (
    SELECT 
        lead_id,
        change_date AS RECENT_PRICE_DROP_DATE,
        previous_price AS LAST_PRICE_BEFORE_PRICE_DROP,
        (previous_price - current_price) AS PRICE_DROP,
        days_since_last_change AS DAYS_OF_LAST_PRICE_DROP,
        CASE 
            WHEN days_since_last_change <= 7 THEN '0-7 days'
            WHEN days_since_last_change <= 14 THEN '8-14 days'
            WHEN days_since_last_change <= 30 THEN '15-30 days'
            ELSE '30+ days'
        END AS LAST_PRICE_DROP_DAYS_BUCKET,
        ROW_NUMBER() OVER (PARTITION BY lead_id ORDER BY change_date DESC) AS rn
    FROM 
        price_changes 
    WHERE 
        previous_price > current_price 
        AND previous_price IS NOT NULL
),
 listing_days_with_reserve_check AS (
  SELECT
    APPOINTMENT_ID,
    COUNT(DISTINCT CASE 
      WHEN ORDER_STATE = 'PUBLISH' AND TOKEN_TYPE IS DISTINCT FROM 'RESERVE'
      THEN DATE END) AS Effective_Listing_Days_With_Reserve_Check
  FROM (
    SELECT 
      DT.DATE,
      STATE.APPOINTMENT_ID,
      STATE.ORDER_STATE,
      TOKEN.TOKEN_TYPE
    FROM (
      SELECT TO_DATE(DATEADD(DAY, -SEQ4(), CURRENT_DATE())) AS DATE
      FROM TABLE(GENERATOR(ROWCOUNT => 900))
    ) DT
    LEFT JOIN (
      SELECT
        APPOINTMENTID AS APPOINTMENT_ID,
        CASE
          WHEN (UPPER(TO_CHAR(PUBLISHED)) = 'TRUE' OR TO_CHAR(PUBLISHED) = '1') AND
               (UPPER(NVL(REPLACE(TRY_PARSE_JSON(INVENTORYFLAGS):reservedStatus,'"',''), 'FALSE')) = 'FALSE') AND
               (UPPER(NVL(REPLACE(TRY_PARSE_JSON(INVENTORYFLAGS):pseudoDelistFlag,'"',''), 'FALSE')) = 'FALSE')
          THEN 'PUBLISH'
          WHEN (UPPER(TO_CHAR(SOLD)) = 'TRUE' OR TO_CHAR(SOLD) = '1') THEN 'SOLD'
          ELSE 'ARCHIVE'
        END AS ORDER_STATE,
        TO_DATE(updatedAt) AS UPDATED_DATE,
        TO_DATE(
          IFNULL(LEAD(updatedAt, 1) OVER (PARTITION BY  APPOINTMENTID ORDER BY updatedAt),
                 DATEADD(DAY, 1, CURRENT_DATE()))
        ) AS LEAD_UPDATED_DATE,
        RANK() OVER (
  PARTITION BY APPOINTMENTID, TO_DATE(updatedAt)
  ORDER BY TO_TIMESTAMP_NTZ(REPLACE(SUBSTR(updatedAt, 1, 23), 'T', ' ')) DESC
) AS RANK

      FROM CAPL_REFURB_DB.ARANGO.INVENTORY_LOG_WH_VW
    ) STATE
      ON DT.DATE >= TO_DATE(STATE.UPDATED_DATE)
     AND DT.DATE < TO_DATE(STATE.LEAD_UPDATED_DATE)
     AND STATE.RANK = 1
    LEFT JOIN (
      SELECT
        APPOINTMENTID,
        TO_DATE(token_date_time) AS TOKEN_DATE,
        token_type_with_nrt AS TOKEN_TYPE
      FROM CAPL_GS_DB.PROD.GS_SALES
      WHERE token_type_with_nrt = 'RESERVE'
    ) TOKEN
      ON TOKEN.APPOINTMENTID = STATE.APPOINTMENT_ID
     AND TOKEN.TOKEN_DATE = DT.DATE
  )
  GROUP BY APPOINTMENT_ID
)
select DISTINCT
i.appointmentid,
i.registrationnumber as reg_number,
hub_city.last_stockin_hub as LAST_STOCKIN_HUB,
hub_city.last_stockin_city as LAST_STOCKIN_HUB_CITY,
hub_city.FIRST_STOCKIN_HUB_NAME,
-- i.LOCATIONTYPE,
-- IFF(
--     i.label = 'BOUGHT', 
--     il.LOCATION_NAME,  
--     IFF(
--         il.LOCATION_NAME = '' OR il.LOCATION_NAME IS NULL, 
--         IFF(
--             tolocationname = '' OR tolocationname IS NULL, 
--             fromlocationname,  
--             tolocationname     
--         ), 
--         locationname          
--     )
-- ) AS c2c_location_name
i.location as current_location,


to_date(i.boughtdate) as BOUGHT_DATE,
to_date(i.boughtdate) as STOCKIN_DATE,
TO_DATE(TO_TIMESTAMP_NTZ(h.FIRST_LISTING_TIME / 1000)) AS first_listing_date,
--I.COMMENT,
-- IFF(
--     UPPER(TO_CHAR(i.PUBLISHED)) = 'TRUE' OR TO_CHAR(i.PUBLISHED) = '1',
--     'PUBLISHED',
--     'NOT_PUBLISHED'
-- ) AS LISTING_STATUS
IFF(
    UPPER(TO_CHAR(h.LISTING)) = 'LISTED',
    'PUBLISHED',
    'NOT_PUBLISHED'
) AS LISTING_STATUS
,
-- CASE 
--     WHEN i.comment = 'Published' AND TO_DATE(TO_TIMESTAMP(h.FIRST_LISTING_TIME / 1000)) IS NOT NULL THEN 
--       DATEDIFF(
--         DAY, 
--         TO_DATE(TO_TIMESTAMP(h.FIRST_LISTING_TIME / 1000)), 
--         CURRENT_DATE()
--       ) - COALESCE(rd.paused_days, 0)
--     ELSE NULL
--   END AS total_listing_days
ldr.Effective_Listing_Days_With_Reserve_Check AS total_listing_days,
DATEDIFF('day', to_date(i.boughtdate), 
           COALESCE(sl.delivery_date, CURRENT_DATE)) AS Inventory_age,
 CASE 
        WHEN Inventory_age <= 7 THEN '0-7 days'
        WHEN Inventory_age <= 14 THEN '8-14 days'
        WHEN Inventory_age <= 30 THEN '15-30 days'
        ELSE '30+ days' 
    END AS inventory_age_bucket,           
-- ed.make,
-- ed.model,ed.variant,
-- ed.year,
-- ed.odometer,
-- ed.owner_number,
-- ed.fuel_type,
a.make,
        a.model,
        a.variant,
        t.year,
        t.odometer,
        t.ownership,
        a.fuel_type,

BKP.Lifetime_Bookings,
BKP.Lifetime_Visits,
l7bc.L7d_BC,
l15bc.L15d_BC,
l7v.L7d_Visit,
l15v.L15d_Visit,
l7T.L7d_Token,
l15T.L15d_Token,
l7NRT.L7d_Token_NRT,
l15NRT.L15d_Token_NRT,
vs.classified_price,
FLP.first_listing_price,
i.listingprice as latest_listing_price,
PR.RECENT_PRICE_DROP_DATE,
PR.LAST_PRICE_BEFORE_PRICE_DROP,
PR.PRICE_DROP,
PR.DAYS_OF_LAST_PRICE_DROP,
PR.LAST_PRICE_DROP_DAYS_BUCKET,
null as refurb_amount,
-- iv.refurb_amount,
-- iv.CLASSIFIER_SCORE as CLASSIFIER_Price,
-- iv.IMPF_CNT,
-- iv.IMPF_BKT,
rs.TOKEN_STATUS_ON_WEB,
-- PDM.Last_PD_Date as Resent_Price_Drop_Date,
-- PDM.Old_listing_price as Last_Price_Before_Price_Drop,
-- PDM.Price_Diff as Price_Drop,
-- DATEDIFF(DAY,  PDM.Last_PD_Date,current_date()) AS Days_of_last_Price_Drop,
-- CASE 
--     WHEN DATEDIFF(DAY,  PDM.Last_PD_Date,current_date()) IS NULL THEN 'No_Price_Drop'
--     WHEN DATEDIFF(DAY,  PDM.Last_PD_Date,current_date()) >= 7 THEN 'More_then_7Days'
--     ELSE 'within_7Days'
-- END AS Last_Price_Drop_Days_Bucket,
ed.edge_plus_procurement_price as Plus_Stockin_Price,
SL.Token_date,
lb.latest_token_booking_id,
lb.booking_status,
DATEDIFF('day', lb.token_date, COALESCE(sl.delivery_date, CURRENT_DATE)) AS days_since_token,
om.token_type,
SL.DELIVERY_DATE,
ST.sales_return_date,
sl.total_expected,
sl.total_collected,
SL.final_selling_price,
w.WAIVER_Conversion_Discount,
sl.final_selling_price - coalesce(w.WAIVER_Conversion_Discount,0) as sold_price,
sl.c24_margin,
SD.sold_booking_id,
--rsd.PAYMENT_MODE,
 --case when GSCF.DISBURSED_FLAG_AGAINST_UID_D>0 then'CF'else s.FINAL_PAYMENT_TYPE end as payment_mode,
ed.store_id,

--ah.dealercode
from CAPL_REFURB_DB.ARANGO.INVENTORY_WH_VW i
left join CAPL_GS_DB.ARANGO_B2C_MASTER.LOCATION_VW ah on ah.code = i.locationcode
left join CSPL_C2B_DB.ADMIN_PANEL_PROD_DEALERENGINE_PROD.ORDERS v on v.lead_id = i.appointmentid
left join CAPL_GS_DB.PROD.GS_SALES  s on s.appointmentid = i.appointmentid
left join CSPL_C2B_DB.MONGO_CAR_CATALOG_SVC_CAR_CATALOG_SERVICE.INVENTORY h on h.vehicle_id = i.appointmentid
left join CSPL_C2B_DB.MONGO_C2B_C2B_FRANCHISE_CORE.APPOINTMENT ed on ed.appointment_id =i.appointmentid
LEFT JOIN listing_days_with_reserve_check ldr ON ldr.APPOINTMENT_ID = i.appointmentid
LEFT JOIN CAPL_GS_DB.ARANGO.LOCATION_VW loc ON loc.code = i.locationcode
left join CFSPL_NBFC_DB.PROD.GS_TABLE_VERSION2 v2 on v2.appointmentid = i.appointmentid
left JOIN CSPL_C2B_DB.MONGO_CAR_CATALOG_SVC_CAR_CATALOG_SERVICE.inspection  t
on t.vehicle_id=h.vehicle_id
left join CSPL_C2B_DB.MONGO_CAR_CATALOG_SVC_CAR_CATALOG_SERVICE.MMV_MASTER  a
ON TO_VARCHAR(a.variant_id) = TO_VARCHAR(t.variant_id)



LEFT JOIN latest_booking lb 
    ON lb.lead_id = i.appointmentid 
    AND lb.booking_rank = 1
LEFT JOIN PRICE_DROPS PR ON PR.LEAD_ID = I.APPOINTMENTID
LEFT JOIN (
    SELECT 
        APPOINTMENTID,
        FIRST_VALUE(listingprice) OVER (
            PARTITION BY APPOINTMENTID 
            ORDER BY updatedAt ASC
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS first_listing_price
    FROM CAPL_REFURB_DB.ARANGO.INVENTORY_LOG_WH_VW
    WHERE (UPPER(TO_CHAR(PUBLISHED)) = 'TRUE' OR TO_CHAR(PUBLISHED) = '1')
    QUALIFY ROW_NUMBER() OVER (PARTITION BY APPOINTMENTID ORDER BY updatedAt ASC) = 1
) flp ON flp.APPOINTMENTID = I.APPOINTMENTID

LEFT JOIN (
    SELECT 
        appointment_id,
        token_date,
        delivery_date,
        asp AS final_selling_price,
        total_expected,
        total_collected,
        c24_margin
    FROM CAPL_GS_DB.PROD.C2C_SALES_DATA
    QUALIFY ROW_NUMBER() OVER (PARTITION BY appointment_id ORDER BY token_date DESC) = 1
) sl ON sl.appointment_id = I.APPOINTMENTID

left join (select appointment_id,
try_parse_json(RESPONSE_DATA):classified_data:classified_price_original::int as classified_price,
to_date(created_on) as latest_date
from CSPL_C2B_DB.PROD.VIS_DS_TP_V4
qualify row_number() over(partition by appointment_id order by created_on desc) = 1
) vs on vs.appointment_id =i.appointmentid


LEFT JOIN (
    SELECT 
        AC.appointment_id,
        d.booking_id AS sold_booking_id 
    FROM CAPL_GS_DB.C2C_LMS_C2C_LMS_PROD.DEAL d
    LEFT JOIN CAPL_GS_DB.PROD.C2C_SALES_DATA AC ON TO_VARCHAR(AC.DEAL_ID) = TO_VARCHAR(D.DEAL_ID)
    WHERE d.status IN('DONE','PAYMENT') 
) SD ON SD.appointment_id = I.APPOINTMENTID

left join waiver_conversion w on w.appointment_id= i.APPOINTMENTID
and w.orderid = sd.sold_booking_id 
and w.WAIVER_Conversion_Discount is not null
and w.WAIVER_Conversion_Discount!=0

LEFT JOIN (
    SELECT 
        APPOINTMENT_ID,
        MAX(ACTUAL_DELIVERY_DATE) AS sales_return_date
    FROM CAPL_GS_DB.C2C_ADMIN_C2C_ADMIN_PANEL_PROD.C2C_RC_DETAILS r
    LEFT JOIN CAPL_GS_DB.C2C_LMS_C2C_LMS_PROD.DEAL d ON d.deal_id = r.deal_id
    WHERE d.status ='CANCEL' AND ACTUAL_DELIVERY_DATE IS NOT NULL
    GROUP BY 1
) st ON st.APPOINTMENT_ID = i.appointmentid

left join (select distinct baa.APPOINTMENTID,
 count (baa.APPOINTMENTID) as Lifetime_Bookings,
 sum(baa.Visit_Count) as Lifetime_Visits 
 from ( SELECT ba.ORDERID as Booking_ID,
TO_DATE(
  TO_TIMESTAMP_NTZ(
    REPLACE(SUBSTR(ba.bookingconfirmdate, 1, 23), 'T', ' ')
  ) + INTERVAL '330 minutes'
) AS booking_date,
ba.APPOINTMENTID,
       count(vhm1.DEAL_IDENTIFIER) as Visit_Count
FROM CAPL_GS_DB.ARANGO.ORDER_WH_VW   ba 
   //   where ORDERID in ('BL4NI1')
left join CAPL_GS_DB.ARANGO.ORDER_WH MD on md.order_ID=ba.orderid
left join CAPL_GS_DB.C2C_LMS_C2C_LMS_PROD.DEAL D on  ba.ORDERID =d.booking_id
left join ( Select ed1f.DEAL_IDENTIFIER,ed1f.IS_COMPLETE,TO_TIMESTAMP_NTZ(REPLACE(SUBSTR(ed1f.UPDATED_AT, 1, 23), 'T', ' ')) + INTERVAL '330 minutes' AS first_Visit_date
 from 
          (Select edf.DEAL_IDENTIFIER,edf.IS_COMPLETE,edf.UPDATED_AT,row_number() over(partition by edf.DEAL_IDENTIFIER order by edf.UPDATED_AT asc) as rank
          from CAPL_GS_DB.C2C_LMS_C2C_LMS_PROD.CUSTOMER_VISIT_HISTORY edf
          where IS_COMPLETE='TRUE')ed1f
          where rank>='1') vhm1  //dd.DEAL_IDENTIFIER=d.DEAL_IDENTIFIER
on d.DEAL_IDENTIFIER=vhm1.DEAL_IDENTIFIER
  Where ba.VEHICLETYPE='car'
  and ba.STATUS <> 'CREATED'
  and ba.COUNTRY='IN'
 
  group by 1,2,3      

 )baa
 group by 1) bkp on i.appointmentid=bkp.APPOINTMENTID
 --Last 7 day BC
left join (select gs.APPOINTMENTID,count(APPOINTMENTID) as L7d_BC from CAPL_GS_DB.PROD.GS_SALES gs
where gs.booking_date >= current_date()-7
group by 1) l7bc on l7bc.APPOINTMENTID=i.appointmentid 
-- Last 15 Day BC's
left join (select gs.APPOINTMENTID,count(APPOINTMENTID) as L15d_BC from CAPL_GS_DB.PROD.GS_SALES gs
where gs.booking_date >= current_date()-15
group by 1) l15bc on l15bc.APPOINTMENTID=I.appointmentid
--- 7 Days Visit- 
left join (select gs.APPOINTMENTID,count(APPOINTMENTID) as L7d_Visit from CAPL_GS_DB.PROD.GS_SALES gs
where gs.frist_visit_date >= current_date()-7
group by 1) l7V on l7V.APPOINTMENTID=I.appointmentid
--- 15 Days Visit --- 
left join (select gs.APPOINTMENTID,count(APPOINTMENTID) as L15d_Visit from CAPL_GS_DB.PROD.GS_SALES gs
where gs.frist_visit_date >= current_date()-15
group by 1) l15V on l15V.APPOINTMENTID=I.appointmentid

--- 7 Days Token- 
left join (select gs.APPOINTMENTID,count(APPOINTMENTID) as L7d_Token from CAPL_GS_DB.PROD.GS_SALES gs
where gs.token_date_time::DAte >= current_date()-7
group by 1) l7T on l7T.APPOINTMENTID=I.appointmentid
--- 15 Days Visit --- 
left join (select gs.APPOINTMENTID,count(APPOINTMENTID) as L15d_Token from CAPL_GS_DB.PROD.GS_SALES gs
where gs.token_date_time::DAte >= current_date()-15
group by 1) l15T on l15T.APPOINTMENTID=I.appointmentid


--- 7 Days Token- 
left join (select gs.APPOINTMENTID,count(APPOINTMENTID) as L7d_Token_NRT from CAPL_GS_DB.PROD.GS_SALES gs
where gs.token_date_time::DAte >= current_date()-7
and GS.token_type_with_nrt like '%NRT%'
group by 1) l7NRT on l7NRT.APPOINTMENTID=I.appointmentid
--- 15 Days Visit --- 
left join (select gs.APPOINTMENTID,count(APPOINTMENTID) as L15d_Token_NRT from CAPL_GS_DB.PROD.GS_SALES gs
where gs.token_date_time::DAte >= current_date()-15
and GS.token_type_with_nrt like '%NRT%'
group by 1) l15NRT on l15NRT.APPOINTMENTID=I.appointmentid
LEFT JOIN
(select APPOINTMENTID,'CURRENTLY TOKENED ON WEBSITE' AS TOKEN_STATUS_ON_WEB from CAPL_GS_DB.PROD.GS_SALES 
where BOOKING_STATUS='BOOKED' AND TOKEN_TYPE_WITH_NRT IN ('RESERVE','NRT TOKEN UPGRADED') 
AND CAR_STATUS='UnSold' order by APPOINTMENTID) RS
ON RS.APPOINTMENTID=I.appointmentid
left join (select appointmentid,to_date(token_date_time) as Token_date,token_type_with_nrt as token_type
 from CAPL_GS_DB.PROD.GS_SALES where deal_status not like '%CANCEL%'
AND TOKEN_DATE_TIME IS NOT NULL ) OM ON OM.APPOINTMENTID = I.APPOINTMENTID
LEFT JOIN (SELECT APPOINTMENTID,TO_DATE(ACTUAL_DELIVERY_DATE) AS DELIVERY_DATE
FROM CAPL_GS_DB.PROD.GS_SALES WHERE DEAL_STATUS = 'PAYMENT' AND ACTUAL_DELIVERY_DATE IS NOT NULL ) OK ON OK.APPOINTMENTID = I.APPOINTMENTID
-- LEFT JOIN (SELECT store_id,correct_store_name,hub_name FROM CSPL_C2B_DB.GSHEET.EDGE_HUB_MAPPING) hb on TRY_CAST(hb.store_id AS NUMBER) = ed.store_id
-- left join (select code as city_code , name as Last_stockin_hub_city from CAPL_GS_DB.ARANGO.CITY_VW) cc on i.citycode=cc.city_code
LEFT JOIN (

    WITH ranked AS (
        SELECT 
            appointmentid,
            locationcode,
            citycode,
            ROW_NUMBER() OVER (
                PARTITION BY appointmentid 
                ORDER BY UPDATEDAT DESC
            ) AS rn_desc,
            ROW_NUMBER() OVER (
                PARTITION BY appointmentid 
                ORDER BY UPDATEDAT ASC
            ) AS rn_asc
        FROM CAPL_REFURB_DB.ARANGO.INVENTORY_LOG_WH_VW
        WHERE countrycode = 'IN'
          AND VEHICLETYPE = 'CAR'
          AND locationcode IS NOT NULL
          AND citycode IS NOT NULL
    )

    SELECT 
        r.appointmentid,

        
        MAX(CASE WHEN rn_asc = 1 THEN loc.name END) AS first_stockin_hub_name,
        MAX(CASE WHEN rn_asc = 1 THEN city.name END) AS first_stockin_city,

        MAX(CASE WHEN rn_desc = 1 THEN loc.name END) AS last_stockin_hub,
        MAX(CASE WHEN rn_desc = 1 THEN city.name END) AS last_stockin_city

    FROM ranked r

    LEFT JOIN CAPL_GS_DB.ARANGO.LOCATION_VIEW loc
        ON r.locationcode = loc.code

    LEFT JOIN CAPL_GS_DB.ARANGO.CITY_VIEW city
        ON loc.citycode = city.code

    GROUP BY r.appointmentid

) hub_city

ON hub_city.appointmentid = I.appointmentid
WHERE i.appointmentid in ( select distinct appointment_id from  CSPL_C2B_DB.MONGO_C2B_C2B_FRANCHISE_CORE.APPOINTMENT where edge_plus = 'TRUE'
and EDGE_PLUS_CAR_STATUS is not null
and lower(EDGE_PLUS_CAR_STATUS) not like '%rejected%' 
)

and (lower(hub_city.first_stockin_hub_name)  like '%elite%')


qualify row_number() over (partition by i.appointmentid order by sl.delivery_date desc) =1
order by stockin_date asc;
    """
    try:
        starrocks_query = convert_snowflake_to_starrocks(sample_query)
        print(f"Input Query:\n{sample_query}\n")
        print(f"Output StarRocks Query:\n{starrocks_query}")
    except Exception as e:
        print(f"Error: {e}")