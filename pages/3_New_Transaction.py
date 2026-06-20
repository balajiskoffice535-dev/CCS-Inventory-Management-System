import streamlit as st
from datetime import datetime
from database.db_connection import run_query
import os
import json

st.set_page_config(page_title="New Transaction - CCS",page_icon="title_logo.png", layout="wide")

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

st.title("📥 New Transaction")
st.write("Add purchase and sales records by serial number.")

# --- CUSTOM CSS FOR REPLIT LOOK ---
st.markdown("""
    <style>
    div[data-testid="stBlock"] {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
    }
    </style>
""", unsafe_allow_html=True)

# --- FORM CONTAINERS ---
# This creates the side-by-side layout from your screenshot
col1, col2 = st.columns(2)

with col1:
    st.subheader("📋 Purchase Register")
    purchase_date = st.date_input("Purchase Date *", datetime.now(),format="DD/MM/YYYY")
    supplier_name = st.text_input("Supplier Name *", placeholder="e.g., Redington Limited")
    supplier_number = st.text_input("Supplier Number *", placeholder="e.g., SUP-001")
    
    # ✨ NEW PRODUCT NAME FIELD ✨
    product_name = st.text_input("Product Name *", placeholder="e.g., Dynabook Portage X40")
    
    payment_type = st.selectbox("Payment Type", ["Cash", "Credit", "NEFT", "RTGS"])
    new_pur_rate = st.number_input("Purchase (Rate - Without Tax) ₹ *", min_value=0.0, format="%.2f")

with col2:
    st.subheader("🧾 Sales Invoice Details")
    customer_name = st.text_input("Customer Name", placeholder="e.g., Mantle Solutions")
    sales_invoice_date = st.date_input("Sales Invoice Date", value=None, help="Leave blank if not sold yet",format="DD/MM/YYYY")
    invoice_number = st.text_input("Invoice Number", placeholder="e.g., INV-001")
    new_sales_rate = st.number_input("Sales (Rate - Without Tax) ₹", min_value=0.0, format="%.2f")
    
    # Extra Dispatch and Payment Dates from your spec
    dispatch_col, payment_col = st.columns(2)
    with dispatch_col:
        date_of_dispatch = st.date_input("Dispatch Date", value=None, format="DD/MM/YYYY")
    with payment_col:
        date_of_payment = st.date_input("Payment Date", value=None,format="DD/MM/YYYY")

# --- BOTTOM SECTION: SERIAL NUMBERS & LOGIC ---
st.markdown("<br>", unsafe_allow_html=True)
st.subheader("🔢 Serial Numbers")
st.write("Each serial number entered below will automatically create a separate transaction record.")

# Text area where user can paste serial numbers separated by commas or new lines
serial_input = st.text_area("Enter Serial Numbers (Separated by commas or new lines)", 
                            placeholder="ABC001, ABC002, ABC003", 
                            height=150)

notes = st.text_area("Additional Notes")

# --- SAVE BUTTON ACTION ---
if st.button("💾 Save Transactions", type="primary", use_container_width=True):
    # 1. Validation check (Added product_name to mandatory fields)
    if not supplier_name or not supplier_number or not product_name or not serial_input or new_pur_rate <= 0:
        st.error("Please fill in all mandatory fields (*) marked with an asterisk and enter at least one serial number.")
    else:
        # 2. Process and split serial numbers (Module 3 Business Logic)
        import re
        raw_serials = re.split(r'[,\n]+', serial_input)
        serial_list = [s.strip() for s in raw_serials if s.strip()]
        
        if not serial_list:
            st.error("No valid serial numbers found.")
        else:
            success_count = 0
            error_count = 0
            
            # 3. First, insert or update the Supplier Master behind the scenes
            supplier_query = """
                INSERT INTO suppliers (supplier_number, supplier_name) 
                VALUES (%s, %s) 
                ON CONFLICT (supplier_number) DO UPDATE SET supplier_name = EXCLUDED.supplier_name
                RETURNING id;
            """
            supplier_rows = run_query(supplier_query, (supplier_number, supplier_name))
            
            # 4. Insert or update the Customer Master if a customer name is given
            customer_id = None
            if customer_name.strip():
                customer_query = """
                    INSERT INTO customers (customer_name) 
                    VALUES (%s) 
                    ON CONFLICT (customer_name) DO NOTHING
                    RETURNING id;
                """
                customer_rows = run_query(customer_query, (customer_name.strip(),))
                
                # If it already existed, fetch its ID
                if not customer_rows:
                    fetch_cust = run_query("SELECT id FROM customers WHERE customer_name = %s;", (customer_name.strip(),))
                    customer_id = fetch_cust[0]['id'] if fetch_cust else None
                else:
                    customer_id = customer_rows[0]['id']
            
            supplier_id = supplier_rows[0]['id'] if supplier_rows else None

            # 5. Loop through every single serial number and create a separate database row
            for serial in serial_list:
                # ✨ INJECTED PRODUCT NAME INTO THE SQL QUERY ✨
                transaction_query = """
                    INSERT INTO transactions (
                        serial_number, purchase_date, supplier_id, product_name, payment_type, purchase_rate,
                        sales_invoice_date, invoice_number, customer_id, sales_rate,
                        date_of_dispatch, date_of_payment, notes
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (serial_number) DO NOTHING;
                """
                
                result = run_query(transaction_query, (
                    serial, purchase_date, supplier_id, product_name, payment_type, new_pur_rate,
                    sales_invoice_date, invoice_number, customer_id, 
                    new_sales_rate if new_sales_rate > 0 else None,
                    date_of_dispatch, date_of_payment, notes
                ))
                
                if result:
                    success_count += 1
                else:
                    error_count += 1

            # 6. Show final user report
            if success_count > 0:
                st.success(f"Successfully saved {success_count} individual product unit records!")
            if error_count > 0:
                st.warning(f"{error_count} serial numbers were skipped because they already exist in the database.")
