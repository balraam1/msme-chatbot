import streamlit as st

def apply_custom_theme():
    custom_css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

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

    /* Sidebar navigation links */
    [data-testid="stSidebarNav"] {
        background-color: #0F0F12 !important;
        height: 75vh !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
    }

    [data-testid="stSidebarNav"] ul {
        display: flex !important;
        flex-direction: column !important;
        justify-content: space-around !important;
        height: 100% !important;
        padding: 24px 0 !important;
        margin: 0 !important;
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

    /* "View more" expander link in sidebar nav */
    [data-testid="stSidebarNav"] a[kind="secondaryFormSubmit"],
    [data-testid="stSidebarNav"] button,
    [data-testid="stSidebarNav"] summary,
    [data-testid="stSidebarNav"] details summary span {
        text-transform: capitalize !important;
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

    /* Right-align the logout button inside the welcome container column */
    div[data-testid="column"]:has(.welcome-text-container) div.stButton button {
        margin-left: auto !important;
        display: block !important;
    }

    /* Primary CTA Button (Haulix "Activate Route" equivalent) */
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
    st.markdown(custom_css, unsafe_allow_html=True)

def update_plotly_layout(fig):
    """
    Applies the design specification's high-tech dark theme layout to Plotly figures.
    """
    fig.update_layout(
        paper_bgcolor="#141417",
        plot_bgcolor="#141417",
        font_family="Syne, sans-serif",
        font_color="#F2F2F5",
        xaxis=dict(
            gridcolor="rgba(255, 255, 255, 0.05)",
            linecolor="rgba(255, 255, 255, 0.15)",
            tickfont=dict(family="JetBrains Mono", size=10)
        ),
        yaxis=dict(
            gridcolor="rgba(255, 255, 255, 0.05)",
            linecolor="rgba(255, 255, 255, 0.15)",
            tickfont=dict(family="JetBrains Mono", size=10)
        ),
        margin=dict(l=40, r=20, t=30, b=40)
    )
    return fig
