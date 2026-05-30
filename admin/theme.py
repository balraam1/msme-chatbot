import streamlit as st
import streamlit.config as _stconfig

def apply_custom_theme():
    # 1. Read theme from query parameters if set
    if "theme" in st.query_params:
        new_theme = st.query_params["theme"]
        if new_theme in ["light", "dark"] and new_theme != st.session_state.get("theme"):
            st.session_state["theme"] = new_theme
            st.rerun()

    if "theme" not in st.session_state:
        st.session_state["theme"] = "light"

    is_dark = (st.session_state["theme"] == "dark")

    # Render a small circular toggle button at the bottom of the sidebar as a custom HTML link
    with st.sidebar:
        st.markdown("<div style='flex:1;'></div>", unsafe_allow_html=True)
        toggle_text = "Change to : Light" if is_dark else "Change to : Dark"
        target_theme = "light" if is_dark else "dark"
        
        # We render a custom HTML <a> tag that styles exactly like our button and updates query params
        st.markdown(
            f"""
            <div style="display: flex; justify-content: center; width: 100%; margin: 12px 0;">
                <a href="?theme={target_theme}" target="_self" class="theme-toggle-link" style="text-decoration: none;">
                    <div class="theme-toggle-btn-circle">{toggle_text}</div>
                </a>
            </div>
            """,
            unsafe_allow_html=True
        )

    is_dark = (st.session_state["theme"] == "dark")

    # Dynamically override Streamlit's internal theme engine — this controls inline
    # styles on ALL built-in components (inputs, alerts, buttons, tables, uploaders).
    # CSS <style> blocks alone cannot override Streamlit's inline styles.
    if is_dark:
        _stconfig.set_option("theme.primaryColor", "#C4FF32")
        _stconfig.set_option("theme.backgroundColor", "#0C0C0E")
        _stconfig.set_option("theme.secondaryBackgroundColor", "#141417")
        _stconfig.set_option("theme.textColor", "#F2F2F5")
    else:
        _stconfig.set_option("theme.primaryColor", "#3B82F6")
        _stconfig.set_option("theme.backgroundColor", "#F0F4FA")
        _stconfig.set_option("theme.secondaryBackgroundColor", "#FFFFFF")
        _stconfig.set_option("theme.textColor", "#0F172A")

    if is_dark:
        custom_css = """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

        :root {
            --text-color: #F2F2F5;
            --text-color-muted: rgba(242, 242, 245, 0.55);
            --border-color: rgba(255, 255, 255, 0.06);
        }

        /* Tighter page padding and vertical gaps to prevent scrolling */
        [data-testid="stAppViewContainer"] .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 1rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            max-width: 98% !important;
        }
        [data-testid="stVerticalBlock"] {
            gap: 0.5rem !important;
        }

        /* Page background */
        html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
            font-family: 'Syne', sans-serif !important;
            background-color: #0C0C0E !important;
            color: #F2F2F5 !important;
        }

        /* Top bar header background */
        [data-testid="stHeader"] {
            background-color: rgba(12, 12, 14, 0.6) !important;
            backdrop-filter: blur(10px) !important;
        }

        /* Sidebar Navigation */
        [data-testid="stSidebar"] {
            background-color: #0F0F12 !important;
            border-right: 1px solid rgba(255,255,255,0.06) !important;
        }

        /* Hide the collapse/expand sidebar button */
        [data-testid="collapsedControl"],
        [data-testid="stSidebarCollapsedControl"] {
            display: none !important;
        }

        /* Sidebar navigation links */
        [data-testid="stSidebarNav"],
        [data-testid="stSidebarNavigation"] {
            background-color: #0F0F12 !important;
            height: auto !important;
            display: flex !important;
            flex-direction: column !important;
            justify-content: flex-start !important;
            overflow: visible !important;
        }

        [data-testid="stSidebarNav"] ul,
        [data-testid="stSidebarNavigation"] ul {
            display: flex !important;
            flex-direction: column !important;
            justify-content: flex-start !important;
            height: auto !important;
            padding: 10px 0 !important;
            margin: 0 !important;
        }

        [data-testid="stSidebarNav"] ul li,
        [data-testid="stSidebarNavigation"] ul li {
            margin: 20px 0 !important;
        }
        
        [data-testid="stSidebarNav"] ul li a,
        [data-testid="stSidebarNav"] ul li a span {
            color: rgba(242,242,245,0.50) !important;
            font-size: 13px !important;
            padding: 10px 16px !important;
            border-radius: 8px !important;
            margin: 0px 8px !important;
            transition: none !important;
            font-family: 'Syne', sans-serif !important;
            text-transform: capitalize !important;
        }

        /* Force all sidebar nav items visible — remove View more/less */
        [data-testid="stSidebarNav"] details,
        [data-testid="stSidebarNavigation"] details {
            display: contents !important;
        }
        [data-testid="stSidebarNav"] details[open],
        [data-testid="stSidebarNavigation"] details[open] {
            display: contents !important;
        }
        [data-testid="stSidebarNav"] details summary,
        [data-testid="stSidebarNavigation"] details summary {
            display: none !important;
        }
        [data-testid="stSidebarNav"] details > *:not(summary),
        [data-testid="stSidebarNavigation"] details > *:not(summary),
        [data-testid="stSidebarNav"] details:not([open]) > *:not(summary),
        [data-testid="stSidebarNavigation"] details:not([open]) > *:not(summary) {
            display: contents !important;
        }
        [data-testid="stSidebarNav"] details ul,
        [data-testid="stSidebarNavigation"] details ul {
            display: flex !important;
            flex-direction: column !important;
        }
        [data-testid="stSidebarNav"] a[kind="secondaryFormSubmit"] {
            display: none !important;
        }

        /* Circular theme toggle button */
        .theme-toggle-btn-circle {
            padding: 8px 16px !important;
            border-radius: 20px !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            font-size: 13px !important;
            font-weight: 600 !important;
            color: #F2F2F5 !important;
            margin: 0 auto !important;
            background: rgba(255,255,255,0.06) !important;
            border: 1px solid rgba(255,255,255,0.15) !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3) !important;
            transition: all 0.2s ease !important;
            cursor: pointer !important;
            width: fit-content !important;
            min-width: 160px !important;
        }
        .theme-toggle-btn-circle:hover {
            background: rgba(255,255,255,0.12) !important;
            border-color: rgba(255,255,255,0.25) !important;
            transform: scale(1.05) !important;
        }

        [data-testid="stSidebarNav"] ul li a:hover {
            background: #1C1C21 !important;
            color: #F2F2F5 !important;
        }

        /* Active Nav Item */
        [data-testid="stSidebarNav"] ul li a[aria-current="page"] {
            background: rgba(196,255,50,0.08) !important;
            color: #C4FF32 !important;
            border-left: 2px solid #C4FF32 !important;
            font-weight: 600 !important;
        }

        /* Headers */
        h1, h2, h3, h4, h5, h6 {
            font-family: 'Syne', sans-serif !important;
            font-weight: 700 !important;
            color: #F2F2F5 !important;
            letter-spacing: -0.02em !important;
        }

        h1 {
            font-size: 28px !important;
            margin-bottom: 24px !important;
        }

        /* Metric / KPI Card styling */
        div[data-testid="stMetric"] {
            background: #141417 !important;
            border: 1px solid rgba(255,255,255,0.06) !important;
            border-radius: 14px !important;
            padding: 12px 18px !important;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.04), 0 4px 16px rgba(0,0,0,0.6) !important;
            transition: all 0.2s ease !important;
        }

        div[data-testid="stMetric"]:hover {
            background: #1C1C21 !important;
            border-color: rgba(255,255,255,0.10) !important;
        }

        div[data-testid="stMetricValue"] {
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 32px !important;
            font-weight: 500 !important;
            color: #C4FF32 !important;
            margin: 8px 0 4px !important;
            line-height: 1.1 !important;
        }

        div[data-testid="stMetricLabel"] {
            font-size: 10px !important;
            letter-spacing: 0.1em !important;
            text-transform: uppercase !important;
            color: rgba(242,242,245,0.50) !important;
            font-weight: 600 !important;
        }

        /* Buttons styling */
        div.stButton > button {
            background: transparent !important;
            border: 1px solid rgba(255,255,255,0.10) !important;
            color: rgba(242,242,245,0.70) !important;
            font-size: 12px !important;
            padding: 8px 16px !important;
            border-radius: 8px !important;
            font-family: 'Syne', sans-serif !important;
            font-weight: 600 !important;
            transition: all 0.15s ease !important;
        }

        div.stButton > button:hover {
            background: #1C1C21 !important;
            border-color: rgba(255,255,255,0.20) !important;
            color: #F2F2F5 !important;
        }

        /* Right-align and make smaller the logout button inside the welcome container column */
        div[data-testid*="column"]:has(.welcome-text-container) div.stButton {
            display: flex !important;
            justify-content: flex-end !important;
            width: 100% !important;
        }
        div[data-testid*="column"]:has(.welcome-text-container) div.stButton button {
            margin-top: 4px !important;
            padding: 2px 8px !important;
            font-size: 10px !important;
            line-height: 1.1 !important;
            min-height: 24px !important;
            height: auto !important;
            width: fit-content !important;
        }

        /* Primary CTA Button */
        div.stButton > button[kind="primary"], 
        div.stButton > button.st-emotion-cache-129842a, 
        button[type="submit"] {
            background: #C4FF32 !important;
            color: #0C0C0E !important;
            font-weight: 700 !important;
            border: none !important;
            box-shadow: 0 0 16px rgba(196,255,50,0.25), 0 2px 8px rgba(0,0,0,0.4) !important;
        }

        div.stButton > button[kind="primary"]:hover, 
        div.stButton > button.st-emotion-cache-129842a:hover, 
        button[type="submit"]:hover {
            background: #D6FF5A !important;
            box-shadow: 0 0 24px rgba(196,255,50,0.4) !important;
        }

        /* Table / Dataframes styling */
        div[data-testid="stDataFrame"] {
            border: 1px solid rgba(255,255,255,0.06) !important;
            border-radius: 12px !important;
            overflow: hidden !important;
            background-color: #141417 !important;
            box-shadow: 0 4px 16px rgba(0,0,0,0.4) !important;
        }

        /* Input styling */
        div[data-testid="stTextInput"] input, 
        div[data-testid="stTextArea"] textarea, 
        div[data-testid="stSelectbox"] select,
        div[data-testid="stNumberInput"] input {
            background-color: #141417 !important;
            border: 1px solid rgba(255,255,255,0.06) !important;
            color: #F2F2F5 !important;
            border-radius: 8px !important;
            font-family: 'Syne', sans-serif !important;
        }

        div[data-testid="stTextInput"] input:focus, 
        div[data-testid="stTextArea"] textarea:focus, 
        div[data-testid="stSelectbox"] select:focus {
            border-color: #C4FF32 !important;
            box-shadow: 0 0 8px rgba(196,255,50,0.2) !important;
        }

        /* Style multiselect pills/tags with black text on green background */
        span[data-baseweb="tag"], 
        span[data-baseweb="tag"] * {
            color: #0C0C0E !important;
            fill: #0C0C0E !important;
        }

        /* Markdown container styling */
        .stMarkdown p, .stMarkdown li {
            font-family: 'Syne', sans-serif !important;
            color: rgba(242,242,245,0.70) !important;
            font-size: 13px !important;
        }

        /* Custom cards & layouts */
        .msme-card {
            background-color: #141417;
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 14px;
            padding: 20px 22px;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.04), 0 4px 16px rgba(0,0,0,0.6);
            margin-bottom: 20px;
        }
        .msme-card:hover {
            background-color: #1C1C21;
            border-color: rgba(255,255,255,0.10);
            transition: all 0.2s ease;
        }

        /* Status Badge styling */
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 3px 9px;
            border-radius: 999px;
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 0.07em;
            text-transform: uppercase;
            font-family: 'Syne', sans-serif !important;
        }

        .badge::before {
            content: '';
            width: 5px; height: 5px;
            border-radius: 50%;
            background: currentColor;
            opacity: 0.8;
        }

        .badge-critical { background: rgba(255,68,85,0.12); color: #FF4455; border: 1px solid rgba(255,68,85,0.25); }
        .badge-high     { background: rgba(245,158,11,0.12); color: #F59E0B; border: 1px solid rgba(245,158,11,0.25); }
        .badge-normal   { background: rgba(59,130,246,0.12); color: #3B82F6; border: 1px solid rgba(59,130,246,0.25); }
        .badge-resolved { background: rgba(34,197,94,0.12);  color: #22C55E; border: 1px solid rgba(34,197,94,0.25); }
        .badge-pending  { background: rgba(139,92,246,0.12); color: #8B5CF6; border: 1px solid rgba(139,92,246,0.25); }

        /* Alert Banners */
        .alert-banner {
            background: rgba(245,158,11,0.08) !important;
            border: 1px solid rgba(245,158,11,0.20) !important;
            border-radius: 10px !important;
            padding: 12px 16px !important;
            color: rgba(242,242,245,0.75) !important;
            font-size: 12px !important;
            display: flex; gap: 10px; align-items: flex-start;
            margin-bottom: 20px;
        }
        
        .alert-banner-critical {
            background: rgba(255,68,85,0.08) !important;
            border-color: rgba(255,68,85,0.20) !important;
            box-shadow: 0 0 12px rgba(255,68,85,0.25) !important;
        }

        /* Page Header style */
        .page-header {
            display: flex; align-items: center; gap: 14px;
            margin-bottom: 28px;
        }
        .page-icon {
            width: 42px; height: 42px;
            border-radius: 10px;
            background: rgba(196,255,50,0.10);
            border: 1px solid rgba(196,255,50,0.20);
            display: grid; place-items: center;
            font-size: 20px;
        }
        .page-title {
            font-family: 'Syne', sans-serif !important;
            font-size: 28px;
            font-weight: 700;
            color: #F2F2F5;
            letter-spacing: -0.02em;
            margin: 0 !important;
        }

        /* Make Streamlit Tabs stretch to full width equally */
        div[data-testid="stTabs"] {
            width: 100% !important;
            gap: 0px !important;
        }
        div[data-testid="stTabs"] button {
            flex: 1 1 0% !important;
            text-align: center !important;
            padding: 10px 16px !important;
            font-family: 'Syne', sans-serif !important;
            font-size: 14px !important;
            font-weight: 600 !important;
            color: rgba(242,242,245,0.60) !important;
            border-bottom: 2px solid rgba(255,255,255,0.06) !important;
            transition: all 0.2s ease !important;
        }
        div[data-testid="stTabs"] button[aria-selected="true"] {
            color: #C4FF32 !important;
            border-bottom: 2px solid #C4FF32 !important;
        }
        div[data-testid="stTabs"] button:hover {
            color: #F2F2F5 !important;
            background-color: rgba(255,255,255,0.02) !important;
        }
        </style>
        """
    else:
        custom_css = """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

        :root {
            --text-color: #0F172A;
            --text-color-muted: #475569;
            --border-color: #E2E8F0;
        }

        /* Tighter page padding and vertical gaps to prevent scrolling */
        [data-testid="stAppViewContainer"] .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 1rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            max-width: 98% !important;
        }
        [data-testid="stVerticalBlock"] {
            gap: 0.5rem !important;
        }

        /* Page background */
        html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
            font-family: 'Syne', sans-serif !important;
            background-color: #F0F4FA !important;
            color: #0F172A !important;
        }

        /* Top bar header background */
        [data-testid="stHeader"] {
            background-color: rgba(240, 244, 250, 0.6) !important;
            backdrop-filter: blur(10px) !important;
        }

        /* Sidebar Navigation */
        [data-testid="stSidebar"] {
            background-color: #F8FAFC !important;
            border-right: 1px solid #E2E8F0 !important;
        }

        /* Hide the collapse/expand sidebar button */
        [data-testid="collapsedControl"],
        [data-testid="stSidebarCollapsedControl"] {
            display: none !important;
        }

        /* Sidebar navigation links */
        [data-testid="stSidebarNav"],
        [data-testid="stSidebarNavigation"] {
            background-color: #F8FAFC !important;
            height: auto !important;
            display: flex !important;
            flex-direction: column !important;
            justify-content: flex-start !important;
            overflow: visible !important;
        }

        [data-testid="stSidebarNav"] ul,
        [data-testid="stSidebarNavigation"] ul {
            display: flex !important;
            flex-direction: column !important;
            justify-content: flex-start !important;
            height: auto !important;
            padding: 10px 0 !important;
            margin: 0 !important;
        }

        [data-testid="stSidebarNav"] ul li,
        [data-testid="stSidebarNavigation"] ul li {
            margin: 20px 0 !important;
        }
        
        [data-testid="stSidebarNav"] ul li a,
        [data-testid="stSidebarNav"] ul li a span {
            color: #475569 !important;
            font-size: 13px !important;
            padding: 10px 16px !important;
            border-radius: 8px !important;
            margin: 0px 8px !important;
            transition: none !important;
            font-family: 'Syne', sans-serif !important;
            text-transform: capitalize !important;
        }

        /* Force all sidebar nav items visible — remove View more/less */
        [data-testid="stSidebarNav"] details,
        [data-testid="stSidebarNavigation"] details {
            display: contents !important;
        }
        [data-testid="stSidebarNav"] details[open],
        [data-testid="stSidebarNavigation"] details[open] {
            display: contents !important;
        }
        [data-testid="stSidebarNav"] details summary,
        [data-testid="stSidebarNavigation"] details summary {
            display: none !important;
        }
        [data-testid="stSidebarNav"] details > *:not(summary),
        [data-testid="stSidebarNavigation"] details > *:not(summary),
        [data-testid="stSidebarNav"] details:not([open]) > *:not(summary),
        [data-testid="stSidebarNavigation"] details:not([open]) > *:not(summary) {
            display: contents !important;
        }
        [data-testid="stSidebarNav"] details ul,
        [data-testid="stSidebarNavigation"] details ul {
            display: flex !important;
            flex-direction: column !important;
        }
        [data-testid="stSidebarNav"] a[kind="secondaryFormSubmit"] {
            display: none !important;
        }

        /* Circular theme toggle button */
        .theme-toggle-btn-circle {
            padding: 8px 16px !important;
            border-radius: 20px !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            font-size: 13px !important;
            font-weight: 600 !important;
            color: #0F172A !important;
            margin: 0 auto !important;
            background: #FFFFFF !important;
            border: 1px solid #CBD5E1 !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
            transition: all 0.2s ease !important;
            cursor: pointer !important;
            width: fit-content !important;
            min-width: 160px !important;
        }
        .theme-toggle-btn-circle:hover {
            background: #F1F5F9 !important;
            border-color: #94A3B8 !important;
            transform: scale(1.05) !important;
        }

        [data-testid="stSidebarNav"] ul li a:hover {
            background: #F1F5F9 !important;
            color: #0F172A !important;
        }

        /* Active Nav Item */
        [data-testid="stSidebarNav"] ul li a[aria-current="page"] {
            background: rgba(59, 130, 246, 0.1) !important;
            color: #3B82F6 !important;
            border-left: 2px solid #3B82F6 !important;
            font-weight: 600 !important;
        }

        /* Headers */
        h1, h2, h3, h4, h5, h6 {
            font-family: 'Syne', sans-serif !important;
            font-weight: 700 !important;
            color: #0F172A !important;
            letter-spacing: -0.02em !important;
        }

        h1 {
            font-size: 28px !important;
            margin-bottom: 24px !important;
        }

        /* Metric / KPI Card styling */
        div[data-testid="stMetric"] {
            background: #FFFFFF !important;
            border: 1px solid #E2E8F0 !important;
            border-radius: 14px !important;
            padding: 12px 18px !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05) !important;
            transition: all 0.2s ease !important;
        }

        div[data-testid="stMetric"]:hover {
            background: #F8FAFC !important;
            border-color: #CBD5E1 !important;
        }

        div[data-testid="stMetricValue"] {
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 32px !important;
            font-weight: 500 !important;
            color: #3B82F6 !important;
            margin: 8px 0 4px !important;
            line-height: 1.1 !important;
        }

        div[data-testid="stMetricLabel"] {
            font-size: 10px !important;
            letter-spacing: 0.1em !important;
            text-transform: uppercase !important;
            color: #475569 !important;
            font-weight: 600 !important;
        }

        /* Buttons styling */
        div.stButton > button {
            background: #FFFFFF !important;
            border: 1px solid #CBD5E1 !important;
            color: #475569 !important;
            font-size: 12px !important;
            padding: 8px 16px !important;
            border-radius: 8px !important;
            font-family: 'Syne', sans-serif !important;
            font-weight: 600 !important;
            transition: all 0.15s ease !important;
        }

        div.stButton > button:hover {
            background: #F1F5F9 !important;
            border-color: #94A3B8 !important;
            color: #0F172A !important;
        }

        /* Right-align and make smaller the logout button inside the welcome container column */
        div[data-testid*="column"]:has(.welcome-text-container) div.stButton {
            display: flex !important;
            justify-content: flex-end !important;
            width: 100% !important;
        }
        div[data-testid*="column"]:has(.welcome-text-container) div.stButton button {
            margin-top: 4px !important;
            padding: 2px 8px !important;
            font-size: 10px !important;
            line-height: 1.1 !important;
            min-height: 24px !important;
            height: auto !important;
            width: fit-content !important;
        }

        /* Primary CTA Button */
        div.stButton > button[kind="primary"], 
        div.stButton > button.st-emotion-cache-129842a, 
        button[type="submit"] {
            background: #3B82F6 !important;
            color: #FFFFFF !important;
            font-weight: 700 !important;
            border: none !important;
            box-shadow: 0 4px 12px rgba(59,130,246,0.2) !important;
        }

        div.stButton > button[kind="primary"]:hover, 
        div.stButton > button.st-emotion-cache-129842a:hover, 
        button[type="submit"]:hover {
            background: #1D4ED8 !important;
        }

        /* Table / Dataframes styling */
        div[data-testid="stDataFrame"] {
            border: 1px solid #E2E8F0 !important;
            border-radius: 12px !important;
            overflow: hidden !important;
            background-color: #FFFFFF !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05) !important;
        }

        /* Input styling */
        div[data-testid="stTextInput"] input, 
        div[data-testid="stTextArea"] textarea, 
        div[data-testid="stSelectbox"] select,
        div[data-testid="stNumberInput"] input {
            background-color: #FFFFFF !important;
            border: 1px solid #CBD5E1 !important;
            color: #0F172A !important;
            border-radius: 8px !important;
            font-family: 'Syne', sans-serif !important;
        }

        div[data-testid="stTextInput"] input:focus, 
        div[data-testid="stTextArea"] textarea:focus, 
        div[data-testid="stSelectbox"] select:focus {
            border-color: #3B82F6 !important;
            box-shadow: 0 0 8px rgba(59,130,246,0.2) !important;
        }

        /* Style multiselect pills/tags — yellowish-white background with dark text */
        span[data-baseweb="tag"] {
            background-color: #FEF9C3 !important;
            border: 1px solid #FDE68A !important;
        }
        span[data-baseweb="tag"], 
        span[data-baseweb="tag"] * {
            color: #78350F !important;
            fill: #78350F !important;
        }

        /* Markdown container styling */
        .stMarkdown p, .stMarkdown li {
            font-family: 'Syne', sans-serif !important;
            color: #475569 !important;
            font-size: 13px !important;
        }

        /* Custom cards & layouts */
        .msme-card {
            background-color: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 14px;
            padding: 20px 22px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            margin-bottom: 20px;
        }
        .msme-card:hover {
            background-color: #F8FAFC;
            border-color: #CBD5E1;
            transition: all 0.2s ease;
        }

        /* Status Badge styling */
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 3px 9px;
            border-radius: 999px;
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 0.07em;
            text-transform: uppercase;
            font-family: 'Syne', sans-serif !important;
        }

        .badge::before {
            content: '';
            width: 5px; height: 5px;
            border-radius: 50%;
            background: currentColor;
            opacity: 0.8;
        }

        .badge-critical { background: rgba(255,68,85,0.12); color: #FF4455; border: 1px solid rgba(255,68,85,0.25); }
        .badge-high     { background: rgba(245,158,11,0.12); color: #F59E0B; border: 1px solid rgba(245,158,11,0.25); }
        .badge-normal   { background: rgba(59,130,246,0.12); color: #3B82F6; border: 1px solid rgba(59,130,246,0.25); }
        .badge-resolved { background: rgba(34,197,94,0.12);  color: #22C55E; border: 1px solid rgba(34,197,94,0.25); }
        .badge-pending  { background: rgba(139,92,246,0.12); color: #8B5CF6; border: 1px solid rgba(139,92,246,0.25); }

        /* Alert Banners */
        .alert-banner {
            background: #FFFBEB !important;
            border: 1px solid #FDE68A !important;
            border-radius: 10px !important;
            padding: 12px 16px !important;
            color: #B45309 !important;
            font-size: 12px !important;
            display: flex; gap: 10px; align-items: flex-start;
            margin-bottom: 20px;
        }
        
        .alert-banner-critical {
            background: #FEF2F2 !important;
            border-color: #FCA5A5 !important;
            color: #B91C1C !important;
        }

        /* Page Header style */
        .page-header {
            display: flex; align-items: center; gap: 14px;
            margin-bottom: 28px;
        }
        .page-icon {
            width: 42px; height: 42px;
            border-radius: 10px;
            background: rgba(59, 130, 246, 0.1);
            border: 1px solid rgba(59, 130, 246, 0.2);
            display: grid; place-items: center;
            font-size: 20px;
        }
        .page-title {
            font-family: 'Syne', sans-serif !important;
            font-size: 28px;
            font-weight: 700;
            color: #0F172A;
            letter-spacing: -0.02em;
            margin: 0 !important;
        }

        /* Make Streamlit Tabs stretch to full width equally */
        div[data-testid="stTabs"] {
            width: 100% !important;
            gap: 0px !important;
        }
        div[data-testid="stTabs"] button {
            flex: 1 1 0% !important;
            text-align: center !important;
            padding: 10px 16px !important;
            font-family: 'Syne', sans-serif !important;
            font-size: 14px !important;
            font-weight: 600 !important;
            color: #475569 !important;
            border-bottom: 2px solid #E2E8F0 !important;
            transition: all 0.2s ease !important;
        }
        div[data-testid="stTabs"] button[aria-selected="true"] {
            color: #3B82F6 !important;
            border-bottom: 2px solid #3B82F6 !important;
        }
        div[data-testid="stTabs"] button:hover {
            color: #0F172A !important;
            background-color: #F1F5F9 !important;
        }

        /* ==========================================================
           LIGHT MODE FIXES — Login, Grievances, Documents, Sessions
           ========================================================== */

        /* --- 1. LOGIN PAGE FIXES --- */

        /* Input field labels and placeholder text visibility */
        div[data-testid="stTextInput"] label,
        div[data-testid="stTextInput"] label p,
        div[data-testid="stNumberInput"] label,
        div[data-testid="stNumberInput"] label p {
            color: #0F172A !important;
        }

        div[data-testid="stTextInput"] input::placeholder {
            color: #94A3B8 !important;
            opacity: 1 !important;
        }

        /* Login / Submit button text always visible on dark background */
        div.stButton > button[kind="primary"] *,
        div.stButton > button.st-emotion-cache-129842a *,
        button[type="submit"] * {
            color: #FFFFFF !important;
        }

        /* Streamlit warning banner (amber) — "Please enter your username…" */
        div[data-testid="stAlert"][data-baseweb="notification"],
        div.stAlert,
        div[role="alert"] {
            background-color: #FEF3C7 !important;
            color: #92400E !important;
            border: 1px solid #FDE68A !important;
            border-radius: 8px !important;
        }
        div[data-testid="stAlert"] p,
        div.stAlert p,
        div[role="alert"] p,
        div[role="alert"] span {
            color: #92400E !important;
        }

        /* Streamlit error banner (red) — "Username/password is incorrect" */
        div[data-testid="stAlert"][kind="error"],
        div.stAlert.st-emotion-cache-error {
            background-color: #FEF2F2 !important;
            color: #991B1B !important;
            border: 1px solid #FCA5A5 !important;
        }

        /* Streamlit info banner — used on Sessions page and elsewhere */
        div[data-testid="stAlert"][kind="info"],
        div.stAlert.st-emotion-cache-info {
            background-color: #EFF6FF !important;
            color: #1E3A5F !important;
            border: 1px solid #BFDBFE !important;
        }
        div[data-testid="stAlert"][kind="info"] p,
        div[data-testid="stAlert"][kind="info"] span {
            color: #1E3A5F !important;
        }

        /* Streamlit success banner */
        div[data-testid="stAlert"][kind="success"] {
            background-color: #F0FDF4 !important;
            color: #166534 !important;
            border: 1px solid #BBF7D0 !important;
        }

        /* --- 2. GRIEVANCES PAGE — FILTER SECTION FIXES --- */

        /* Multiselect dropdown containers (Status, Severity, Scheme, Type) */
        div[data-testid="stMultiSelect"] > div,
        div[data-testid="stMultiSelect"] > div > div {
            background-color: #F9FAFB !important;
            border-color: #E5E7EB !important;
        }

        /* Multiselect inner input area */
        div[data-testid="stMultiSelect"] [data-baseweb="select"] > div {
            background-color: #F9FAFB !important;
            border: 1px solid #E5E7EB !important;
            border-radius: 8px !important;
        }

        /* Multiselect dropdown menu */
        div[data-testid="stMultiSelect"] [data-baseweb="popover"],
        div[data-testid="stMultiSelect"] ul,
        [data-baseweb="popover"] > div,
        [data-baseweb="menu"] {
            background-color: #FFFFFF !important;
            border: 1px solid #E5E7EB !important;
        }

        /* Multiselect dropdown menu items */
        [data-baseweb="menu"] li,
        [data-baseweb="menu"] ul li {
            background-color: #FFFFFF !important;
            color: #0F172A !important;
        }
        [data-baseweb="menu"] li:hover {
            background-color: #F1F5F9 !important;
        }

        /* Multiselect labels */
        div[data-testid="stMultiSelect"] label,
        div[data-testid="stMultiSelect"] label p {
            color: #0F172A !important;
        }

        /* Filter tags/pills — yellowish-white with dark amber text */
        span[data-baseweb="tag"] {
            background-color: #FEF9C3 !important;
            border: 1px solid #FDE68A !important;
            color: #78350F !important;
        }
        span[data-baseweb="tag"] span,
        span[data-baseweb="tag"] svg {
            color: #78350F !important;
            fill: #78350F !important;
        }

        /* Search bar text input border */
        div[data-testid="stTextInput"] input {
            border: 1px solid #D1D5DB !important;
        }

        /* Selectbox containers */
        div[data-testid="stSelectbox"] > div > div,
        div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
            background-color: #FFFFFF !important;
            border: 1px solid #CBD5E1 !important;
            color: #0F172A !important;
        }

        /* Selectbox label text */
        div[data-testid="stSelectbox"] label,
        div[data-testid="stSelectbox"] label p {
            color: #0F172A !important;
        }

        /* Date input containers */
        div[data-testid="stDateInput"] > div > div,
        div[data-testid="stDateInput"] input {
            background-color: #FFFFFF !important;
            border: 1px solid #CBD5E1 !important;
            color: #0F172A !important;
        }

        div[data-testid="stDateInput"] label,
        div[data-testid="stDateInput"] label p {
            color: #0F172A !important;
        }

        /* --- 3. DOCUMENTS PAGE FIXES --- */

        /* Dataframe / table rows — white background, light border, dark text */
        div[data-testid="stDataFrame"] table,
        div[data-testid="stDataFrame"] thead,
        div[data-testid="stDataFrame"] tbody,
        div[data-testid="stDataFrame"] tr,
        div[data-testid="stDataFrame"] th,
        div[data-testid="stDataFrame"] td {
            background-color: #FFFFFF !important;
            color: #0F172A !important;
            border-color: #E5E7EB !important;
        }

        div[data-testid="stDataFrame"] th {
            background-color: #F9FAFB !important;
            color: #475569 !important;
            font-weight: 600 !important;
        }

        /* File uploader / drag-and-drop zone */
        div[data-testid="stFileUploader"],
        div[data-testid="stFileUploader"] > div,
        div[data-testid="stFileUploader"] section,
        div[data-testid="stFileUploader"] section > div {
            background-color: #F9FAFB !important;
            border: 2px dashed #D1D5DB !important;
            border-radius: 10px !important;
            color: #475569 !important;
        }

        div[data-testid="stFileUploader"] span,
        div[data-testid="stFileUploader"] p,
        div[data-testid="stFileUploader"] small,
        div[data-testid="stFileUploader"] label {
            color: #475569 !important;
        }

        /* File uploader inner button */
        div[data-testid="stFileUploader"] button {
            background-color: #FFFFFF !important;
            border: 1px solid #CBD5E1 !important;
            color: #475569 !important;
        }

        /* ChromaDB / Info status box — force readable text in st.info blocks */
        div[data-testid="stAlert"] code,
        div.stAlert code {
            background-color: rgba(59,130,246,0.08) !important;
            color: #1E3A5F !important;
            padding: 2px 6px !important;
            border-radius: 4px !important;
        }

        /* --- 4. SESSIONS PAGE FIXES --- */
        /* Handled above via the general stAlert[kind="info"] rule */

        /* --- GENERAL LIGHT-MODE POLISH --- */

        /* Checkbox labels and text area labels */
        div[data-testid="stCheckbox"] label span,
        div[data-testid="stTextArea"] label,
        div[data-testid="stTextArea"] label p {
            color: #0F172A !important;
        }

        /* Text area styling */
        div[data-testid="stTextArea"] textarea {
            background-color: #FFFFFF !important;
            border: 1px solid #CBD5E1 !important;
            color: #0F172A !important;
        }

        /* Expander headers */
        div[data-testid="stExpander"] summary,
        div[data-testid="stExpander"] summary span {
            color: #0F172A !important;
        }

        div[data-testid="stExpander"] > div {
            background-color: #FFFFFF !important;
            border: 1px solid #E5E7EB !important;
            border-radius: 8px !important;
        }

        /* Download buttons */
        div.stDownloadButton > button {
            background-color: #FFFFFF !important;
            border: 1px solid #CBD5E1 !important;
            color: #475569 !important;
        }
        div.stDownloadButton > button:hover {
            background-color: #F1F5F9 !important;
            border-color: #94A3B8 !important;
            color: #0F172A !important;
        }

        /* Horizontal rules / dividers */
        hr {
            border-color: #E2E8F0 !important;
        }

        </style>
        """
        
    st.markdown(custom_css, unsafe_allow_html=True)

def update_plotly_layout(fig, light_primary="#3B82F6"):
    """
    Applies the design specification's theme layout to Plotly figures based on active session state theme.
    """
    is_dark = st.session_state.get("theme", "dark") == "dark"
    bg_color = "#141417" if is_dark else "#FFFFFF"
    text_color = "#F2F2F5" if is_dark else "#0F172A"
    grid_color = "rgba(255, 255, 255, 0.05)" if is_dark else "rgba(15, 23, 42, 0.06)"
    line_color = "rgba(255, 255, 255, 0.15)" if is_dark else "rgba(15, 23, 42, 0.12)"
    
    fig.update_layout(
        paper_bgcolor=bg_color,
        plot_bgcolor=bg_color,
        font_family="Syne, sans-serif",
        font_color=text_color,
        xaxis=dict(
            gridcolor=grid_color,
            linecolor=line_color,
            tickfont=dict(family="JetBrains Mono", size=10)
        ),
        yaxis=dict(
            gridcolor=grid_color,
            linecolor=line_color,
            tickfont=dict(family="JetBrains Mono", size=10)
        ),
        margin=dict(l=40, r=20, t=30, b=40)
    )
    
    # Adjust bar/line/pie colors in light mode if they use the dark primary color
    if not is_dark:
        for trace in fig.data:
            if hasattr(trace, "marker") and trace.marker:
                if hasattr(trace.marker, "color") and trace.marker.color:
                    if trace.marker.color == "#C4FF32":
                        trace.marker.color = light_primary
                    elif isinstance(trace.marker.color, list):
                        trace.marker.color = [(light_primary if c == "#C4FF32" else c) for c in trace.marker.color]
                if hasattr(trace.marker, "colors") and trace.marker.colors is not None:
                    colors = list(trace.marker.colors)
                    trace.marker.colors = [(light_primary if c == "#C4FF32" else c) for c in colors]
            if hasattr(trace, "line") and trace.line:
                if hasattr(trace.line, "color") and trace.line.color:
                    if trace.line.color == "#C4FF32":
                        trace.line.color = light_primary
        if hasattr(fig, "layout") and fig.layout:
            if hasattr(fig.layout, "piecolorway") and fig.layout.piecolorway:
                colors = list(fig.layout.piecolorway)
                fig.layout.piecolorway = [(light_primary if c == "#C4FF32" else c) for c in colors]
                        
    return fig
