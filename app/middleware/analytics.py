import threading
import json
from typing import Optional, Dict, Any
from app.db import get_db_connection

def log_event(
    session_id: str,
    event_type: str,
    intent: Optional[str] = None,
    scheme_name: Optional[str] = None,
    language: Optional[str] = None,
    response_ms: Optional[int] = None,
    is_fallback: bool = False,
    user_agent: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None
):
    """
    Logs an event to the events table asynchronously using a background thread.
    This is non-blocking and works in both sync and async environments.
    """
    def _insert_event():
        try:
            extra_json = json.dumps(extra) if extra else None
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO events (
                session_id, event_type, intent, scheme_name, language,
                response_ms, is_fallback, user_agent, extra_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                event_type,
                intent,
                scheme_name,
                language,
                response_ms,
                1 if is_fallback else 0,
                user_agent,
                extra_json
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            # Silently catch and log DB errors to console
            print(f"Analytics logging database error: {e}")

    try:
        t = threading.Thread(target=_insert_event, daemon=True)
        t.start()
    except Exception as e:
        print(f"Failed to start thread for event logging: {e}")

