import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "..", "crm.db")

def get_conn():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    # enforce foreign keys in sqlite
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # main tickets table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id TEXT UNIQUE NOT NULL,
        customer_name TEXT NOT NULL,
        customer_email TEXT NOT NULL,
        subject TEXT NOT NULL,
        description TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Open',
        is_vip INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    # internal notes thread
    cur.execute("""
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id TEXT NOT NULL,
        note_text TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (ticket_id) REFERENCES tickets (ticket_id) ON DELETE CASCADE
    );
    """)

    conn.commit()
    conn.close()

def get_tkt_id():
    conn = get_conn()
    cur = conn.cursor()
    # get latest id for auto code generation
    cur.execute("SELECT MAX(id) FROM tickets;")
    res = cur.fetchone()[0]
    conn.close()
    cnt = (res if res else 0) + 1
    return f"TKT-DS-{cnt:04d}"