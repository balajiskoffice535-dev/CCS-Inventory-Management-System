import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database.db_connection import run_query
import os
import json

st.set_page_config(page_title="Records - CCS",page_icon="title_logo.png", layout="wide")

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

st.title("🗃️ Records")
st.write("Search, filter, sort & manage all transactions.")

# --- CUSTOM CSS FOR METRIC CARDS ---
st.markdown("""
    <style>
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)

# =========================================================
# SECTION 1: FILTERS & DATA VISUALIZATION
# =========================================================
with st.container():
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        search_query = st.text_input("Search", placeholder="Customer / Supplier / Invoice # / Serial")
        payment_type = st.selectbox("Payment Type", ["All", "Cash", "Credit", "NEFT", "RTGS"])
    with col2:
        date_field = st.selectbox("Date Field", ["Sales Date", "Purchase Date"])
        sort_by = st.selectbox("Sort By", ["Created", "Sales Date", "Purchase Date", "Purchase Value", "Sales Value"])
    with col3:
        from_date = st.date_input("From", datetime.today() - timedelta(days=30))
        direction = st.selectbox("Direction", ["Descending", "Ascending"])
    with col4:
        to_date = st.date_input("To", datetime.today())
        st.markdown("<br>", unsafe_allow_html=True)
        apply_filters = st.button("Apply Filters", type="primary", use_container_width=True)

st.divider()

# 1. The Smart Filter Buttons
view_type = st.radio(
    "Filter Data:", 
    ["Unsold Stock (Available to Sell)", "Completed Sales", "Everything"],
    horizontal=True
)

# 2. Your exact base query without the semicolon at the end
base_query = """
    SELECT
        t.sales_invoice_date as "Sales Date",
        COALESCE(t.invoice_number, '-') as "Invoice #",
        COALESCE(c.customer_name, 'Unsold') as "Customer",
        s.supplier_number as "Supplier No.",
        s.supplier_name as "Supplier",
        COALESCE(t.payment_type, '-') as "Payment",
        t.purchase_rate as "Purchase",
        COALESCE(t.sales_rate, 0) as "Sales",
        t.date_of_dispatch as "Dispatch",
        t.date_of_payment as "Paid On",
        t.purchase_date as "Purchase Date",
        t.created_at as "Created",
        t.serial_number as "Serial No",
        COUNT(t.serial_number) OVER(PARTITION BY t.purchase_date, t.supplier_id, t.purchase_rate) as "Total Qty"
    FROM transactions t
    LEFT JOIN suppliers s ON t.supplier_id = s.id
    LEFT JOIN customers c ON t.customer_id = c.id
"""

# 3. Decide what filter to apply based on the button clicked
if view_type == "Unsold Stock (Available to Sell)":
    query = base_query + " WHERE t.sales_invoice_date IS NULL;"
elif view_type == "Completed Sales":
    query = base_query + " WHERE t.sales_invoice_date IS NOT NULL;"
else:
    query = base_query + ";" # Just cap it off for "Everything"

# 4. Fetch the data!
raw_data = run_query(query)

if not raw_data:
    st.info("No transactions found in the database.")
else:
    df = pd.DataFrame(raw_data)
    
    if search_query:
        search_term = search_query.lower()
        df = df[
            df["Customer"].str.lower().str.contains(search_term, na=False) |
            df["Supplier"].str.lower().str.contains(search_term, na=False) |
            df["Invoice #"].str.lower().str.contains(search_term, na=False) |
            df["Serial No"].str.lower().str.contains(search_term, na=False)
        ]
        
    if payment_type != "All":
        df = df[df["Payment"] == payment_type]
        
    date_col = "Sales Date" if date_field == "Sales Date" else "Purchase Date"
    
    # Force both the column and the calendar inputs into the exact same Pandas datetime format
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    pd_from_date = pd.to_datetime(from_date)
    pd_to_date = pd.to_datetime(to_date)

    df = df[(df[date_col] >= pd_from_date) & (df[date_col] <= pd_to_date)]
    
    sort_col_map = {
        "Created": "Created", "Sales Date": "Sales Date", "Purchase Date": "Purchase Date",
        "Purchase Value": "Purchase", "Sales Value": "Sales"
    }
    df = df.sort_values(by=sort_col_map[sort_by], ascending=(direction == "Ascending"))

    # ==========================================
    # DYNAMIC METRICS CARDS
    # ==========================================
    total_records = len(df)
    total_purchase = df['Purchase'].sum() if 'Purchase' in df.columns else 0
    total_sales = df['Sales'].sum() if 'Sales' in df.columns else 0
    revenue = total_sales - total_purchase

    if view_type == "Unsold Stock (Available to Sell)":
        m1, m2 = st.columns(2)
        m1.metric("RECORDS", total_records)
        m2.metric("TOTAL PURCHASE", f"₹ {total_purchase:,.2f}")
    else:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("RECORDS", total_records)
        m2.metric("TOTAL SALES", f"₹ {total_sales:,.2f}")
        m3.metric("TOTAL PURCHASE", f"₹ {total_purchase:,.2f}")
        m4.metric("REVENUE", f"₹ {revenue:,.2f}")

    st.markdown("<br>", unsafe_allow_html=True)

    # ==========================================
    # DYNAMIC TABLE COLUMNS
    # ==========================================
    df.insert(0, "SL", range(1, len(df) + 1))
    display_cols = ["SL", "Purchase Date", "Sales Date", "Total Qty", "Serial No", "Invoice #", "Customer", "Supplier No.", "Supplier", "Payment", "Purchase", "Sales", "Dispatch", "Paid On"]
    
    # --- VISUAL CLEANUP: Hide ONLY the repeating Total Qty ---
    display_df = df.copy()
    
    # Check if this row is part of the same purchase batch as the row above it
    mask = (display_df['Purchase Date'] == display_df['Purchase Date'].shift()) & \
           (display_df['Supplier No.'] == display_df['Supplier No.'].shift())
           
    # Convert to text BEFORE masking
    display_df['Total Qty'] = display_df['Total Qty'].astype(str)
    
    # ONLY erase the 'Total Qty' for duplicate rows. Leave EVERYTHING else completely alone!
    display_df.loc[mask, 'Total Qty'] = ""

    # If looking at Unsold Stock, remove the irrelevant sales columns from the list
    if view_type == "Unsold Stock (Available to Sell)":
        sales_cols_to_hide = ["Sales Date", "Invoice #", "Customer", "Sales", "Dispatch", "Paid On"]
        display_cols = [c for c in display_cols if c not in sales_cols_to_hide]

    # Display the final dynamically sized table
    st.dataframe(display_df[display_cols], use_container_width=True, hide_index=True, height=300)

# =========================================================
# SECTION 2: MANAGE RECORDS (EDIT & DELETE) - RESTORED!
# =========================================================
st.divider()
st.subheader("🛠️ Manage Records (Edit / Delete)")
st.write("Select a specific Serial Number below to update its details or remove it completely.")

all_serials = run_query("SELECT serial_number FROM transactions ORDER BY created_at DESC")
serial_list = [row['serial_number'] for row in all_serials] if all_serials else []

selected_serial = st.selectbox("Select Serial Number", ["-- Select --"] + serial_list)

if selected_serial != "-- Select --":
    fetch_query = """
        SELECT t.*, s.supplier_name, s.supplier_number, c.customer_name 
        FROM transactions t
        LEFT JOIN suppliers s ON t.supplier_id = s.id
        LEFT JOIN customers c ON t.customer_id = c.id
        WHERE t.serial_number = %s
    """
    raw_txn = run_query(fetch_query, (selected_serial,))
    
    if raw_txn:
        txn = raw_txn[0]
        
        tab1, tab2 = st.tabs(["✏️ Edit All Details", "🗑️ Delete Record"])
        
        with tab1:
            with st.form("edit_form"):
                st.info("You can edit ANY field below, including the Serial Number itself.")
                new_serial = st.text_input("Serial Number *", value=txn['serial_number'])
                st.markdown("<hr/>", unsafe_allow_html=True)
                
                ec1, ec2 = st.columns(2)
                
                with ec1:
                    st.write("**📋 Purchase Details**")
                    new_pur_date = st.date_input("Purchase Date", value=txn['purchase_date'])
                    new_sup_name = st.text_input("Supplier Name *", value=txn['supplier_name'] or "")
                    new_sup_num = st.text_input("Supplier Number *", value=txn['supplier_number'] or "")
                    
                    current_payment = txn['payment_type']
                    payment_options = ["Cash", "Credit", "NEFT", "RTGS"]
                    pay_index = payment_options.index(current_payment) if current_payment in payment_options else 0
                    new_payment = st.selectbox("Payment Type", payment_options, index=pay_index)
                    
                    new_pur_rate = st.number_input("Purchase Rate (₹) *", value=float(txn['purchase_rate']), format="%.2f")

                with ec2:
                    st.write("**🧾 Sales Details**")
                    new_cust_name = st.text_input("Customer Name", value=txn['customer_name'] or "")
                    new_inv_date = st.date_input("Sales Invoice Date", value=txn['sales_invoice_date'] if txn['sales_invoice_date'] else None)
                    new_invoice = st.text_input("Invoice Number", value=txn['invoice_number'] or "")
                    new_sales_rate = st.number_input("Sales Rate (₹)", value=float(txn['sales_rate'] or 0.0), format="%.2f")
                    
                    dc1, dc2 = st.columns(2)
                    with dc1:
                        new_dispatch = st.date_input("Dispatch Date", value=txn['date_of_dispatch'] if txn['date_of_dispatch'] else None)
                    with dc2:
                        new_payment_date = st.date_input("Payment Date", value=txn['date_of_payment'] if txn['date_of_payment'] else None)

                new_notes = st.text_area("Additional Notes", value=txn['notes'] or "")
                
                update_btn = st.form_submit_button("💾 Save All Changes", type="primary", use_container_width=True)
                
                if update_btn:
                    if not new_sup_name or not new_sup_num or not new_serial:
                        st.error("Serial Number, Supplier Name, and Supplier Number are mandatory.")
                    else:
                        # 1. Handle Supplier safely
                        sup_rows = run_query("""
                            INSERT INTO suppliers (supplier_number, supplier_name) 
                            VALUES (%s, %s) 
                            ON CONFLICT (supplier_number) DO NOTHING
                            RETURNING id;
                        """, (new_sup_num, new_sup_name))
                        
                        if not sup_rows:
                            fetch_sup = run_query("SELECT id FROM suppliers WHERE supplier_number = %s;", (new_sup_num,))
                            supplier_id = fetch_sup[0]['id'] if fetch_sup else None
                        else:
                            supplier_id = sup_rows[0]['id']

                        # 2. Handle Customer safely
                        customer_id = None
                        if new_cust_name.strip():
                            cust_rows = run_query("""
                                INSERT INTO customers (customer_name) 
                                VALUES (%s) 
                                ON CONFLICT (customer_name) DO NOTHING
                                RETURNING id;
                            """, (new_cust_name.strip(),))
                            
                            if not cust_rows:
                                fetch_cust = run_query("SELECT id FROM customers WHERE customer_name = %s;", (new_cust_name.strip(),))
                                customer_id = fetch_cust[0]['id'] if fetch_cust else None
                            else:
                                customer_id = cust_rows[0]['id']

                        # 3. Update Transaction
                        update_query = """
                            UPDATE transactions 
                            SET serial_number = %s, purchase_date = %s, supplier_id = %s, payment_type = %s, purchase_rate = %s,
                                sales_invoice_date = %s, invoice_number = %s, customer_id = %s, sales_rate = %s,
                                date_of_dispatch = %s, date_of_payment = %s, notes = %s
                            WHERE serial_number = %s
                        """
                        result = run_query(update_query, (
                            new_serial, new_pur_date, supplier_id, new_payment, new_pur_rate,
                            new_inv_date, new_invoice if new_invoice.strip() else None, customer_id, new_sales_rate if new_sales_rate > 0 else None,
                            new_dispatch, new_payment_date, new_notes, 
                            selected_serial 
                        ))
                        
                        if result:
                            st.success("All details updated successfully! Reloading...")
                            st.rerun() 
                        else:
                            st.error("Database failed to update. Please check your inputs.")

        with tab2:
            st.warning(f"Are you sure you want to permanently delete **{selected_serial}**? This cannot be undone.")
            if st.button("🚨 Yes, Delete this Record", type="primary"):
                run_query("DELETE FROM transactions WHERE serial_number = %s", (selected_serial,))
                st.success("Record deleted permanently! Reloading...")
                st.rerun()
