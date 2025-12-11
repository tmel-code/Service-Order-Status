import streamlit as st
import pandas as pd
import io

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="Service Order Volume Counter", layout="wide")
st.title("🔢 Service Order Volume Counter")
st.markdown("""
**Goal:** Count **Unique Service Orders** (Volume Only).
*Ignores line items and dollar values. Focuses on the Count.*
""")

# --- 2. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Settings")
    if st.button("🗑️ Reset"):
        st.cache_data.clear()
        st.rerun()
    header_row = st.number_input("Header Row (0=First Row)", value=0)

# --- 3. ROBUST LOADER ---
@st.cache_data
def load_data(file, header_idx):
    if not file: return None
    try:
        # Try OpenPyXL (Best for .xlsx)
        return pd.read_excel(file, sheet_name=0, header=header_idx, engine='openpyxl')
    except:
        try:
            # Fallback to standard
            return pd.read_excel(file, sheet_name=0, header=header_idx)
        except:
            # Fallback to CSV
            file.seek(0)
            return pd.read_csv(file, header=header_idx, sep=None, engine='python')

# --- 4. MAIN APP ---
uploaded_file = st.file_uploader("Upload Report", type=['xlsx', 'xls', 'csv'])

if uploaded_file:
    df = load_data(uploaded_file, header_row)

    if df is not None:
        # --- 5. DETECT COLUMNS ---
        cols = df.columns.tolist()
        def get_col(candidates):
            for c in cols:
                if any(x in str(c) for x in candidates): return c
            return cols[0]

        # Select Columns
        col1, col2 = st.columns(2)
        id_col = col1.selectbox("Order ID Column:", cols, index=cols.index(get_col(['ServiceOrder', 'Order'])))
        stat_col = col2.selectbox("Status Column:", cols, index=cols.index(get_col(['Status', 'SOStatus'])))

        # --- 6. PROCESS DATA ---
        
        # A. Filter Valid Data (Must have an ID)
        df_clean = df.dropna(subset=[id_col])
        df_clean = df_clean[df_clean[id_col].astype(str).str.strip() != '']
        
        #
