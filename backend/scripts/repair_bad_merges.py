import os
import sys
import psycopg2
import json

def run():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL is not set.")
        sys.exit(1)

    try:
        conn = psycopg2.connect(db_url)
        with conn.cursor() as cur:
            # Find the bad merge brand
            cur.execute('''
                SELECT id, canonical_name, aliases 
                FROM brands 
                WHERE canonical_name = 'Maui Real Estate' 
            ''')
            
            brand = cur.fetchone()
            if not brand:
                print("Bad merge 'Maui Real Estate' not found.")
            else:
                brand_id = brand[0]
                canonical_name = brand[1]
                aliases = brand[2]
                
                print(f"Found bad merge brand: ID={brand_id}, aliases={aliases}")
                
                if 'Kauai Real Estate' in aliases:
                    # Remove Kauai Real Estate from aliases
                    new_aliases = [a for a in aliases if a != 'Kauai Real Estate']
                    
                    cur.execute('''
                        UPDATE brands
                        SET aliases = %s::jsonb
                        WHERE id = %s
                    ''', (json.dumps(new_aliases), brand_id))
                    
                    print("Removed 'Kauai Real Estate' from aliases.")
                else:
                    print("Kauai Real Estate not in aliases. Already fixed.")
                
            conn.commit()
            print("Repair complete.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run()
