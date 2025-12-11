import streamlit as st
import pandas as pd
import io

# --- 1. CONFIG ---
st.set_page_config(page_title="Service Order Manager v32", layout="wide")
st.title("💰 Service Order Manager (Fix & Verify)")
st.markdown("Fixes: **Zero Values** (Comma removal) and **Zero Counts** (Text trimming).")

# --- 2. ROBUST LOADER ---
@st.cache_data
def load_data(file, header_idx):
    if not file: return None
    methods = [('openpyxl', None), ('xlrd', None), ('python', ','), ('python', ';'), ('python', '\t')]
    for engine, sep in methods:
        try:
            file.seek(0)
            if sep: return pd.read_csv(file, header=header_idx, sep=sep, engine=engine)
            else: return pd.read_excel(file, sheet_name=0, header=header_idx, engine=engine)
        except: continue
    return None

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ 1. File Setup")
    if st.button("🔄 Reset App"):
        st.cache_data.clear()
        st.rerun()
    
    header_row = st.number_input("Header Row Number:", value=0, min_value=0)
    st.caption("Adjust this until the 'Data Preview' shows correct column names.")
    
    st.divider()
    st.header("📊 2. Summary")
    summary_box = st.container()

# --- 4. MAIN APP ---
uploaded_file = st.file_uploader("Upload Report", type=['xlsx', 'xls', 'csv'])

if uploaded_file:
    df = load_data(uploaded_file, header_row)

    if df is not None:
        
        # --- A. DATA PREVIEW ---
        with st.expander("👀 Data Preview (Click to Open)", expanded=True):
            st.write("First 3 rows of your file:")
            st.dataframe(df.head(3), use_container_width=True)
            
            # Check for bad headers
            if "Unnamed" in str(df.columns[0]):
                st.error("⚠️ Headers look wrong (Unnamed). Increase 'Header Row Number' in the sidebar!")

        # --- B. COLUMN MAPPING ---
        cols = df.columns.tolist()
        def find_col(keywords):
            for c in cols:
                if any(k in str(c).lower() for k in keywords): return c
            return cols[0]

        c1, c2, c3 = st.columns(3)
        id_col = c1.selectbox("Order ID:", cols, index=cols.index(find_col(['serviceorder', 'order'])))
        stat_col = c2.selectbox("SO Status:", cols, index=cols.index(find_col(['sostatus', 'status'])))
        sales_col = c3.selectbox("Total Sales:", cols, index=cols.index(find_col(['totalsales', 'sales', 'amount'])))

        # --- C. DATA CLEANING (THE FIX) ---
        
        # 1. CLEAN MONEY (Remove $ and ,)
        # Converts "1,234.56" -> 1234.56
        df['CleanSales'] = pd.to_numeric(
            df[sales_col].astype(str).str.replace(r'[$,]', '', regex=True), 
            errors='coerce'
        ).fillna(0)

        # 2. CLEAN STATUS (Trim spaces, Title Case)
        # Converts " costed " -> "Costed", "COSTED" -> "Costed"
        df['CleanStatus'] = df[stat_col].astype(str).str.strip().str.title()
        # Handle Blanks
        df.loc[df['CleanStatus'].isin(['Nan', 'None', '']), 'CleanStatus'] = 'Blank'

        # 3. FILTER VALID ORDERS
        # Must have an ID
        df_processed = df.dropna(subset=[id_col])
        df_processed = df_processed[df_processed[id_col].astype(str).str.strip() != '']
        
        # --- D. CALCULATE METRICS ---
        
        # Group by Status
        # Count = Unique IDs
        # Value = Sum of All Lines
        status_stats = df_processed.groupby('CleanStatus').agg({
            id_col: 'nunique',
            'CleanSales': 'sum'
        }).reset_index()
        
        status_stats.columns = ['Status', 'Count', 'Value']
        
        # Totals
        total_count = df_processed[id_col].nunique()
        total_val = df_processed['CleanSales'].sum()

        # --- E. SIDEBAR SUMMARY ---
        target_list = ['Costed', 'Released', 'Completed', 'Planned', 'Free', 'Blank']
        
        with summary_box:
            st.metric("TOTAL ORDERS", f"{total_count:,}")
            st.metric("TOTAL VALUE", f"${total_val:,.2f}")
            st.markdown("---")
            
            for target in target_list:
                # Find row in stats
                row = status_stats[status_stats['Status'] == target]
                
                if not row.empty:
                    cnt = row['Count'].values[0]
                    val = row['Value'].values[0]
                else:
                    cnt = 0
                    val = 0.0
                
                st.write(f"**{target}**")
                st.caption(f"📦 {cnt:,} | 💰 ${val:,.2f}")
                st.markdown("---")

        # --- F. MAIN DISPLAY ---
        st.divider()
        st.subheader("Filter & View")
        
        c_filter, c_view = st.columns([1, 3])
        
        with c_filter:
            # Filter options
            avail_stats = ["Show All"] + sorted(status_stats['Status'].tolist())
            sel_stat = st.radio("Select Status:", avail_stats)
            
            # Export
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_processed.to_excel(writer, sheet_name='Full_Data', index=False)
                status_stats.to_excel(writer, sheet_name='Summary', index=False)
            st.download_button("💾 Download Excel", buffer, "Volume_Value_Report.xlsx")
            
            # DEBUG INFO
            with st.expander("Debug: Statuses Found"):
                st.write(status_stats)

        with c_view:
            if sel_stat == "Show All":
                view_df = df_processed
            else:
                view_df = df_processed[df_processed['CleanStatus'] == sel_stat]
            
            # Metrics for View
            v_cnt = view_df[id_col].nunique()
            v_val = view_df['CleanSales'].sum()
            
            m1, m2 = st.columns(2)
            m1.metric("Selected Volume", f"{v_cnt:,} Orders")
            m2.metric("Selected Value", f"${v_val:,.2f}")
            
            st.dataframe(view_df, use_container_width=True)
