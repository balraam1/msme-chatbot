import os
import json
import httpx
from fastapi import APIRouter, Request, HTTPException, Response, BackgroundTasks
from app.whatsapp_formatter import format_whatsapp_message
from app.translate import detect_language

router = APIRouter(prefix="/api/webhook", tags=["whatsapp"])

# Read configurations
ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "")

async def send_whatsapp_message(to_phone: str, text: str):
    """
    Sends a formatted message to the user's phone number via Meta WhatsApp Cloud API.
    """
    safe_text_for_console = text.encode('ascii', errors='backslashreplace').decode('ascii')
    if not ACCESS_TOKEN or not PHONE_NUMBER_ID or "dummy" in ACCESS_TOKEN or "dummy" in PHONE_NUMBER_ID:
        print(f"[WHATSAPP MOCK] Sending to {to_phone}:\n{safe_text_for_console}")
        return True

    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_phone,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": text
        }
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(url, json=payload, headers=headers)
            if res.status_code in (200, 201):
                print(f"[WHATSAPP] Successfully sent message to {to_phone}")
                return True
            else:
                print(f"[WHATSAPP ERROR] Failed to send. Status: {res.status_code}, Body: {res.text.encode('ascii', errors='backslashreplace').decode('ascii')}")
                return False
    except Exception as e:
        print(f"[WHATSAPP EXCEPTION] Error: {str(e).encode('ascii', errors='backslashreplace').decode('ascii')}")
        return False

@router.get("/whatsapp")
async def verify_webhook(request: Request):
    """
    Handles Meta webhook verification.
    """
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token:
        if token == VERIFY_TOKEN or (not VERIFY_TOKEN and token == "dummy_whatsapp_verify_token"):
            print("[WHATSAPP] Webhook verified successfully.")
            return Response(content=challenge, media_type="text/plain")
        else:
            print(f"[WHATSAPP] Webhook verification failed. Token mismatch: expected {VERIFY_TOKEN}, got {token}")
            raise HTTPException(status_code=403, detail="Verification token mismatch")
    
    print("[WHATSAPP] Invalid webhook verification query parameters.")
    raise HTTPException(status_code=400, detail="Missing hub parameters")

@router.post("/whatsapp")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Handles incoming messages from Meta WhatsApp API.
    """
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # Safe log of payload to console
    print("[WHATSAPP WEBHOOK DATA]:", json.dumps(data, ensure_ascii=True))

    # Check if object is whatsapp_business_account
    if data.get("object") != "whatsapp_business_account":
        # Return HTTP 200 to acknowledge receipt of other events (like test pings)
        return {"status": "ignored", "reason": "not a whatsapp business account"}

    # Extract messages
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            if "messages" in value:
                for msg in value.get("messages", []):
                    # We only process text messages
                    if msg.get("type") == "text":
                        sender_phone = msg.get("from")
                        message_text = msg.get("text", {}).get("body", "")

                        if not sender_phone or not message_text.strip():
                            continue

                        safe_msg_for_console = message_text.encode('ascii', errors='backslashreplace').decode('ascii')
                        print(f"[WHATSAPP MESSAGE RECEIVED] From: {sender_phone}, Text: {safe_msg_for_console}")

                        # Import main app's chat endpoint logic dynamically to avoid circular imports
                        from main import chat_endpoint, ChatRequest

                        # Detect the language of the incoming message
                        detected_lang = detect_language(message_text)

                        # Create ChatRequest payload
                        payload = ChatRequest(
                            message=message_text,
                            sessionId=f"whatsapp_{sender_phone}",
                            isVoiceMode=False,
                            language=detected_lang
                        )

                        try:
                            # Invoke the main chatbot endpoint logic
                            chat_response = await chat_endpoint(payload, request, background_tasks)
                            
                            # Format response using our whatsapp formatter
                            formatted_reply = format_whatsapp_message(chat_response.reply)

                            # Send response back to the user on WhatsApp
                            await send_whatsapp_message(sender_phone, formatted_reply)
                        except Exception as chat_err:
                            safe_err_for_console = str(chat_err).encode('ascii', errors='backslashreplace').decode('ascii')
                            print(f"[WHATSAPP CHAT ERROR] Error invoking chat flow: {safe_err_for_console}")
                            # Send a generic fallback error response
                            fallback_msg = "Sorry, I am facing technical difficulties processing your request. Please try again. / क्षमा करें, मुझे आपकी सहायता करने में तकनीकी कठिनाई हो रही है।"
                            await send_whatsapp_message(sender_phone, fallback_msg)

    return {"status": "processed"}
