import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def create_rooms_table():
    print("🔌 Connecting to Database...")
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME")
    )
    cursor = conn.cursor()
    
    try:
        # Create a table to store Room Names and Passwords
        query = """
        CREATE TABLE IF NOT EXISTS rooms (
            room_name VARCHAR(50) PRIMARY KEY,
            password VARCHAR(50) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        cursor.execute(query)
        print("✅ Table 'rooms' created successfully.")
    except Exception as e:
        print(f"❌ Error: {e}")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_rooms_table()