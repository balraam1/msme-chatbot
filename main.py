import os
import time
import re
from typing import Dict, List, Optional
from pydantic import BaseModel
from fastapi import FastAPI, Depends, HTTPException, status, Request, BackgroundTasks, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from datetime import datetime
from app.knowledge_base import retrieve_context, client as chroma_client
from app.llm import get_chat_response
from app.db import init_db, get_db_connection
from app.content_filter import is_blocked
from app.privacy import scrub_pii, generate_consent_notice
from app.auth import get_admin_user
from app.middleware.analytics import log_event
from app.grievance import extract_grievance, register_grievance_in_db, get_grievance_by_ticket
from app.schemas.grievance_schema import GrievanceExtraction
from app.tts import get_tts_audio
from app.translate import translate_text, detect_language
from app.agent import agent_chat

# SlowAPI imports
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# ---------------------------------------------------------------------------
# FastAPI App & Limiter Initialization
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="MSME Saathi API", description="Backend for MSME Saathi Chatbot")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Enable CORS and SlowAPI Middleware
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register WhatsApp Webhook Router
from routers.whatsapp import router as whatsapp_router
app.include_router(whatsapp_router)

# ---------------------------------------------------------------------------
# State Management (In-Memory Session Store)
# ---------------------------------------------------------------------------
# Store conversation history per session ID.
# Format: { "session_id": { "last_active": timestamp, "messages": [], "consent_acknowledged": bool } }
sessions: Dict[str, Dict] = {}

SESSION_TIMEOUT_SECONDS = 3600  # 1 hour

def clean_old_sessions():
    """Removes sessions that have been inactive for longer than the timeout."""
    current_time = time.time()
    expired_keys = [
        sid for sid, data in sessions.items()
        if current_time - data["last_active"] > SESSION_TIMEOUT_SECONDS
    ]
    for sid in expired_keys:
        del sessions[sid]

# ---------------------------------------------------------------------------
# API Models
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str
    sessionId: str
    isVoiceMode: Optional[bool] = False
    language: Optional[str] = "en"

class ChatResponse(BaseModel):
    reply: str
    structured: dict
    sessionId: str
    language: Optional[str] = "en"

class LanguagePayload(BaseModel):
    sessionId: str
    language: str

class GrievanceSubmit(BaseModel):
    scheme_name: str
    query: str
    session_id: Optional[str] = None

class GrievanceCheck(BaseModel):
    ticket_id: str

class TTSRequest(BaseModel):
    text: str
    language: str
    session_id: str

class GrievanceSubmitDynamic(BaseModel):
    session_id: Optional[str] = None
    raw_text: str
    scheme_name: str
    grievance_type: str
    contact_number: str
    severity: Optional[str] = "Medium"
    entity_bank: Optional[str] = None
    entity_amount: Optional[str] = None
    entity_duration_days: Optional[int] = None
    summary_en: Optional[str] = None
    summary_hi: Optional[str] = None

# ---------------------------------------------------------------------------
# Background Tasks helpers
# ---------------------------------------------------------------------------
def get_missing_grievance_fields(extraction: GrievanceExtraction) -> list:
    fields = []
    
    # 1. Scheme Name
    fields.append({
        "name": "scheme_name",
        "label": "Associated Government Scheme",
        "type": "select",
        "value": extraction.scheme_name or "",
        "options": [
            {"value": "PMEGP", "label": "PMEGP"},
            {"value": "MUDRA Loan", "label": "MUDRA Loan"},
            {"value": "Udyam Registration", "label": "Udyam Registration"},
            {"value": "CGTMSE", "label": "CGTMSE"},
            {"value": "PM SVANidhi", "label": "PM SVANidhi"},
            {"value": "ZED Certification", "label": "ZED Certification"},
            {"value": "GeM Portal", "label": "GeM Portal"},
            {"value": "TReDS", "label": "TReDS"},
            {"value": "Champions Portal", "label": "Champions Portal"},
            {"value": "Other", "label": "Other"}
        ]
    })
    
    # 2. Grievance Category
    fields.append({
        "name": "grievance_type",
        "label": "Grievance Category",
        "type": "select",
        "value": extraction.grievance_type or "",
        "options": [
            {"value": "Loan Delay", "label": "Loan Delay"},
            {"value": "Rejection", "label": "Rejection"},
            {"value": "Portal Error", "label": "Portal Error"},
            {"value": "Documentation Issue", "label": "Documentation Issue"},
            {"value": "Harassment", "label": "Harassment"},
            {"value": "Other", "label": "Other"}
        ]
    })
    
    # 3. Bank Name
    fields.append({
        "name": "entity_bank",
        "label": "Involved Bank Name (if applicable)",
        "type": "text",
        "value": extraction.entity_bank or "",
        "placeholder": "e.g. State Bank of India"
    })
    
    # 4. Amount
    fields.append({
        "name": "entity_amount",
        "label": "Amount Involved (if applicable)",
        "type": "text",
        "value": extraction.entity_amount or "",
        "placeholder": "e.g. 10 Lakhs"
    })
    
    # 5. Duration of Delay
    fields.append({
        "name": "entity_duration_days",
        "label": "Duration of Delay (in days, if applicable)",
        "type": "number",
        "value": extraction.entity_duration_days or "",
        "placeholder": "e.g. 45"
    })
    
    # 6. Contact Number (Indian number, compulsory)
    fields.append({
        "name": "contact_number",
        "label": "Indian Contact Number (Required for scheduling call)",
        "type": "text",
        "value": extraction.contact_number or "",
        "placeholder": "e.g. 9876543210"
    })
    
    return fields

async def run_chatbot_nlp_extraction(ticket_id: str, raw_text: str, session_id: str):
    try:
        scrubbed_query = scrub_pii(raw_text)
        extraction = await extract_grievance(scrubbed_query)
        db_conn = get_db_connection()
        db_cursor = db_conn.cursor()
        db_cursor.execute("""
        UPDATE grievances SET
            scheme_name = ?,
            grievance_type = ?,
            severity = ?,
            summary_en = ?,
            summary_hi = ?,
            entity_bank = ?,
            entity_amount = ?,
            entity_duration_days = ?,
            contact_number = ?,
            updated_at = ?
        WHERE ticket_id = ?
        """, (
            extraction.scheme_name,
            extraction.grievance_type,
            extraction.severity,
            extraction.summary_en,
            extraction.summary_hi,
            extraction.entity_bank,
            extraction.entity_amount,
            extraction.entity_duration_days,
            extraction.contact_number,
            datetime.now(),
            ticket_id
        ))
        db_conn.commit()
        db_conn.close()
        
        # Log event with extracted metadata
        log_event(
            session_id=session_id or "system",
            event_type="grievance_submit",
            scheme_name=extraction.scheme_name,
            extra={"ticket_id": ticket_id, "severity": extraction.severity, "type": extraction.grievance_type}
        )
    except Exception as e:
        print(f"Background chatbot ticket extraction failed for {ticket_id}: {e}")

# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/grievance/submit")
@limiter.limit("5/minute")
async def grievance_submit(payload: GrievanceSubmit, request: Request, background_tasks: BackgroundTasks):
    # Scrub PII
    scrubbed_query = scrub_pii(payload.query)
    
    # Generate unique ticket number
    next_num = 1
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM grievances")
    next_num = cursor.fetchone()[0] + 1
    conn.close()
    
    ticket_id = f"GRV-{next_num:05d}"
    
    # Insert initially with basic placeholder values so it is registered
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO grievances (
        ticket_id, session_id, scheme_name, grievance_type, severity,
        raw_text, status, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ticket_id,
        payload.session_id,
        payload.scheme_name,
        "Other",
        "Medium",
        scrubbed_query,
        "Open",
        datetime.now()
    ))
    conn.commit()
    conn.close()
    
    # Run heavy extraction in background
    async def run_nlp_extraction(tid: str, query: str):
        try:
            extraction = await extract_grievance(query)
            db_conn = get_db_connection()
            db_cursor = db_conn.cursor()
            db_cursor.execute("""
            UPDATE grievances SET
                scheme_name = ?,
                grievance_type = ?,
                severity = ?,
                summary_en = ?,
                summary_hi = ?,
                entity_bank = ?,
                entity_amount = ?,
                entity_duration_days = ?,
                updated_at = ?
            WHERE ticket_id = ?
            """, (
                extraction.scheme_name,
                extraction.grievance_type,
                extraction.severity,
                extraction.summary_en,
                extraction.summary_hi,
                extraction.entity_bank,
                extraction.entity_amount,
                extraction.entity_duration_days,
                datetime.now(),
                tid
            ))
            db_conn.commit()
            db_conn.close()
            # Log event with extracted metadata
            log_event(
                session_id=payload.session_id or "system",
                event_type="grievance_submit",
                scheme_name=extraction.scheme_name,
                extra={"ticket_id": tid, "severity": extraction.severity, "type": extraction.grievance_type}
            )
        except Exception as e:
            print(f"Background extraction failed for ticket {tid}: {e}")
            
    background_tasks.add_task(run_nlp_extraction, ticket_id, scrubbed_query)
    
    return {"ticket_id": ticket_id}

@app.post("/api/grievance/submit_dynamic")
@limiter.limit("5/minute")
async def grievance_submit_dynamic(payload: GrievanceSubmitDynamic, request: Request):
    # Scrub PII
    scrubbed_query = scrub_pii(payload.raw_text)
    
    # Generate unique sequential ticket number
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM grievances")
    next_num = cursor.fetchone()[0] + 1
    conn.close()
    
    ticket_id = f"TKT-MSME-{next_num:05d}"
    
    # Backfill missing summaries/severity via NLP extraction
    severity = payload.severity or "Medium"
    summary_en = payload.summary_en
    summary_hi = payload.summary_hi
    if not summary_en or not summary_hi:
        try:
            extraction = await extract_grievance(payload.raw_text)
            if not summary_en:
                summary_en = extraction.summary_en
            if not summary_hi:
                summary_hi = extraction.summary_hi
            if not payload.severity or payload.severity == "Medium":
                severity = extraction.severity
        except Exception as e:
            print(f"Failed to run extraction in submit_dynamic: {e}")
            if not summary_en:
                summary_en = payload.raw_text[:200]
            if not summary_hi:
                summary_hi = payload.raw_text[:200]
                
    # Insert in DB
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO grievances (
        ticket_id, session_id, scheme_name, grievance_type, severity,
        raw_text, summary_en, summary_hi, entity_bank, entity_amount,
        entity_duration_days, status, contact_number, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ticket_id,
        payload.session_id,
        payload.scheme_name,
        payload.grievance_type,
        severity,
        scrubbed_query,
        summary_en,
        summary_hi,
        payload.entity_bank,
        payload.entity_amount,
        payload.entity_duration_days,
        "Open",
        payload.contact_number,
        datetime.now()
    ))
    conn.commit()
    conn.close()
    
    # Log event
    log_event(
        session_id=payload.session_id or "system",
        event_type="grievance_submit",
        scheme_name=payload.scheme_name,
        extra={"ticket_id": ticket_id, "severity": severity, "type": payload.grievance_type}
    )
    
    return {"ticket_id": ticket_id, "contact_number": payload.contact_number}

@app.post("/api/grievance/check")
@limiter.limit("5/minute")
async def grievance_check(payload: GrievanceCheck, request: Request):
    row = get_grievance_by_ticket(payload.ticket_id)
    found = row is not None
    status_val = row["status"] if found else "Not Found"
    
    log_event(
        session_id="system",
        event_type="status_check",
        extra={"ticket_id": payload.ticket_id, "found": found}
    )
    
    return {"found": found, "status": status_val}

@app.get("/api/grievance/ticket/{ticket_id}")
@limiter.limit("30/minute")
async def get_grievance_ticket(ticket_id: str, request: Request, username: str = Depends(get_admin_user)):
    row = get_grievance_by_ticket(ticket_id)
    if not row:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return dict(row)

@app.post("/api/language")
async def update_language(payload: LanguagePayload):
    session_id = payload.sessionId
    if session_id not in sessions:
        sessions[session_id] = {
            "last_active": time.time(),
            "messages": [],
            "consent_acknowledged": False,
            "language": payload.language
        }
    else:
        sessions[session_id]["language"] = payload.language
        sessions[session_id]["last_active"] = time.time()
    return {"status": "success", "language": payload.language}

@app.post("/api/chat", response_model=ChatResponse)
@limiter.limit("15/minute")
async def chat_endpoint(payload: ChatRequest, request: Request, background_tasks: BackgroundTasks):
    start_time = time.time()
    agent_used = False
    
    # Occasionally clean up old sessions
    if len(sessions) % 10 == 0:
        clean_old_sessions()
        
    session_id = payload.sessionId
    is_new_session = session_id not in sessions
    
    # Initialize session if it doesn't exist
    if is_new_session:
        sessions[session_id] = {
            "last_active": time.time(),
            "messages": [],
            "consent_acknowledged": False,
            "language": payload.language or "en"
        }
        log_event(session_id=session_id, event_type="session_start")
    
    session = sessions[session_id]
    session["last_active"] = time.time()

    # Dynamic Language Auto-detection & Selection:
    incoming_text = payload.message.strip()
    detected_lang = detect_language(incoming_text)
    
    has_devanagari = any(ord(char) >= 0x0900 and ord(char) <= 0x097F for char in incoming_text)
    has_bengali = any(ord(char) >= 0x0980 and ord(char) <= 0x09FF for char in incoming_text)
    
    current_lang = session.get("language", "en")
    
    if has_devanagari:
        # If input has Devanagari script, switch to Hindi if the current set language is not Devanagari-based
        if current_lang not in ("hi", "bho", "mai"):
            session["language"] = "hi"
    elif has_bengali:
        session["language"] = "ben"
    else:
        # Otherwise, check detected language for English or Bengali
        if detected_lang == "en":
            session["language"] = "en"
        elif detected_lang == "ben":
            session["language"] = "ben"
        elif detected_lang == "hi" and current_lang == "en":
            session["language"] = "hi"
            
    # Respect explicit payload language updates (from frontend dropdown change)
    if payload.language and payload.language != current_lang:
        session["language"] = payload.language
        
    user_lang = session["language"]

    # If regional language, translate input message to Hindi first
    if user_lang in ("bho", "mai", "ben"):
        payload.message = await translate_text(payload.message, user_lang, "hi")
        
    # 1. Content Filtering
    blocked, reason = is_blocked(payload.message)
    if blocked:
        log_event(
            session_id=session_id,
            event_type="blocked_query",
            extra={"message": payload.message[:200], "reason": reason}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This query cannot be processed on this platform."
        )
    
    user_message = payload.message
    user_message_lower = user_message.strip().lower()

    # Reset chat history if a top-level option is clicked
    top_level_intents = [
        "udyam registration", "pmegp loan", "grievance", "mudra loan",
        "उद्यम पंजीकरण", "pmegp ऋण", "शिकायत", "mudra ऋण"
    ]
    if user_message_lower in top_level_intents:
        session["messages"] = []
    
    # 1.5 Active LangGraph Session Checks
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT graph_name, state_json FROM conversation_state WHERE session_id = ?", (session_id,))
    active_graph = cursor.fetchone()
    conn.close()
    
    intercepted = False
    structured = {}
    raw_for_history = ""
    
    if active_graph:
        graph_name = active_graph["graph_name"]
        import json
        state_data = json.loads(active_graph["state_json"])
        
        if graph_name == "eligibility":
            from app.graphs.eligibility_graph import eligibility_graph
            state_data["last_message"] = payload.message
            new_state = eligibility_graph.invoke(state_data)
            
            conn = get_db_connection()
            cursor = conn.cursor()
            if new_state.get("complete"):
                cursor.execute("DELETE FROM conversation_state WHERE session_id = ?", (session_id,))
            else:
                cursor.execute(
                    "UPDATE conversation_state SET state_json = ?, updated_at = ? WHERE session_id = ?",
                    (json.dumps(new_state), datetime.now(), session_id)
                )
            conn.commit()
            conn.close()
            
            title = "Eligibility Questionnaire:"
            structured = {
                "intent": "scheme_guidance",
                "items": [],
                "next_step": f"**{title}**\n\n{new_state.get('reply')}",
                "disclaimer": "Step-by-step guided questionnaire."
            }
            raw_for_history = new_state.get("reply")
            intercepted = True

        elif graph_name == "form_wizard":
            from app.graphs.form_wizard import form_wizard_graph
            state_data["last_message"] = payload.message
            new_state = form_wizard_graph.invoke(state_data)
            
            conn = get_db_connection()
            cursor = conn.cursor()
            if new_state.get("complete"):
                cursor.execute("DELETE FROM conversation_state WHERE session_id = ?", (session_id,))
            else:
                cursor.execute(
                    "UPDATE conversation_state SET state_json = ?, updated_at = ? WHERE session_id = ?",
                    (json.dumps(new_state), datetime.now(), session_id)
                )
            conn.commit()
            conn.close()
            
            title = "Guided Form Wizard:"
            structured = {
                "intent": "registration_help",
                "items": [],
                "next_step": f"**{title}**\n\n{new_state.get('reply')}",
                "disclaimer": "Validating fields in real-time."
            }
            raw_for_history = new_state.get("reply")
            intercepted = True

    # 1.6 LangGraph Trigger keywords
    elif any(kw in payload.message.lower() for kw in ("dhundhna", "find scheme", "check eligibility", "start eligibility", "eligibility check")):
        from app.graphs.eligibility_graph import eligibility_graph
        init_state = {
            "session_id": session_id,
            "answers": {},
            "next_question": None,
            "last_message": "",
            "reply": "",
            "complete": False
        }
        new_state = eligibility_graph.invoke(init_state)
        
        import json
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO conversation_state (thread_id, session_id, graph_name, state_json) VALUES (?, ?, ?, ?)",
            (session_id + "_eligibility", session_id, "eligibility", json.dumps(new_state))
        )
        conn.commit()
        conn.close()
        
        title = "Starting Eligibility Questionnaire:"
        structured = {
            "intent": "scheme_guidance",
            "items": [],
            "next_step": f"**{title}**\n\n{new_state.get('reply')}",
            "disclaimer": "Let's check which schemes match your profile."
        }
        raw_for_history = new_state.get("reply")
        intercepted = True

    elif any(kw in payload.message.lower() for kw in ("form fill", "start wizard", "fill udyam", "fill pmegp", "form wizard")):
        from app.graphs.form_wizard import form_wizard_graph
        init_state = {
            "session_id": session_id,
            "answers": {},
            "next_question": None,
            "last_message": "",
            "error_message": None,
            "reply": "",
            "complete": False
        }
        new_state = form_wizard_graph.invoke(init_state)
        
        import json
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO conversation_state (thread_id, session_id, graph_name, state_json) VALUES (?, ?, ?, ?)",
            (session_id + "_wizard", session_id, "form_wizard", json.dumps(new_state))
        )
        conn.commit()
        conn.close()
        
        title = "Starting Guided Form Wizard:"
        structured = {
            "intent": "registration_help",
            "items": [],
            "next_step": f"**{title}**\n\n{new_state.get('reply')}",
            "disclaimer": "Please enter your details step-by-step."
        }
        raw_for_history = new_state.get("reply")
        intercepted = True

    # 2. Intercept Document Checklist, Comparison, and Udyam status checks
    from app.checklist import get_document_checklist
    from app.comparison import generate_comparison
    from app.status_tracker import track_udyam_status
    import re

    intercepted = False
    structured = {}
    raw_for_history = ""

    # Udyam Status check lookup
    udyam_match = re.search(r'(UDYAM-[A-Z]{2}-\d{2}-\d{7})', payload.message.upper())
    if udyam_match:
        udyam_number = udyam_match.group(1)
        result = track_udyam_status(udyam_number)
        is_hi = (user_lang != "en")
        msg = result["message_hi"] if is_hi else result["message_en"]
        
        title = "Udyam Verification Result:"
        structured = {
            "intent": "faq",
            "items": [
                {
                    "label": "Udyam Number",
                    "detail": result.get("udyam_number", udyam_number),
                    "badge": "Verified" if result["valid"] else "Invalid",
                    "meta": ""
                },
                {
                    "label": "Status",
                    "detail": result["status"],
                    "badge": "Active" if result.get("status") == "Active" else "Error",
                    "meta": ""
                }
            ] if result["valid"] else [],
            "next_step": f"**{title}**\n\n{msg}",
            "disclaimer": "Official verification tool is available at udyamregistration.gov.in"
        }
        raw_for_history = msg
        intercepted = True

    # Document Checklist lookup
    elif any(kw in payload.message.lower() for kw in ("checklist", "document", "दस्तावेज", "कागजात")):
        checklist = get_document_checklist(payload.message)
        if checklist:
            title_desc = f"**{checklist['title']}**\n{checklist['description']}"
            structured = {
                "intent": "faq",
                "items": [
                    {"label": f"Prerequisite {i+1}", "detail": req, "badge": "Required", "meta": ""}
                    for i, req in enumerate(checklist["prerequisites"])
                ] + [
                    {"label": "Common Error", "detail": err, "badge": "Warning", "meta": ""}
                    for err in checklist["common_errors"]
                ],
                "next_step": f"{title_desc}\n\nApply here: {checklist['official_url']}",
                "disclaimer": "Note: Requirements are subject to updates. Check the official portal"
            }
            raw_for_history = f"### {checklist['title']}\n{checklist['description']}\n\nRequired Documents:\n" + "\n".join(f"- {req}" for req in checklist["prerequisites"])
            intercepted = True

    # Comparison lookup
    elif any(kw in payload.message.lower() for kw in ("compare", "difference", "vs", "बनाम", "तुलना", "अंतर")):
        comp = generate_comparison(payload.message)
        if comp:
            items = []
            is_hi = (user_lang != "en")
            title = comp["title_hi"] if is_hi else comp["title_en"]
            
            for p in comp["parameters"]:
                param_name = p["name_hi"] if is_hi else p["name_en"]
                pmegp_val = p.get("pmegp", "")
                mudra_val = p.get("mudra", "")
                cgtmse_val = p.get("cgtmse", "")
                
                detail_parts = []
                if pmegp_val: detail_parts.append(f"**PMEGP:** {pmegp_val}")
                if mudra_val: detail_parts.append(f"**MUDRA:** {mudra_val}")
                if cgtmse_val: detail_parts.append(f"**CGTMSE:** {cgtmse_val}")
                
                items.append({
                    "label": param_name,
                    "detail": "\n\n".join(detail_parts),
                    "badge": "Comparison",
                    "meta": ""
                })
                
            structured = {
                "intent": "scheme_guidance",
                "items": items,
                "next_step": f"**{title}**\n\nWhich of these schemes would you like to explore further?",
                "disclaimer": "Comparisons are for guidance. Always check current portal rules"
            }
            raw_for_history = f"### {title}\n" + "\n".join(f"**{item['label']}**:\n{item['detail']}" for item in items)
            intercepted = True

    if not intercepted:
        # Check if query meets agent trigger conditions
        msg_len = len(payload.message)
        msg_lower = payload.message.lower()
        
        is_grievance = any(kw in msg_lower for kw in ("complain", "problem", "shikayat", "शिकायत", "समस्या"))
        is_status = any(kw in msg_lower for kw in ("ticket", "tkt", "status", "स्थिति")) or "UDYAM-" in payload.message.upper()
        
        schemes = ["udyam", "pmegp", "mudra", "cgtmse", "zed", "gem", "treds", "champions",
                   "उद्यम", "मुद्रा", "ऋण", "योजना"]
        found_schemes = [s for s in schemes if s in msg_lower]
        comparison_words = ["compare", "difference", "vs", "better", "अंतर", "तुलना", "बनाम"]
        has_comparison = any(cw in msg_lower for cw in comparison_words)
        multipart_indicators = ["aur", "and", "also", "bhi", "भी", "और"]
        has_multipart = any(indicator in msg_lower for indicator in multipart_indicators) or msg_lower.count("?") >= 2
        
        if (msg_len > 30) and (not is_grievance) and (not is_status) and (len(found_schemes) >= 2 or has_comparison or has_multipart):
            import asyncio
            try:
                # Run with 15 second timeout
                agent_reply = await asyncio.wait_for(
                    agent_chat(payload.message, session["messages"]),
                    timeout=15.0
                )
                title = "Here is the response from MSME Saathi ReAct Agent:"
                structured = {
                    "intent": "general",
                    "items": [],
                    "next_step": f"**{title}**\n\nLet me know if you have other questions about MSME schemes.",
                    "disclaimer": "This analysis was generated by MSME Saathi ReAct agent",
                    "raw": agent_reply
                }
                raw_for_history = agent_reply
                intercepted = True
                agent_used = True
            except Exception as e:
                print(f"Agent execution failed or timed out: {e}. Falling back to standard pipeline.")

    if not intercepted:
        # Retrieve RAG Context (Bypass ONLY for greetings and general help queries)
        if any(greet in user_message_lower for greet in ["hi", "hello", "hey", "help", "greet", "नमस्ते", "सहायता"]):
            rag_context = ""
        else:
            # If it's a scheme search payload, extract just the values for cleaner semantic search
            rag_query = user_message
            is_scheme_search = False
            if "State of Residence" in user_message and ":" in user_message:
                try:
                    fields = {}
                    clean_msg = user_message.replace('\\n', '\n')
                    for line in clean_msg.split('\n'):
                        if ":" in line:
                            key, _, val = line.partition(":")
                            key = key.strip()
                            val = val.strip()
                            if val and val.lower() not in ('-- select --', ''):
                                fields[key] = val
                    if fields:
                        role = fields.get("Are you a Student or Entrepreneur/Business Owner", "")
                        state = fields.get("State of Residence", "")
                        gender = fields.get("Gender", "")
                        category = fields.get("Social Category (General / SC / ST / OBC / EBC / Minority / PwD)", "")
                        venture = fields.get("Is your business/venture new or existing", "")
                        biz_type = fields.get("Business Type (Manufacturing / Agro / Tech-Innovation / Service / Other)", "")
                        rag_query = (
                            f"{role} from {state}, {gender}, {category} category, "
                            f"{venture} {biz_type} business. "
                            f"Looking for MSME government schemes and financial assistance."
                        )
                        is_scheme_search = True
                except Exception:
                    pass
            
            if is_scheme_search:
                rag_context = retrieve_context(rag_query, k=5)
            else:
                rag_context = retrieve_context(rag_query, k=3)
        
        # Get LLM Response
        structured = get_chat_response(
            user_message=payload.message,
            conversation_history=session["messages"],
            rag_context=rag_context,
            is_voice_mode=payload.isVoiceMode
        )
        raw_for_history = structured.get("raw", str(structured))
    
    # Ticket Generation Interceptor
    next_step_text = (structured.get("next_step") or "").strip()
    disclaimer_text = (structured.get("disclaimer") or "").strip()
    raw_text = (structured.get("raw") or "").strip()
    
    has_generate_ticket = "[GENERATE_TICKET]" in next_step_text or "[GENERATE_TICKET]" in disclaimer_text or "[GENERATE_TICKET]" in raw_text
    if has_generate_ticket:
        # Run NLP extraction synchronously
        extraction = await extract_grievance(user_message)
        
        # Check for missing fields
        missing_fields = get_missing_grievance_fields(extraction)
        
        if not missing_fields:
            # Generate ticket ID sequentially
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM grievances")
            next_num = cursor.fetchone()[0] + 1
            conn.close()
            ticket_id = f"TKT-MSME-{next_num:05d}"
            
            # Save to SQL grievances database synchronously
            register_grievance_in_db(ticket_id, session_id, user_message, extraction)
            
            # Log event
            log_event(
                session_id=session_id or "system",
                event_type="grievance_submit",
                scheme_name=extraction.scheme_name,
                extra={"ticket_id": ticket_id, "severity": extraction.severity, "type": extraction.grievance_type}
            )
            
            # Replace the tag with actual ticket ID in frontend output
            success_message = f"Grievance successfully registered. We will schedule a call for your grievance on your contact number: {extraction.contact_number}. Please remember your Ticket ID: {ticket_id}"
            if "next_step" in structured:
                structured["next_step"] = structured["next_step"].replace("[GENERATE_TICKET]", success_message)
            if "disclaimer" in structured:
                structured["disclaimer"] = structured["disclaimer"].replace("[GENERATE_TICKET]", success_message)
            if "raw" in structured:
                structured["raw"] = structured["raw"].replace("[GENERATE_TICKET]", success_message)
        else:
            # Add dynamic_form payload
            structured["dynamic_form"] = {
                "raw_text": user_message,
                "extracted_data": {
                    "scheme_name": extraction.scheme_name,
                    "grievance_type": extraction.grievance_type,
                    "contact_number": extraction.contact_number,
                    "entity_bank": extraction.entity_bank,
                    "entity_amount": extraction.entity_amount,
                    "entity_duration_days": extraction.entity_duration_days,
                    "summary_en": extraction.summary_en,
                    "summary_hi": extraction.summary_hi,
                    "severity": extraction.severity
                },
                "fields": missing_fields
            }
            # Output instruction message for form filling
            instruction_message = "Please review and complete the grievance form below to register your ticket:"
            if "next_step" in structured:
                structured["next_step"] = structured["next_step"].replace("[GENERATE_TICKET]", instruction_message)
            if "disclaimer" in structured:
                structured["disclaimer"] = structured["disclaimer"].replace("[GENERATE_TICKET]", instruction_message)
            if "raw" in structured:
                structured["raw"] = structured["raw"].replace("[GENERATE_TICKET]", instruction_message)
            
    # Ticket Checking Interceptor
    has_check_ticket = "[CHECK_TICKET" in next_step_text or "[CHECK_TICKET" in disclaimer_text or "[CHECK_TICKET" in raw_text
    if has_check_ticket:
        match = None
        for text in [next_step_text, disclaimer_text, raw_text]:
            m = re.search(r'\[CHECK_TICKET:\s*(.+?)\]', text)
            if m:
                match = m
                break
        if match:
            ticket_id_to_check = match.group(1).strip()
            row = get_grievance_by_ticket(ticket_id_to_check)
            
            if row:
                status_message = f"Issue status is currently: {row['status']}."
            else:
                status_message = "Ticket not found in the database. Please verify the number."
                
            if "next_step" in structured:
                structured["next_step"] = structured["next_step"].replace(match.group(0), status_message)
            if "disclaimer" in structured:
                structured["disclaimer"] = structured["disclaimer"].replace(match.group(0), status_message)
            if "raw" in structured:
                structured["raw"] = structured["raw"].replace(match.group(0), status_message)
    
    raw_for_history = structured.get("raw", str(structured))
    
    # Update Conversation History (saves Hindi/English version)
    scrubbed_user_message = scrub_pii(payload.message)
    session["messages"].append({"role": "user", "content": scrubbed_user_message})
    session["messages"].append({"role": "assistant", "content": raw_for_history})
    
    if len(session["messages"]) > 20:
        session["messages"] = session["messages"][-20:]

    # Translate reply and structured fields for the client if target language is regional or Hindi
    reply_to_return = raw_for_history
    if user_lang in ("hi", "bho", "mai", "ben"):
        detected_src = detect_language(raw_for_history)
        src_lang = "hi" if detected_src == "hi" else "en"
        
        reply_to_return = await translate_text(raw_for_history, src_lang, user_lang)
        
        # Translate each text key in structured dict
        if "next_step" in structured and structured["next_step"]:
            structured["next_step"] = await translate_text(structured["next_step"], src_lang, user_lang)
        if "disclaimer" in structured and structured["disclaimer"]:
            structured["disclaimer"] = await translate_text(structured["disclaimer"], src_lang, user_lang)
        if "raw" in structured and structured["raw"]:
            # Do not translate SHOW_WELCOME_CARDS identifier tag
            if "SHOW_WELCOME_CARDS" not in structured["raw"]:
                structured["raw"] = await translate_text(structured["raw"], src_lang, user_lang)
        if "items" in structured and structured["items"]:
            for item in structured["items"]:
                if "label" in item and item["label"] and "SHOW_WELCOME_CARDS" not in item["label"]:
                    item["label"] = await translate_text(item["label"], src_lang, user_lang)
                if "detail" in item and item["detail"]:
                    item["detail"] = await translate_text(item["detail"], src_lang, user_lang)
                if "meta" in item and item["meta"]:
                    item["meta"] = await translate_text(item["meta"], src_lang, user_lang)
        if "actions" in structured and structured["actions"]:
            translated_actions = []
            for action in structured["actions"]:
                translated_actions.append(await translate_text(action, src_lang, user_lang))
            structured["actions"] = translated_actions
            
        if "dynamic_form" in structured:
            df_data = structured["dynamic_form"]
            if "fields" in df_data:
                for field in df_data["fields"]:
                    if "label" in field and field["label"]:
                        field["label"] = await translate_text(field["label"], src_lang, user_lang)
                    if "placeholder" in field and field["placeholder"]:
                        field["placeholder"] = await translate_text(field["placeholder"], src_lang, user_lang)
                    if "options" in field and field["options"]:
                        for opt in field["options"]:
                            if isinstance(opt, dict) and "label" in opt:
                                opt["label"] = await translate_text(opt["label"], src_lang, user_lang)
        
    # Log event
    elapsed_ms = int((time.time() - start_time) * 1000)
    extra_data = {"agent_used": True} if agent_used else {}
    log_event(
        session_id=session_id,
        event_type="message",
        intent=structured.get("intent", "general"),
        response_ms=elapsed_ms,
        user_agent=request.headers.get("user-agent", "unknown"),
        extra=extra_data
    )
        
    return ChatResponse(reply=reply_to_return, structured=structured, sessionId=session_id, language=user_lang)

@app.get("/api/health")
@limiter.limit("30/minute")
async def health_check(request: Request):
    return {"status": "ok"}

@app.post("/tts")
@limiter.limit("20/minute")
async def play_tts(payload: TTSRequest, request: Request):
    import io
    audio = await get_tts_audio(payload.text, payload.language)
    if audio:
        log_event(
            session_id=payload.session_id,
            event_type="tts_play",
            language=payload.language,
            extra={"text_len": len(payload.text)}
        )
        return StreamingResponse(io.BytesIO(audio), media_type="audio/mpeg")
    else:
        return Response(status_code=204)

# ---------------------------------------------------------------------------
# Admin & Internal APIs
# ---------------------------------------------------------------------------

@app.post("/admin/documents/ingest")
async def admin_documents_ingest(request: Request, username: str = Depends(get_admin_user)):
    """
    Ingests all text and PDF files in data/documents/ into ChromaDB.
    """
    docs_dir = os.path.join(os.path.dirname(__file__), "data", "documents")
    if not os.path.exists(docs_dir):
        os.makedirs(docs_dir, exist_ok=True)
        return {"status": "ok", "document_count": 0, "message": "Directory was empty"}
        
    from pypdf import PdfReader
    
    files = [f for f in os.listdir(docs_dir) if f.endswith(".txt") or f.endswith(".pdf")]
    
    # Reset / clear collection
    try:
        chroma_client.delete_collection(name="bihar_msme_schemes")
    except Exception:
        pass
    
    new_collection = chroma_client.create_collection(name="bihar_msme_schemes")
    
    chunk_size = 600
    overlap = 80
    total_chunks_added = 0
    
    for f in files:
        file_path = os.path.join(docs_dir, f)
        text = ""
        
        # Read text
        if f.endswith(".txt"):
            with open(file_path, "r", encoding="utf-8", errors="ignore") as file_obj:
                text = file_obj.read()
        elif f.endswith(".pdf"):
            try:
                reader = PdfReader(file_path)
                for page in reader.pages:
                    text_content = page.extract_text()
                    if text_content:
                        text += text_content + "\n"
            except Exception as pdf_err:
                print(f"Error reading PDF {f}: {pdf_err}")
                continue
                
        if not text.strip():
            continue
            
        # Extract scheme name from first line
        first_line = text.split("\n")[0].strip()
        scheme_name = first_line[:100] if len(first_line) > 0 else "Unknown Scheme"
        
        # Simple boundary-based splitter (split on Hindi '।' and English '.')
        sentences = re.split(r"([।\.\n])", text)
        chunks = []
        current_chunk = ""
        
        for part in sentences:
            if len(current_chunk) + len(part) < chunk_size:
                current_chunk += part
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                # Start new chunk with overlap
                current_chunk = current_chunk[-overlap:] + part if len(current_chunk) > overlap else part
                
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
            
        # Add to ChromaDB
        ids = [f"{f}_chunk_{idx}" for idx in range(len(chunks))]
        metadatas = [{"source": f, "scheme_name": scheme_name, "chunk_index": idx} for idx in range(len(chunks))]
        
        if chunks:
            new_collection.add(
                documents=chunks,
                ids=ids,
                metadatas=metadatas
            )
            total_chunks_added += len(chunks)
            log_event(
                session_id="admin",
                event_type="document_ingest",
                scheme_name=scheme_name,
                extra={"filename": f, "chunks": len(chunks)}
            )
            
    return {"status": "ok", "document_count": total_chunks_added}

@app.get("/internal/session-stats")
async def get_internal_session_stats(request: Request):
    # Enforce localhost-only via IP check
    client_ip = request.client.host
    if client_ip not in ("127.0.0.1", "localhost", "::1"):
        raise HTTPException(status_code=403, detail="Access denied. Localhost only.")
        
    active_sessions_count = len(sessions)
    
    # Calculate total messages today from database
    total_messages_today = 0
    oldest_session_age = 0
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM events WHERE event_type = 'message' AND date(timestamp) = date('now')")
        total_messages_today = cursor.fetchone()[0]
    except Exception:
        pass
    finally:
        conn.close()
        
    if sessions:
        oldest_time = min(data["last_active"] for data in sessions.values())
        oldest_session_age = int((time.time() - oldest_time) / 60)
        
    sessions_list = []
    if sessions:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            for sid, data in sessions.items():
                # Retrieve language from events table or default to 'en'
                lang = "en"
                try:
                    cursor.execute("SELECT language FROM events WHERE session_id = ? AND language IS NOT NULL ORDER BY timestamp DESC LIMIT 1", (sid,))
                    row = cursor.fetchone()
                    if row:
                        lang = row["language"]
                except Exception:
                    pass
                
                sessions_list.append({
                    "session_id": sid,
                    "started_at": datetime.fromtimestamp(data.get("last_active", time.time())).strftime('%Y-%m-%d %H:%M:%S'), # fallback start
                    "message_count": len(data.get("messages", [])),
                    "last_active": datetime.fromtimestamp(data.get("last_active", time.time())).strftime('%Y-%m-%d %H:%M:%S'),
                    "language": lang
                })
        finally:
            conn.close()
            
    return {
        "active_sessions": active_sessions_count,
        "total_messages_today": total_messages_today,
        "oldest_session_age_minutes": oldest_session_age,
        "sessions": sessions_list
    }

@app.delete("/internal/session/{session_id}")
async def delete_session_endpoint(session_id: str, request: Request):
    if session_id in sessions:
        del sessions[session_id]
        return {"status": "ok", "message": f"Session {session_id} terminated"}
    raise HTTPException(status_code=404, detail="Session not found")

# ---------------------------------------------------------------------------
# Static File Serving
# ---------------------------------------------------------------------------
# Serve frontend files from the project root directory.
app.mount("/static", StaticFiles(directory=".", html=False), name="static")

@app.get("/")
@limiter.limit("30/minute")
async def serve_index(request: Request):
    return FileResponse("index.html")

@app.get("/{filename}")
@limiter.limit("30/minute")
async def serve_file(filename: str, request: Request):
    if filename in ["style.css", "app.js", "favicon.ico"]:
        if os.path.exists(filename):
            return FileResponse(filename)
    return FileResponse("index.html")

# ---------------------------------------------------------------------------
# Startup Event
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    # Initialize SQLite database
    init_db()
    
    print(r"""
  __  __  _____ __  __  _____   ____                  _     _ _ 
 |  \/  |/ ____|  \/  |/ ____| / ___|  __ _  __ _| |_| |__ (_) |
 | \  / | (___ | \  / | (___   \___ \ / _` |/ _` | __| '_ \| | |
 | |\/| |\___ \| |\/| |\___ \   ___) | (_| | (_| | |_| | | | | |
 |_|  |_|_____/|_|  |_|_____/  |____/ \__,_|\__,_|\__|_| |_|_|_|
                                                                
    Bilingual Citizen Voice Chatbot Backend Started (FastAPI)
    """)
