import psycopg
import json
import uuid
from config import config

def check_db():
    conn = psycopg.connect(config.database.connection_string, autocommit=True)
    target_id = "1a32a32d-8afc-4d09-a032-7497f0eb1efb"
    
    print(f"Checking for ID: {target_id}")
    with conn.cursor() as cur:
        # Check conversations
        cur.execute("SELECT id, namespace FROM conversations WHERE id = %s", (target_id,))
        conv = cur.fetchone()
        print(f"Conversation record: {conv}")
        
        # Check namespaces
        cur.execute("SELECT DISTINCT namespace FROM conversations")
        namespaces = cur.fetchall()
        print(f"Exiting namespaces: {namespaces}")
        
        # Check total message count
        cur.execute("SELECT COUNT(*) FROM chat_messages")
        count = cur.fetchone()[0]
        print(f"Total chat messages: {count}")

if __name__ == "__main__":
    check_db()
