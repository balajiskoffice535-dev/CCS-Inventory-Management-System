import streamlit as st
import pandas as pd
from database.db_connection import run_query
import os
import json

st.set_page_config(page_title="Customers - CCS",page_icon="title_logo.png", layout="wide")

# ==========================================
# GLOBAL SIDEBAR BRANDING (PERMANENT DISK VERSION)
# ==========================================

# ✨ THE CSS HACK TO FLIP THE SIDEBAR ORDER ✨
st.markdown("""
    <style>
        /* Force the sidebar to behave like a vertical flexbox */
        [data-testid="stSidebar"] > div:first-child {
            display: flex;
            flex-direction: column;
        }
        /* Force the default Streamlit navigation menu to drop down to the bottom */
        [data-testid="stSidebarNav"] {
            order: 2;
            margin-top: -110px; /* Adds a little breathing room above the menu */
        }
        /* Optional: Hide the default Streamlit watermark at the very bottom */
        [data-testid="stSidebarNav"]::before {
            content: "";
        }
    </style>
""", unsafe_allow_html=True)

# 1. Look for the physical logo file
if os.path.exists("saved_logo.png"):
    st.sidebar.image("saved_logo.png", use_column_width=True)

# 2. Look for the physical settings file
company_title = "CENTREAL CONSULTANCY SERVICES" # Default
if os.path.exists("settings.json"):
    with open("settings.json", "r") as f:
        try:
            saved_data = json.load(f)
            company_title = saved_data.get("company_name", company_title)
        except Exception:
            pass

st.sidebar.markdown(f"<h3 style='text-align: center;'>{company_title}</h3>", unsafe_allow_html=True)
st.sidebar.markdown("---")

st.title("👥 Customer & Warranty Lookup")
st.write("Search transactions by customer name, invoice, or serial number.")

# --- SEARCH BAR ---
search_query = st.text_input("🔍 Search", placeholder="Search by customer name, serial number, invoice...")

st.markdown("<br>", unsafe_allow_html=True)

# --- FETCH DATA ---
query = """
    SELECT 
        c.customer_name as "Customer",
        t.serial_number as "Serial Number",
        COALESCE(t.invoice_number, '-') as "Invoice",
        t.sales_invoice_date as "Sales Date",
        t.date_of_dispatch as "Dispatch Date",
        s.supplier_name as "Supplier"
    FROM transactions t
    INNER JOIN customers c ON t.customer_id = c.id
    LEFT JOIN suppliers s ON t.supplier_id = s.id
    ORDER BY t.sales_invoice_date DESC
"""
raw_data = run_query(query)

if not raw_data:
    st.info("No customer sales records found.")
else:
    df = pd.DataFrame(raw_data)
    
    # --- SEARCH LOGIC ---
    if search_query:
        search_term = search_query.lower()
        df = df[
            df["Customer"].str.lower().str.contains(search_term, na=False) |
            df["Serial Number"].str.lower().str.contains(search_term, na=False) |
            df["Invoice"].str.lower().str.contains(search_term, na=False)
        ]
        
    if df.empty:
        st.warning("No records match your search.")
    else:
        st.caption(f"Showing {len(df)} matching records.")
        
        # Insert the SL column at the very beginning (position 0)
        df.insert(0, "SL", range(1, len(df) + 1))
        
        # Display the clean table
        st.dataframe(
            df, 
            use_container_width=True, 
            hide_index=True,
            height=500
        )
