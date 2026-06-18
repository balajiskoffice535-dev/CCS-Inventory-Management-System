import streamlit as st
import os
import json

st.set_page_config(page_title="Login - CCS", page_icon="title_logo.png", layout="centered")

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

# Initialize the session state so the app remembers if you are logged in
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# --- LOGGED OUT VIEW ---
if not st.session_state['logged_in']:
    
    # Hide the sidebar completely when logged out
    st.markdown("""
        <style>
            [data-testid="collapsedControl"] {display: none;}
            [data-testid="stSidebar"] {display: none;}
        </style>
    """, unsafe_allow_html=True)
    
    st.title("🔒 CCS Secure Login")
    st.write("Please enter your credentials to access the database.")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password_input = st.text_input("Password", type="password")
        submit = st.form_submit_button("Log In", type="primary", use_container_width=True)
        
        if submit:
            # ✨ DYNAMIC FILE CHECK ENGINE (THE PROPER FIX) ✨
            # 1. Assume the default password is your current one
            master_password = "ccs2026" 
            
            # 2. Check if a new password has been saved to the hard drive
            if os.path.exists("settings.json"):
                with open("settings.json", "r") as f:
                    try:
                        saved_settings = json.load(f)
                        # Grab the real password, or fallback if it's missing inside the file
                        master_password = saved_settings.get("app_password", "ccs2026")
                    except Exception:
                        master_password = "ccs2026"

            # 3. Authenticate against the dynamic file password!
            if username == "admin" and password_input == master_password:
                st.session_state['logged_in'] = True
                
                # Also store the username in memory so our settings page knows who is logged in!
                st.session_state['username'] = username 
                st.success("✅ Logged in successfully!")
                st.rerun() 
            else:
                st.error("❌ Incorrect username or password.")

# --- LOGGED IN VIEW ---
else:
    st.success("✅ Logged in successfully!")
    st.title("Welcome to the CCS Management System")
    st.write("👈 Please select **Dashboard** or **Transactions** from the sidebar menu to begin.")
    
    st.divider()
    
    if st.button("🚪 Log Out"):
        st.session_state['logged_in'] = False
        if 'username' in st.session_state:
            del st.session_state['username']
        st.rerun()
