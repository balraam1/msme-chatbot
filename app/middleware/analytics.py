import threading
import json
from typing import Optional, Dict, Any
from app.db import get_db_connection

def analyze_sentiment(text: str) -> str:
    """
    Classifies the sentiment of the user query into Positive, Neutral, Frustrated, or Angry.
    """
    if not text:
        return "Neutral"
        
    text_lower = text.lower()
    
    # Frustrated/Negative keywords
    negative_keywords = [
        "delay", "slow", "late", "pending", "not approved", "rejected",
        "problem", "issue", "complaint", "grievance", "fraud", "scam",
        "deeri", "delay", "ruk gaya", "pareshan", "samasya", "shikayat",
        "galti", "galat", "kharab", "bekar", "paisa fasa", "nahi mila",
        "nhi mila", "attka", "टका", "लटका", "देरी", "धीमा", "परेशान",
        "समस्या", "शिकायत", "गलत", "धोखा", "पेंडिंग", "नहीं हुआ", "रिजेक्ट"
    ]
    
    # Positive/Appreciation keywords
    positive_keywords = [
        "thank", "thanks", "dhanyawad", "shukriya", "good", "great", "nice",
        "helped", "resolved", "solved", "dhanyavad", "bahut achha", "achha",
        "aacha", "sundar", "help mila", "मदद मिली", "धन्यवाद", "शुक्रिया",
        "अच्छा", "बढ़िया", "সুলঝ", "ধন্যবাদ"
    ]
    
    # Highly critical/angry indicators
    angry_indicators = [
        "fraud", "dhokha", "loot", "fake", "badtameezi", "ghoos", "bribery", 
        "angry", "chutiya", "bakwas", "corruption", "corrupt", "bhrashtachar",
        "chor", "chori", "fasa diya", "loot liya", "luta"
    ]
    
    if any(ai in text_lower for ai in angry_indicators):
        return "Angry"
    elif any(nk in text_lower for nk in negative_keywords):
        return "Frustrated"
    elif any(pk in text_lower for pk in positive_keywords):
        return "Positive"
    else:
        return "Neutral"

def log_event(
    session_id: str,
    event_type: str,
    intent: Optional[str] = None,
    scheme_name: Optional[str] = None,
    language: Optional[str] = None,
    response_ms: Optional[int] = None,
    is_fallback: bool = False,
    user_agent: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
    query_text: Optional[str] = None
):
    """
    Logs an event to the events table asynchronously using a background thread.
    This is non-blocking and works in both sync and async environments.
    """
    def _insert_event():
        try:
            extra_json = json.dumps(extra) if extra else None
            sentiment = None
            if event_type == "message" and query_text:
                sentiment = analyze_sentiment(query_text)
                
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO events (
                session_id, event_type, intent, scheme_name, language,
                response_ms, is_fallback, user_agent, extra_json, query_text, sentiment
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                event_type,
                intent,
                scheme_name,
                language,
                response_ms,
                1 if is_fallback else 0,
                user_agent,
                extra_json,
                query_text,
                sentiment
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

