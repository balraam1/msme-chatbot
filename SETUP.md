# MSME Saathi - System Cloning & Deployment Guide

This document details the step-by-step instructions to configure, initialize, and deploy the **MSME Saathi Chatbot** and **Admin Panel** on a new system.

---

## 📋 Prerequisites
Before starting, ensure the target system has the following dependencies installed:
* **Git**: To clone the repository.
* **Python (version 3.10, 3.11, or 3.12)**: Python 3.10–3.12 is recommended for database and NLP library compatibility.

---

## 🚀 Deployment Steps

### Step 1: Clone the Repository
Clone the codebase to your target deployment environment and navigate to the project root:
```bash
git clone <your-repository-url>
cd bilingual-chatbot
```

### Step 2: Configure Virtual Environment
Set up a localized Python virtual environment (`venv`) to isolate dependencies:

* **Windows (PowerShell)**:
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate
  ```
* **macOS / Linux**:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### Step 3: Install Core Dependencies
Install the required python packages and download the SpaCy English NLP model for PII filtering:
```bash
# Install packages
pip install -r requirements.txt

# Download NLP model for Presidio Analyzer
python -m spacy download en_core_web_sm
```

### Step 4: Configure Local Environment Variables
Create a new file named `.env` in the root directory (where `main.py` is located) and define the following variables:
```ini
# Gemini API Key (Required for Chatbot LLM)
GEMINI_API_KEY=AIzaSyDluLqcr6z0... # Replace with active Gemini API key

# Server Port
PORT=8000

# Admin Panel Authentication credentials (Username & Pass Hash)
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=$2b$12$m39YEouF6pNwxOWZlfWpFOD.8hqGUWo3Cmj.jnR8rX5A/Oz0wk4zq
ADMIN_JWT_SECRET=9e30a515ea1c40ea8e4c7943ff7f68c4

# Bhashini Translation API Credentials (Required for Regional Languages translation)
BHASHINI_API_KEY=your_bhashini_api_key_here
BHASHINI_USER_ID=your_bhashini_userid_here

# SMTP Email Configuration (Required for Grievance Email Alerts)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-email-app-password
```

### Step 5: Initialize Databases
1. **SQLite Grievance Database (`data/msme_saathi.db`)**:
   * The database tables are automatically generated on your first server launch by the backend initialization scripts. No manual action is needed.
2. **Vector Database (`chroma_db/`)**:
   * To build the vector index for scheme search, run:
     ```bash
     python scrape_bihar_schemes.py
     ```
   * Alternatively, once the servers are active, open the Admin Dashboard, navigate to the **Document Manager** page, and click **Ingest into ChromaDB**.

---

## ⚡ Running the Services

Launch both components in separate terminal sessions:

### 1. Launch FastAPI Chatbot Backend
Serves the chatbot API and hosts the user-facing web interface:
```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
* **User Chatbot URL**: [http://127.0.0.1:8000](http://127.0.0.1:8000)

### 2. Launch Streamlit Admin Panel
Hosts the grievance management and documents dashboard:
```bash
streamlit run admin/Admin_Panel.py
```
* **Admin Dashboard URL**: [http://127.0.0.1:8501](http://127.0.0.1:8501)
