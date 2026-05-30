import os
import re
from typing import List, Dict, Optional
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from .system_prompt import SYSTEM_PROMPT

client_initialized = False
model: Optional[genai.GenerativeModel] = None

def init_client():
    global client_initialized, model
    if not client_initialized:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("Warning: GEMINI_API_KEY is not set.")
        else:
            genai.configure(api_key=api_key)
            
            # Configure the model
            generation_config = {
                "temperature": 0.3,
                "top_p": 0.9,
                "max_output_tokens": 4096,
            }
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
            
            model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                generation_config=generation_config,
                safety_settings=safety_settings,
                system_instruction=SYSTEM_PROMPT
            )
        client_initialized = True


def _make_error_dict(msg: str) -> dict:
    """Wraps an error string into the structured response dict format."""
    return {
        "items": [],
        "disclaimer": None,
        "next_step": msg,
        "actions": [],
        "raw": msg
    }


def parse_structured_response(raw: str) -> dict:
    """
    Parses the LLM's structured markdown output into a dict for frontend rendering.
    Returns:
    {
      "items": [{"label": str, "badge": str, "detail": str, "meta": str}],
      "disclaimer": str | None,
      "next_step": str,
      "actions": [str, str, str],
      "raw": str
    }
    """
    result = {
        "items": [],
        "disclaimer": None,
        "next_step": "",
        "actions": [],
        "raw": raw
    }

    try:
        # --- Extract LIST items ---
        list_match = re.search(
            r'\*\*\[LIST\]\*\*\s*\n(.*?)(?=\n\*\*\[DISCLAIMER\]|\n\*\*\[ACTIONS\]|$)',
            raw, re.DOTALL
        )
        if list_match:
            list_block = list_match.group(1)
            # Split by ### headers
            item_blocks = re.split(r'###\s+', list_block)
            for block in item_blocks:
                block = block.strip()
                if not block:
                    continue
                lines = block.split('\n')
                header = lines[0]

                # Extract badge from backticks
                badge_match = re.search(r'`([^`]+)`', header)
                badge = badge_match.group(1) if badge_match else ""

                # Extract label: remove emoji prefix and badge
                label = re.sub(r'`[^`]+`', '', header).strip()
                # Remove leading emoji (first character if it's not ASCII letter)
                label = re.sub(r'^[^\w\s]+\s*', '', label, flags=re.UNICODE).strip()

                detail_lines = []
                meta = ""
                for ln in lines[1:]:
                    ln_stripped = ln.strip()
                    if ln_stripped.startswith('*') and ln_stripped.endswith('*') and len(ln_stripped) > 2:
                        meta = ln_stripped.strip('*').strip()
                    elif ln_stripped:
                        detail_lines.append(ln_stripped)

                result["items"].append({
                    "label": label,
                    "badge": badge,
                    "detail": ' '.join(detail_lines),
                    "meta": meta
                })

        # --- Extract DISCLAIMER ---
        disc_match = re.search(
            r'\*\*\[DISCLAIMER\]\*\*\s*\n(.*?)(?=\n\*\*\[|$)', raw, re.DOTALL
        )
        if disc_match:
            result["disclaimer"] = disc_match.group(1).strip()

        # --- Extract NEXT STEP (Removed) ---
        result["next_step"] = ""

        # --- Extract ACTIONS ---
        act_match = re.search(
            r'\*\*\[ACTIONS\]\*\*\s*\n(.*?)$', raw, re.DOTALL
        )
        if act_match:
            action_block = act_match.group(1)
            actions = re.findall(r'-\s*`([^`]+)`', action_block)
            result["actions"] = actions

    except Exception as e:
        print(f"parse_structured_response error: {e}")
        # Graceful fallback: raw goes into raw, next_step remains empty
        result["next_step"] = ""

    return result


def detect_active_language(current_message: str, history: list) -> str:
    """Calculates the stateful Active Language by replaying the conversation history."""
    active_language = "CLASS A (English)"  # Default baseline

    hinglish_trigger_words = r'\b(kya|hai|bata|mujhe|yaar|karo|thoda|nahi|samjhao|chahiye|kal|aaj|matlab|toh|haan|theek|bilkul|bhai|waise|bas|mil|kaisa|kaise|kyun|abhi|pehle|baad|lagao|dena|lena|hoga|karein|batao|samajh|suno|madad|kadam)\b'

    # Extract only user messages in chronological order
    all_user_msgs = [msg["content"] for msg in history if msg.get("role") == "user"]
    all_user_msgs.append(current_message)

    for msg in all_user_msgs:
        if re.search(r'[\u0980-\u09FF]', msg):
            active_language = "CLASS D (Bengali)"
        elif re.search(r'[\u0900-\u097F]', msg):
            active_language = "CLASS C (Devanagari)"
        elif re.search(hinglish_trigger_words, msg, re.IGNORECASE):
            active_language = "CLASS B (Hinglish)"
        else:
            # If no Devanagari/Bengali and no Hinglish triggers, it defaults to English.
            # Short affirmatives ("okay"), scheme names ("Udyam"), or standard English set this.
            active_language = "CLASS A (English)"

    # Format the strict directive based on the final derived active_language
    if "CLASS D" in active_language:
        return "CLASS D (Bengali). Output MUST be 100% Bengali script. No exceptions."
    elif "CLASS C" in active_language:
        return "CLASS C (Devanagari). Output MUST be 100% Devanagari script. If the query script is Hindi, Bhojpuri, or Maithili, generate output in the corresponding Devanagari language/dialect matching the user's intent."
    elif "CLASS B" in active_language:
        return "CLASS B (Hinglish). Output MUST be 100% Roman-script Hinglish. ZERO Devanagari script allowed."
    else:
        return "CLASS A (English). Output MUST be 100% standard English."


def get_chat_response(
    user_message: str,
    conversation_history: List[Dict[str, str]],
    rag_context: str = "",
    is_voice_mode: bool = False
) -> dict:
    """
    Calls the Groq LLM to get a response for the MSME Saathi chatbot.

    Args:
        user_message: The citizen's query (text or STT transcript).
        conversation_history: List of prior {"role": "...", "content": "..."} dicts.
        rag_context: Retrieved documents from knowledge base (empty string if none).
        is_voice_mode: True if input came from microphone (STT).

    Returns:
        A structured dict parsed from the LLM's markdown output.
    """
    init_client()
    if model is None:
        return _make_error_dict(
            "क्षमा करें, सर्वर में अभी कोई समस्या है (API Key missing)। कृपया 1800-111-188 पर कॉल करें।\n"
            "Sorry, there is a server issue right now (API Key missing). Please call 1800-111-188."
        )

    # Build the user message with voice flag and RAG context
    formatted_user_message = ""
    if is_voice_mode:
        formatted_user_message += "[VOICE MODE]\n"

    if rag_context:
        formatted_user_message += f"<context>\n{rag_context}\n</context>\n\n"

    formatted_user_message += user_message

    # PRE-FLIGHT LANGUAGE DETECTION AND ENFORCEMENT
    lang_instruction = detect_active_language(user_message, conversation_history)
    dynamic_instruction = f"\n\n[CRITICAL SYSTEM DIRECTIVE FOR THIS TURN]:\nCURRENT ACTIVE LANGUAGE: {lang_instruction}\nYou MUST obey this Active Language classification strictly for all output surfaces. Do not drift."
    formatted_user_message += dynamic_instruction

    # Append few-shot examples (structured format)
    few_shot_examples = [
        {
            "role": "user",
            "content": "bhai mujhe sarkari madad chahiye business ke liye"
        },
        {
            "role": "assistant",
            "content": """**[LIST]**
### Business Type
Kya aapka business manufacturing ka hai ya service sector ka?

### State
Aap kis state se hain? Kuch schemes state-specific hoti hain.

### Stage
Kya aap naya business shuru kar rahe hain ya existing business expand karna chahte hain?

**[DISCLAIMER]**
Note: I can only guide you — visit msme.gov.in for more information.

**[ACTIONS]**
- `Udyam Registration kaise karte hain?`
- `MUDRA loan ke baare mein batao`
- `PMEGP scheme kya hai?`
- `CGTMSE scheme kya hai?`"""
        },
        {
            "role": "user",
            "content": "Udyam Registration"
        },
        {
            "role": "assistant",
            "content": """**[LIST]**
### Step 1: Visit the Official Udyam Portal
Go to the Government of India’s official Udyam Registration portal.
*Portal: udyamregistration.gov.in*

### Step 2: Select Registration Type
Click “For New Entrepreneurs who are not Registered yet as MSME” for fresh registration or select migration options.
*Portal: udyamregistration.gov.in*

### Step 3: Aadhaar Verification
Enter Aadhaar Number and Entrepreneur Name (exactly as per Aadhaar), then click “Validate & Generate OTP” and complete OTP verification.
*Portal: udyamregistration.gov.in*

### Step 4: PAN Verification
Enter PAN Number and Organization Type. The portal auto-fetches tax details linked to PAN.
*Portal: udyamregistration.gov.in*

### Step 5: Fill Business Details
Enter Business Name, Address, Contact details, Bank Details, Employee Count, and NIC code.
*Portal: udyamregistration.gov.in*

### Step 6: Submit Application
Review all details carefully and submit the application using final OTP authentication.
*Portal: udyamregistration.gov.in*

### Step 7: Receive Udyam Certificate
After successful submission, a 19-digit Udyam Registration Number (URN) is generated and Udyam Certificate with QR Code is issued.
*Portal: udyamregistration.gov.in*

### Step 8: Download Certificate
Download your final certificate from the print login page on the portal.
*Portal: udyamregistration.gov.in*

**[DISCLAIMER]**
Note: I can only guide you — visit udyamregistration.gov.in for more information.

**[ACTIONS]**
- `What documents are required for Udyam?`
- `Is Udyam Registration free?`
- `What are the benefits of Udyam?`
- `How to update my existing Udyam certificate?`"""
        },
        {
            "role": "user",
            "content": "How to register for Udyam?"
        },
        {
            "role": "assistant",
            "content": """**[LIST]**
### Step 1: Visit the Official Udyam Portal
Go to the Government of India’s official Udyam Registration portal.
*Portal: udyamregistration.gov.in*

### Step 2: Select Registration Type
Click “For New Entrepreneurs who are not Registered yet as MSME” for fresh registration or select migration options.
*Portal: udyamregistration.gov.in*

### Step 3: Aadhaar Verification
Enter Aadhaar Number and Entrepreneur Name (exactly as per Aadhaar), then click “Validate & Generate OTP” and complete OTP verification.
*Portal: udyamregistration.gov.in*

### Step 4: PAN Verification
Enter PAN Number and Organization Type. The portal auto-fetches tax details linked to PAN.
*Portal: udyamregistration.gov.in*

### Step 5: Fill Business Details
Enter Business Name, Address, Contact details, Bank Details, Employee Count, and NIC code.
*Portal: udyamregistration.gov.in*

### Step 6: Submit Application
Review all details carefully and submit the application using final OTP authentication.
*Portal: udyamregistration.gov.in*

### Step 7: Receive Udyam Certificate
After successful submission, a 19-digit Udyam Registration Number (URN) is generated and Udyam Certificate with QR Code is issued.
*Portal: udyamregistration.gov.in*

### Step 8: Download Certificate
Download your final certificate from the print login page on the portal.
*Portal: udyamregistration.gov.in*

**[DISCLAIMER]**
Note: I can only guide you — visit udyamregistration.gov.in for more information.

**[ACTIONS]**
- `Is Udyam Registration completely free?`
- `What documents are required for Udyam?`
- `How to update my existing Udyam certificate?`
- `Can I register without a PAN card?`"""
        },
        {
            "role": "user",
            "content": "What is the exact subsidy amount I will get under PMEGP for a food processing unit in rural Maharashtra?"
        },
        {
            "role": "assistant",
            "content": """**[LIST]**
### General Category Subsidy
Rural areas generally qualify for 25% subsidy on project cost under PMEGP.
*Portal: kviconline.gov.in/pmegpplus*

### Special Category Subsidy
SC/ST/OBC/Women/Ex-serviceman/PwD candidates may get up to 35% subsidy in rural areas.
*Portal: kviconline.gov.in/pmegpplus*

### Loan Limit
Manufacturing projects can get up to ₹25 lakh, service projects up to ₹10 lakh.

**[DISCLAIMER]**
> ⓘ Subsidy rates and loan limits may change — verify at kviconline.gov.in/pmegpplus
Note: I can only guide you — visit kviconline.gov.in/pmegpplus for more information.

**[ACTIONS]**
- `What documents do I need for PMEGP?`
- `How long does PMEGP approval take?`
- `Am I eligible for PMEGP as a woman entrepreneur?`
- `How to apply for PMEGP online?`"""
        },
        {
            "role": "user",
            "content": "Grievance"
        },
        {
            "role": "assistant",
            "content": """**[DISCLAIMER]**
Note: I can only guide you — visit msme.gov.in for more information.

**[ACTIONS]**
- `Register a Complaint`
- `Check Ticket Status`"""
        },
        {
            "role": "user",
            "content": "Register a Complaint"
        },
        {
            "role": "assistant",
            "content": """**[DISCLAIMER]**
Please type your complete grievance in the chat so I can generate a ticket for you."""
        },
        {
            "role": "user",
            "content": "help / kuch batao"
        },
        {
            "role": "assistant",
            "content": """**[LIST]**
### Scheme Guidance
Main aapko central aur state govt schemes ke baare mein eligibility, benefits aur process batane mein help kar sakta hoon.

### Policy Discovery
Aapke business stage aur type ke hisab se main sahi schemes aur policies search karne mein madad kar sakta hoon.

### Grievance Assistance
Aap complaints register aur status check kar sakte hain. Main ticket create karne mein help karunga.

### Process Walkthroughs
Udyam registration, MUDRA loan, aur PMEGP loan ke steps seekhein.

**[DISCLAIMER]**
[SHOW_WELCOME_CARDS]
Note: I can only guide you — visit msme.gov.in for more information.

**[ACTIONS]**"""
        },
        {
            "role": "user",
            "content": "dfb"
        },
        {
            "role": "assistant",
            "content": """**[LIST]**
### Scheme Guidance
I can provide information on various central and state government schemes for MSMEs, including eligibility, benefits, and application processes.

### Policy Discovery
I can help you find relevant government policies based on your business type and stage.

### Grievance Assistance
I can assist you in understanding how to file, track, and escalate complaints related to MSMEs.

### Process Walkthroughs
I can provide step-by-step guidance for various MSME-related processes, such as registration and application procedures.

**[DISCLAIMER]**
[SHOW_WELCOME_CARDS]
Note: I can only guide you — visit msme.gov.in for more information.

**[ACTIONS]**"""
        },
        {
            "role": "user",
            "content": "bhai aaj ka mausam kaisa hai?"
        },
        {
            "role": "assistant",
            "content": """**[LIST]**
### Scheme Guidance
Main aapko central aur state govt schemes ke baare mein eligibility, benefits aur process batane mein help kar sakta hoon.

### Policy Discovery
Aapke business stage aur type ke hisab se main sahi schemes aur policies search karne mein madad kar sakta hoon.

### Grievance Assistance
Aap complaints register aur status check kar sakte hain. Main ticket create karne mein help karunga.

### Process Walkthroughs
Udyam registration, MUDRA loan, aur PMEGP loan ke steps seekhein.

**[DISCLAIMER]**
[SHOW_WELCOME_CARDS]
Note: I can only guide you — visit msme.gov.in for more information.

**[ACTIONS]**"""
        },
        {
            "role": "user",
            "content": "hinglish mein baat kariye"
        },
        {
            "role": "assistant",
            "content": """**[LIST]**
### Scheme Guidance
Main aapko central aur state govt schemes ke baare mein eligibility, benefits aur process batane mein help kar sakta hoon.

### Policy Discovery
Aapke business stage aur type ke hisab se main sahi schemes aur policies search karne mein madad kar sakta hoon.

### Grievance Assistance
Aap complaints register aur status check kar sakte hain. Main ticket create karne mein help karunga.

### Process Walkthroughs
Udyam registration, MUDRA loan, aur PMEGP loan ke steps seekhein.

**[DISCLAIMER]**
[SHOW_WELCOME_CARDS]
Note: I can only guide you — visit msme.gov.in for more information.

**[ACTIONS]**"""
        },
        {
            "role": "user",
            "content": "मुझे मदद चाहिए"
        },
        {
            "role": "assistant",
            "content": """**[LIST]**
### योजना मार्गदर्शन
मैं आपको एमएसएमई के लिए विभिन्न केंद्रीय और राज्य सरकारी योजनाओं के बारे में पात्रता, लाभ और आवेदन प्रक्रियाओं की जानकारी दे सकता हूँ।

### नीति खोज
मैं आपके व्यवसाय के प्रकार और चरण के आधार पर प्रासंगिक सरकारी नीतियों को खोजने में आपकी सहायता कर सकता हूँ।

### शिकायत सहायता
मैं एमएसएमई से संबंधित शिकायतों को दर्ज करने, ट्रैक करने और आगे बढ़ाने में आपकी सहायता कर सकता हूँ।

### प्रक्रिया विवरण
मैं पंजीकरण और आवेदन प्रक्रियाओं जैसी विभिन्न एमएसएमई-संबंधित प्रक्रियाओं के लिए चरण-दर-चरण मार्गदर्शन प्रदान कर सकता हूँ।

**[DISCLAIMER]**
[SHOW_WELCOME_CARDS]
नोट: मैं केवल मार्गदर्शन कर सकता हूँ — msme.gov.in पर जाएँ।

**[ACTIONS]**"""
        },
        {
            "role": "user",
            "content": "Bank ne mera loan reject kar diya hai. Application no: 123456. Pichle hafte apply kiya tha."
        },
        {
            "role": "assistant",
            "content": """**[DISCLAIMER]**
[GENERATE_TICKET]

**[ACTIONS]**"""
        },
        {
            "role": "user",
            "content": "Check Ticket Status"
        },
        {
            "role": "assistant",
            "content": """**[DISCLAIMER]**
Enter your exact Ticket ID (e.g., TKT-MSME-123456) in the chat below.

**[ACTIONS]**"""
        },
        {
            "role": "user",
            "content": "TKT-MSME-847291"
        },
        {
            "role": "assistant",
            "content": """**[DISCLAIMER]**
[CHECK_TICKET: TKT-MSME-847291]

**[ACTIONS]**"""
        },
        {
            "role": "user",
            "content": "Are you a Student or Entrepreneur/Business Owner : Student\\nState of Residence : Bihar\\nGender : Male\\nSocial Category (General / SC / ST / OBC / EBC / Minority / PwD) : SC\\nIs your business/venture new or existing : New\\nBusiness Type (Manufacturing / Agro / Tech-Innovation / Service / Other) : Manufacturing"
        },
        {
            "role": "assistant",
            "content": """**[LIST]**
### Mukhyamantri Udyami Yojana
This scheme provides ₹10 Lakh financial assistance (₹5 Lakh grant + ₹5 Lakh loan) to SC/ST/OBC/EBC youth in Bihar setting up new MSME units.
*Portal: industries.bih.nic.in*

### Mukhyamantri Mahila Udyami Yojana
If the applicant is female, this scheme offers ₹10 Lakh project cost coverage specifically for women entrepreneurs in Bihar.
*Portal: industries.bih.nic.in*

### Bihar Industrial Investment Promotion Policy
Provides stamp duty exemption, land conversion fee waiver, and interest subvention for new industrial investments in Bihar across all categories.
*Portal: industries.bih.nic.in*

**[DISCLAIMER]**
> ⓘ Benefit amounts and eligibility criteria may change — verify at industries.bih.nic.in
Note: I can only guide you — visit industries.bih.nic.in for more information.

**[ACTIONS]**
- `Tell me more about Mukhyamantri Udyami Yojana`
- `How to apply for Mukhyamantri Mahila Udyami Yojana?`
- `What are the benefits under Bihar Industrial Investment Promotion Policy?`"""
        },
        {
            "role": "user",
            "content": "Are you a Student or Entrepreneur/Business Owner : Student\\nState of Residence : Delhi\\nGender : Male\\nSocial Category (General / SC / ST / OBC / EBC / Minority / PwD) : PwD\\nIs your business/venture new or existing : New\\nBusiness Type (Manufacturing / Agro / Tech-Innovation / Service / Other) : Other"
        },
        {
            "role": "assistant",
            "content": """**[LIST]**
### National Overseas Scholarship For Students With Disabilities
This scheme provides financial assistance to students with benchmark disabilities for pursuing higher education abroad. It is a central government scheme open to all Indian states.
*Portal: scholarship.gov.in*

**[DISCLAIMER]**
> ⓘ Eligibility criteria and income limits may change — verify at scholarship.gov.in
Note: I can only guide you — visit scholarship.gov.in for more information.

**[ACTIONS]**
- `What is the eligibility for the Disability Scholarship?`
- `What documents are needed for the Disability Scholarship?`
- `What is the scholarship amount?`"""
        }
    ]
    
    # We must convert the openai-style messages into gemini history format
    # which is `[{"role": "user"|"model", "parts": ["..."]}]`
    gemini_history = []
    
    for msg in few_shot_examples:
        role = "model" if msg["role"] == "assistant" else "user"
        gemini_history.append({"role": role, "parts": [msg["content"]]})
        
    for msg in conversation_history:
        role = "model" if msg["role"] == "assistant" else "user"
        gemini_history.append({"role": role, "parts": [msg["content"]]})

    try:
        chat = model.start_chat(history=gemini_history)
        response = chat.send_message(formatted_user_message)
        print("FINISH REASON:", response.candidates[0].finish_reason)
        return parse_structured_response(response.text)
    except Exception as e:
        print(f"LLM Error: {e}")
        return _make_error_dict(
            "क्षमा करें, मुझे उत्तर देने में समस्या हो रही है। कृपया थोड़ी देर बाद प्रयास करें या 1800-111-188 पर कॉल करें।\n"
            "Sorry, I am having trouble responding right now. Please try again later or call 1800-111-188."
        )
