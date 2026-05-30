# MSME Saathi - Standout Features & Government Impact

This document outlines the core capabilities, architectural highlights, and administrative benefits of the **MSME Saathi Chatbot** for government officials and stakeholders.

---

## 🌐 1. Local Language & Dialect Support (Bhashini Integration)
* **Regional Language Capabilities**: The chatbot natively supports local dialects spoken in Bihar, including **Bhojpuri (भोजपुरी)**, **Maithili (मैथिली)**, and **Bengali (বাংলা)**, alongside English and Hindi.
* **Auto-Language Detection**: Automatically detects the language or script the citizen is using, updating all buttons, placeholders, speech recognition, and replies dynamically.

---

## 📝 2. End-to-End Grievance Redressal Pipeline
* **NLP-Driven Ticket Generation**: Citizens can explain their complaint in conversational language. The chatbot automatically extracts crucial structured data (e.g., Bank Name, Dispute Amount, Delay Days, and Contact Number) to register a ticket.
* **Callback Scheduling**: Captures verified 10-digit mobile numbers during complaint registration and flags them for call scheduling, making it easy for officials to follow up.
* **Instant Status Checks**: Citizens can query the exact live status of their grievance in real-time by entering their unique Ticket ID directly in the chat.

---

## 🔒 3. Data Privacy & Security (DPDP Compliance)
* **Built-in PII Scrubber**: Automatically detects, logs, and masks sensitive personal identifiers (such as Aadhaar, PAN, Bank IFSC codes, and mobile numbers) inside query logs to protect citizen privacy.
* **DPDP Guidelines**: Enforces consent rules and lists privacy storage disclosures solely at the footer of finalized ticket confirmations.

---

## 🔍 4. Semantic Scheme Search (RAG)
* **Intelligent Document Ingestion**: Connected to a local vector store (ChromaDB) to search through Bihar state and central MSME schemes (PMEGP, MUDRA, Udyam).
* **Custom Scheme Recommendations**: Recommends appropriate schemes matching the citizen's specific profile (e.g., investment size, residence, sector) instead of prompting them to read static, complex guidelines.

---

## ⚙️ 5. Stateful Interactive Conversational Wizards
* **Guided Questionnaires**: Uses stateful multi-turn agents (LangGraph) to guide users step-by-step through checking eligibility or filling applications in their preferred language.

---

## 📊 6. Comprehensive Administrative Dashboard
* **Admin Control Center**: A custom Streamlit-based panel that allows government officials to:
  * **Track Grievances**: Review, search, inspect, and update the status of citizen tickets.
  * **Manage Knowledge Base**: Upload new government notifications or scheme guidelines and re-index the vector database instantly with a single click.
  * **Monitor Analytics**: Inspect real-time traffic statistics, system latency, active sessions, and system uptime.
