import os
import re
import httpx
from typing import Optional
from langdetect import detect
from dotenv import load_dotenv

load_dotenv()

# Bhashini credentials
BHASHINI_API_KEY = os.environ.get("BHASHINI_API_KEY", "")
BHASHINI_USER_ID = os.environ.get("BHASHINI_USER_ID", "")

# Language code mapping for Bhashini
LANG_MAP = {
    "hi": "hi",
    "en": "en",
    "bho": "bho",
    "mai": "mai",
    "ben": "bn"
}

def detect_language(text: str) -> str:
    """
    Detects the language of the text. Returns 'ben' for Bengali, 'en' for English,
    and 'hi' for Hindi / Indo-Aryan languages (including Hinglish).
    """
    if not text.strip():
        return "en"

    # Direct script-based detection
    has_devanagari = any(ord(char) >= 0x0900 and ord(char) <= 0x097F for char in text)
    has_bengali = any(ord(char) >= 0x0980 and ord(char) <= 0x09FF for char in text)

    if has_devanagari:
        return "hi"
    if has_bengali:
        return "ben"

    # Check for Hinglish Roman script keywords
    cleaned_words = set(re.findall(r'\b[a-zA-Z]+\b', text.lower()))
    
    hinglish_keywords = {
        "kya", "hai", "bata", "mujhe", "yaar", "karo", "thoda", "nahi", "samjhao", 
        "chahiye", "kal", "aaj", "matlab", "toh", "haan", "theek", "bilkul", "bhai", 
        "waise", "bas", "mil", "kaisa", "kaise", "kyun", "abhi", "pehle", "baad", 
        "lagao", "dena", "lena", "hoga", "karein", "batao", "samajh", "suno", "madad", 
        "kadam", "bataiye", "dijiye", "kijiye", "shuru", "rha", "raha", "hoon", 
        "mein", "bhi", "gaya", "rhi", "rahe", "badhein", "aage", "jaao", "jaaein", 
        "wapas", "lein", "dekhein", "khojein", "shikayat", "se", "ko", "ki", "ka", "ke"
    }

    if cleaned_words.intersection(hinglish_keywords):
        return "hi"

    # Fallback to langdetect but force 'en' if it detects any other language
    try:
        lang = detect(text)
        if lang == "bn":
            return "ben"
        elif lang == "hi":
            return "hi"
    except Exception:
        pass

    return "en"

async def translate_text(text: str, source_lang: str, target_lang: str) -> str:
    """
    Translates text from source_lang to target_lang using MeitY Bhashini API.
    If credentials are missing or API fails, returns the original text.
    """
    if not text.strip() or source_lang == target_lang:
        return text

    # Map to Bhashini language codes
    src_code = LANG_MAP.get(source_lang, source_lang)
    tgt_code = LANG_MAP.get(target_lang, target_lang)

    if src_code == tgt_code:
        return text

    if not BHASHINI_API_KEY or not BHASHINI_USER_ID or "dummy" in BHASHINI_API_KEY:
        print("Bhashini Translation credentials missing or dummy. Returning original text.")
        return text

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # 1. Fetch Pipeline Config
            config_url = "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline"
            headers = {
                "userID": BHASHINI_USER_ID,
                "ulcaApiKey": BHASHINI_API_KEY,
                "Content-Type": "application/json"
            }
            config_payload = {
                "pipelineTasks": [
                    {
                        "taskType": "translation",
                        "config": {
                            "language": {
                                "sourceLanguage": src_code,
                                "targetLanguage": tgt_code
                            }
                        }
                    }
                ],
                "pipelineRequestConfig": {
                    "pipelineId": "64392f96daac500b55c543cd"
                }
            }

            config_res = await client.post(config_url, json=config_payload, headers=headers)
            if config_res.status_code != 200:
                print(f"Bhashini Translation Config API failed: {config_res.status_code}")
                return text

            config_data = config_res.json()
            
            # Extract endpoint and auth details
            pipeline_response = config_data.get("pipelineResponseConfig", [])
            if not pipeline_response:
                return text
                
            inference_config = pipeline_response[0]
            inference_endpoint = config_data.get("pipelineInferenceAPIEndPoint", {}).get("callbackUrl")
            inference_api_key_name = config_data.get("pipelineInferenceAPIEndPoint", {}).get("inferenceApiKey", {}).get("name")
            inference_api_key_value = config_data.get("pipelineInferenceAPIEndPoint", {}).get("inferenceApiKey", {}).get("value")
            
            if not inference_endpoint:
                return text

            service_id = inference_config.get("model", [{}])[0].get("modelId")
            if not service_id:
                return text

            # 2. Make Translation Inference Call
            inference_headers = {
                inference_api_key_name: inference_api_key_value,
                "Content-Type": "application/json"
            }
            
            inference_payload = {
                "pipelineTasks": [
                    {
                        "taskType": "translation",
                        "config": {
                            "language": {
                                "sourceLanguage": src_code,
                                "targetLanguage": tgt_code
                            },
                            "serviceId": service_id
                        }
                    }
                ],
                "inputData": {
                    "input": [
                        {
                            "source": text
                        }
                    ]
                }
            }

            inf_res = await client.post(inference_endpoint, json=inference_payload, headers=inference_headers)
            if inf_res.status_code != 200:
                print(f"Bhashini Translation Inference API failed: {inf_res.status_code}")
                return text

            inf_data = inf_res.json()
            translated_text = inf_data.get("pipelineResponse", [{}])[0].get("output", [{}])[0].get("target")
            if translated_text:
                return translated_text
            return text

    except Exception as e:
        print(f"Bhashini Translation Exception: {e}")
        return text
