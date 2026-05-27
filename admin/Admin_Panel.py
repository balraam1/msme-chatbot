import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import time
import requests
import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
from datetime import datetime

# Load environment configurations
from dotenv import load_dotenv
load_dotenv()

# Track start time for uptime
if "start_time" not in st.session_state:
    st.session_state["start_time"] = time.time()

# Configure page
st.set_page_config(
    page_title="MSME Saathi — Backend Admin Panel",
    page_icon="🎫",
    layout="wide"
)

# Apply custom theme
from admin.theme import apply_custom_theme
apply_custom_theme()

# Load authenticator config
config_path = os.path.join(os.path.dirname(__file__), "auth_config.yaml")
with open(config_path) as file:
    config = yaml.load(file, Loader=SafeLoader)

# Override with environment variable values
admin_username = os.environ.get("ADMIN_USERNAME", "admin")
admin_password_hash = os.environ.get("ADMIN_PASSWORD_HASH", "")

if admin_username and admin_password_hash:
    config['credentials']['usernames'][admin_username] = {
        'email': 'admin@msmesaathi.gov.in',
        'name': 'MSME Saathi Admin',
        'password': admin_password_hash
    }

# Initialize Authenticator
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# Render Login Form
authenticator.login('main')

authentication_status = st.session_state.get("authentication_status")
username = st.session_state.get("username")
name = st.session_state.get("name")

if authentication_status is False:
    st.error('Username/password is incorrect')
elif authentication_status is None:
    st.warning('Please enter your username and password')
elif authentication_status:
    # Authenticated!

    # --- TOP BAR: Welcome + Logout (top-right, small) ---
    # --- TOP BAR: Title + Welcome & Logout (in the same row) ---
    top_col, auth_col = st.columns([7.8, 2.2])
    with top_col:
        st.markdown(
            """
            <h1 style="text-align:left; font-family:'Syne',sans-serif; font-size:26px; font-weight:700; color:#F2F2F5; letter-spacing:-0.02em; margin:8px 0; padding:0;">
                🎫 MSME Saathi — Administrative Control Center
            </h1>
            """,
            unsafe_allow_html=True
        )
    with auth_col:
        st.markdown(
            f"""
            <div class="welcome-text-container" style="text-align:right; white-space:nowrap; margin-top:2px; margin-bottom:-4px;">
                <span style="font-family:'Syne',sans-serif; font-size:12px; font-weight:500; color:rgba(242,242,245,0.55); letter-spacing:0.04em;">
                    Welcome, {name}
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )
        authenticator.logout('Logout', 'main', key='logout_btn')

    # Tight divider
    st.markdown("<hr style='margin: 8px 0; border: 0; border-top: 1px solid rgba(255,255,255,0.06);'>", unsafe_allow_html=True)

    # --- SYSTEM HEALTH DASHBOARD ---
    st.markdown("<h3 style='margin: 8px 0 4px 0; font-family:\"Syne\",sans-serif; font-size:18px; font-weight:700; color:#F2F2F5;'>🖥️ System Health Dashboard</h3>", unsafe_allow_html=True)

    # 1. Fetch ChromaDB document count
    db_count = 0
    try:
        import sys
        import importlib
        if 'app.knowledge_base' in sys.modules:
            try:
                importlib.reload(sys.modules['app.knowledge_base'])
            except Exception:
                pass
        from app.knowledge_base import get_collection
        collection_ref = get_collection()
        if collection_ref is not None:
            db_count = collection_ref.count()
        else:
            db_count = "Offline"
    except Exception:
        db_count = "Error"

    # 2. Fetch SQLite grievances count
    grv_count = 0
    try:
        from app.db import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM grievances")
        grv_count = cursor.fetchone()[0]
        conn.close()
    except Exception:
        grv_count = "Error"

    # 3. Fetch active sessions
    sessions_count = "N/A"
    try:
        r = requests.get("http://127.0.0.1:8000/internal/session-stats", timeout=10)
        if r.status_code == 200:
            sessions_count = r.json().get("active_sessions", 0)
    except Exception:
        pass

    # 4. Calculate Uptime (Ticks dynamically second by second using Streamlit fragment)
    @st.fragment(run_every=1)
    def render_uptime_card():
        uptime_seconds = int(time.time() - st.session_state["start_time"])
        uptime_str = f"{uptime_seconds // 3600}h {(uptime_seconds % 3600) // 60}m {uptime_seconds % 60}s"
        st.metric(label="Uptime", value=uptime_str)

    # Render all 4 metrics in a single horizontal row
    h1, h2, h3, h4 = st.columns(4)
    h1.metric(label="ChromaDB Corpus Chunks", value=db_count)
    h2.metric(label="Total SQLite Grievances", value=grv_count)
    h3.metric(label="Active Chat Sessions", value=sessions_count)
    with h4:
        render_uptime_card()

    # --- BOT PERFORMANCE & ACTIVITY METRICS ---
    st.markdown("<h3 style='margin: 12px 0 4px 0; font-family:\"Syne\",sans-serif; font-size:18px; font-weight:700; color:#F2F2F5;'>📊 Bot Performance & Activity Metrics</h3>", unsafe_allow_html=True)

    # 5. Fetch Total Messages Processed
    msg_count = 0
    try:
        from app.db import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM events WHERE event_type = 'message'")
        msg_count = cursor.fetchone()[0]
        conn.close()
    except Exception:
        msg_count = "Error"

    # 6. Fetch Scheduled Appointments
    appt_count = 0
    try:
        from app.db import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM appointments")
        appt_count = cursor.fetchone()[0]
        conn.close()
    except Exception:
        appt_count = "Error"

    # 7. Fetch Avg Response Time
    avg_resp_time = "N/A"
    try:
        from app.db import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT AVG(response_ms) FROM events WHERE response_ms IS NOT NULL")
        val = cursor.fetchone()[0]
        if val is not None:
            avg_resp_time = f"{int(val)} ms"
        conn.close()
    except Exception:
        avg_resp_time = "Error"

    # 8. Fetch Resolved Grievances
    resolved_count = 0
    try:
        from app.db import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM grievances WHERE status = 'Resolved'")
        resolved_count = cursor.fetchone()[0]
        conn.close()
    except Exception:
        resolved_count = "Error"

    # Render these in another row of 4 columns
    h5, h6, h7, h8 = st.columns(4)
    h5.metric(label="Total Messages Processed", value=msg_count)
    h6.metric(label="Scheduled Appointments", value=appt_count)
    h7.metric(label="Avg Response Time", value=avg_resp_time)
    h8.metric(label="Resolved Grievances", value=resolved_count)

    # --- OPERATIONAL & QUALITY METRICS (third row) ---
    st.markdown("<h3 style='margin: 12px 0 4px 0; font-family:\"Syne\",sans-serif; font-size:18px; font-weight:700; color:#F2F2F5;'>⚙️ Operational & Quality Metrics</h3>", unsafe_allow_html=True)

    # 9. Fetch Critical & High Severity Grievances
    critical_high_count = 0
    try:
        from app.db import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM grievances WHERE severity IN ('Critical', 'High')")
        critical_high_count = cursor.fetchone()[0]
        conn.close()
    except Exception:
        critical_high_count = "Error"

    # 10. Fetch Hindi conversations (language = 'hi')
    hindi_count = 0
    try:
        from app.db import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM events WHERE language = 'hi'")
        hindi_count = cursor.fetchone()[0]
        conn.close()
    except Exception:
        hindi_count = "Error"

    # 11. Fetch Fallback Queries (is_fallback = 1)
    fallback_count = 0
    try:
        from app.db import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM events WHERE is_fallback = 1")
        fallback_count = cursor.fetchone()[0]
        conn.close()
    except Exception:
        fallback_count = "Error"

    # 12. Fetch Pending Appointments
    pending_appt_count = 0
    try:
        from app.db import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM appointments WHERE status = 'Pending'")
        pending_appt_count = cursor.fetchone()[0]
        conn.close()
    except Exception:
        pending_appt_count = "Error"

    # Render these in the third row of 4 columns
    h9, h10, h11, h12 = st.columns(4)
    h9.metric(label="Urgent Grievances (Critical/High)", value=critical_high_count)
    h10.metric(label="Hindi Language Interactions", value=hindi_count)
    h11.metric(label="Fallback Bot Responses", value=fallback_count)
    h12.metric(label="Pending Appointments", value=pending_appt_count)

