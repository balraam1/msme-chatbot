# app/comparison.py
from typing import Dict, List, Optional

COMPARISONS: Dict[str, Dict] = {
    "pmegp_vs_mudra": {
        "title_en": "Comparison: PMEGP vs MUDRA Loan",
        "title_hi": "तुलना: PMEGP बनाम MUDRA लोन",
        "parameters": [
            {
                "name_en": "Target Business Type",
                "name_hi": "लक्षित व्यवसाय प्रकार",
                "pmegp": "NEW businesses/ventures only. (नया व्यवसाय शुरू करने के लिए)",
                "mudra": "Both NEW and EXISTING businesses. (नए और पुराने दोनों के लिए)"
            },
            {
                "name_en": "Maximum Loan Amount",
                "name_hi": "अधिकतम ऋण राशि",
                "pmegp": "Up to ₹25 Lakh for manufacturing; ₹10 Lakh for service sector. (मैन्युफैक्चरिंग के लिए ₹25 लाख, सर्विस के लिए ₹10 लाख)",
                "mudra": "Up to ₹10 Lakh across Shishu, Kishor, and Tarun categories. (₹10 लाख तक)"
            },
            {
                "name_en": "Government Subsidy",
                "name_hi": "सरकारी सब्सिडी",
                "pmegp": "15% to 35% subsidy depending on category and location. (15% से 35% तक सब्सिडी मिलती है)",
                "mudra": "No subsidy (it is a standard commercial credit facility). (कोई सब्सिडी नहीं मिलती)"
            },
            {
                "name_en": "Collateral Required",
                "name_hi": "कोलैटरल (बंधक) आवश्यकता",
                "pmegp": "No collateral required (covered under CGTMSE guarantee). (कोई कोलैटरल नहीं)",
                "mudra": "No collateral required (collateral-free credit). (कोई कोलैटरल नहीं)"
            },
            {
                "name_en": "Eligibility Criteria",
                "name_hi": "पात्रता मापदंड",
                "pmegp": "Age 18+; Class VIII pass required for loans above ₹10L (mfg) or ₹5L (svc). (18 वर्ष से अधिक, 8वीं पास कुछ ऋणों के लिए)",
                "mudra": "Any Indian citizen with a viable business plan. (कोई भी भारतीय नागरिक)"
            }
        ]
    },
    "mudra_vs_cgtmse": {
        "title_en": "Comparison: MUDRA vs CGTMSE Guarantee",
        "title_hi": "तुलना: MUDRA बनाम CGTMSE गारंटी",
        "parameters": [
            {
                "name_en": "Core Nature",
                "name_hi": "मूल स्वरूप",
                "mudra": "A direct loan scheme provided by banks/NBFCs to borrowers. (बैंकों द्वारा दिया जाने वाला सीधा ऋण)",
                "cgtmse": "A credit guarantee trust that covers loans given by banks. (बैंकों के ऋण को सुरक्षा देने वाली गारंटी ट्रस्ट)"
            },
            {
                "name_en": "Maximum Funding Limit",
                "name_hi": "अधिकतम सीमा",
                "mudra": "Up to ₹10 Lakh. (₹10 लाख तक)",
                "cgtmse": "Up to ₹2 Crore (guarantees loans up to this limit). (₹2 करोड़ तक)"
            },
            {
                "name_en": "Target Borrowers",
                "name_hi": "लक्षित उद्यमी",
                "mudra": "Micro units, retail stores, small traders, artisans. (सूक्ष्म इकाइयां, छोटे व्यापारी, कारीगर)",
                "cgtmse": "Manufacturing and service Micro & Small Enterprises (MSEs). (सूक्ष्म एवं लघु विनिर्माण और सेवा इकाइयां)"
            },
            {
                "name_en": "Collateral Fee",
                "name_hi": "कोलैटरल फीस",
                "mudra": "No special fee. (कोई विशेष फीस नहीं)",
                "cgtmse": "Annual guarantee fee (approx 0.5% to 1.5% charged on the loan amount). (वार्षिक गारंटी फीस लगती है)"
            }
        ]
    }
}

def generate_comparison(query: str) -> Optional[Dict]:
    """
    Analyzes query and returns a matching comparison config if found.
    """
    q = query.lower()
    if "pmegp" in q and ("mudra" in q or "मुद्रा" in q):
        return COMPARISONS["pmegp_vs_mudra"]
    elif ("mudra" in q or "मुद्रा" in q) and ("cgtmse" in q or "guarantee" in q or "गारंटी" in q):
        return COMPARISONS["mudra_vs_cgtmse"]
    elif "pmegp" in q and ("cgtmse" in q or "guarantee" in q or "गारंटी" in q):
        # Fallback comparison info using pmegp_vs_mudra structure
        return {
            "title_en": "Comparison: PMEGP vs CGTMSE",
            "title_hi": "तुलना: PMEGP बनाम CGTMSE",
            "parameters": [
                {
                    "name_en": "Nature",
                    "name_hi": "प्रकृति",
                    "pmegp": "Direct credit-linked subsidy scheme for setting up new units. (नई इकाई के लिए सब्सिडी युक्त ऋण)",
                    "cgtmse": "Credit guarantee coverage scheme for bank loans. (बैंक ऋण के लिए सुरक्षा गारंटी)"
                },
                {
                    "name_en": "Max Limit",
                    "name_hi": "अधिकतम सीमा",
                    "pmegp": "₹25 Lakh for manufacturing, ₹10 Lakh for service. (₹25 लाख विनिर्माण, ₹10 लाख सेवा)",
                    "cgtmse": "Loans up to ₹2 Crore can be covered. (₹2 करोड़ तक के ऋण)"
                }
            ]
        }
    return None
