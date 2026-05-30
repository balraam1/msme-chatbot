import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import streamlit as st

# Apply custom theme immediately to prevent layout pop/flicker
from admin.theme import apply_custom_theme
apply_custom_theme()

import json
import time
import pandas as pd
from datetime import datetime, timedelta
from app.db import get_db_connection
from app.auth import verify_admin_token

# Enforce authentication (re-use session state from Admin_Panel.py)
if "authentication_status" not in st.session_state or not st.session_state["authentication_status"]:
    st.error("Please login from the main page first.")
    st.stop()

st.title("Grievance Management Center")

# Helper function to fetch grievances
def fetch_grievances():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM grievances ORDER BY created_at DESC", conn)
    conn.close()
    return df

df = fetch_grievances()

if df.empty:
    st.info("No grievances registered in the database yet.")
    st.stop()

# Ensure correct data types
df["created_at"] = pd.to_datetime(df["created_at"], format='mixed')

# --- SECTION A: FILTERS ---
st.write("### Filters")
col1, col2, col3 = st.columns(3)

with col1:
    # Date Range Filter
    min_date = df["created_at"].min().date() if not df.empty else datetime.now().date()
    max_date = df["created_at"].max().date() if not df.empty else datetime.now().date()
    date_range = st.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

with col2:
    # Multi-select filters
    statuses = st.multiselect("Status", options=["Open", "In Progress", "Resolved", "Closed"], default=["Open", "In Progress"])
    severities = st.multiselect("Severity", options=["Low", "Medium", "High", "Critical"], default=["Low", "Medium", "High", "Critical"])

with col3:
    schemes = st.multiselect("Scheme Name", options=list(df["scheme_name"].unique()), default=list(df["scheme_name"].unique()))
    types = st.multiselect("Grievance Type", options=list(df["grievance_type"].unique()), default=list(df["grievance_type"].unique()))

# Text Search Box
search_query = st.text_input("Search raw text / summaries", "")

# Apply Filters
filtered_df = df.copy()

# Date range filtering
if len(date_range) == 2:
    start_date, end_date = date_range
    filtered_df = filtered_df[
        (filtered_df["created_at"].dt.date >= start_date) &
        (filtered_df["created_at"].dt.date <= end_date)
    ]

# Status, Severity, Scheme, Type filtering
if statuses:
    filtered_df = filtered_df[filtered_df["status"].isin(statuses)]
if severities:
    filtered_df = filtered_df[filtered_df["severity"].isin(severities)]
if schemes:
    filtered_df = filtered_df[filtered_df["scheme_name"].isin(schemes)]
if types:
    filtered_df = filtered_df[filtered_df["grievance_type"].isin(types)]

# Search query
if search_query:
    q = search_query.lower()
    filtered_df = filtered_df[
        filtered_df["raw_text"].str.lower().str.contains(q, na=False) |
        filtered_df["summary_en"].str.lower().str.contains(q, na=False) |
        filtered_df["ticket_id"].str.lower().str.contains(q, na=False)
    ]

# Display Badge count
st.markdown(f"**Found {len(filtered_df)} matching tickets.**")

# --- SECTION B: TABLE ---
st.write("### Grievances List")

# pandas styling for Severity
def color_severity(val):
    if val == "Critical":
        return "background-color: #ffcccc; color: #cc0000; font-weight: bold;"
    elif val == "High":
        return "background-color: #ffe6cc; color: #cc6600;"
    elif val == "Medium":
        return "background-color: #ffffcc; color: #888800;"
    elif val == "Low":
        return "background-color: #e6ffcc; color: #006600;"
    return ""

# Choose display columns
display_cols = ["ticket_id", "created_at", "contact_number", "scheme_name", "grievance_type", "severity", "summary_en", "status"]
display_df = filtered_df[display_cols].copy()

# Sort for display
display_df = display_df.sort_values(by="created_at", ascending=False)

styled_df = display_df.style.map(color_severity, subset=["severity"])

st.dataframe(
    styled_df,
    use_container_width=True,
    hide_index=True
)

# Ticket Selection for Details
st.write("### Inspect & Update Ticket")
ticket_ids = ["-- Select Ticket ID --"] + list(filtered_df["ticket_id"].unique())
selected_ticket_id = st.selectbox("Select a ticket to view details or modify status:", options=ticket_ids)

# --- SECTION C: DETAILS PANEL ---
if selected_ticket_id != "-- Select Ticket ID --":
    ticket_data = filtered_df[filtered_df["ticket_id"] == selected_ticket_id].iloc[0]
    
    st.markdown("---")
    col_d1, col_d2 = st.columns(2)
    
    with col_d1:
        st.write(f"#### Ticket: **{ticket_data['ticket_id']}**")
        st.write(f"**Date Created:** {ticket_data['created_at']}")
        st.write(f"**Contact Number:** `{ticket_data['contact_number'] or 'N/A'}`")
        st.write(f"**Associated Scheme:** `{ticket_data['scheme_name']}`")
        st.write(f"**Grievance Type:** `{ticket_data['grievance_type']}`")
        st.write(f"**Severity Level:** `{ticket_data['severity']}`")
        
        st.write("**Extracted PII-Scrubbed Text:**")
        st.info(ticket_data["raw_text"])

    with col_d2:
        st.write("#### Extracted Metadata Entities")
        st.write(f"**Bank Name:** {ticket_data['entity_bank'] or 'N/A'}")
        st.write(f"**Amount mentioned:** {ticket_data['entity_amount'] or 'N/A'}")
        delay_val = ticket_data['entity_duration_days']
        delay_str = f"{delay_val} days" if delay_val else 'N/A'
        st.write(f"**Duration of delay:** {delay_str}")
        
        st.write("**English Summary:**")
        st.markdown(f"> *{ticket_data['summary_en']}*")
        st.write("**Hindi Summary:**")
        st.markdown(f"> *{ticket_data['summary_hi']}*")

    st.write("#### Update Ticket Status")
    
    status_options = ["Open", "In Progress", "Resolved", "Closed"]
    current_status_idx = status_options.index(ticket_data["status"]) if ticket_data["status"] in status_options else 0
    new_status = st.selectbox("Update Status", options=status_options, index=current_status_idx)
    
    resolution_note = st.text_area("Resolution Notes", value=ticket_data["resolution_note"] or "")
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("Update Ticket", use_container_width=True):
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE grievances SET status = ?, resolution_note = ?, updated_at = ? WHERE ticket_id = ?
            """, (new_status, resolution_note, datetime.now(), selected_ticket_id))
            conn.commit()
            conn.close()
            st.success(f"Ticket {selected_ticket_id} updated successfully!")
            
            # Log admin update action in events
            from app.middleware.analytics import log_event
            log_event(
                session_id="admin",
                event_type="ticket_update",
                extra={"ticket_id": selected_ticket_id, "new_status": new_status}
            )
            time.sleep(1)
            st.rerun()
            
    with col_btn2:
        if st.button("Delete Ticket", use_container_width=True):
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM grievances WHERE ticket_id = ?", (selected_ticket_id,))
            conn.commit()
            conn.close()
            st.warning(f"Ticket {selected_ticket_id} deleted successfully!")
            
            # Log admin delete action in events
            from app.middleware.analytics import log_event
            log_event(
                session_id="admin",
                event_type="ticket_delete",
                extra={"ticket_id": selected_ticket_id}
            )
            time.sleep(1)
            st.rerun()

    # Export Ticket as JSON
    single_ticket_json = ticket_data.to_dict()
    # Normalize datetimes for JSON serialization
    for k, v in single_ticket_json.items():
        if isinstance(v, datetime) or isinstance(v, pd.Timestamp):
            single_ticket_json[k] = str(v)
            
    st.download_button(
        label="Export This Ticket as JSON",
        data=json.dumps(single_ticket_json, indent=2, ensure_ascii=False),
        file_name=f"ticket_{selected_ticket_id}.json",
        mime="application/json"
    )

# --- SECTION D: BULK ACTIONS ---
st.markdown("---")
st.write("### Bulk Actions")

# Convert full filtered dataframe to CSV
csv_data = filtered_df.to_csv(index=False).encode('utf-8')

# Convert full filtered dataframe to JSON
bulk_dict = filtered_df.to_dict(orient="records")
for record in bulk_dict:
    for k, v in record.items():
        if isinstance(v, datetime) or isinstance(v, pd.Timestamp):
            record[k] = str(v)
bulk_json = json.dumps(bulk_dict, indent=2, ensure_ascii=False).encode('utf-8')

col_b1, col_b2 = st.columns(2)
with col_b1:
    st.download_button(
        label="Export All Filtered as CSV",
        data=csv_data,
        file_name=f"grievances_export_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )
with col_b2:
    st.download_button(
        label="Export All Filtered as JSON",
        data=bulk_json,
        file_name=f"grievances_export_{datetime.now().strftime('%Y%m%d')}.json",
        mime="application/json"
    )
