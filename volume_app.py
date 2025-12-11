import streamlit as st
import pandas as pd
import io

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="Volume Counter (Diagnostic)", layout="wide")
st.title("🔢 Service Order Volume Counter (Diagnostic Mode)")
st.markdown("""
**Troubleshooting:**
1. Upload your file.
2. Look at the **Data Preview** below.
3. If the headers look wrong (e.g., "Unnamed: 0"), change the **Header Row** setting in the sidebar.
""")

# --- 2. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ File Settings")
    if st.button("🗑️ Reset"):
        st.cache_data.clear()
        st.rerun()
    
    # Crucial Setting for "No Result" issues
    header_row = st.number_input("Header Row (0=First Row)", value=0, help="Change this if your file has a title at the top.")

# --- 3. ROBUST LOADER ---
@st.cache_data
def load_data_diagnostic(file, header_idx):
    if not file: return None
    try:
        # Try CSV
        if file.name.endswith('.csv'):
            try:
                return pd.read_csv(file, header=header_idx)
            except:
                file.seek(0)
                return pd.read_csv(file, header=header_idx, sep=';')
        
        # Try Excel (Force openpyxl)
        return pd.read_excel(file, sheet_name=0, header=header_idx, engine='openpyxl')
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return None

# --- 4. MAIN APP ---
uploaded_file = st.file_uploader("Upload Report", type=['xlsx', 'xls', 'csv'])

if uploaded_file:
    df = load_data_diagnostic(uploaded_file, header_row)

    if df is not None:
        # --- 5. DIAGNOSTIC PREVIEW (The Fix) ---
        st.divider()
        st.subheader("👀 Data Preview")
        st.write("Does this look like your data? If the bold headers are wrong, increase 'Header Row' in the sidebar.")
        st.dataframe(df.head(3), use_container_width=True)
        st.write(f"**Rows Loaded:** {len(df):,}")

        # --- 6. COLUMN SELECTION ---
        cols = df.columns.tolist()
        
        # Smart Auto-Select
        def get_col_index(candidates):
            for i, c in enumerate(cols):
                if any(x in str(c) for x in candidates): return i
            return 0

        st.subheader("⚙️ Configure Columns")
        c1, c2 = st.columns(2)
        id_col = c1.selectbox("Order ID Column:", cols, index=get_col_index(['ServiceOrder', 'Order']))
        stat_col = c2.selectbox("Status Column:", cols, index=get_col_index(['Status', 'SOStatus']))

        # --- 7. CALCULATION ---
        if st.button("Calculate Volume"):
            
            # A. Filter Empty IDs
            # We treat everything as a string to be safe
            df_clean = df[df[id_col].notna()].copy()
            df_clean = df_clean[df_clean[id_col].astype(str).str.strip() != '']
            
            if len(df_clean) == 0:
                st.error("❌ Result is 0. This means the 'Order ID' column you selected is empty. Please check the Column Selection above.")
            else:
                # B. Deduplicate (Count Unique Orders)
                df_unique = df_clean.drop_duplicates(subset=[id_col])
                
                # --- 8. RESULTS ---
                st.divider()
                st.metric("Total Unique Orders", f"{len(df_unique):,}")
                
                # Breakdown
                c_left, c_right = st.columns([1, 2])
                
                with c_left:
                    st.subheader("📊 Counts by Status")
                    breakdown = df_unique[stat_col].value_counts().reset_index()
                    breakdown.columns = ['Status', 'Count']
                    st.dataframe(breakdown, use_container_width=True, hide_index=True)

                with c_right:
                    st.subheader("🔍 Filter List")
                    # Filter
                    all_statuses = ["All"] + sorted(df_unique[stat_col].astype(str).unique().tolist())
                    sel_stat = st.selectbox("Show Orders:", all_statuses)
                    
                    if sel_stat == "All":
                        st.dataframe(df_unique, use_container_width=True)
                    else:
                        st.dataframe(df_unique[df_unique[stat_col].astype(str) == sel_stat], use_container_width=True)
