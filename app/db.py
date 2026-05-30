import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "msme_saathi.db")

def get_db_connection() -> sqlite3.Connection:
    """Returns a SQLite connection with Row factory enabled."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Creates tables if they do not exist and runs migrations."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Create grievances table
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
    
    # 2. Create events table
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
    
    # 3. Create appointments table
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
    
    # 4. Create conversation_state table
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

    # Migration: Add contact_number to grievances if it doesn't exist
    try:
        cursor.execute("ALTER TABLE grievances ADD COLUMN contact_number TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass # Column already exists

    # Migration: Add query_text and sentiment columns to events if they don't exist
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
    """Migrates legacy pipe-delimited grievances to the SQLite database."""
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
