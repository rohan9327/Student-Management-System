
import os
import psycopg
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(BASE_DIR, ".env"))

DATABASE_URL = os.getenv("DATABASE_URL")


def get_db_connection():

    if not DATABASE_URL:
        raise ValueError("DATABASE_URL not found")

    conn = psycopg.connect(
        DATABASE_URL,
        sslmode="require"
    )

    return conn


def add_log(username, action):

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO "ActivityLogs"
            (username, action, activity_date)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
        """, (username, action))

        conn.commit()

    finally:
        cursor.close()
        conn.close()
