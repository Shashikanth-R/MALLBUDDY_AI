import sqlite3
import os

DB_PATH = 'instance/mallbuddy.db'

def add_column():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'last_login' not in columns:
            print("Adding last_login column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN last_login DATETIME")
            conn.commit()
            print("Column added successfully.")
        else:
            print("Column last_login already exists.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    add_column()
