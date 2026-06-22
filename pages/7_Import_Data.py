import streamlit as st
import pandas as pd
from datetime import datetime
import os
from database.db_connection import run_query

st.set_page_config(page_title="Import Data - CCS", page_icon="title_logo.png", layout="wide")

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def clean_price(val):
    """Strips commas and converts to a clean float number."""
    if pd.isna(val): return 0.0
    clean_str = str(val).replace(',', '').replace('Rs', '').replace('₹', '').strip()
    try:
        return float(clean_str)
    except ValueError:
        return 0.0

# ==========================================
# GLOBAL SIDEBAR BRANDING
# ==========================================
st.markdown("""
    <style>
        [data-testid="stSidebar"] > div:first-child { display: flex; flex-direction: column; }
        [data-testid="stSidebarNav"] { order: 2; margin-top: -110px; }
        [data-testid="stSidebarNav"]::before { content: ""; }
    </style>
""", unsafe_allow_html=True)

if os.path.exists("saved_logo.png"):
    st.sidebar.image("saved_logo.png", use_container_width=True)

# ✨ DYNAMIC COMPANY NAME FIX ✨
company_title = "CENTREAL CONSULTANCY SERVICES" # Default fallback
if os.path.exists("settings.json"):
    import json
    try:
        with open("settings.json", "r") as f:
            settings_data = json.load(f)
            if "company_name" in settings_data and settings_data["company_name"]:
                company_title = settings_data["company_name"]
    except Exception:
        pass

st.sidebar.markdown(f"<h3 style='text-align: center;'>{company_title}</h3>", unsafe_allow_html=True)
st.sidebar.markdown("---")

# ==========================================
# IMPORT UI
# ==========================================
st.title("📥 Bulk Import Historical Data")
st.write("Upload your existing Excel records to bring them into the new system.")
st.info("💡 The system is now custom-configured to read your exact 'Purchase Register / Sales Invoice Details' format!")
st.divider()

# FILE UPLOADER
uploaded_file = st.file_uploader("Choose your Excel file", type=['xlsx', 'xls'])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file, header=1)
        df.columns = df.columns.str.strip()
        
        # Nuke actual ghost rows FIRST before doing anything else
        df = df.dropna(subset=['Purchase Date', 'Serial Number', 'Rate - Without Tax'], how='all')
        
        # Forward-fill the valid merged cells safely
        fill_cols = [c for c in ['Purchase Date', 'Supplier No', 'Product Name', 'Supplier Name', 'Rate - Without Tax'] if c in df.columns]
        if fill_cols:
            df[fill_cols] = df[fill_cols].ffill()
        
        st.subheader("👀 Data Preview (Headers Detected)")
        st.dataframe(df.head(10), use_container_width=True)
        st.write(f"**Total Valid Excel Rows Found:** {len(df
