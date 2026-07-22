import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL")

def run():
    print(f"Connecting to DB...")
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    cursor = conn.cursor()

    try:
        # Add column
        cursor.execute("ALTER TABLE aeo_runs ADD COLUMN IF NOT EXISTS error_message TEXT;")
        print("Added error_message to aeo_runs.")

        # Reload PostgREST schema cache
        cursor.execute("NOTIFY pgrst, 'reload schema';")
        print("Notified PostgREST to reload schema.")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run()
