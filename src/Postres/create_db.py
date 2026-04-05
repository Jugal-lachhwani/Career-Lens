import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv
import os

load_dotenv()
# DB credentials
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
NEW_DB_NAME = "job_ai_agent"

try:
    # Connect to default database
    conn = psycopg2.connect(
        dbname="postgres",  # IMPORTANT
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

    cursor = conn.cursor()

    # Create database
    cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{NEW_DB_NAME}'")
    exists = cursor.fetchone()

    if not exists:
        cursor.execute(f"CREATE DATABASE {NEW_DB_NAME};")
        print(f"✅ Database '{NEW_DB_NAME}' created successfully!")
    else:
        print("⚠️ Database already exists")

   

    cursor.close()
    conn.close()

except Exception as e:
    print("❌ Error:", e)