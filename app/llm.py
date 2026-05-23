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
                model_name="gemini-2.5-flash-lite",
                generation_config=generation_config,
                safety_settings=safety_settings,
                system_instruction=SYSTEM_PROMPT
            )
        client_initialized = True


def _make_error_dict(msg: str) -> dict:
    """Wraps an error string into the structured response dict format."""
    return {
        "acknowledge": msg,
        "items": [],
        "disclaimer": None,
        "next_step": "",
        "actions": [],
        "raw": msg
    }


def parse_structured_response(raw: str) -> dict:
    """
    Parses the LLM's structured markdown output into a dict for frontend rendering.
    Returns:
    {
      "acknowledge": str,
      "items": [{"label": str, "badge": str, "detail": str, "meta": str}],
      "disclaimer": str | None,
      "next_step": str,
      "actions": [str, str, str],
      "raw": str
    }
    """
    result = {
        "acknowledge": "",
        "items": [],
        "disclaimer": None,
        "next_step": "",
        "actions": [],
        "raw": raw
    }

    try:
        # --- Extract ACKNOWLEDGE ---
        ack_match = re.search(
            r'\*\*\[ACKNOWLEDGE\]\*\*\s*\n(.*?)(?=\n\*\*\[|$)', raw, re.DOTALL
        )
        if ack_match:
            result["acknowledge"] = ack_match.group(1).strip()
        else:
            # Fallback: first non-empty line
            for line in raw.split('\n'):
                stripped = line.strip()
                if stripped and not stripped.startswith('**['):
                    result["acknowledge"] = stripped
                    break

        # --- Extract LIST items ---
        list_match = re.search(
            r'\*\*\[LIST\]\*\*\s*\n(.*?)(?=\n\*\*\[DISCLAIMER\]|\n\*\*\[NEXT STEP\]|\n\*\*\[ACTIONS\]|$)',
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
            r'\*\*\[DISCLAIMER\]\*\*.*?\n>\s*\u24d8\s*(.+?)(?=\n\s*\n|\n\*\*\[|$)', raw, re.DOTALL
        )
        if disc_match:
            result["disclaimer"] = disc_match.group(1).strip()

        # --- Extract NEXT STEP ---
        ns_match = re.search(
            r'\*\*\[NEXT STEP\]\*\*\s*\n(.+?)(?=\n\s*\n|\n\*\*\[|$)', raw, re.DOTALL
        )
        if ns_match:
            result["next_step"] = ns_match.group(1).strip()

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
        # Graceful fallback: raw goes into acknowledge
        result["acknowledge"] = raw

    return result


def detect_active_language(current_message: str, history: list) -> str:
    """Calculates the stateful Active Language by replaying the conversation history."""
    active_language = "CLASS A (English)"  # Default baseline

    hinglish_trigger_words = r'\b(kya|hai|bata|mujhe|yaar|karo|thoda|nahi|samjhao|chahiye|kal|aaj|matlab|toh|haan|theek|bilkul|bhai|waise|bas|mil|kaisa|kaise|kyun|abhi|pehle|baad|lagao|dena|lena|hoga|karein|batao|samajh|suno|madad|kadam)\b'

    # Extract only user messages in chronological order
    all_user_msgs = [msg["content"] for msg in history if msg.get("role") == "user"]
    all_user_msgs.append(current_message)

    for msg in all_user_msgs:
        if re.search(r'[\u0900-\u097F]', msg):
            active_language = "CLASS C (Devanagari Hindi)"
        elif re.search(hinglish_trigger_words, msg, re.IGNORECASE):
            active_language = "CLASS B (Hinglish)"
        else:
            # If no Devanagari and no Hinglish triggers, it defaults to English.
            # Short affirmatives ("okay"), scheme names ("Udyam"), or standard English set this.
            active_language = "CLASS A (English)"

    # Format the strict directive based on the final derived active_language
    if "CLASS C" in active_language:
        return "CLASS C (Devanagari Hindi). Output MUST be 100% Devanagari Hindi script. No exceptions."
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
            "content": """**[ACKNOWLEDGE]**
Main samajh sakta hoon ki aapko business ke liye sarkari madad chahiye.

**[LIST]**
### Business Type
Kya aapka business manufacturing ka hai ya service sector ka?

### State
Aap kis state se hain? Kuch schemes state-specific hoti hain.

### Stage
Kya aap naya business shuru kar rahe hain ya existing business expand karna chahte hain?

**[NEXT STEP]**
**Agle Kadam:** Upar ke sawaalon ka jawab dijiye toh main aapke liye sahi scheme suggest karunga. Note: Main apply nahi kar sakta — visit msme.gov.in

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
            "content": """**[ACKNOWLEDGE]**
I can help you with Udyam Registration. What would you like to know?

**[LIST]**
### Registration Process
Step-by-step guidance on how to apply on the official portal.

### Documents Required
Find out what details you need before starting the application.

### Cost and Fees
Learn about the cost involved in registering your business.

### Key Benefits
Discover the government advantages you get after registering.

**[NEXT STEP]**
**Next step:** Please select one of the specific questions below so I can guide you further. Note: I cannot complete the registration for you — visit udyamregistration.gov.in

**[ACTIONS]**
- `How to register for Udyam?`
- `What documents are required for Udyam?`
- `Is Udyam Registration free?`
- `What are the benefits of Udyam?`"""
        },
        {
            "role": "user",
            "content": "How to register for Udyam?"
        },
        {
            "role": "assistant",
            "content": """**[ACKNOWLEDGE]**
Here is the step-by-step process for Udyam Registration.

**[LIST]**
### Visit Official Portal
Go to the official udyamregistration.gov.in website. Ensure you do not pay any fees to fake sites.

### Enter Aadhaar Details
Provide the Aadhaar number of the proprietor, partner, or director and validate via OTP.

### Fill Business Details
Enter your PAN, bank account details, and business activity information (NIC code).

### Download Certificate
Submit the form with OTP and instantly download your Udyam Registration Certificate.

**[NEXT STEP]**
**Next step:** Gather your Aadhaar and PAN before starting. Note: I cannot complete the registration for you — visit udyamregistration.gov.in

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
            "content": """**[ACKNOWLEDGE]**
Great question about PMEGP subsidy for your food processing unit in rural Maharashtra.

**[LIST]**
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

**[NEXT STEP]**
**Next step:** Check your exact eligibility and apply online. Note: I cannot apply for you — visit kviconline.gov.in/pmegpplus

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
            "content": """**[ACKNOWLEDGE]**
I can help you with your MSME grievance. What would you like to do?

**[NEXT STEP]**
**Next step:** Please select one of the options below. Note: I can only guide you — visit msme.gov.in

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
            "content": """**[ACKNOWLEDGE]**
Please type your complete grievance in the chat so I can generate a ticket for you.

**[NEXT STEP]**
**Next step:** Enter your grievance text below.

**[ACTIONS]**"""
        },
        {
            "role": "user",
            "content": "help / kuch batao"
        },
        {
            "role": "assistant",
            "content": """**[ACKNOWLEDGE]**
Main aapki madad karna chahta hoon! Pehle thoda samajhna hoga ki aapko kis cheez mein help chahiye.

**[LIST]**
### [SHOW_WELCOME_CARDS]
Select an option above to get started.

**[NEXT STEP]**
**Agle Kadam:** Batayein ki upar mein se kaunsi cheez mein madad chahiye. Note: Main sirf guide kar sakta hoon — visit msme.gov.in

**[ACTIONS]**"""
        },
        {
            "role": "user",
            "content": "dfb"
        },
        {
            "role": "assistant",
            "content": """**[ACKNOWLEDGE]**
I can only assist with MSME government schemes and business registrations. Please select an option below.

**[LIST]**
### [SHOW_WELCOME_CARDS]
Select an option above to get started.

**[NEXT STEP]**
**Next step:** Tell me what you need help with. Note: I can only guide you — visit msme.gov.in

**[ACTIONS]**"""
        },
        {
            "role": "user",
            "content": "bhai aaj ka mausam kaisa hai?"
        },
        {
            "role": "assistant",
            "content": """**[ACKNOWLEDGE]**
Main sirf MSME government schemes aur business registration mein help kar sakta hoon. Kripya niche diye gaye options mein se chunein.

**[LIST]**
### [SHOW_WELCOME_CARDS]
Select an option above to get started.

**[NEXT STEP]**
**Agle Kadam:** Batayein ki upar mein se kaunsi cheez mein madad chahiye. Note: Main sirf guide kar sakta hoon — visit msme.gov.in

**[ACTIONS]**"""
        },
        {
            "role": "user",
            "content": "hinglish mein baat kariye"
        },
        {
            "role": "assistant",
            "content": """**[ACKNOWLEDGE]**
Zaroor, main aapse Hinglish mein baat karunga. Batayein main aapki kis tarah madad kar sakta hoon?

**[LIST]**
### [SHOW_WELCOME_CARDS]
Select an option above to get started.

**[NEXT STEP]**
**Agle Kadam:** Upar diye gaye vikalpon mein se ek chunein. Note: Main sirf guide kar sakta hoon — visit msme.gov.in

**[ACTIONS]**"""
        },
        {
            "role": "user",
            "content": "मुझे मदद चाहिए"
        },
        {
            "role": "assistant",
            "content": """**[ACKNOWLEDGE]**
मैं आपकी मदद करने के लिए यहाँ हूँ! कृपया बताएं कि आपको किस प्रकार की सहायता चाहिए।

**[LIST]**
### [SHOW_WELCOME_CARDS]
Select an option above to get started.

**[NEXT STEP]**
**अगले कदम:** ऊपर दिए गए विकल्पों में से एक चुनें। नोट: मैं केवल मार्गदर्शन कर सकता हूँ — msme.gov.in पर जाएँ।

**[ACTIONS]**"""
        },
        {
            "role": "user",
            "content": "Bank ne mera loan reject kar diya hai. Application no: 123456. Pichle hafte apply kiya tha."
        },
        {
            "role": "assistant",
            "content": """**[ACKNOWLEDGE]**
Aapki jankari ke liye shukriya. Main aapki shikayat system mein darj kar raha hoon.

**[NEXT STEP]**
**Agle Kadam:** [GENERATE_TICKET]

**[ACTIONS]**"""
        },
        {
            "role": "user",
            "content": "Check Ticket Status"
        },
        {
            "role": "assistant",
            "content": """**[ACKNOWLEDGE]**
Please provide your ticket number to check the status.

**[NEXT STEP]**
**Next step:** Enter your exact Ticket ID (e.g., TKT-MSME-123456) in the chat below.

**[ACTIONS]**"""
        },
        {
            "role": "user",
            "content": "TKT-MSME-847291"
        },
        {
            "role": "assistant",
            "content": """**[ACKNOWLEDGE]**
Checking the database for your ticket TKT-MSME-847291.

**[NEXT STEP]**
**Next step:** [CHECK_TICKET: TKT-MSME-847291]

**[ACTIONS]**"""
        },
        {
            "role": "user",
            "content": "Are you a Student or Entrepreneur/Business Owner : Student\\nState of Residence : Bihar\\nGender : Male\\nSocial Category (General / SC / ST / OBC / EBC / Minority / PwD) : SC\\nIs your business/venture new or existing : New\\nBusiness Type (Manufacturing / Agro / Tech-Innovation / Service / Other) : Manufacturing"
        },
        {
            "role": "assistant",
            "content": """**[ACKNOWLEDGE]**
Based on your profile, here are all the relevant MSME schemes for your new manufacturing venture in Bihar.

**[LIST]**
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

**[NEXT STEP]**
**Next step:** Tell me which scheme you want to learn more about. Note: I can only guide you — visit industries.bih.nic.in

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
            "content": """**[ACKNOWLEDGE]**
Based on your profile as a student with disability, here is the most relevant scheme for you.

**[LIST]**
### National Overseas Scholarship For Students With Disabilities
This scheme provides financial assistance to students with benchmark disabilities for pursuing higher education abroad. It is a central government scheme open to all Indian states.
*Portal: scholarship.gov.in*

**[DISCLAIMER]**
> ⓘ Eligibility criteria and income limits may change — verify at scholarship.gov.in

**[NEXT STEP]**
**Next step:** Check your eligibility and apply online. Note: I can only guide you — visit scholarship.gov.in

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
