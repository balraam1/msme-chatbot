# app/graphs/form_wizard.py
import re
from typing import TypedDict, Dict, Optional, List, Any
from langgraph.graph import StateGraph, START, END

# Define state schema
class WizardState(TypedDict):
    session_id: str
    answers: Dict[str, str]
    next_question: Optional[str]
    last_message: str
    error_message: Optional[str]
    reply: str
    complete: bool

def validate_field(field: str, value: str) -> tuple[bool, str]:
    """
    Validates field values (email, phone, Aadhaar, PAN).
    Returns (is_valid, error_message).
    """
    val = value.strip()
    if field == "name":
        if len(val) < 2:
            return False, "Name should be at least 2 characters."
        return True, ""
    
    elif field == "email":
        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(pattern, val):
            return False, "Invalid email address format. (e.g. name@domain.com)"
        return True, ""
        
    elif field == "phone":
        pattern = r"^\d{10}$"
        if not re.match(pattern, val):
            return False, "Phone number must be exactly 10 digits."
        return True, ""
        
    elif field == "aadhaar":
        pattern = r"^\d{12}$"
        if not re.match(pattern, val):
            return False, "Aadhaar number must be exactly 12 digits."
        return True, ""
        
    elif field == "pan":
        pattern = r"^[A-Z]{5}\d{4}[A-Z]{1}$"
        if not re.match(pattern, val.upper()):
            return False, "PAN number must be in standard format (e.g., ABCDE1234F)."
        return True, ""
        
    return True, ""

def check_next_question(state: WizardState) -> WizardState:
    answers = state.get("answers", {})
    required = ["name", "email", "phone", "aadhaar", "pan"]
    
    prompts = {
        "name": "Please enter the Applicant Name:",
        "email": "Please enter your Email Address:",
        "phone": "Please enter your 10-digit Phone Number:",
        "aadhaar": "Please enter your 12-digit Aadhaar Number:",
        "pan": "Please enter your 10-character PAN Number:"
    }
    
    # If there is an active error, repeat the current question with the error prepended
    error_msg = state.get("error_message")
    current_q = state.get("next_question")
    
    if error_msg and current_q:
        return {
            **state,
            "reply": f"{error_msg}\n\n{prompts[current_q]}",
            "error_message": None,
            "complete": False
        }
    
    for field in required:
        if not answers.get(field):
            return {
                **state,
                "next_question": field,
                "reply": prompts[field],
                "error_message": None,
                "complete": False
            }
            
    return {
        **state,
        "next_question": None,
        "complete": True
    }

def process_answer(state: WizardState) -> WizardState:
    answers = state.get("answers", {}).copy()
    current_q = state.get("next_question")
    user_input = state.get("last_message", "").strip()
    
    if current_q and user_input:
        # Validate input
        is_valid, err_msg = validate_field(current_q, user_input)
        if is_valid:
            answers[current_q] = user_input.upper() if current_q == "pan" else user_input
            return {
                **state,
                "answers": answers,
                "last_message": "",
                "error_message": None
            }
        else:
            return {
                **state,
                "last_message": "",
                "error_message": err_msg
            }
            
    return {
        **state,
        "last_message": ""
    }

def generate_summary(state: WizardState) -> WizardState:
    answers = state.get("answers", {})
    # Anonymize sensitive fields in final success card except last 4 digits
    aadhaar_masked = "XXXX-XXXX-" + answers.get("aadhaar", "")[-4:]
    pan_masked = "XXXXX" + answers.get("pan", "")[-5:]
    
    summary = (
        f"### Form Validation Success\n\n"
        f"Here are your validated details (securely processed):\n"
        f"Applicant Name: **{answers.get('name')}**\n"
        f"Email: **{answers.get('email')}**\n"
        f"Phone Number: **{answers.get('phone')}**\n"
        f"Aadhaar Number: **{aadhaar_masked}**\n"
        f"PAN Number: **{pan_masked}**\n\n"
        f"Verification is complete. You can now download the pre-filled questionnaire template or schedule an appointment with a District Industries Centre officer."
    )
    
    return {
        **state,
        "reply": summary,
        "complete": True
    }

# Build workflow
workflow = StateGraph(WizardState)
workflow.add_node("check_next", check_next_question)
workflow.add_node("process", process_answer)
workflow.add_node("summary", generate_summary)

workflow.add_edge(START, "check_next")

def route_next(state: WizardState):
    if state.get("complete"):
        return "summary"
    else:
        return END

workflow.add_conditional_edges("check_next", route_next, {
    "summary": "summary",
    END: END
})
workflow.add_edge("process", "check_next")
workflow.add_edge("summary", END)

form_wizard_graph = workflow.compile()
