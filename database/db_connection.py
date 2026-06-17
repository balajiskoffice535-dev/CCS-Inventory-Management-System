import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor

def init_connection():
    """Initializes and returns a fresh connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            host=st.secrets["postgres"]["host"],
            database=st.secrets["postgres"]["dbname"],
            user=st.secrets["postgres"]["user"],
            password=st.secrets["postgres"]["password"],
            port=st.secrets["postgres"]["port"]
        )
        conn.autocommit = True 
        return conn
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return None

def run_query(query, params=None):
    """A helper function to run queries, fetch data, and safely close connections."""
    conn = init_connection()
    if conn is None:
        return None
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            if cur.description is not None:
                result = cur.fetchall()
                return result
            return True
            
    except Exception as e:
        st.error(f"Database Error: {e}")
        return False
    finally:
        # Crucial for the cloud: always hang up the phone when done!
        if conn:
            conn.close()
