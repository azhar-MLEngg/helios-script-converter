"""Example Snowflake script for testing conversion."""

import snowflake.connector

# Snowflake connection
conn = snowflake.connector.connect(
    user='myuser',
    password='mypassword',
    account='myaccount',
    warehouse='mywarehouse',
    database='mydb',
    schema='myschema'
)

# Example query with various Snowflake-specific features
query = """
SELECT 
    user_id,
    name::VARCHAR as user_name,
    email::VARCHAR as user_email,
    metadata::VARIANT as user_metadata,
    created_at::TIMESTAMP_NTZ as created_timestamp,
    PARSE_JSON(preferences):theme::VARCHAR as theme,
    IFF(status = 'active', 1, 0) as is_active,
    DATEADD(day, 7, created_at) as week_later,
    COUNT(*) OVER (PARTITION BY status) as status_count
FROM users
WHERE created_at >= TO_TIMESTAMP('2024-01-01')
    AND status IN ('active', 'pending')
ORDER BY created_at DESC
LIMIT 100
"""

# Execute query
cursor = conn.cursor()
try:
    cursor.execute(query)
    results = cursor.fetchall()
    
    for row in results:
        print(row)
        
finally:
    cursor.close()
    conn.close()
