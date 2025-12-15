import streamlit as st
import pandas as pd
import io

# --- 1. CONFIG ---
st.set_page_config(page_title="Service Order Manager v33", layout="wide")
st.title("💰 Service Order Manager (Summary)")
st.markdown("Fixes: **Correctly identifies 'SOStatus'** vs 'QuoStatus'. Adds **'Completed'** to summary.")

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
    
    st.divider()
    st.header("📊 2. Status Summary")
    summary_box = st.container()

# --- 4. MAIN APP ---
uploaded_file = st.file_uploader("Upload Report", type=['xlsx', 'xls', 'csv'])

if uploaded_file:
    df = load_data(uploaded_file, header_row)

    if df is not None:
        
        # --- A. DATA PREVIEW ---
        with st.expander("👀 Data Preview (Click to check headers)", expanded=False):
            st.dataframe(df.head(3), use_container_width=True)

        # --- B. SMART COLUMN MAPPING (FIXED) ---
        cols = df.columns.tolist()
        
        # Priority Search Helper
        def find_best_col(priority_keywords, fallback_keywords=None):
            # 1. Try Priority Match (Exact string in column name)
            for c in cols:
                c_str = str(c).lower().strip()
                if any(pk in c_str for pk in priority_keywords): return c
            
            # 2. Try Fallback (Partial match)
            if fallback_keywords:
                for c in cols:
                    c_str = str(c).lower().strip()
                    if any(fk in c_str for fk in fallback_keywords): return c
            
            return cols[0]

        # Improved Logic: Look for "SO" specifically to avoid "QuoStatus"
        default_id = find_best_col(['serviceorder', 'service order'], ['order'])
        default_stat = find_best_col(['sostatus', 'so status', 'so_status'], ['status']) 
        default_sales = find_best_col(['totalsales', 'total sales'], ['sales', 'amount', 'total'])

        st.subheader("1. Confirm Columns")
        c1, c2, c3 = st.columns(3)
        id_col = c1.selectbox("Order ID:", cols, index=cols.index(default_id))
        stat_col = c2.selectbox("SO Status:", cols, index=cols.index(default_stat))
        sales_col = c3.selectbox("Total Sales:", cols, index=cols.index(default_sales))

        # --- C. DATA PROCESSING ---
        
        # 1. Clean Money (Remove $ and ,)
        df['CleanSales'] = pd.to_numeric(
            df[sales_col].astype(str).str.replace(r'[^\d.,-]', '', regex=True), 
            errors='coerce'
        ).fillna(0)

        # 2. Clean Status (Trim, Title Case, Fix Blank)
        df['CleanStatus'] = df[stat_col].astype(str).str.strip().str.title()
        # Fix known "Empty" strings
        df.loc[df['CleanStatus'].isin(['Nan', 'None', '', 'Na']), 'CleanStatus'] = 'Blank'

        # 3. Filter Valid Orders
        df_processed = df.dropna(subset=[id_col])
        df_processed = df_processed[df_processed[id_col].astype(str).str.strip() != '']
        
        # --- D. METRICS CALCULATION ---
        
        # Group by CleanStatus
        status_stats = df_processed.groupby('CleanStatus').agg({
            id_col: 'nunique',      # Count Unique
            'CleanSales': 'sum'     # Sum All Lines
        }).reset_index()
        
        status_stats.columns = ['Status', 'Count', 'Value']
        
        total_count = df_processed[id_col].nunique()
        total_val = df_processed['CleanSales'].sum()

        # --- E. SIDEBAR SUMMARY (UPDATED LIST) ---
        target_list = ['Costed', 'Released', 'Planned', 'Free', 'Completed', 'Blank']
        
        with summary_box:
            st.metric("TOTAL ORDERS", f"{total_count:,}")
            st.metric("TOTAL VALUE", f"${total_val:,.2f}")
            st.markdown("---")
            
            for target in target_list:
                # Find matching row
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
        st.subheader("2. Filter & View")
        
        c_filter, c_view = st.columns([1, 3])
        
        with c_filter:
            # Sort statuses for dropdown
            avail_stats = ["Show All"] + sorted(status_stats['Status'].tolist())
            sel_stat = st.radio("Select Status:", avail_stats)
            
            # Export
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_processed.to_excel(writer, sheet_name='Full_Data', index=False)
                status_stats.to_excel(writer, sheet_name='Summary', index=False)
            st.download_button("💾 Download Excel", buffer, "Volume_Value_Report.xlsx")

        with c_view:
            if sel_stat == "Show All":
                view_df = df_processed
            else:
                view_df = df_processed[df_processed['CleanStatus'] == sel_stat]
            
            # Selection Metrics
            v_cnt = view_df[id_col].nunique()
            v_val = view_df['CleanSales'].sum()
            
            m1, m2 = st.columns(2)
            m1.metric("Selected Volume", f"{v_cnt:,} Orders")
            m2.metric("Selected Value", f"${v_val:,.2f}")
            
            st.dataframe(view_df, use_container_width=True)
