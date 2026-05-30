import os
import re
import json
import asyncio
import google.generativeai as genai
from typing import Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app.schemas.grievance_schema import GrievanceExtraction, extract_grievance_fields, calculate_initial_severity
from app.db import get_db_connection
from app.privacy import scrub_pii

# Ensure Gemini is configured
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    print("Warning: GEMINI_API_KEY environment variable is missing in grievance.py")

async def extract_grievance(raw_text: str) -> GrievanceExtraction:
    """
    Calls Gemini 2.5 Flash to extract structured fields from the citizen grievance
    using function calling.
    """
    try:
        # Pre-flight severity scoring: parse duration or amount if we can easily see it
        # Try to find number of days or months
        duration_days = None
        duration_match = re.search(r"(\d+)\s*(mahine|mahina|month|months|saal|year|years|din|days|days old)", raw_text, re.IGNORECASE)
        if duration_match:
            val = int(duration_match.group(1))
            unit = duration_match.group(2).lower()
            if "mahine" in unit or "mahina" in unit or "month" in unit:
                duration_days = val * 30
            elif "saal" in unit or "year" in unit:
                duration_days = val * 365
            else:
                duration_days = val
                
        # Try to find amount
        amount_match = re.search(r"(\d+)\s*(lakh|lacs|laakh|crore|cr|लाख|करोड़)", raw_text, re.IGNORECASE)
        amount_str = amount_match.group(0) if amount_match else None
        
        initial_severity = calculate_initial_severity(raw_text, duration_days, amount_str)
        
        # Build prompt
        prompt = f"""You are a grievance classification system for Indian MSME schemes.
Extract structured information from this citizen complaint.
The text may be in Hindi, English, or Hinglish.
Respond ONLY by calling the extract_grievance_fields function.

Text: {raw_text}"""
        
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            tools=[extract_grievance_fields]
        )
        
        # Call Gemini in an executor to keep it async
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: model.generate_content(
                prompt,
                tool_config={"function_calling_config": {"mode": "ANY", "allowed_function_names": ["extract_grievance_fields"]}}
            )
        )
        
        # Parse the function call
        candidate = response.candidates[0]
        function_call = candidate.content.parts[0].function_call
        args = dict(function_call.args)
        
        # Ensure severity is at least the initial pre-scored severity (or let Gemini override if it's higher)
        gemini_severity = args.get("severity", "Medium")
        severity_order = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}
        if severity_order.get(initial_severity, 2) > severity_order.get(gemini_severity, 2):
            args["severity"] = initial_severity
            
        # If duration or amount is not populated by Gemini but we found it, backfill
        if not args.get("entity_duration_days") and duration_days:
            args["entity_duration_days"] = duration_days
        if not args.get("entity_amount") and amount_str:
            args["entity_amount"] = amount_str
            
        return GrievanceExtraction(
            grievance_type=args.get("grievance_type", "Other"),
            scheme_name=args.get("scheme_name", "Other"),
            severity=args.get("severity", "Medium"),
            entity_bank=args.get("entity_bank"),
            entity_amount=args.get("entity_amount"),
            entity_duration_days=args.get("entity_duration_days"),
            summary_en=args.get("summary_en", raw_text[:200]),
            summary_hi=args.get("summary_hi", raw_text[:200]),
            contact_number=args.get("contact_number")
        )
        
    except Exception as e:
        print(f"Grievance extraction error: {e}")
        # Default fallback
        summary = raw_text[:200]
        return GrievanceExtraction(
            grievance_type="Other",
            scheme_name="Other",
            severity="Medium",
            entity_bank=None,
            entity_amount=None,
            entity_duration_days=None,
            summary_en=summary,
            summary_hi=summary,
            contact_number=None
        )

def register_grievance_in_db(
    ticket_id: str,
    session_id: Optional[str],
    raw_text: str,
    extraction: GrievanceExtraction
) -> bool:
    """Writes the PII-scrubbed grievance details to the SQLite database."""
    scrubbed_text = scrub_pii(raw_text)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO grievances (
            ticket_id, session_id, scheme_name, grievance_type, severity,
            raw_text, summary_en, summary_hi, entity_bank, entity_amount,
            entity_duration_days, status, contact_number, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticket_id,
            session_id,
            extraction.scheme_name,
            extraction.grievance_type,
            extraction.severity,
            scrubbed_text,
            extraction.summary_en,
            extraction.summary_hi,
            extraction.entity_bank,
            extraction.entity_amount,
            extraction.entity_duration_days,
            "Open",
            extraction.contact_number,
            datetime.now()
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Failed to insert grievance into DB: {e}")
        return False
    finally:
        conn.close()

def get_grievance_by_ticket(ticket_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a grievance detail row by ticket ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM grievances WHERE ticket_id = ?", (ticket_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()
