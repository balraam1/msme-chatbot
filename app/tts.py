import os
import base64
import httpx
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Bhashini credentials
BHASHINI_API_KEY = os.environ.get("BHASHINI_API_KEY", "")
BHASHINI_USER_ID = os.environ.get("BHASHINI_USER_ID", "")

# Language mapping
LANG_MAP = {
    "hi": "hi",
    "en": "en",
    "bho": "bho",
    "mai": "mai",
    "ben": "bn"
}

async def get_tts_audio(text: str, language: str) -> Optional[bytes]:
    """
    Calls MeitY's Bhashini TTS pipeline API to synthesize speech from text.
    Returns bytes on success, or None on failure.
    """
    if not BHASHINI_API_KEY or not BHASHINI_USER_ID:
        # Silently fail if credentials are not configured
        print("Bhashini TTS Credentials missing.")
        return None

    # Trim to 500 chars for reasonable response times
    text_to_speak = text[:500].strip()
    if not text_to_speak:
        return None

    lang_code = LANG_MAP.get(language, "hi")

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
                        "taskType": "tts",
                        "config": {
                            "language": {
                                "sourceLanguage": lang_code
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
                print(f"Bhashini Config API failed with status {config_res.status_code}: {config_res.text}")
                return None

            config_data = config_res.json()
            
            # Extract endpoint and auth details
            pipeline_response = config_data.get("pipelineResponseConfig", [])
            if not pipeline_response:
                return None
                
            inference_config = pipeline_response[0]
            inference_url = inference_config.get("config", [{}])[0].get("inferenceApiKey", {}).get("value")
            # Wait, actually the inference endpoint is returned in computeCallServerUrl or inside config:
            inference_endpoint = config_data.get("pipelineInferenceAPIEndPoint", {}).get("callbackUrl")
            inference_api_key_name = config_data.get("pipelineInferenceAPIEndPoint", {}).get("inferenceApiKey", {}).get("name")
            inference_api_key_value = config_data.get("pipelineInferenceAPIEndPoint", {}).get("inferenceApiKey", {}).get("value")
            
            if not inference_endpoint:
                return None

            # Find service ID
            service_id = inference_config.get("model", [{}])[0].get("modelId")
            if not service_id:
                # Fallback service ID mapping
                service_id = "ai4bharat/indic-tts-coqui-hi-gpu--t4"

            # 2. Make TTS Inference Call
            inference_headers = {
                inference_api_key_name: inference_api_key_value,
                "Content-Type": "application/json"
            }
            
            inference_payload = {
                "pipelineTasks": [
                    {
                        "taskType": "tts",
                        "config": {
                            "language": {
                                "sourceLanguage": lang_code
                            },
                            "serviceId": service_id,
                            "gender": "female",
                            "samplingRate": 8000
                        }
                    }
                ],
                "inputData": {
                    "input": [
                        {
                            "source": text_to_speak
                        }
                    ]
                }
            }

            inf_res = await client.post(inference_endpoint, json=inference_payload, headers=inference_headers)
            if inf_res.status_code != 200:
                print(f"Bhashini Inference API failed with status {inf_res.status_code}: {inf_res.text}")
                return None

            inf_data = inf_res.json()
            audio_b64 = inf_data.get("pipelineResponse", [{}])[0].get("audio", [{}])[0].get("audioContent")
            if not audio_b64:
                return None

            # Return decoded bytes
            return base64.b64decode(audio_b64)

    except Exception as e:
        print(f"Bhashini TTS Call Exception: {e}")
        return None
