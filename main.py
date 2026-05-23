import os
import time
from typing import Dict, List, Optional
from pydantic import BaseModel
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from datetime import datetime
from app.knowledge_base import retrieve_context
from app.llm import get_chat_response

# ---------------------------------------------------------------------------
# FastAPI App Initialization
# ---------------------------------------------------------------------------
app = FastAPI(title="MSME Saathi API", description="Backend for MSME Saathi Chatbot")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# State Management (In-Memory Session Store)
# ---------------------------------------------------------------------------
# Store conversation history per session ID.
# Format: { "session_id": { "last_active": timestamp, "messages": [...] } }
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

class ChatResponse(BaseModel):
    reply: str
    structured: dict
    sessionId: str

class GrievanceSubmit(BaseModel):
    scheme_name: str
    query: str

class GrievanceCheck(BaseModel):
    ticket_id: str

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/grievance/submit")
async def grievance_submit(request: GrievanceSubmit):
    next_num = 0
    if os.path.exists("grievances.txt"):
        with open("grievances.txt", "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    next_num += 1
    ticket_id = f"GRV-{next_num+1:05d}"
    with open("grievances.txt", "a", encoding="utf-8") as f:
        f.write(f"{ticket_id}|{request.scheme_name}|{request.query}|Register Complaint|{datetime.now()}\n")
    return {"ticket_id": ticket_id}

@app.post("/api/grievance/check")
async def grievance_check(request: GrievanceCheck):
    found = False
    if os.path.exists("grievances.txt"):
        with open("grievances.txt", "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    parts = line.split("|")
                    if parts[0].strip().lower() == request.ticket_id.strip().lower():
                        found = True
                        break
    return {"found": found}

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    # Occasionally clean up old sessions
    if len(sessions) % 10 == 0:
        clean_old_sessions()
        
    session_id = request.sessionId
    
    # Initialize session if it doesn't exist
    if session_id not in sessions:
        sessions[session_id] = {
            "last_active": time.time(),
            "messages": []
        }
    
    session = sessions[session_id]
    session["last_active"] = time.time()
    
    user_message = request.message
    user_message_lower = user_message.strip().lower()

    # 2. Reset chat history if a top-level option is clicked
    top_level_intents = [
        "udyam registration", "pmegp loan", "grievance", "mudra loan",
        "उद्यम पंजीकरण", "pmegp ऋण", "शिकायत", "mudra ऋण"
    ]
    if user_message_lower in top_level_intents:
        session["messages"] = []
    
    # 1. Retrieve RAG Context (Bypass for Udyam and general help queries)
    if "udyam" in user_message_lower or "उद्यम" in user_message:
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
    
    # 2. Get LLM Response (now returns a structured dict)
    structured = get_chat_response(
        user_message=request.message,
        conversation_history=session["messages"],
        rag_context=rag_context,
        is_voice_mode=request.isVoiceMode
    )
    
    # 3. Ticket Generation Interceptor
    next_step_text = structured.get("next_step", "").strip()
    if "[GENERATE_TICKET]" in next_step_text:
        import random
        from datetime import datetime
        
        # Generate ticket ID
        ticket_id = f"TKT-MSME-{random.randint(100000, 999999)}"
        
        # Save to database file
        with open("grievances.txt", "a", encoding="utf-8") as f:
            f.write(f"--- TICKET: {ticket_id} ---\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Raw Grievance Text: {user_message}\n")
            f.write("\n")
            
        # Replace the tag with actual ticket ID in frontend output
        success_message = f"Grievance successfully registered. Please remember your Ticket ID: {ticket_id}"
        structured["next_step"] = next_step_text.replace("[GENERATE_TICKET]", success_message)
        
        # Replace tag in raw output for history logging
        if "raw" in structured:
            structured["raw"] = structured["raw"].replace("[GENERATE_TICKET]", success_message)
            
    # 4. Ticket Checking Interceptor
    if "[CHECK_TICKET" in next_step_text:
        import re
        import os
        match = re.search(r'\[CHECK_TICKET:\s*(.+?)\]', next_step_text)
        if match:
            ticket_id_to_check = match.group(1).strip()
            ticket_found = False
            if os.path.exists("grievances.txt"):
                with open("grievances.txt", "r", encoding="utf-8") as f:
                    content = f.read()
                    if f"--- TICKET: {ticket_id_to_check} ---" in content:
                        ticket_found = True
            
            if ticket_found:
                status_message = "Issue being resolved currently."
            else:
                status_message = "Ticket not found in the database. Please verify the number."
                
            structured["next_step"] = next_step_text.replace(match.group(0), status_message)
            if "raw" in structured:
                structured["raw"] = structured["raw"].replace(match.group(0), status_message)
    
    # Store raw string in session history (not the dict)
    raw_for_history = structured.get("raw", str(structured))
    
    # 3. Update Conversation History (Keep only the last 20 messages to save context)
    session["messages"].append({"role": "user", "content": user_message})
    session["messages"].append({"role": "assistant", "content": raw_for_history})
    
    if len(session["messages"]) > 20:
        session["messages"] = session["messages"][-20:]
        
    return ChatResponse(reply=raw_for_history, structured=structured, sessionId=session_id)

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

# ---------------------------------------------------------------------------
# Static File Serving
# ---------------------------------------------------------------------------
# Serve frontend files from the project root directory.
# This should come AFTER the API routes so it doesn't shadow them.
app.mount("/static", StaticFiles(directory=".", html=False), name="static")

@app.get("/")
async def serve_index():
    return FileResponse("index.html")

@app.get("/{filename}")
async def serve_file(filename: str):
    # Simple explicit serving for our main frontend files
    if filename in ["style.css", "app.js", "favicon.ico"]:
        if os.path.exists(filename):
            return FileResponse(filename)
    return FileResponse("index.html")

# ---------------------------------------------------------------------------
# Startup Display
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    print(r"""
  __  __  _____ __  __  _____   ____                  _     _ _ 
 |  \/  |/ ____|  \/  |/ ____| / ___|  __ _  __ _| |_| |__ (_) |
 | \  / | (___ | \  / | (___   \___ \ / _` |/ _` | __| '_ \| | |
 | |\/| |\___ \| |\/| |\___ \   ___) | (_| | (_| | |_| | | | | |
 |_|  |_|_____/|_|  |_|_____/  |____/ \__,_|\__,_|\__|_| |_|_|_|
                                                                
    Bilingual Citizen Voice Chatbot Backend Started (FastAPI)
    """)
