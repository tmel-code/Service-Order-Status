import streamlit as st
import pandas as pd
import io

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="Service Order Volume & Value", layout="wide")
st.title("💰 Service Order Volume & Value Counter")
st.markdown("""
**Goal:** 1. **Count** Unique Orders.
2. **Sum** Total Value (including all duplicate line items).
3. **Filter** by SOStatus.
""")

# --- 2. ROBUST LOADER ---
@st.cache_data
def load_data(file, header_idx):
    if not file: return None
    # Try multiple engines to ensure file opens
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

# --- 3. MAIN APP ---
uploaded_file = st.file_uploader("Upload Report", type=['xlsx', 'xls', 'csv'])

# SIDEBAR INIT
with st.sidebar:
    st.header("⚙️ Settings")
    if st.button("🗑️ Reset App"):
        st.cache_data.clear()
        st.rerun()
    header_row = st.number_input("Header Row (0=First Row)", value=0)
    
    st.divider()
    st.header("📊 Status Summary")
    summary_box = st.container()

if uploaded_file:
    df = load_data(uploaded_file, header_row)

    if df is not None:
        # --- 4. SELECT COLUMNS ---
        cols = df.columns.tolist()
        def get_col(candidates):
            for c in cols:
                if any(x in str(c) for x in candidates): return c
            return cols[0]

        # Auto-detect columns
        st.subheader("1. Confirm Columns")
        c1, c2, c3 = st.columns(3)
        id_col = c1.selectbox("Order ID:", cols, index=cols.index(get_col(['ServiceOrder', 'Order'])))
        stat_col = c2.selectbox("SO Status:", cols, index=cols.index(get_col(['SOStatus', 'Status'])))
        sales_col = c3.selectbox("Sales/Value:", cols, index=cols.index(get_col(['TotalSales', 'Sales', 'Amount', 'Total'])))

        # --- 5. PROCESS DATA ---
        
        # A. Clean Sales Column (Remove $ and ,)
        # This converts text "$1,000.00" into number 1000.00
        df['CleanSales'] = pd.to_numeric(df[sales_col].astype(str).str.replace(r'[^\d.,-]', '', regex=True), errors='coerce').fillna(0)
        
        # B. Remove Empty IDs (Quotes/Bad Data)
        df_clean = df.dropna(subset=[id_col])
        df_clean = df_clean[df_clean[id_col].astype(str).str.strip() != '']
        
        #
