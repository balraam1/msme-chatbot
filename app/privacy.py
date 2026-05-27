import re
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_anonymizer import AnonymizerEngine

# Initialize Engines
analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

# Define patterns
aadhaar_pattern = Pattern(name="aadhaar_pattern", regex=r"\b\d{4}\s?\d{4}\s?\d{4}\b", score=0.85)
pan_pattern = Pattern(name="pan_pattern", regex=r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b", score=0.85)
mobile_pattern = Pattern(name="mobile_pattern", regex=r"\b[6-9]\d{9}\b", score=0.85)
uan_pattern = Pattern(name="uan_pattern", regex=r"\b\d{12}\b", score=0.80)
ifsc_pattern = Pattern(name="ifsc_pattern", regex=r"\b[A-Z]{4}0[A-Z0-9]{6}\b", score=0.85)

# Create custom PatternRecognizers
aadhaar_recognizer = PatternRecognizer(supported_entity="AADHAAR_NUMBER", patterns=[aadhaar_pattern], context=["aadhaar", "uidai", "aadhar"])
pan_recognizer = PatternRecognizer(supported_entity="PAN_NUMBER", patterns=[pan_pattern], context=["pan", "income tax", "pancard"])
mobile_recognizer = PatternRecognizer(supported_entity="PHONE_NUMBER", patterns=[mobile_pattern], context=["mobile", "phone", "number", "call"])
uan_recognizer = PatternRecognizer(supported_entity="UAN_NUMBER", patterns=[uan_pattern], context=["uan", "epfo", "pf"])
ifsc_recognizer = PatternRecognizer(supported_entity="IFSC_CODE", patterns=[ifsc_pattern], context=["ifsc", "bank", "branch", "code"])

# Add custom recognizers to the analyzer
analyzer.registry.add_recognizer(aadhaar_recognizer)
analyzer.registry.add_recognizer(pan_recognizer)
analyzer.registry.add_recognizer(mobile_recognizer)
# To preferentially tag 12-digit numbers as AADHAAR rather than UAN, we add UAN with a slightly lower score (0.80 vs 0.85)
analyzer.registry.add_recognizer(uan_recognizer)
analyzer.registry.add_recognizer(ifsc_recognizer)

def scrub_pii(text: str) -> str:
    """
    Analyzes text and replaces any Indian PII entities with their type tags.
    """
    if not text:
        return ""
        
    # Analyze text
    results = analyzer.analyze(
        text=text,
        language="en",
        entities=["AADHAAR_NUMBER", "PAN_NUMBER", "PHONE_NUMBER", "UAN_NUMBER", "IFSC_CODE", "EMAIL_ADDRESS", "IP_ADDRESS"]
    )
    
    # Sort results by character index in reverse to perform clean text substitution
    sorted_results = sorted(results, key=lambda x: x.start, reverse=True)
    
    scrubbed_text = text
    for result in sorted_results:
        # Check overlaps: if a 12 digit number is detected as both UAN and Aadhaar, prefer AADHAAR
        entity_type = result.entity_type
        if entity_type == "UAN_NUMBER":
            # Check if there is an AADHAAR_NUMBER entity covering the exact same span
            is_aadhaar = any(
                r.entity_type == "AADHAAR_NUMBER" and r.start == result.start and r.end == result.end
                for r in results
            )
            if is_aadhaar:
                continue  # Skip because we will replace it with AADHAAR_NUMBER instead
        
        # Replace entity with tag
        tag = f"<{entity_type}>"
        scrubbed_text = scrubbed_text[:result.start] + tag + scrubbed_text[result.end:]
        
    return scrubbed_text

def generate_consent_notice(lang: str = "en") -> str:
    """Returns the monolingual privacy/consent notice matching the active language."""
    if lang in ("hi", "bho", "mai"):
        return (
            "यह चैटबॉट आपकी शिकायतों को हल करने में मदद करने के लिए उन्हें संग्रहीत करता है। "
            "कोई व्यक्तिगत डेटा तृतीय पक्षों के साथ साझा नहीं किया जाता है।"
        )
    elif lang == "ben":
        return (
            "এই চ্যাটবটটি আপনার অভিযোগগুলি সমাধান করতে সহায়তা করার জন্য সংরক্ষণ করে। "
            "কোনও ব্যক্তিগত তথ্য তৃতীয় পক্ষের সাথে ভাগ করা হয় না।"
        )
    else:
        return (
            "This chatbot stores your grievances to help resolve them. "
            "No personal data is shared with third parties."
        )
