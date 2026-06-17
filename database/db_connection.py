import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor

@st.cache_resource
def init_connection():
    """Initializes and returns a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            host=st.secrets["postgres"]["host"],
            database=st.secrets["postgres"]["dbname"],
            user=st.secrets["postgres"]["user"],
            password=st.secrets["postgres"]["password"],
            port=st.secrets["postgres"]["port"]
        )
        # THIS IS THE MAGIC LINE: Forces the DB to save instantly
        conn.autocommit = True 
        return conn
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return None

def run_query(query, params=None):
    """A helper function to run queries and fetch data easily."""
    conn = init_connection()
    if conn is None:
        return None
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            
            # If the query is supposed to return data, fetch it
            if cur.description is not None:
                return cur.fetchall()
            
            # If it's a simple UPDATE/DELETE, just return True
            return True
            
    except Exception as e:
        # If ANYTHING goes wrong, yell loudly in a red box!
        st.error(f"Database Error: {e}")
        return False