import streamlit as st
import pandas as pd
import io

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="Volume Counter v22", layout="wide")
st.title("🔢 Service Order Volume Counter v22 (Unbreakable)")
st.markdown("""
**Fixing 'File is not a zip file':**
This app ignores the file extension and tries every known method to read your file.
""")

# --- 2. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Settings")
    if st.button("🗑️ Reset"):
        st.cache_data.clear()
        st.rerun()
    header_row = st.number_input("Header Row (0=First Row)", value=0)

# --- 3. UNBREAKABLE LOADER ---
@st.cache_data
def load_data_v22(file, header_idx):
    if not file: return None
    
    # METHOD 1: Try as Modern Excel (.xlsx)
    try:
        file.seek(0)
        return pd.read_excel(file, sheet_name=0, header=header_idx, engine='openpyxl')
    except Exception:
        pass # Failed? Move to next.

    # METHOD 2: Try as Old Excel (.xls)
    try:
        file.seek(0)
        return pd.read_excel(file, sheet_name=0, header=header_idx, engine='xlrd')
    except Exception:
        pass

    # METHOD 3: Try as CSV (Comma)
    try:
        file.seek(0)
        return pd.read_csv(file, header=header_idx, sep=',')
    except Exception:
        pass

    # METHOD 4: Try as CSV (Semicolon)
    try:
        file.seek(0)
        return pd.read_csv(file, header=header_idx, sep=';')
    except Exception:
        pass
        
    # METHOD 5: Try as HTML (Sometimes reports are just HTML tables)
    try:
        file.seek(0)
        dfs = pd.read_html(file, header=header_idx)
        if dfs: return dfs[0]
    except Exception:
        pass

    st.error("❌ Could not read file. It might be encrypted or corrupted.")
    return None

# --- 4. MAIN APP ---
uploaded_file = st.file_uploader("Upload Report", type=['xlsx', 'xls', 'csv'])

if uploaded_file:
    df = load_data_v22(uploaded_file, header_row)

    if df is not None:
        # --- 5. DATA PREVIEW (Verify Headers) ---
        st.divider()
        st.caption("Data Preview (Check if headers are correct):")
        st.dataframe(df.head(3), use_container_width=True)
        
        # --- 6. SELECT COLUMNS ---
        cols = df.columns.tolist()
        def get_col(candidates):
            for c in cols:
                if any(x in str(c) for x in candidates): return c
            return cols[0]

        c1, c2 = st.columns(2)
        id_col = c1.selectbox("Order ID:", cols, index=cols.index(get_col(['ServiceOrder', 'Order'])))
        stat_col = c2.selectbox("Status:", cols, index=cols.index(get_col(['Status', 'SOStatus'])))

        # --- 7. CALCULATION ---
        
        # Filter Valid
        df_clean = df.dropna(subset=[id_col])
        df_clean = df_clean[df_clean[id_col].astype(str).str.strip() != '']
        
        # Deduplicate (Volume Count)
        df_unique = df_clean.drop_duplicates(subset=[id_col])
        
        # METRICS
        total_unique = len(df_unique)
        st.divider()
        st.metric("Total Unique Orders", f"{total_unique:,}")
        
        # BREAKDOWN
        c1, c2 = st.columns([1, 2])
        
        with c1:
            st.subheader("📊 Breakdown")
            breakdown = df_unique[stat_col].value_counts().reset_index()
            breakdown.columns = ['Status', 'Count']
            st.dataframe(breakdown, use_container_width=True, hide_index=True)
            
            # Export
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                breakdown.to_excel(writer, sheet_name='Summary', index=False)
                df_unique.to_excel(writer, sheet_name='Orders', index=False)
            st.download_button("💾 Download Excel", buffer, "Volume_Report.xlsx")

        with c2:
            st.subheader("🔍 Filter")
            sel_stat = st.selectbox("Status:", ["All"] + sorted(df_unique[stat_col].astype(str).unique().tolist()))
            
            if sel_stat == "All":
                st.dataframe(df_unique, use_container_width=True)
            else:
                st.dataframe(df_unique[df_unique[stat_col].astype(str) == sel_stat], use_container_width=True)
