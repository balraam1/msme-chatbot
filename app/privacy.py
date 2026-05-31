import re

def scrub_pii(text: str) -> str:
    """
    Analyzes text and replaces any Indian PII entities with their type tags
    using a fast, pure-python regular expression engine.
    """
    if not text:
        return ""

    patterns = {
        "AADHAAR_NUMBER": r"\b\d{4}\s?\d{4}\s?\d{4}\b",
        "PAN_NUMBER": r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b",
        "PHONE_NUMBER": r"\b[6-9]\d{9}\b",
        "IFSC_CODE": r"\b[A-Z]{4}0[A-Z0-9]{6}\b",
        "EMAIL_ADDRESS": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "IP_ADDRESS": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
    }

    matches = []
    for entity_type, regex in patterns.items():
        for match in re.finditer(regex, text):
            matches.append({
                "start": match.start(),
                "end": match.end(),
                "type": entity_type
            })

    # Sort matches by start index, and for overlapping spans, keep the one with larger span
    matches = sorted(matches, key=lambda x: (x["start"], -x["end"]))
    
    filtered_matches = []
    last_end = -1
    for m in matches:
        if m["start"] >= last_end:
            filtered_matches.append(m)
            last_end = m["end"]

    # Sort in reverse order of start index to perform clean text substitution
    filtered_matches = sorted(filtered_matches, key=lambda x: x["start"], reverse=True)

    scrubbed_text = text
    for m in filtered_matches:
        tag = f"<{m['type']}>"
        scrubbed_text = scrubbed_text[:m["start"]] + tag + scrubbed_text[m["end"]:]

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
