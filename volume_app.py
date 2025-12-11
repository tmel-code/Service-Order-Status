import streamlit as st
import pandas as pd
import io

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="Service Order Volume Counter", layout="wide")
st.title("🔢 Service Order Volume Counter")
st.markdown("""
**Goal:** Count **Unique Service Orders** by Status.
*(1 Order ID = 1 Count, regardless of how many line items it has)*
""")

# --- 2. SIDEBAR SETTINGS ---
with st.sidebar:
    st.header("⚙️ Settings")
    if st.button("🗑️ Reset"):
        st.cache_data.clear()
        st.rerun()
    header_row = st.number_input("Header Row (0=First Row)", value=0)

# --- 3. ROBUST DATA LOADER ---
@st.cache_data
def load_data(file, header_idx):
    if not file: return None
    try:
        # Try OpenPyXL first (Best for .xlsx)
        return pd.read_excel(file, sheet_name=0, header=header_idx, engine='openpyxl')
    except:
        try:
            # Fallback to standard
            return pd.read_excel(file, sheet_name=0, header=header_idx)
        except:
            # Fallback to CSV text reading
            file.seek(0)
            return pd.read_csv(file, header=header_idx, sep=None, engine='python')

# --- 4. MAIN APP ---
uploaded_file = st.file_uploader("Upload Service Order Report", type=['xlsx', 'xls', 'csv'])

if uploaded_file:
    df = load_data(uploaded_file, header_row)

    if df is not None:
        # --- 5. COLUMN DETECTION ---
        cols = df.columns.tolist()
        def get_col(candidates):
            for c in cols:
                if any(x in str(c) for x in candidates): return c
            return cols[0]

        # Select Columns
        col1, col2 = st.columns(2)
        id_col = col1.selectbox("Select Order ID Column:", cols, index=cols.index(get_col(['ServiceOrder', 'Order'])))
        stat_col = col2.selectbox("Select Status Column:", cols, index=cols.index(get_col(['Status', 'SOStatus'])))

        # --- 6. CALCULATION ENGINE ---
        
        # A. Filter Valid Data (Remove Quotes/Empty IDs)
        # We only want rows that have a Service Order ID
        df_clean = df.dropna(subset=[id_col])
        df_clean = df_clean[df_clean[id_col].astype(str).str.strip() != '']
        
        # B. Deduplicate
        # Keep only ONE row per Service Order ID to count "Volume"
        df_unique = df_clean.drop_duplicates(subset=[id_col])

        # --- 7. DASHBOARD ---
        st.divider()
        
        # METRICS
        total_unique = len(df_unique)
        st.metric("Total Unique Service Orders", f"{total_unique:,}")
        
        # --- 8. STATUS FILTER & BREAKDOWN ---
        c1, c2 = st.columns([1, 2])
        
        with c1:
            st.subheader("📊 Breakdown by Status")
            # Calculate Counts
            breakdown = df_unique[stat_col].value_counts().reset_index()
            breakdown.columns = ['Status', 'Order Count']
