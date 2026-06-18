import streamlit as st
import os
import json

st.set_page_config(page_title="Settings - CCS",page_icon="title_logo.png", layout="wide")

# ==========================================
# PERMANENT STORAGE SETUP
# ==========================================
SETTINGS_FILE = "settings.json"
LOGO_FILE = "saved_logo.png"

# Helper function to load settings from the hard drive safely
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            try:
                data = json.load(f)
                # Ensure the password fallback exists inside the file schema
                if "app_password" not in data:
                    data["app_password"] = "ccs2026"
                return data
            except Exception:
                pass
    return {
        "company_name": "CENTREAL CONSULTANCY SERVICES",
        "default_emails": "",
        "default_whatsapp": "",
        "app_password": "ccs2026"
    }

# Load the permanent settings object
current_settings = load_settings()

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
# 1. BRANDING CONTAINER
# ==========================================
with st.container(border=True):
    st.subheader("🏢 Branding")
    
    col_logo_preview, col_logo_upload = st.columns([1, 4])
    
    with col_logo_preview:
        if os.path.exists(LOGO_FILE):
            st.image(LOGO_FILE, use_column_width=True) 
        else:
            st.markdown(
                "<div style='width:100px; height:100px; border-radius:10px; background-color:#f1f5f9; display:flex; align-items:center; justify-content:center; color:#94a3b8; font-size:12px; font-weight:bold;'>No Logo</div>", 
                unsafe_allow_html=True
            )
            
    with col_logo_upload:
        uploaded_file = st.file_uploader("Upload Logo", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
        
        if uploaded_file is not None:
            if st.session_state.get('last_uploaded') != uploaded_file.name:
                with open(LOGO_FILE, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.session_state['last_uploaded'] = uploaded_file.name 
                st.rerun() 
            else:
                st.success("Logo saved permanently!")
            
        if st.button("Remove Logo", type="secondary"):
            if os.path.exists(LOGO_FILE):
                os.remove(LOGO_FILE)
            if 'last_uploaded' in st.session_state:
                del st.session_state['last_uploaded']
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    company_name_input = st.text_input("Company Name", value=current_settings.get('company_name', 'CENTREAL CONSULTANCY SERVICES'))

# ==========================================
# 2. DEFAULT RECIPIENTS CONTAINER
# ==========================================
st.markdown("<br>", unsafe_allow_html=True)
with st.container(border=True):
    st.subheader("📬 Default Recipients")
    
    emails_input = st.text_area(
        "Email Recipients (comma-separated)", 
        value=current_settings.get('default_emails', ''),
        placeholder="e.g., ceo@example.com, finance@example.com",
        height=68
    )
    whatsapp_input = st.text_area(
        "WhatsApp Numbers (with country code, comma-separated)", 
        value=current_settings.get('default_whatsapp', ''),
        placeholder="e.g., +919876543210",
        height=68
    )
    
    if st.button("💾 Save Settings", type="primary"):
        # Update the values inside our main configuration dictionary
        current_settings["company_name"] = company_name_input
        current_settings["default_emails"] = emails_input
        current_settings["default_whatsapp"] = whatsapp_input
        
        # Write back to file, maintaining the saved password state!
        with open(SETTINGS_FILE, "w") as f:
            json.dump(current_settings, f)
            
        st.success("Settings saved successfully!")
        st.rerun()

# ==========================================
# 3. SECURITY / CHANGE PASSWORD CONTAINER
# ==========================================
st.markdown("<br>", unsafe_allow_html=True)
with st.container(border=True):
    st.subheader("🔒 Change Password")
    
    col_curr, col_new, col_conf = st.columns(3)
    
    with col_curr:
        curr_pass = st.text_input("Current Password", type="password", key="curr_pass_entry")
    with col_new:
        new_pass = st.text_input("New Password", type="password", key="new_pass_entry")
    with col_conf:
        conf_pass = st.text_input("Confirm Password", type="password", key="conf_pass_entry")
        
    if st.button("Update Password"):
        if not curr_pass or not new_pass or not conf_pass:
            st.error("All password fields are required.")
        elif new_pass != conf_pass:
            st.error("New password and Confirm password do not match!")
        else:
            # Check authentication against local file cache instead of database
            saved_password = current_settings.get("app_password", "ccs2026")
            
            if curr_pass != saved_password:
                st.error("Incorrect current password!")
            else:
                # Assign new password value to the file structure
                current_settings["app_password"] = new_pass
                
                with open(SETTINGS_FILE, "w") as f:
                    json.dump(current_settings, f)
                    
                st.success("✅ Password successfully updated")
