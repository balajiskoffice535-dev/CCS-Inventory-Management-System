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
        st.write(f"**Total Valid Excel Rows Found:** {len(df)}")
        
        if st.button("🚀 Start Import to Database", type="primary"):
            with st.spinner("Importing data... This might take a minute."):
                success_count = 0
                error_count = 0
                
                for index, row in df.iterrows():
                    try:
                        # ✨ FIX 1: If it's an unsold item with a blank serial, give it a temporary one so Edit/Delete works!
                        serial_no = str(row.get('Serial Number', '')).strip()
                        if pd.isna(row.get('Serial Number')) or serial_no.lower() == 'nan' or serial_no == '':
                            serial_no = f"PENDING-UNSOLD-ROW-{index + 2}"
                            
                        # Extract Purchase Data
                        supp_name = str(row.get('Supplier Name', '')).strip()
                        supp_num = str(row.get('Supplier No', '')).strip()
                        p_date = row.get('Purchase Date') if pd.notna(row.get('Purchase Date')) else None
                        
                        if supp_name.lower() == 'nan' or supp_name == "": supp_name = "Unknown Supplier"
                        
                        # Check/Create Supplier
                        if supp_num and supp_num.lower() != 'nan' and supp_num != '':
                            supp_check = run_query("SELECT id FROM suppliers WHERE supplier_number = %s", (supp_num,))
                        else:
                            supp_check = run_query("SELECT id FROM suppliers WHERE supplier_name = %s", (supp_name,))

                        if supp_check:
                            supplier_id = supp_check[0]['id']
                        else:
                            run_query("INSERT INTO suppliers (supplier_name, supplier_number) VALUES (%s, %s)", (supp_name, supp_num))
                            if supp_num and supp_num.lower() != 'nan' and supp_num != '':
                                supp_check = run_query("SELECT id FROM suppliers WHERE supplier_number = %s", (supp_num,))
                            else:
                                supp_check = run_query("SELECT id FROM suppliers WHERE supplier_name = %s", (supp_name,))
                            supplier_id = supp_check[0]['id']

                        # Extract Sales Data
                        cust_name = str(row.get('Customer Name', '')).strip()
                        customer_id = None
                        s_date = row.get('Sales Invoice Date') if pd.notna(row.get('Sales Invoice Date')) else None
                        
                        if pd.notna(row.get('Customer Name')) and cust_name != "" and cust_name.lower() != "nan":
                            cust_check = run_query("SELECT id FROM customers WHERE customer_name = %s", (cust_name,))
                            if cust_check:
                                customer_id = cust_check[0]['id']
                            else:
                                run_query("INSERT INTO customers (customer_name) VALUES (%s)", (cust_name,))
                                cust_check = run_query("SELECT id FROM customers WHERE customer_name = %s", (cust_name,))
                                customer_id = cust_check[0]['id']

                        # ✨ FIX 2: Fixed the typo that caused the crash!
                        prod_name_purch = str(row.get('Product Name', '-')).strip()
                        prod_name_sales = str(row.get('Product Name.1', prod_name_purch)).strip()
                        
                        final_product_name = prod_name_purch
                        if final_product_name.lower() == "nan" or final_product_name == "-":
                            final_product_name = prod_name_sales

                        # Extract Rates safely
                        p_rate = clean_price(row.get('Rate - Without Tax'))
                        s_rate = clean_price(row.get('Rate- Without Tax', row.get('Rate - Without Tax.1')))
                        
                        # ✨ FIX 3: THIS IS THE MAGIC FIX! Grab the payment type from Excel.
                        payment_val = str(row.get('Payment', row.get('Payment Type', '-'))).strip()
                        if payment_val.lower() == 'nan' or payment_val == '':
                            payment_val = '-'

                        inv_no = str(row.get('Invoice No', '')).strip()
                        if inv_no.lower() == 'nan': inv_no = None

                        # Insert into Database
                        insert_query = """
                            INSERT INTO transactions 
                            (purchase_date, supplier_id, product_name, payment_type, purchase_rate, 
                             serial_number, sales_invoice_date, invoice_number, customer_id, sales_rate)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        
                        # We pass `payment_val` here instead of the hardcoded "-"
                        run_query(insert_query, (
                            p_date, supplier_id, final_product_name, payment_val, p_rate,
                            serial_no, s_date, inv_no, customer_id, s_rate
                        ))
                        
                        success_count += 1
                        
                    except Exception as e:
                        error_count += 1
                        st.error(f"Error on row {index + 2} (Serial: {row.get('Serial Number', 'Unknown')}): {str(e)}")

                if error_count == 0:
                    st.success(f"✅ Successfully imported {success_count} records into the database!")
                    st.balloons()
                else:
                    st.warning(f"⚠️ Imported {success_count} records, but failed on {error_count} records.")

    except Exception as e:
        st.error(f"Failed to read the Excel file. Error: {str(e)}")
        
# ==========================================
# ⚠️ DANGER ZONE: WIPE DATABASE ⚠️
# ==========================================
st.markdown("<br><br><br>", unsafe_allow_html=True)
st.divider()
st.subheader("⚠️ Danger Zone: Reset System")
st.error("WARNING: This will permanently delete ALL transactions, suppliers, and customers from your database.")

confirm_delete = st.checkbox("I understand this will permanently erase all data.")
if confirm_delete:
    if st.button("🗑️ Delete ALL Database Records", type="primary", use_container_width=True):
        try:
            with st.spinner("Nuking the database..."):
                run_query("DELETE FROM transactions")
                run_query("DELETE FROM suppliers")
                run_query("DELETE FROM customers")
                st.success("✅ Database completely wiped! You can now start fresh.")
                st.balloons()
        except Exception as e:
            st.error(f"Failed to wipe database: {str(e)}")
