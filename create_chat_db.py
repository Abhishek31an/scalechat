import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def init_db():
    print("🔌 Connecting to Database...")
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            port=os.getenv("DB_PORT"),
            database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor()

        # Create the table strictly for this Chat App
        query = """
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INT AUTO_INCREMENT PRIMARY KEY,
            client_id VARCHAR(50),
            message TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        cursor.execute(query)
        print("✅ Table 'chat_messages' created successfully.")

        conn.close()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    init_db()