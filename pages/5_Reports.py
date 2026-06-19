import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io
from database.db_connection import run_query
from fpdf import FPDF
import time
import os
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# ==========================================
# GMAIL EMAIL ENGINE (FREE & BUILT-IN)
# ==========================================
def send_email_with_pdf(to_email, pdf_data, excel_data, file_name_base):
    sender_email = st.secrets["email"]["sender"]
    app_password = st.secrets["email"]["password"]

    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = "Report: Centreal Consultancy Services"

        body = "<p>Hello,<br><br>Please find the requested PDF and Excel reports attached.<br><br>Best regards,<br>Centreal Consultancy Services</p>"
        msg.attach(MIMEText(body, 'html'))

        pdf_attachment = MIMEApplication(pdf_data, _subtype="pdf")
        pdf_attachment.add_header('Content-Disposition', 'attachment', filename=f"{file_name_base}.pdf")
        msg.attach(pdf_attachment)

        excel_attachment = MIMEApplication(excel_data, _subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        excel_attachment.add_header('Content-Disposition', 'attachment', filename=f"{file_name_base}.xlsx")
        msg.attach(excel_attachment)

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(msg)
        server.quit()

        return {"id": "success"} 
        
    except Exception as e:
        return str(e)
        
st.set_page_config(page_title="Reports - CCS",page_icon="title_logo.png", layout="wide")

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
    st.sidebar.image("saved_logo.png", use_column_width=True)

company_title = "CENTREAL CONSULTANCY SERVICES" 
if os.path.exists("settings.json"):
    with open("settings.json", "r") as f:
        try:
            saved_data = json.load(f)
            company_title = saved_data.get("company_name", company_title)
        except Exception:
            pass

st.sidebar.markdown(f"<h3 style='text-align: center;'>{company_title}</h3>", unsafe_allow_html=True)
st.sidebar.markdown("---")

# --- 1. FILTER SECTION ---
st.subheader("1. Select Report Criteria")

col1, col2, col3 = st.columns(3)
with col1:
    report_type = st.selectbox("Report Type", ["ALL TRANSACTIONS", "PURCHASE REPORT", "SALES REPORT"])
with col2:
    start_date = st.date_input("Start Date", datetime.today() - timedelta(days=30))
with col3:
    end_date = st.date_input("End Date", datetime.today())

st.markdown("<br>", unsafe_allow_html=True)
generate_btn = st.button("Generate Report", type="primary", use_container_width=True)

st.divider()

# --- 2. GENERATE & STORE REPORT ---
if generate_btn:
    with st.spinner("Generating Report..."):
        st.subheader("2. Report Preview")
        
        base_query = """
            SELECT 
                t.purchase_date as "Purchase Date",
                s.supplier_number as "Supplier No.",
                COALESCE(t.product_name, '-') as "Product Name",
                s.supplier_name as "Supplier Name",
                COALESCE(t.payment_type, '-') as "Purchase Mode",
                COUNT(t.serial_number) OVER(PARTITION BY t.purchase_date, s.supplier_number, t.product_name) as "Total Qty",
                t.purchase_rate as "Rate - Without Tax (P)",
                t.serial_number as "Serial Number",
                t.sales_invoice_date as "Sales Invoice Date",
                COALESCE(t.invoice_number, '-') as "Invoice No.",
                COALESCE(c.customer_name, 'Unsold') as "Customer Name",
                COALESCE(t.sales_rate, 0) as "Rate - Without Tax (S)"
            FROM transactions t
            LEFT JOIN suppliers s ON t.supplier_id = s.id
            LEFT JOIN customers c ON t.customer_id = c.id
            WHERE t.purchase_date >= %s AND t.purchase_date <= %s
        """
        
        if report_type == "PURCHASE REPORT":
            query = base_query + " ORDER BY t.purchase_date DESC, s.supplier_number ASC"
        else:
            query = base_query + " AND t.sales_invoice_date IS NOT NULL ORDER BY t.purchase_date DESC, s.supplier_number ASC"
            
        data = run_query(query, (start_date, end_date))

        if not data:
            st.warning("No data found for the selected dates.")
        else:
            df = pd.DataFrame(data)
            df.insert(0, "SL", range(1, len(df) + 1))
            
            total_qty = len(df)
            total_purchase = df["Rate - Without Tax (P)"].sum()
            total_sales = df["Rate - Without Tax (S)"].sum()
            revenue = total_sales - total_purchase
            
            # ✨ DYNAMIC WEB PREVIEW (WITH DUPLICATED SALES PRODUCT NAME) ✨
            st.write("Preview of Data:")
            display_df = df.copy()
            
            if report_type == "ALL TRANSACTIONS":
                 display_df['Product Name (Sold)'] = display_df['Product Name']
                 display_df = display_df[['SL', 'Purchase Date', 'Supplier No.', 'Product Name', 'Supplier Name', 'Purchase Mode', 'Total Qty', 'Rate - Without Tax (P)', 'Serial Number', 'Sales Invoice Date', 'Invoice No.', 'Product Name (Sold)', 'Customer Name', 'Rate - Without Tax (S)']]
            elif report_type == "PURCHASE REPORT":
                display_df = display_df[['SL', 'Purchase Date', 'Supplier No.', 'Product Name', 'Supplier Name', 'Purchase Mode', 'Total Qty', 'Rate - Without Tax (P)', 'Serial Number']]
            elif report_type == "SALES REPORT":
                display_df = display_df[['SL', 'Serial Number', 'Purchase Date', 'Sales Invoice Date', 'Invoice No.', 'Product Name', 'Customer Name', 'Rate - Without Tax (S)']]

            if 'Total Qty' in display_df.columns:
                display_df['Total Qty'] = display_df['Total Qty'].astype(str)
                mask = (display_df['Purchase Date'] == display_df['Purchase Date'].shift()) & \
                       (display_df.get('Supplier No.', "") == display_df.get('Supplier No.', "").shift()) & \
                       (display_df.get('Product Name', "") == display_df.get('Product Name', "").shift())
                display_df.loc[mask, ['Total Qty']] = ""
                
            st.dataframe(display_df, use_container_width=True, hide_index=True, height=300)
            
            # ==========================================
            # EXCEL EXPORT (UPDATED WITH DUPLICATE COLUMN)
            # ==========================================
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                workbook = writer.book
                worksheet = workbook.add_worksheet('Report')
                
                title_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 14})
                subtitle_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 11})
                italic_format = workbook.add_format({'italic': True, 'align': 'center'})
                purchase_head_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#0033CC', 'font_color': 'white', 'border': 1})
                sales_head_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#001A66', 'font_color': 'white', 'border': 1})
                col_header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#F2F2F2', 'border': 1, 'text_wrap': True})
                data_format = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter'})
                currency_data_format = workbook.add_format({'border': 1, 'align': 'right', 'valign': 'vcenter', 'num_format': '₹#,##0'})
                bold_currency_format = workbook.add_format({'num_format': '₹#,##0', 'bold': True, 'align': 'right'})
                bold_right_format = workbook.add_format({'bold': True, 'align': 'right'})
                
                max_col = 'N' if report_type == "ALL TRANSACTIONS" else 'I' if report_type == "PURCHASE REPORT" else 'H'
                worksheet.merge_range(f'A1:{max_col}1', company_title, title_format)
                worksheet.merge_range(f'A2:{max_col}2', f'Report Type: {report_type}', subtitle_format)
                worksheet.merge_range(f'A4:{max_col}4', f'Generated: {datetime.now().strftime("%d-%m-%Y %H:%M")}', italic_format)

                if report_type == "ALL TRANSACTIONS":
                    worksheet.merge_range('A6:I6', 'PURCHASE REGISTER', purchase_head_format)
                    worksheet.merge_range('J6:N6', 'SALES INVOICE DETAILS', sales_head_format)
                    headers = ['SL', 'Purchase Date', 'Supplier No.', 'Product Name', 'Supplier Name', 'Purchase Mode', 'Total Qty', 'Rate - Without Tax (P)', 'Serial Number', 'Sales Invoice Date', 'Invoice No.', 'Product Name', 'Customer Name', 'Rate - Without Tax (S)']
                    worksheet.set_column('A:A', 5); worksheet.set_column('B:C', 12); worksheet.set_column('D:E', 25)
                    worksheet.set_column('F:G', 10); worksheet.set_column('H:I', 15); worksheet.set_column('J:K', 15)
                    worksheet.set_column('L:M', 25); worksheet.set_column('N:N', 15)
                
                elif report_type == "PURCHASE REPORT":
                    worksheet.merge_range('A6:I6', 'PURCHASE REGISTER ONLY', purchase_head_format)
                    headers = ['SL', 'Purchase Date', 'Supplier No.', 'Product Name', 'Supplier Name', 'Purchase Mode', 'Total Qty', 'Rate - Without Tax', 'Serial Number']
                    worksheet.set_column('A:A', 5); worksheet.set_column('B:C', 15); worksheet.set_column('D:E', 30); worksheet.set_column('F:F', 15)
                    worksheet.set_column('G:G', 10); worksheet.set_column('H:I', 20)
                
                elif report_type == "SALES REPORT":
                    worksheet.merge_range('A6:H6', 'SALES INVOICE DETAILS ONLY', sales_head_format)
                    headers = ['SL', 'Serial Number', 'Purchase Date', 'Sales Invoice Date', 'Invoice No.', 'Product Name', 'Customer Name', 'Rate - Without Tax']
                    worksheet.set_column('A:A', 5); worksheet.set_column('B:E', 15); worksheet.set_column('F:G', 30); worksheet.set_column('H:H', 20)

                for col_num, header_text in enumerate(headers):
                    worksheet.write(6, col_num, header_text, col_header_format)

                blocks = []
                current_start = 0
                for i in range(1, len(df)):
                    if (df.iloc[i]['Purchase Date'] != df.iloc[i-1]['Purchase Date']) or (df.iloc[i]['Supplier No.'] != df.iloc[i-1]['Supplier No.']) or (df.iloc[i]['Product Name'] != df.iloc[i-1]['Product Name']):
                        blocks.append((current_start, i - 1))
                        current_start = i
                blocks.append((current_start, len(df) - 1))

                for idx, row in df.iterrows():
                    excel_row = 7 + idx
                    worksheet.write(excel_row, 0, row['SL'], data_format)
                    
                    if report_type == "ALL TRANSACTIONS":
                        worksheet.write(excel_row, 1, str(row['Purchase Date']), data_format)
                        worksheet.write(excel_row, 2, row['Supplier No.'], data_format)
                        worksheet.write(excel_row, 3, row['Product Name'], data_format)
                        worksheet.write(excel_row, 4, row['Supplier Name'], data_format)
                        worksheet.write(excel_row, 5, row['Purchase Mode'], data_format)
                        worksheet.write(excel_row, 7, row['Rate - Without Tax (P)'], currency_data_format)
                        worksheet.write(excel_row, 8, row['Serial Number'], data_format)
                        worksheet.write(excel_row, 9, str(row['Sales Invoice Date']) if pd.notnull(row['Sales Invoice Date']) else '-', data_format)
                        worksheet.write(excel_row, 10, row['Invoice No.'], data_format)
                        worksheet.write(excel_row, 11, row['Product Name'], data_format)
                        worksheet.write(excel_row, 12, row['Customer Name'], data_format)
                        worksheet.write(excel_row, 13, row['Rate - Without Tax (S)'], currency_data_format)
                    
                    elif report_type == "PURCHASE REPORT":
                        worksheet.write(excel_row, 1, str(row['Purchase Date']), data_format)
                        worksheet.write(excel_row, 2, row['Supplier No.'], data_format)
                        worksheet.write(excel_row, 3, row['Product Name'], data_format)
                        worksheet.write(excel_row, 4, row['Supplier Name'], data_format)
                        worksheet.write(excel_row, 5, row['Purchase Mode'], data_format)
                        worksheet.write(excel_row, 7, row['Rate - Without Tax (P)'], currency_data_format)
                        worksheet.write(excel_row, 8, row['Serial Number'], data_format)

                    elif report_type == "SALES REPORT":
                        worksheet.write(excel_row, 1, row['Serial Number'], data_format)
                        worksheet.write(excel_row, 2, str(row['Purchase Date']), data_format)
                        worksheet.write(excel_row, 3, str(row['Sales Invoice Date']) if pd.notnull(row['Sales Invoice Date']) else '-', data_format)
                        worksheet.write(excel_row, 4, row['Invoice No.'], data_format)
                        worksheet.write(excel_row, 5, row['Product Name'], data_format)
                        worksheet.write(excel_row, 6, row['Customer Name'], data_format)
                        worksheet.write(excel_row, 7, row['Rate - Without Tax (S)'], currency_data_format)

                if report_type != "SALES REPORT":
                    for start_idx, end_idx in blocks:
                        start_row = 7 + start_idx
                        end_row = 7 + end_idx
                        qty_val = df.iloc[start_idx]['Total Qty']
                        if start_row == end_row:
                            worksheet.write(start_row, 6, qty_val, data_format)
                        else:
                            worksheet.merge_range(start_row, 6, end_row, 6, qty_val, data_format)

                last_row = 7 + len(df)
                if report_type == "ALL TRANSACTIONS":
                    worksheet.write(last_row + 2, 7, total_purchase, bold_currency_format)
                    worksheet.write(last_row + 2, 13, total_sales, bold_currency_format)
                    worksheet.write(last_row + 6, 12, "Total Qty:", bold_right_format)
                    worksheet.write(last_row + 6, 13, total_qty, bold_right_format)
                    worksheet.write(last_row + 7, 12, "Total Purchase Value:", bold_right_format)
                    worksheet.write(last_row + 7, 13, total_purchase, bold_currency_format)
                    worksheet.write(last_row + 8, 12, "Total Sales Value:", bold_right_format)
                    worksheet.write(last_row + 8, 13, total_sales, bold_currency_format)
                    worksheet.write(last_row + 9, 12, "Revenue:", bold_right_format)
                    worksheet.write(last_row + 9, 13, revenue, bold_currency_format)
                    
                elif report_type == "PURCHASE REPORT":
                    worksheet.write(last_row + 2, 7, total_purchase, bold_currency_format)
                    worksheet.write(last_row + 5, 6, "Total Qty:", bold_right_format)
                    worksheet.write(last_row + 5, 7, total_qty, bold_right_format)
                    worksheet.write(last_row + 6, 6, "Total Purchase Value:", bold_right_format)
                    worksheet.write(last_row + 6, 7, total_purchase, bold_currency_format)
                    
                elif report_type == "SALES REPORT":
                    worksheet.write(last_row + 2, 7, total_sales, bold_currency_format)
                    worksheet.write(last_row + 5, 6, "Total Qty:", bold_right_format)
                    worksheet.write(last_row + 5, 7, total_qty, bold_right_format)
                    worksheet.write(last_row + 6, 6, "Total Sales Value:", bold_right_format)
                    worksheet.write(last_row + 6, 7, total_sales, bold_currency_format)

            buffer.seek(0)
            
            # ==========================================
            # PDF EXPORT (RECALCULATED FOR 14 COLUMNS)
            # ==========================================
            class ReportPDF(FPDF):
                def header(self):
                    self.set_font("helvetica", "B", 16)
                    self.set_text_color(0, 51, 204)
                    self.cell(0, 10, company_title, new_x="LMARGIN", new_y="NEXT", align="C")
                    self.set_font("helvetica", "B", 11)
                    self.set_text_color(30, 41, 59)
                    self.cell(0, 8, f"Report Type: {report_type}", new_x="LMARGIN", new_y="NEXT", align="C")
                    self.set_font("helvetica", "I", 9)
                    self.set_text_color(100, 116, 139)
                    self.cell(0, 6, f"Generated: {datetime.now().strftime('%d-%m-%Y %H:%M')}", new_x="LMARGIN", new_y="NEXT", align="C")
                    self.ln(10)
                def footer(self):
                    self.set_y(-15)
                    self.set_font("helvetica", "I", 8)
                    self.set_text_color(150, 150, 150)
                    self.cell(0, 10, f"Page {self.page_no()}", align="C")

            orient = 'L' if report_type == "ALL TRANSACTIONS" else 'P'
            pdf = ReportPDF(orientation=orient, unit='mm', format='A4')
            pdf.add_page()
            
            if report_type == "ALL TRANSACTIONS":
                pdf.set_fill_color(37, 99, 235); pdf.set_text_color(255, 255, 255); pdf.set_font("helvetica", "B", 9)
                pdf.cell(138, 8, "PURCHASE REGISTER", border=1, align="C", fill=True)
                pdf.set_fill_color(30, 58, 138)
                pdf.cell(96, 8, "SALES INVOICE DETAILS", border=1, align="C", fill=True, new_x="LMARGIN", new_y="NEXT")

                pdf.set_fill_color(241, 245, 249); pdf.set_text_color(30, 41, 59); pdf.set_font("helvetica", "B", 6.5)
                col_widths = [7, 18, 18, 22, 22, 10, 8, 15, 18, 18, 16, 22, 25, 15] 
                headers_list = ['SL', 'Purch Date', 'Supp No.', 'Product Name', 'Supplier Name', 'Mode', 'Qty', 'Rate(P)', 'Serial No.', 'Sales Date', 'Inv No.', 'Product Name', 'Customer Name', 'Rate(S)']
            
            elif report_type == "PURCHASE REPORT":
                pdf.set_fill_color(37, 99, 235); pdf.set_text_color(255, 255, 255); pdf.set_font("helvetica", "B", 9)
                pdf.cell(190, 8, "PURCHASE REGISTER", border=1, align="C", fill=True, new_x="LMARGIN", new_y="NEXT")

                pdf.set_fill_color(241, 245, 249); pdf.set_text_color(30, 41, 59); pdf.set_font("helvetica", "B", 8)
                col_widths = [8, 22, 25, 30, 35, 15, 10, 20, 25] 
                headers_list = ['SL', 'Purch Date', 'Supp No.', 'Product Name', 'Supplier Name', 'Mode', 'Qty', 'Rate (P)', 'Serial No.']
                
            elif report_type == "SALES REPORT":
                pdf.set_fill_color(30, 58, 138); pdf.set_text_color(255, 255, 255); pdf.set_font("helvetica", "B", 9)
                pdf.cell(190, 8, "SALES INVOICE DETAILS", border=1, align="C", fill=True, new_x="LMARGIN", new_y="NEXT")

                pdf.set_fill_color(241, 245, 249); pdf.set_text_color(30, 41, 59); pdf.set_font("helvetica", "B", 8)
                col_widths = [8, 25, 22, 22, 25, 30, 38, 20] 
                headers_list = ['SL', 'Serial No.', 'Purch Date', 'Sales Date', 'Inv No.', 'Product Name', 'Customer Name', 'Rate (S)']

            for i, h in enumerate(headers_list):
                pdf.cell(col_widths[i], 8, h, border=1, align="C", fill=True)
            pdf.ln()

            pdf.set_font("helvetica", "", 6.5 if report_type == "ALL TRANSACTIONS" else 7.5) 
            pdf.set_text_color(0, 0, 0)
            
            for start_idx, end_idx in blocks:
                qty_val = str(df.iloc[start_idx]['Total Qty'])
                mid_idx = start_idx + (end_idx - start_idx) // 2
                
                for idx in range(start_idx, end_idx + 1):
                    row = df.iloc[idx]
                    pdf.cell(col_widths[0], 8, str(row['SL']), border=1, align="C")
                    
                    if report_type == "ALL TRANSACTIONS":
                        pdf.cell(col_widths[1], 8, str(row['Purchase Date'])[:10], border=1, align="C")
                        pdf.cell(col_widths[2], 8, str(row['Supplier No.']), border=1, align="C")
                        pdf.cell(col_widths[3], 8, str(row['Product Name'])[:18], border=1, align="L")
                        pdf.cell(col_widths[4], 8, str(row['Supplier Name'])[:18], border=1, align="L")
                        pdf.cell(col_widths[5], 8, str(row['Purchase Mode'])[:5], border=1, align="C")
                        qty_border = 'LR' 
                        if idx == start_idx: qty_border += 'T' 
                        if idx == end_idx:   qty_border += 'B' 
                        display_qty = qty_val if idx == mid_idx else ""
                        pdf.cell(col_widths[6], 8, display_qty, border=qty_border, align="C")
                        pdf.cell(col_widths[7], 8, f"{row['Rate - Without Tax (P)']:,.0f}", border=1, align="R")
                        pdf.cell(col_widths[8], 8, str(row['Serial Number'])[:15], border=1, align="C")
                        pdf.cell(col_widths[9], 8, str(row['Sales Invoice Date'])[:10] if pd.notnull(row['Sales Invoice Date']) else "-", border=1, align="C")
                        pdf.cell(col_widths[10], 8, str(row['Invoice No.'])[:12], border=1, align="C")
                        pdf.cell(col_widths[11], 8, str(row['Product Name'])[:18], border=1, align="L")
                        pdf.cell(col_widths[12], 8, str(row['Customer Name'])[:20], border=1, align="L")
                        pdf.cell(col_widths[13], 8, f"{row['Rate - Without Tax (S)']:,.0f}", border=1, align="R", new_x="LMARGIN", new_y="NEXT")

                    elif report_type == "PURCHASE REPORT":
                        pdf.cell(col_widths[1], 8, str(row['Purchase Date'])[:10], border=1, align="C")
                        pdf.cell(col_widths[2], 8, str(row['Supplier No.']), border=1, align="C")
                        pdf.cell(col_widths[3], 8, str(row['Product Name'])[:20], border=1, align="L")
                        pdf.cell(col_widths[4], 8, str(row['Supplier Name'])[:25], border=1, align="L")
                        pdf.cell(col_widths[5], 8, str(row['Purchase Mode']), border=1, align="C")
                        qty_border = 'LR' 
                        if idx == start_idx: qty_border += 'T' 
                        if idx == end_idx:   qty_border += 'B' 
                        display_qty = qty_val if idx == mid_idx else ""
                        pdf.cell(col_widths[6], 8, display_qty, border=qty_border, align="C")
                        pdf.cell(col_widths[7], 8, f"{row['Rate - Without Tax (P)']:,.0f}", border=1, align="R")
                        pdf.cell(col_widths[8], 8, str(row['Serial Number']), border=1, align="C", new_x="LMARGIN", new_y="NEXT")

                    elif report_type == "SALES REPORT":
                        pdf.cell(col_widths[1], 8, str(row['Serial Number']), border=1, align="C")
                        pdf.cell(col_widths[2], 8, str(row['Purchase Date'])[:10], border=1, align="C")
                        pdf.cell(col_widths[3], 8, str(row['Sales Invoice Date'])[:10] if pd.notnull(row['Sales Invoice Date']) else "-", border=1, align="C")
                        pdf.cell(col_widths[4], 8, str(row['Invoice No.']), border=1, align="C")
                        pdf.cell(col_widths[5], 8, str(row['Product Name'])[:20], border=1, align="L")
                        pdf.cell(col_widths[6], 8, str(row['Customer Name'])[:25], border=1, align="L")
                        pdf.cell(col_widths[7], 8, f"{row['Rate - Without Tax (S)']:,.0f}", border=1, align="R", new_x="LMARGIN", new_y="NEXT")

            pdf.ln(5) 
            pdf.set_font("helvetica", "B", 9)
            pdf.set_text_color(30, 41, 59)
            
            sum_x = 180 if report_type == "ALL TRANSACTIONS" else 130
            
            if report_type in ["ALL TRANSACTIONS", "PURCHASE REPORT"]:
                pdf.set_x(sum_x); pdf.cell(30, 8, "Total Qty:", align="R"); pdf.cell(30, 8, str(total_qty), align="R", new_x="LMARGIN", new_y="NEXT")
                pdf.set_x(sum_x); pdf.cell(30, 8, "Total Purchase:", align="R"); pdf.cell(30, 8, f"Rs. {total_purchase:,.0f}", align="R", new_x="LMARGIN", new_y="NEXT")
            if report_type in ["ALL TRANSACTIONS", "SALES REPORT"]:
                if report_type == "SALES REPORT":
                    pdf.set_x(sum_x); pdf.cell(30, 8, "Total Qty:", align="R"); pdf.cell(30, 8, str(total_qty), align="R", new_x="LMARGIN", new_y="NEXT")
                pdf.set_x(sum_x); pdf.cell(30, 8, "Total Sales:", align="R"); pdf.cell(30, 8, f"Rs. {total_sales:,.0f}", align="R", new_x="LMARGIN", new_y="NEXT")
            if report_type == "ALL TRANSACTIONS":
                pdf.set_text_color(16, 185, 129) 
                pdf.set_x(sum_x); pdf.cell(30, 8, "Revenue:", align="R"); pdf.cell(30, 8, f"Rs. {revenue:,.0f}", align="R", new_x="LMARGIN", new_y="NEXT")
            
            st.session_state['pdf_bytes'] = bytes(pdf.output())
            st.session_state['excel_buffer'] = buffer.getvalue()
            prefix = "All" if report_type == "ALL TRANSACTIONS" else "Purch" if report_type == "PURCHASE REPORT" else "Sales"
            st.session_state['report_name'] = f"CCS_{prefix}_Report_{datetime.today().strftime('%Y%m%d')}"
            st.session_state['report_ready'] = True

# ==========================================
# 3. SHARE & DOWNLOAD UI
# ==========================================
if st.session_state.get('report_ready', False):
    st.markdown("<br><hr>", unsafe_allow_html=True)
    st.subheader("📧 Share & Download")
    
    col_email, col_excel, col_pdf = st.columns([2, 1, 1])
    
    with col_email:
        recipient_email = st.text_input("Recipient Email (MUST be your Resend account email!)")
        msg_box = st.empty() 
        
        if st.button("🚀 Send Email", type="primary"):
            if not recipient_email:
                msg_box.error("Please enter a valid email address.")
                time.sleep(3)
                msg_box.empty() 
            else:
                msg_box.info("Sending...")
                try:
                    response = send_email_with_pdf(
                        to_email=recipient_email, 
                        pdf_data=st.session_state['pdf_bytes'], 
                        excel_data=st.session_state['excel_buffer'], 
                        file_name_base=st.session_state['report_name']
                    )
                    if isinstance(response, dict) and 'id' in response:
                        msg_box.success(f"✅ SUCCESS! Email sent from Gmail to {recipient_email}")
                    else:
                        msg_box.warning(f"⚠️ Sent, but unconfirmed: {response}")
                    time.sleep(5)
                    msg_box.empty() 
                except Exception as e:
                    msg_box.error(f"🚨 ERROR: {str(e)}")
                    time.sleep(5)
                    msg_box.empty()

    with col_excel:
        st.write("") 
        st.write("")
        st.download_button(
            label="📊 Download Excel",
            data=st.session_state['excel_buffer'],
            file_name=f"{st.session_state['report_name']}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
    with col_pdf:
        st.write("") 
        st.write("")
        st.download_button(
            label="📄 Download PDF",
            data=st.session_state['pdf_bytes'],
            file_name=f"{st.session_state['report_name']}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
