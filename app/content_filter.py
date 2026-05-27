import re

BLOCKED_PATTERNS = [
    # 1. System Prompt Override/Jailbreak attempts
    (r"ignore (all )?previous instructions", "Prompt override attempt detected"),
    (r"ignore the instructions above", "Prompt override attempt detected"),
    (r"act as a ", "Roleplay attempt detected"),
    (r"you are now a ", "Roleplay attempt detected"),
    (r"jailbreak", "Jailbreak attempt detected"),
    (r"system prompt", "System prompt access attempt detected"),
    (r"reveal your instructions", "System prompt access attempt detected"),
    
    # 2. Aadhaar/PAN extraction attempts
    (r"tell me aadhaar", "PII extraction attempt"),
    (r"show all data", "Data dump attempt"),
    (r"show all grievances", "Data dump attempt"),
    (r"show database", "Data dump attempt"),
    (r"select \* from", "SQL injection attempt"),
    (r"get all records", "Data dump attempt"),
    (r"aadhaar number batayein", "PII extraction attempt"),
    (r"pan card details dikhao", "PII extraction attempt"),
    
    # 3. Election/political content (Hindi + English)
    (r"\belection(s)?\b", "Political/election content is not permitted"),
    (r"\bvote(s|r|rs)?\b", "Political/election content is not permitted"),
    (r"\bpolitician(s)?\b", "Political/election content is not permitted"),
    (r"\bpolitical party\b", "Political/election content is not permitted"),
    (r"\bchunav\b", "Political/election content is not permitted"),
    (r"\bmatdan\b", "Political/election content is not permitted"),
    (r"\bnetaji\b", "Political/election content is not permitted"),
    (r"\brajnitik\b", "Political/election content is not permitted"),
    (r"\brajniti\b", "Political/election content is not permitted"),
    (r"\bmodi\b", "Political content is not permitted"),
    (r"\brahul gandhi\b", "Political content is not permitted"),
    (r"\bkejriwal\b", "Political content is not permitted"),
    (r"\bbjp\b", "Political content is not permitted"),
    (r"\bcongress\b", "Political content is not permitted"),
    (r"\bjdu\b", "Political content is not permitted"),
    (r"\brjd\b", "Political content is not permitted"),
    (r"\bsarkari sarkar\b", "Political content is not permitted"),
    
    # 4. Caste-violence/incitement (Hindi + English)
    (r"\bcaste violence\b", "Caste-based incitement is not permitted"),
    (r"\bjaati vaad\b", "Caste-based incitement is not permitted"),
    (r"\bjaativad\b", "Caste-based incitement is not permitted"),
    (r"\bdang(a|ey)?\b", "Violence incitement is not permitted"),
    (r"\briot(s)?\b", "Violence incitement is not permitted"),
    (r"\bviolence\b", "Violence/incitement is not permitted"),
    (r"\bhinsa\b", "Violence/incitement is not permitted"),
    (r"\bmaar pit\b", "Violence/incitement is not permitted"),
    (r"\bjaati dangey\b", "Caste-based violence is not permitted")
]

def is_blocked(text: str) -> tuple[bool, str]:
    """
    Checks if a user query matches any of the blocked patterns.
    Returns (True, reason) if blocked, otherwise (False, "").
    """
    if not text:
        return False, ""
    
    text_lower = text.strip().lower()
    
    for pattern, reason in BLOCKED_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True, reason
            
    return False, ""
