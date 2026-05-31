import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Check if PostgreSQL URL is provided in the environment
DATABASE_URL = os.environ.get("DATABASE_URL")

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "msme_saathi.db")

# Helper class to dynamically translate sqlite query parameters (?) to PostgreSQL (%s)
class PostgresCursorWrapper:
    def __init__(self, real_cursor):
        self.real_cursor = real_cursor

    def execute(self, query, params=None):
        if params is not None:
            # Safely swap sqlite "?" placeholder to PostgreSQL "%s"
            query = query.replace('?', '%s')
        return self.real_cursor.execute(query, params)

    def executemany(self, query, params_list=None):
        if params_list is not None:
            query = query.replace('?', '%s')
        return self.real_cursor.executemany(query, params_list)

    def __getattr__(self, name):
        return getattr(self.real_cursor, name)

class PostgresConnectionWrapper:
    def __init__(self, real_conn):
        self.real_conn = real_conn

    def cursor(self, *args, **kwargs):
        cursor = self.real_conn.cursor(*args, **kwargs)
        return PostgresCursorWrapper(cursor)

    def __getattr__(self, name):
        return getattr(self.real_conn, name)

def get_db_connection():
    """Returns a Database connection (SQLite locally or PostgreSQL in production)"""
    if DATABASE_URL:
        import psycopg2
        import psycopg2.extras
        # Use DictCursor to emulate sqlite3.Row dictionary interface
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.DictCursor)
        return PostgresConnectionWrapper(conn)
    else:
        os.makedirs(DB_DIR, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    """Initializes tables inside the connected database."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = get_db_connection()
    cursor = conn.cursor()

    if DATABASE_URL:
        # PostgreSQL Schema Creation
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS grievances (
            id SERIAL PRIMARY KEY,
            ticket_id VARCHAR(255) UNIQUE NOT NULL,
            session_id VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            scheme_name VARCHAR(255),
            grievance_type VARCHAR(255),
            severity VARCHAR(50) DEFAULT 'Medium',
            raw_text TEXT,
            summary_en TEXT,
            summary_hi TEXT,
            entity_bank VARCHAR(255),
            entity_amount VARCHAR(255),
            entity_duration_days INTEGER,
            status VARCHAR(50) DEFAULT 'Open',
            resolution_note TEXT,
            updated_at TIMESTAMP,
            contact_number TEXT
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(255) NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            event_type VARCHAR(255) NOT NULL,
            intent VARCHAR(255),
            scheme_name VARCHAR(255),
            language VARCHAR(50),
            response_ms INTEGER,
            is_fallback BOOLEAN DEFAULT FALSE,
            user_agent VARCHAR(555),
            extra_json TEXT,
            query_text TEXT,
            sentiment VARCHAR(100)
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id SERIAL PRIMARY KEY,
            ticket_ref VARCHAR(255),
            name VARCHAR(255),
            phone VARCHAR(50),
            preferred_slot VARCHAR(255),
            query_topic VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status VARCHAR(50) DEFAULT 'Pending'
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversation_state (
            thread_id VARCHAR(255) PRIMARY KEY,
            session_id VARCHAR(255),
            graph_name VARCHAR(255),
            state_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        conn.commit()
    else:
        # SQLite Schema Creation
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS grievances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id TEXT UNIQUE NOT NULL,
            session_id TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            scheme_name TEXT,
            grievance_type TEXT,
            severity TEXT DEFAULT 'Medium',
            raw_text TEXT,
            summary_en TEXT,
            summary_hi TEXT,
            entity_bank TEXT,
            entity_amount TEXT,
            entity_duration_days INTEGER,
            status TEXT DEFAULT 'Open',
            resolution_note TEXT,
            updated_at DATETIME
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            event_type TEXT NOT NULL,
            intent TEXT,
            scheme_name TEXT,
            language TEXT,
            response_ms INTEGER,
            is_fallback BOOLEAN DEFAULT 0,
            user_agent TEXT,
            extra_json TEXT
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_ref TEXT,
            name TEXT,
            phone TEXT,
            preferred_slot TEXT,
            query_topic TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'Pending'
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversation_state (
            thread_id TEXT PRIMARY KEY,
            session_id TEXT,
            graph_name TEXT,
            state_json TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()

        # SQLite legacy migrations (Postgres tables are created with columns already included)
        try:
            cursor.execute("ALTER TABLE grievances ADD COLUMN contact_number TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass # Column already exists

        try:
            cursor.execute("ALTER TABLE events ADD COLUMN query_text TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE events ADD COLUMN sentiment TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass

    conn.close()
    
    # Check for legacy grievances.txt file migration
    legacy_txt = os.path.join(os.path.dirname(os.path.dirname(__file__)), "grievances.txt")
    if os.path.exists(legacy_txt):
        migrate_grievances_from_txt(legacy_txt)

def migrate_grievances_from_txt(txt_path: str):
    """Migrates legacy pipe-delimited grievances to the SQLite/PostgreSQL database."""
    if not os.path.exists(txt_path):
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    migrated_count = 0
    skipped_count = 0
    
    with open(txt_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            # Skip divider lines if any exist in raw txt
            if line.startswith("---"):
                continue
                
            parts = line.split("|")
            
            # Format could be:
            # 5 parts: ticket_id|scheme_name|raw_text|status|timestamp
            # 6 parts: ticket_id|session_id|scheme|query_text|timestamp|status
            if len(parts) == 5:
                ticket_id = parts[0].strip()
                session_id = None
                scheme_name = parts[1].strip()
                raw_text = parts[2].strip()
                status = parts[3].strip()
                timestamp_str = parts[4].strip()
            elif len(parts) >= 6:
                ticket_id = parts[0].strip()
                session_id = parts[1].strip()
                scheme_name = parts[2].strip()
                raw_text = parts[3].strip()
                timestamp_str = parts[4].strip()
                status = parts[5].strip()
            else:
                continue
                
            # Normalise status: if it is placeholder or "Register Complaint", store as "Open"
            if status in ("Register Complaint", "status"):
                status = "Open"
                
            # Check if already exists in database
            cursor.execute("SELECT id FROM grievances WHERE ticket_id = ?", (ticket_id,))
            if cursor.fetchone():
                skipped_count += 1
                continue
                
            try:
                cursor.execute("""
                INSERT INTO grievances (
                    ticket_id, session_id, scheme_name, raw_text, status,
                    grievance_type, severity, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ticket_id, session_id, scheme_name, raw_text, status,
                    "Other", "Medium", timestamp_str
                ))
                migrated_count += 1
            except Exception as e:
                print(f"Error migrating ticket {ticket_id}: {e}")
                
    conn.commit()
    conn.close()
    print(f"Migration completed. Migrated: {migrated_count}, Skipped: {skipped_count}")

# Initialize database at module load time
init_db()
