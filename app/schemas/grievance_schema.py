import re
from typing import Literal, Optional
from pydantic import BaseModel, Field

class GrievanceExtraction(BaseModel):
    grievance_type: Literal["Loan Delay", "Rejection", "Portal Error", "Documentation Issue", "Harassment", "Other"] = Field(
        ..., description="The primary type of grievance. Choose 'Other' if it doesn't fit the rest."
    )
    scheme_name: Literal["PMEGP", "MUDRA", "Udyam", "PM SVANidhi", "CGTMSE", "Other"] = Field(
        ..., description="The name of the government scheme. Choose 'Other' if not specified or different."
    )
    severity: Literal["Low", "Medium", "High", "Critical"] = Field(
        default="Medium", description="The calculated urgency or severity of the grievance."
    )
    entity_bank: Optional[str] = Field(
        None, description="Name of the bank or financial institution involved, if mentioned."
    )
    entity_amount: Optional[str] = Field(
        None, description="The loan or subsidy amount mentioned, if any."
    )
    entity_duration_days: Optional[int] = Field(
        None, description="Number of days the application has been delayed or pending, if mentioned."
    )
    summary_en: str = Field(
        ..., description="A one-sentence summary of the citizen complaint in plain English."
    )
    summary_hi: str = Field(
        ..., description="A one-sentence summary of the citizen complaint in plain conversational Hindi (Devanagari script)."
    )
    contact_number: Optional[str] = Field(
        None, description="The user's Indian contact number (10 digits), if mentioned in raw text."
    )

def calculate_initial_severity(
    raw_text: str,
    duration_days: Optional[int] = None,
    amount_str: Optional[str] = None
) -> str:
    """
    Applies baseline severity auto-scoring rules before invoking Gemini.
    """
    text_lower = raw_text.lower()
    
    # 1. Keywords ["court", "FIR", "police"] -> Critical
    critical_keywords = ["court", "fir", "police", "न्यायालय", "पुलिस", "मुकदमा", "एफआईआर"]
    if any(kw in text_lower for kw in critical_keywords):
        return "Critical"
        
    # 2. duration_days > 90 -> Critical
    if duration_days is not None and duration_days > 90:
        return "Critical"
        
    # 3. duration_days > 30 -> High
    if duration_days is not None and duration_days > 30:
        return "High"
        
    # 4. amount mentioned > "10 lakh" -> High
    # Simple regex parsing for amounts like "10 lakh", "15 lakh", "1 crore", "50 lakh" etc.
    amount_high_match = False
    if amount_str:
        amt_lower = amount_str.lower()
        if "crore" in amt_lower or "करोड़" in amt_lower or "cr" in amt_lower:
            amount_high_match = True
        else:
            # Look for numbers >= 10 followed by lakh
            match = re.search(r"(\d+)\s*(lakh|lacs|लाख)", amt_lower)
            if match and int(match.group(1)) >= 10:
                amount_high_match = True
    
    if amount_high_match:
        return "High"
        
    return "Medium"

# Define the Gemini function declaration dict matching the schema
extract_grievance_fields = {
    "name": "extract_grievance_fields",
    "description": "Extract structured information from an Indian MSME citizen grievance or complaint.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "grievance_type": {
                "type": "STRING",
                "enum": ["Loan Delay", "Rejection", "Portal Error", "Documentation Issue", "Harassment", "Other"],
                "description": "The category of the complaint."
            },
            "scheme_name": {
                "type": "STRING",
                "enum": ["PMEGP", "MUDRA", "Udyam", "PM SVANidhi", "CGTMSE", "Other"],
                "description": "The target government scheme."
            },
            "severity": {
                "type": "STRING",
                "enum": ["Low", "Medium", "High", "Critical"],
                "description": "The urgency/severity of the issue."
            },
            "entity_bank": {
                "type": "STRING",
                "description": "Name of the bank involved, or null if none."
            },
            "entity_amount": {
                "type": "STRING",
                "description": "Amount mentioned in the query (e.g. '₹15 Lakh'), or null."
            },
            "entity_duration_days": {
                "type": "INTEGER",
                "description": "Estimated duration of delay/pending status in days, or null."
            },
            "summary_en": {
                "type": "STRING",
                "description": "One-sentence summary in English."
            },
            "summary_hi": {
                "type": "STRING",
                "description": "One-sentence summary in Hindi (Devanagari script)."
            },
            "contact_number": {
                "type": "STRING",
                "description": "The user's 10-digit Indian mobile number, or null if not mentioned."
            }
        },
        "required": ["grievance_type", "scheme_name", "severity", "summary_en", "summary_hi"]
    }
}
