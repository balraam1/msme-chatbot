import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import streamlit as st

# Apply custom theme immediately to prevent layout pop/flicker
from admin.theme import apply_custom_theme, update_plotly_layout
apply_custom_theme()

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from app.db import get_db_connection

# Theme Color (aligned with chatbot primary color)
BIHAR_BLUE = "#3b82f6"

# Enforce authentication
if "authentication_status" not in st.session_state or not st.session_state["authentication_status"]:
    st.error("Please login from the main page first.")
    st.stop()

st.title("Chatbot Analytics Dashboard")

# Date range selector (default: last 30 days)
st.write("### Date Filters")
col_f1, col_f2 = st.columns(2)
with col_f1:
    start_date = st.date_input("Start Date", value=datetime.now().date() - timedelta(days=30))
with col_f2:
    end_date = st.date_input("End Date", value=datetime.now().date())

# Load events data
@st.cache_data(ttl=10) # cache for 10 seconds
def load_events_data(start, end):
    conn = get_db_connection()
    
    # Convert start/end dates to datetime objects for database-agnostic range matching
    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(end, datetime.max.time())
    
    # Query events
    query = """
        SELECT * FROM events 
        WHERE timestamp >= ? AND timestamp <= ?
    """
    df_events = pd.read_sql_query(query, conn, params=(start_dt, end_dt))
    
    # Query grievances
    query_grv = """
        SELECT * FROM grievances 
        WHERE created_at >= ? AND created_at <= ?
    """
    df_grv = pd.read_sql_query(query_grv, conn, params=(start_dt, end_dt))
    conn.close()
    
    # Parse timestamps
    df_events["timestamp"] = pd.to_datetime(df_events["timestamp"], format='mixed')
    df_grv["created_at"] = pd.to_datetime(df_grv["created_at"], format='mixed')
    return df_events, df_grv

df_events, df_grv = load_events_data(start_date, end_date)

if df_events.empty:
    st.warning("No analytics events logged in this date range.")
    st.stop()

# Initialize tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Overview", 
    "Intent & Schemes", 
    "Grievance Funnel", 
    "Performance",
    "Drop-off Analysis",
    "Sentiment Insights"
])

# ---------------------------------------------------------------------------
# TAB 1 — OVERVIEW
# ---------------------------------------------------------------------------
with tab1:
    st.header("Overall Key Metrics")
    
    # Metric Calculations
    total_sessions = df_events["session_id"].nunique()
    total_messages = len(df_events[df_events["event_type"] == "message"])
    grievances_submitted = len(df_grv)
    
    response_times = df_events[df_events["response_ms"].notnull()]["response_ms"]
    avg_response_time = int(response_times.mean()) if not response_times.empty else 0
    
    # Render metric cards
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Sessions", total_sessions)
    m2.metric("Total Messages", total_messages)
    m3.metric("Grievance Tickets", grievances_submitted)
    m4.metric("Avg Response Time (ms)", f"{avg_response_time} ms")
    
    # Line Chart: Daily Active Sessions
    st.subheader("Daily Active Sessions")
    daily_sessions = df_events.groupby(df_events["timestamp"].dt.date)["session_id"].nunique().reset_index()
    daily_sessions.columns = ["date", "active_sessions"]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily_sessions["date"], 
        y=daily_sessions["active_sessions"],
        mode='lines+markers',
        line=dict(color="#C4FF32", width=3),
        marker=dict(size=6, color="#C4FF32")
    ))
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Sessions Count",
        margin=dict(l=20, r=20, t=20, b=20)
    )
    fig = update_plotly_layout(fig)
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# TAB 2 — INTENT & SCHEME ANALYSIS
# ---------------------------------------------------------------------------
with tab2:
    st.header("Intent & Scheme Distribution")
    col_t2_1, col_t2_2 = st.columns(2)
    
    with col_t2_1:
        st.subheader("Top Intents by Message Count")
        intent_df = df_events[df_events["intent"].notnull()].groupby("intent").size().reset_index(name="count")
        intent_df = intent_df.sort_values(by="count", ascending=True).tail(10)
        
        fig_intent = px.bar(
            intent_df, 
            x="count", 
            y="intent", 
            orientation='h',
            color_discrete_sequence=["#C4FF32"]
        )
        fig_intent = update_plotly_layout(fig_intent)
        st.plotly_chart(fig_intent, use_container_width=True)

    with col_t2_2:
        st.subheader("Language Distribution")
        # Ensure language counts are populated
        lang_df = df_events[df_events["language"].notnull()].groupby("language").size().reset_index(name="count")
        if lang_df.empty:
            lang_df = pd.DataFrame([{"language": "hi", "count": 1}]) # fallback template
            
        fig_lang = px.pie(
            lang_df, 
            values="count", 
            names="language",
            color_discrete_sequence=["#C4FF32", "#3B82F6", "#8B5CF6", "#F59E0B"]
        )
        fig_lang = update_plotly_layout(fig_lang, light_primary="#22c55e")
        fig_lang.update_layout(margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_lang, use_container_width=True)
        
    st.subheader("Top Mentioned MSME Schemes")
    # Combine schemes mentioned in events and in grievances
    scheme_events = df_events[df_events["scheme_name"].notnull() & (df_events["scheme_name"] != "Other")]["scheme_name"]
    scheme_grvs = df_grv[df_grv["scheme_name"].notnull() & (df_grv["scheme_name"] != "Other")]["scheme_name"]
    combined_schemes = pd.concat([scheme_events, scheme_grvs]).value_counts().reset_index()
    combined_schemes.columns = ["scheme_name", "mentions"]
    
    fig_scheme = px.bar(
        combined_schemes.head(10),
        x="mentions",
        y="scheme_name",
        orientation='h',
        color_discrete_sequence=["#C4FF32"]
    )
    fig_scheme = update_plotly_layout(fig_scheme)
    st.plotly_chart(fig_scheme, use_container_width=True)

# ---------------------------------------------------------------------------
# TAB 3 — GRIEVANCE FUNNEL
# ---------------------------------------------------------------------------
with tab3:
    st.header("Grievance Conversion Funnel")
    
    # Event counts for funnel steps
    session_starts = df_events[df_events["event_type"] == "session_start"]["session_id"].nunique()
    messages_sent = df_events[df_events["event_type"] == "message"]["session_id"].nunique()
    grv_submits = df_events[df_events["event_type"] == "grievance_submit"]["session_id"].nunique()
    
    # Resolved from grievances table
    resolved_grvs = len(df_grv[df_grv["status"] == "Resolved"])
    
    funnel_data = dict(
        number=[session_starts, messages_sent, grv_submits, resolved_grvs],
        stage=["session_start", "message", "grievance_submit", "resolved"]
    )
    
    fig_funnel = px.funnel(funnel_data, y="stage", x="number", color_discrete_sequence=["#C4FF32"])
    fig_funnel = update_plotly_layout(fig_funnel)
    st.plotly_chart(fig_funnel, use_container_width=True)

    col_t3_1, col_t3_2 = st.columns(2)
    with col_t3_1:
        st.subheader("Severity Distribution")
        severity_counts = df_grv["severity"].value_counts().reset_index()
        severity_counts.columns = ["severity", "count"]
        fig_sev = px.bar(severity_counts, x="severity", y="count", color="severity",
                         color_discrete_map={"Critical": "#FF4455", "High": "#F59E0B", "Medium": "#3B82F6", "Low": "#22C55E"})
        fig_sev = update_plotly_layout(fig_sev)
        st.plotly_chart(fig_sev, use_container_width=True)
        
    with col_t3_2:
        st.subheader("Grievance Type Distribution")
        type_counts = df_grv["grievance_type"].value_counts().reset_index()
        type_counts.columns = ["grievance_type", "count"]
        fig_type = px.bar(type_counts, x="grievance_type", y="count", color_discrete_sequence=["#C4FF32"])
        fig_type = update_plotly_layout(fig_type)
        st.plotly_chart(fig_type, use_container_width=True)

    st.write("---")
    st.write("### Export Events Log")
    csv_events = df_events.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Events Log as CSV",
        data=csv_events,
        file_name=f"events_log_{start_date}_to_{end_date}.csv",
        mime="text/csv"
    )

# ---------------------------------------------------------------------------
# TAB 4 — PERFORMANCE
# ---------------------------------------------------------------------------
with tab4:
    st.header("Response Time and Fallback Performance")
    
    col_t4_1, col_t4_2 = st.columns(2)
    with col_t4_1:
        st.subheader("Hourly Avg Response Time (ms)")
        # Resample response_ms by hour
        df_perf = df_events[df_events["response_ms"].notnull()].copy()
        if not df_perf.empty:
            df_perf.set_index("timestamp", inplace=True)
            hourly_perf = df_perf["response_ms"].resample("h").mean().reset_index()
            
            fig_perf = px.line(hourly_perf, x="timestamp", y="response_ms", color_discrete_sequence=["#C4FF32"])
            fig_perf.update_yaxes(title="Avg Latency (ms)")
            fig_perf = update_plotly_layout(fig_perf)
            st.plotly_chart(fig_perf, use_container_width=True)
        else:
            st.info("No latency data recorded yet.")
            
    with col_t4_2:
        st.subheader("Response Latency Distribution")
        if not df_perf.empty:
            fig_hist = px.histogram(df_perf, x="response_ms", nbins=30, color_discrete_sequence=["#3B82F6"])
            fig_hist.update_xaxes(title="Response Time (ms)")
            fig_hist = update_plotly_layout(fig_hist)
            st.plotly_chart(fig_hist, use_container_width=True)
        else:
            st.info("No latency distribution available.")

    # Fallback Rate Calculation
    fallback_msgs = len(df_events[df_events["is_fallback"].fillna(False).astype(bool) == True])
    total_msgs = len(df_events[df_events["event_type"] == "message"])
    fallback_rate = (fallback_msgs / total_msgs * 100) if total_msgs > 0 else 0.0
    
    st.metric("Fallback Rate (%)", f"{fallback_rate:.2f}%", help="Percentage of citizen messages resulting in bot fallback / unknown answers.")

# ---------------------------------------------------------------------------
# TAB 5 — DROP-OFF ANALYSIS
# ---------------------------------------------------------------------------
with tab5:
    st.header("Citizen Engagement Drop-off Analysis")
    
    # 1. Bounced Sessions (Sessions with only 1 message)
    session_msg_counts = df_events[df_events["event_type"] == "message"].groupby("session_id").size()
    bounced_sessions = session_msg_counts[session_msg_counts == 1]
    bounced_count = len(bounced_sessions)
    bounce_rate = (bounced_count / total_sessions * 100) if total_sessions > 0 else 0.0
    
    st.metric("Bounced Sessions (Single Message)", value=f"{bounced_count} ({bounce_rate:.1f}%)")

    # 2. Scheme search drop-offs
    # Sessions that had event_type='scheme_search' (or intent matches scheme/eligibility) but no grievance or ticket resolved
    searched_sessions = set(df_events[df_events["intent"].str.contains("scheme|eligibility|guidance", case=False, na=False)]["session_id"])
    grievanced_sessions = set(df_grv["session_id"])
    dropoff_search = searched_sessions - grievanced_sessions
    
    st.metric("Search-to-Grievance Drop-off Count", value=len(dropoff_search), 
              help="Sessions where citizens searched or asked about schemes but did not complete a grievance ticket.")

    # 3. Last Event Before Session Ended
    st.subheader("Last User Event Before Drop-off")
    # Get the last event for each session
    last_events = df_events.sort_values(by="timestamp").groupby("session_id").last().reset_index()
    last_event_counts = last_events["event_type"].value_counts().reset_index()
    last_event_counts.columns = ["last_event_type", "count"]
    
    fig_drop = px.bar(
        last_event_counts,
        x="count",
        y="last_event_type",
        orientation='h',
        color_discrete_sequence=["#FF4455"]
    )
    fig_drop = update_plotly_layout(fig_drop)
    st.plotly_chart(fig_drop, use_container_width=True)

# ---------------------------------------------------------------------------
# TAB 6 — SENTIMENT INSIGHTS
# ---------------------------------------------------------------------------
with tab6:
    st.header("Citizen Sentiment Analysis")
    
    # Filter messages only
    df_sent = df_events[df_events["event_type"] == "message"].copy()
    
    if not df_sent.empty:
        # Fill missing values for legacy rows
        if "sentiment" in df_sent.columns:
            df_sent["sentiment"] = df_sent["sentiment"].fillna("Neutral")
        else:
            df_sent["sentiment"] = "Neutral"
            
        sentiment_counts = df_sent["sentiment"].value_counts().reset_index()
        sentiment_counts.columns = ["sentiment", "count"]
        
        # Consistent color map for sentiments
        color_map = {
            "Positive": "#22C55E",    # Emerald green
            "Neutral": "#3B82F6",     # Blue
            "Frustrated": "#F59E0B",  # Orange
            "Angry": "#FF4455"        # Red
        }
        
        col_t6_1, col_t6_2 = st.columns(2)
        
        with col_t6_1:
            st.subheader("Overall Sentiment Share")
            fig_sent_pie = px.pie(
                sentiment_counts,
                values="count",
                names="sentiment",
                color="sentiment",
                color_discrete_map=color_map
            )
            fig_sent_pie = update_plotly_layout(fig_sent_pie)
            fig_sent_pie.update_layout(margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig_sent_pie, use_container_width=True)
            
        with col_t6_2:
            st.subheader("Sentiment Intensity Counts")
            fig_sent_bar = px.bar(
                sentiment_counts,
                x="sentiment",
                y="count",
                color="sentiment",
                color_discrete_map=color_map
            )
            fig_sent_bar = update_plotly_layout(fig_sent_bar)
            st.plotly_chart(fig_sent_bar, use_container_width=True)
            
        # Sentiment vs Intent Stacked Chart
        st.subheader("Sentiment Distribution by Conversation Intent")
        if "intent" in df_sent.columns:
            intent_sent = df_sent.groupby(["intent", "sentiment"]).size().reset_index(name="count")
            fig_intent_sent = px.bar(
                intent_sent,
                x="intent",
                y="count",
                color="sentiment",
                color_discrete_map=color_map,
                barmode="stack"
            )
            fig_intent_sent = update_plotly_layout(fig_intent_sent)
            st.plotly_chart(fig_intent_sent, use_container_width=True)
            
        # High-Alert queries feed
        st.subheader("Citizen Queries Needing Attention")
        high_alert_queries = df_sent[df_sent["sentiment"].isin(["Frustrated", "Angry"])]
        if not high_alert_queries.empty:
            alert_display = high_alert_queries.sort_values(by="timestamp", ascending=False).head(10)
            if "query_text" in alert_display.columns:
                display_df = alert_display[["timestamp", "intent", "sentiment", "query_text"]].copy()
                display_df.columns = ["Timestamp", "Intent", "Sentiment", "User Query"]
                display_df["User Query"] = display_df["User Query"].fillna("N/A")
            else:
                display_df = alert_display[["timestamp", "intent", "sentiment"]].copy()
                display_df.columns = ["Timestamp", "Intent", "Sentiment"]
                
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("No frustrated or angry user queries logged in this date range.")
    else:
        st.info("No query logs available to calculate sentiment distribution.")
