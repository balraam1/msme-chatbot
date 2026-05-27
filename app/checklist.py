# app/checklist.py
from typing import Dict, List, Optional

DOCUMENT_CHECKLISTS: Dict[str, Dict] = {
    "udyam": {
        "title": "Udyam Registration Document Checklist",
        "description": "Udyam Registration is fully online, paperless, and free of charge. No physical documents need to be uploaded.",
        "prerequisites": [
            "Aadhaar Number (linked to an active mobile number for OTP verification)",
            "Permanent Account Number (PAN) of the business or proprietor",
            "GST Identification Number (GSTIN) - mandatory for businesses unless exempt under GST rules"
        ],
        "common_errors": [
            "Aadhaar mobile number not active (OTP is required to sign the application)",
            "Using unofficial or fraudulent websites charging fees (the official portal is 100% free)"
        ],
        "official_url": "https://udyamregistration.gov.in"
    },
    "pmegp": {
        "title": "PMEGP Loan Document Checklist",
        "description": "Prime Minister's Employment Generation Programme requires several documents to verify subsidy eligibility and project feasibility.",
        "prerequisites": [
            "Detailed Project Report (DPR) detailing business model, setup cost, and financial projections",
            "Passport size photograph of the applicant",
            "Aadhaar Card and PAN Card",
            "Special Category Certificate (SC/ST/OBC/Minority/Women/Ex-Servicemen) if claiming higher subsidy",
            "Rural Area Certificate from the local Gram Panchayat (if applicant's unit is in a rural area)",
            "Education Qualification Certificate (minimum VIII standard pass certificate is mandatory if the project cost is above ₹10 Lakh for manufacturing or ₹5 Lakh for service units)",
            "Authorization Letter from KVIC/KVIB/DIC (if applicable)"
        ],
        "common_errors": [
            "Project report not having detailed cost breakdown",
            "Units in urban areas applying under rural category (leads to rejection of rural subsidy)"
        ],
        "official_url": "https://www.kviconline.gov.in/pmegpplus/"
    },
    "mudra": {
        "title": "MUDRA Loan Document Checklist",
        "description": "Pradhan Mantri MUDRA Yojana offers loans under Shishu (up to ₹50k), Kishor (₹50k-₹5L), and Tarun (₹5L-₹10L) categories.",
        "prerequisites": [
            "Proof of Identity (Aadhaar Card, PAN Card, Voter ID, or Driving License)",
            "Proof of Residence (Recent utility bill, property tax receipt, or Aadhaar Card)",
            "Proof of Business Identity/Address (Udyam Registration, License, or registration papers)",
            "2 recent passport-size photographs of the applicant(s)",
            "Statement of Account from the bank for the last 6 months",
            "Asset and Liability Statement of the borrower (for Kishor and Tarun loans)",
            "Proof of category (SC/ST/OBC/Minority) if applicable",
            "Quotation of machinery/equipment or other items to be purchased with the loan funds"
        ],
        "common_errors": [
            "No quotation for equipment/machinery attached for Shishu/Kishor business asset requests",
            "Unclear business address proof"
        ],
        "official_url": "https://www.mudra.org.in"
    },
    "cgtmse": {
        "title": "CGTMSE Collateral-Free Loan Document Checklist",
        "description": "Credit Guarantee Fund Trust for Micro and Small Enterprises provides guarantee cover for collateral-free loans up to ₹2 Crore.",
        "prerequisites": [
            "Udyam Registration Certificate",
            "Detailed Business Plan & Project Report",
            "Audited Financial Statements (Balance Sheet, Profit & Loss) for the last 2-3 years (for existing units)",
            "Bank Account Statement for the last 6-12 months",
            "Income Tax Returns (ITR) of the business and promoters",
            "Loan application form of the respective Scheduled Commercial Bank/NBFC"
        ],
        "common_errors": [
            "Applying without a registered Udyam ID",
            "Existing businesses having poor credit scores or incomplete tax filings"
        ],
        "official_url": "https://www.cgtmse.in"
    },
    "zed": {
        "title": "ZED Certification Document Checklist",
        "description": "Zero Defect Zero Effect quality certification checklist for manufacturing MSMEs.",
        "prerequisites": [
            "Udyam Registration Certificate",
            "Mobile number and Email ID linked with Udyam Certificate",
            "Proof of ownership/lease of the manufacturing plant unit",
            "Company PAN Card",
            "Basic evidence of quality standard checks (such as process flows, waste records, or ISO certificates if any)"
        ],
        "common_errors": [
            "Applying under service sector (ZED is only applicable to manufacturing MSMEs)",
            "Unlinked Udyam mobile number causing verification failure"
        ],
        "official_url": "https://zed.msme.gov.in"
    }
}

def get_document_checklist(scheme_query: str) -> Optional[Dict]:
    """
    Finds and returns the document checklist for a given scheme keyword query.
    """
    query = scheme_query.lower()
    if "udyam" in query or "उद्यम" in query:
        return DOCUMENT_CHECKLISTS["udyam"]
    elif "pmegp" in query:
        return DOCUMENT_CHECKLISTS["pmegp"]
    elif "mudra" in query or "मुद्रा" in query:
        return DOCUMENT_CHECKLISTS["mudra"]
    elif "cgtmse" in query or "guarantee" in query:
        return DOCUMENT_CHECKLISTS["cgtmse"]
    elif "zed" in query:
        return DOCUMENT_CHECKLISTS["zed"]
    return None
