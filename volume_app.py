import streamlit as st
import pandas as pd
import io

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="Volume Counter v24", layout="wide")
st.title("🔢 Service Order Volume Counter (Diagnostic)")
st.markdown("""
**TROUBLESHOOTING:**
1. Upload your file.
2. Look at the **'Data Preview'** below.
3. If the first row looks like junk (or "Unnamed"), increase the **Header Row** in the Sidebar until you see **'ServiceOrder'** and **'SOStatus'** at the top.
""")

# --- 2. SIDEBAR SETTINGS ---
with st.sidebar:
    st.header("⚙️ Step 1: Fix Headers")
    if st.button("🗑️ Reset App"):
        st.cache_data.clear()
        st.rerun()
    
    # Crucial Setting
    header_row = st.number_input("Header Row Number:", value=0, min_value=0, help="Increase this if your file has a title/logo at the top.")
    
    st.divider()
    st.header("📊 Status Summary")
    summary_placeholder = st.empty() # Will fill this later

# --- 3. UNIVERSAL LOADER ---
@st.cache_data
def load_data_v24(file, header_idx):
    if not file: return None
    # Try every method to open the file
    methods = [
        ('openpyxl', None), 
        ('xlrd', None), 
        ('python', ','), 
        ('python', ';'), 
        ('python', '\t')
    ]
    for engine, sep in methods:
        try:
            file.seek(0)
            if sep: return pd.read_csv(file, header=header_idx, sep=sep, engine=engine)
            else: return pd.read_excel(file, sheet_name=0, header=header_idx, engine=engine)
        except: continue
    return None

# --- 4. MAIN APP LOGIC ---
uploaded_file = st.file_uploader("Upload Report", type=['xlsx', 'xls', 'csv'])

if uploaded_file:
    # Load
    df = load_data_v24(uploaded_file, header_row)

    if df is not None:
        
        # --- A. DIAGNOSTIC PREVIEW ---
        st.subheader("👀 Data Preview (Check this!)")
        st.write("Do the bold words below match your actual Column Headers (ServiceOrder, SOStatus)?")
        st.dataframe(df.head(3), use_container_width=True)
        
        # --- B. SELECT COLUMNS ---
        st.divider()
        st.subheader("⚙️ Step 2: Select Columns")
        cols = df.columns.tolist()
        
        # Helper to auto-select
        def get_idx(keywords):
            for i, c in enumerate(cols):
                if any(k in str(c) for k in keywords): return i
            return 0

        c1, c2 = st.columns(2)
        id_col = c1.selectbox("Order ID Column:", cols, index=get_idx(['ServiceOrder', 'Order']))
        stat_col = c2.selectbox("SO Status Column:", cols,
