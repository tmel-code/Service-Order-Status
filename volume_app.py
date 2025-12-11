import streamlit as st
import pandas as pd
import io

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="Service Order Volume Counter", layout="wide")
st.title("🔢 Service Order Volume Counter")
st.markdown("This app counts **Unique Orders** (Volume) and summarizes them by Status.")

# --- 2. ROBUST LOADER ---
@st.cache_data
def load_data(file, header_idx):
    if not file: return None
    # Try multiple engines (Unbreakable method)
    methods = [
        ('openpyxl', None), ('xlrd', None), 
        ('python', ','), ('python', ';'), ('python', '\t')
    ]
    for engine, sep in methods:
        try:
            file.seek(0)
            if sep: return pd.read_csv(file, header=header_idx, sep=sep, engine=engine)
            else: return pd.read_excel(file, sheet_name=0, header=header_idx, engine=engine)
        except: continue
    return None

# --- 3. MAIN APP STRUCTURE ---

# A. UPLOAD SECTION (Top of Main Page)
uploaded_file = st.file_uploader("Upload Report", type=['xlsx', 'xls', 'csv'])

# B. SIDEBAR SETTINGS & SUMMARY
with st.sidebar:
    st.header("⚙️ Settings")
    if st.button("🗑️ Reset"):
        st.cache_data.clear()
        st.rerun()
    header_row = st.number_input("Header Row (0=First Row)", value=0)
    
    st.divider()
    st.header("📊 Status Summary")
    
    # Placeholder for summary (will be filled after data loads)
    summary_placeholder = st.empty()

# C. PROCESSING & DISPLAY
if uploaded_file:
    df = load_data(uploaded_file, header_row)

    if df is not None:
        # 1. Detect Columns
        cols = df.columns.tolist()
        def get_col(candidates):
            for c in cols:
                if any(x in str(c) for x in candidates): return c
            return cols[0]
            
        id_col = get_col(['ServiceOrder', 'Order'])
        stat_col = get_col(['SOStatus', 'Status'])

        # 2. Process Data (Volume Only)
        # Filter valid IDs
        df_clean = df.dropna(subset=[id_col])
        df_clean = df_clean[df_clean[id_col].astype(str).str.strip() != '']
        
        # Deduplicate (Unique Orders)
        df_unique = df_clean.drop_duplicates(subset=[id_col])
        
        #
