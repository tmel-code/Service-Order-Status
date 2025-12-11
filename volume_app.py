import streamlit as st
import pandas as pd
import io

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="Service Order Manager", layout="wide")
st.title("💰 Service Order Manager")
st.markdown("""
**Workflow:**
1. Filter by **Quotation Status** (Processed vs Non-Processed).
2. If **Processed**, filter by **SO Status** (Costed, Released, etc.).
3. View **Volume (Count)** and **Value ($)** including all line items.
""")

# --- 2. ROBUST LOADER ---
@st.cache_data
def load_data(file, header_idx):
    if not file: return None
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

# --- 3. SIDEBAR SETTINGS ---
with st.sidebar:
    st.header("⚙️ Settings")
    if st.button("🗑️ Reset App"):
        st.cache_data.clear()
        st.rerun()
    header_row = st.number_input("Header Row (0=First Row)", value=0)
    
    st.divider()
    st.header("📊 Processed Summary")
    summary_box = st.container()

# --- 4. MAIN APP ---
uploaded_file = st.file_uploader("Upload Report", type=['xlsx', 'xls', 'csv'])

if uploaded_file:
    df = load_data(uploaded_file, header_row)

    if df is not None:
        # --- A. DETECT COLUMNS ---
        cols = df.columns.tolist()
        def get_col(candidates):
            for c in cols:
                if any(x in str(c).lower() for x in candidates): return c
            return None

        # Try to find specific columns
        quo_stat_col = get_col(['quostatus', 'quotation status', 'quo status'])
        so_stat_col = get_col(['sostatus', 'so status', 'service order status'])
        id_col = get_col(['serviceorder', 'service order', 'order'])
        sales_col = get_col(['totalsales', 'total sales', 'sales', 'amount'])

        # Fallbacks if detection fails
        if not quo_stat_col: quo_stat_col = cols[0]
        if not so_stat_col: so_stat_col = cols[1] if len(cols)>1 else cols[0]
        if not id_col: id_col = cols[2] if len(cols)>2 else cols[0]
        if not sales_col: sales_col = cols[3] if len(cols)>3 else cols[0]

        # Allow user to fix columns
        with st.expander("⚙️ Verify Columns (Click to Edit)", expanded=False):
            c1, c2, c3, c4 = st.columns(4)
            quo_stat_col = c1.selectbox("Quotation Status:", cols, index=cols.index(quo_stat_col))
            so_stat_col = c2.selectbox("SO Status:", cols, index=cols.index(so_stat_col))
            id_col = c3.selectbox("Order ID:", cols, index=cols.index(id_col))
            sales_col = c4.selectbox("Sales Value:", cols, index=cols.index(sales_col))

        # --- B. PROCESS DATA ---
        
        # 1. Clean Sales
        df['CleanSales'] = pd.to_numeric(df[sales_col].astype(str).str.replace(r'[^\d.,-]', '', regex=True), errors='coerce').fillna(0)
        
        # 2. Standardize Statuses
        df['QuoStatus_Clean'] = df[quo_stat_col].astype(str).str.strip()
        df['
