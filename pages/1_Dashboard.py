import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database.db_connection import run_query
import os
import json

st.set_page_config(page_title="Dashboard - CCS",page_icon="saved_logo.png", layout="wide")

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

# ==========================================
# 1. FETCH LIVE DATA
# ==========================================
metrics_query = """
    SELECT 
        COUNT(serial_number) as total_transactions,
        COALESCE(SUM(purchase_rate), 0) as total_purchase,
        COALESCE(SUM(sales_rate), 0) as total_sales
    FROM transactions
"""
metrics_data = run_query(metrics_query)
data = metrics_data[0] if metrics_data else {'total_transactions': 0, 'total_purchase': 0, 'total_sales': 0}

total_transactions = data['total_transactions']
total_purchase = data['total_purchase']
total_sales = data['total_sales']
revenue = total_sales - total_purchase

# Note: We are using a placeholder for Pending Payments until we build an invoice tracker!
pending_payments = 29500 

# ==========================================
# 2. HEADER & DATE PICKERS
# ==========================================
col_title, col_dates = st.columns([1, 1])
with col_title:
    st.markdown("<h2 style='margin-bottom: 0px; color: #1e293b;'>Dashboard</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748b; margin-top: 0px;'>Overview of your business metrics.</p>", unsafe_allow_html=True)
with col_dates:
    # Just visual placeholders to match your Replit design
    st.markdown("<div style='text-align: right; margin-top: 20px; color: #64748b;'>📅 dd-mm-yyyy &nbsp; to &nbsp; 📅 dd-mm-yyyy &nbsp; <button style='background:white; border:1px solid #e2e8f0; border-radius:4px; padding:4px 10px;'>Clear</button></div>", unsafe_allow_html=True)

# ==========================================
# 3. REPLIT-STYLE METRIC CARDS (Custom HTML)
# ==========================================
def create_card(title, value, value_color="#0f172a"):
    return f"""
    <div style="background-color: white; padding: 20px; border-radius: 8px; border: 1px solid #e2e8f0; box-shadow: 0 1px 2px rgba(0,0,0,0.03); height: 110px;">
        <p style="color: #64748b; font-size: 13px; font-weight: 600; margin-bottom: 5px; text-transform: uppercase;">{title}</p>
        <h2 style="color: {value_color}; margin: 0; font-size: 26px;">{value}</h2>
    </div>
    """

# Changed from 5 columns to 4
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(create_card("Total Transactions", f"{total_transactions}"), unsafe_allow_html=True)
with c2:
    st.markdown(create_card("Purchase Value", f"₹{total_purchase:,.0f}"), unsafe_allow_html=True)
with c3:
    st.markdown(create_card("Sales Value", f"₹{total_sales:,.0f}", "#3b82f6"), unsafe_allow_html=True) 
with c4:
    st.markdown(create_card("Revenue", f"₹{revenue:,.0f}", "#10b981"), unsafe_allow_html=True) 

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 4. FETCH CHART DATA
# ==========================================
chart_query = """
    SELECT 
        purchase_date as date,
        SUM(purchase_rate) as purchase,
        SUM(sales_rate) as sales,
        COUNT(serial_number) as volume
    FROM transactions
    WHERE purchase_date IS NOT NULL
    GROUP BY purchase_date
    ORDER BY purchase_date
"""
chart_data = run_query(chart_query)

if chart_data:
    df_charts = pd.DataFrame(chart_data)
    # Format the date cleanly (e.g., 'Jun 01, 2026')
    df_charts['date_label'] = pd.to_datetime(df_charts['date']).dt.strftime('%b %d, %Y')
    # Calculate Revenue
    df_charts['revenue'] = df_charts['sales'] - df_charts['purchase']
else:
    # Fallback dummy data if database is empty
    df_charts = pd.DataFrame({
        "date_label": ["Jan 2025", "Feb 2025", "Mar 2025", "Jun 2026"],
        "purchase": [40000, 45000, 50000, 380000],
        "sales": [50000, 55000, 60000, 400000],
        "revenue": [10000, 10000, 10000, 20000],
        "volume": [3, 3, 3, 4]
    })

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 5. RENDER THE 4 CHARTS (Perfect 2x2 Grid)
# ==========================================
row1_col1, row1_col2 = st.columns(2)
row2_col1, row2_col2 = st.columns(2)

# --- CHART 1: SALES VS PURCHASE (Bar Chart) ---
with row1_col1:
    with st.container(border=True):
        st.markdown("<h4 style='margin:0; color:#1e293b; font-size: 16px;'>Sales vs Purchase</h4><br>", unsafe_allow_html=True)
        
        fig1 = go.Figure()
        fig1.add_trace(go.Bar(x=df_charts['date_label'], y=df_charts['sales'], name='Sales', marker_color='#2563eb'))
        fig1.add_trace(go.Bar(x=df_charts['date_label'], y=df_charts['purchase'], name='Purchase', marker_color='#e2e8f0'))

        fig1.update_layout(
            barmode='group', plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, t=10, b=0), height=260,
            legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5) 
        )
        fig1.update_yaxes(showgrid=True, gridcolor='#f8fafc', zeroline=False)
        fig1.update_xaxes(type='category', showgrid=False) 
        st.plotly_chart(fig1, use_container_width=True)

# --- CHART 2: SALES TREND (Line Chart) ---
with row1_col2:
    with st.container(border=True):
        st.markdown("<h4 style='margin:0; color:#1e293b; font-size: 16px;'>Sales Trend</h4><br>", unsafe_allow_html=True)
        
        fig2 = go.Figure()
        # Using a slightly lighter blue (#0ea5e9) to distinguish it from Revenue, but keep the Replit vibe
        fig2.add_trace(go.Scatter(
            x=df_charts['date_label'], y=df_charts['sales'], 
            mode='lines+markers', 
            line=dict(color='#0ea5e9', width=2), 
            marker=dict(size=8, color='white', line=dict(width=2, color='#0ea5e9'))
        ))
        fig2.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, t=10, b=0), height=260)
        fig2.update_yaxes(showgrid=True, gridcolor='#f8fafc', zeroline=False)
        fig2.update_xaxes(type='category', showgrid=False)
        st.plotly_chart(fig2, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True) # A little breathing room between rows

# --- CHART 3: REVENUE TREND (Line Chart) ---
with row2_col1:
    with st.container(border=True):
        st.markdown("<h4 style='margin:0; color:#1e293b; font-size: 16px;'>Revenue Trend</h4><br>", unsafe_allow_html=True)
        
        fig3 = go.Figure()
        # Signature Replit primary blue (#2563eb)
        fig3.add_trace(go.Scatter(
            x=df_charts['date_label'], y=df_charts['revenue'], 
            mode='lines+markers', 
            line=dict(color='#2563eb', width=2), 
            marker=dict(size=8, color='white', line=dict(width=2, color='#2563eb'))
        ))
        fig3.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, t=10, b=0), height=260)
        fig3.update_yaxes(showgrid=True, gridcolor='#f8fafc', zeroline=False)
        fig3.update_xaxes(type='category', showgrid=False)
        st.plotly_chart(fig3, use_container_width=True)

# --- CHART 4: TRANSACTION VOLUME (Light Grey Bars) ---
with row2_col2:
    with st.container(border=True):
        st.markdown("<h4 style='margin:0; color:#1e293b; font-size: 16px;'>Transaction Volume</h4><br>", unsafe_allow_html=True)
        
        fig4 = go.Figure()
        fig4.add_trace(go.Bar(x=df_charts['date_label'], y=df_charts['volume'], marker_color='#2563eb'))
        
        fig4.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, t=10, b=0), height=260, showlegend=False)
        fig4.update_yaxes(showgrid=True, gridcolor='#f8fafc', dtick=1, zeroline=False) 
        fig4.update_xaxes(type='category', showgrid=False)
        st.plotly_chart(fig4, use_container_width=True)
        
# ==========================================
# 6. SIMPLE MANUAL STOCK CONTROLLER
# ==========================================
st.markdown("<br>", unsafe_allow_html=True)

# 1. Setup Session State to remember the numbers even if you click away
if 'manual_total_bought' not in st.session_state:
    st.session_state['manual_total_bought'] = 0
if 'manual_total_sold' not in st.session_state:
    st.session_state['manual_total_sold'] = 0

# Calculate what is left
remaining_stock = st.session_state['manual_total_bought'] - st.session_state['manual_total_sold']

# 2. Display the Big Numbers
st.markdown("<h4 style='color:#1e293b; margin-bottom:10px;'>📦 Quick Stock Status</h4>", unsafe_allow_html=True)

col_stat1, col_stat2, col_stat3 = st.columns(3)
with col_stat1:
    with st.container(border=True):
        st.metric("Total Laptops Bought", st.session_state['manual_total_bought'])
with col_stat2:
    with st.container(border=True):
        st.metric("Total Laptops Sold", st.session_state['manual_total_sold'])
with col_stat3:
    with st.container(border=True):
        # Give the remaining stock a color based on if it's running low!
        st.metric("Currently Remaining", remaining_stock, delta="In Stock", delta_color="normal")

st.markdown("<br>", unsafe_allow_html=True)

# 3. The Manager's Input Controls
with st.container(border=True):
    st.markdown("<h5 style='color:#1e293b; margin-bottom:10px;'>⚙️ Update Stock Numbers</h5>", unsafe_allow_html=True)
    
    col_input1, col_input2, col_input3 = st.columns([1, 1, 0.5])
    
    with col_input1:
        new_total = st.number_input("1. Set Overall Total Bought", min_value=0, step=1, value=st.session_state['manual_total_bought'])
        if st.button("Update Total", type="secondary", use_container_width=True):
            st.session_state['manual_total_bought'] = new_total
            st.rerun()
            
    with col_input2:
        daily_sold = st.number_input("2. How many sold today?", min_value=0, step=1, value=0)
        if st.button("Log Daily Sale", type="primary", use_container_width=True):
            if daily_sold > 0:
                st.session_state['manual_total_sold'] += daily_sold
                st.rerun()
                
    with col_input3:
        st.write("Need to start over?")
        st.write("") # spacing
        if st.button("Reset All to Zero", use_container_width=True):
            st.session_state['manual_total_bought'] = 0
            st.session_state['manual_total_sold'] = 0
            st.rerun()
