import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL")

def migrate():
    print(f"Connecting to {DB_URL}")
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    cursor = conn.cursor()

    try:
        # Add attributes to aeo_prompts
        cursor.execute("ALTER TABLE aeo_prompts ADD COLUMN IF NOT EXISTS attributes TEXT[] DEFAULT '{}';")
        print("Added attributes to aeo_prompts.")

        # Create aeo_workstreams table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS aeo_workstreams (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            topics TEXT[] DEFAULT '{}',
            attribute_filters TEXT[] DEFAULT '{}',
            target_visibility NUMERIC(5,2) DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """)
        print("Created workstreams table.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    migrate()
