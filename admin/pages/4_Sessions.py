import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import streamlit as st

# Apply custom theme immediately to prevent layout pop/flicker
from admin.theme import apply_custom_theme
apply_custom_theme()

import requests
import pandas as pd

# Enforce authentication
if "authentication_status" not in st.session_state or not st.session_state["authentication_status"]:
    st.error("Please login from the main page first.")
    st.stop()

st.title("Active User Sessions")

# Fetch session stats and list
def fetch_sessions():
    try:
        from app.auth import create_admin_token
        token = create_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        chatbot_api_url = os.environ.get("CHATBOT_API_URL", "http://127.0.0.1:8000")
        r = requests.get(f"{chatbot_api_url}/internal/session-stats", headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json().get("sessions", [])
        else:
            st.error(f"Could not connect to FastAPI server to retrieve sessions: Status {r.status_code} - {r.text}")
    except Exception as e:
        st.error(f"Could not connect to FastAPI server to retrieve sessions: {e}")
    return []

sessions_list = fetch_sessions()

if not sessions_list:
    st.info("No active chat sessions found.")
else:
    # Build dataframe for presentation
    df_sessions = pd.DataFrame(sessions_list)
    
    # Format table for display (truncate session_id)
    display_df = df_sessions.copy()
    display_df["session_id_short"] = display_df["session_id"].apply(lambda x: x[:10] + "..." if len(x) > 10 else x)
    
    st.dataframe(
        display_df[["session_id_short", "started_at", "message_count", "last_active", "language"]],
        use_container_width=True,
        hide_index=True
    )
    
    # Action buttons for each active session
    st.write("### Session Actions")
    for session in sessions_list:
        sid = session["session_id"]
        sid_short = sid[:10] + "..." if len(sid) > 10 else sid
        
        col1, col2 = st.columns([8, 2])
        with col1:
            st.write(f"**Session {sid_short}** ({session['message_count']} messages, last active {session['last_active']})")
        with col2:
            if st.button("Terminate Session", key=f"term_{sid}", type="primary"):
                try:
                    from app.auth import create_admin_token
                    token = create_admin_token()
                    headers = {"Authorization": f"Bearer {token}"}
                    chatbot_api_url = os.environ.get("CHATBOT_API_URL", "http://127.0.0.1:8000")
                    r = requests.delete(f"{chatbot_api_url}/internal/session/{sid}", headers=headers, timeout=10)
                    if r.status_code == 200:
                        st.success(f"Session {sid_short} terminated successfully!")
                        st.rerun()
                    else:
                        st.error(f"Failed to terminate session: {r.text}")
                except Exception as ex:
                    st.error(f"Error calling terminate endpoint: {ex}")
