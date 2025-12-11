import streamlit as st
import pandas as pd
import io

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="Service Order Manager", layout="wide")
st.title("💰 Service Order Manager (Volume & Value)")
st.markdown("Automated Tracker: Counts **Unique Orders** and Sums **Total Value** by Status.")

# --- 2. SIDEBAR SETTINGS ---
with st.sidebar:
    st.header("⚙️ Settings")
    if st.button("🗑️ Reset App"):
        st.cache_data.clear()
        st.rerun()
    header_row = st.number_input("Header Row (0=First Row)", value=0)
    
    st.divider()
    st.header("📊 Status Summary")
    summary_box = st.container()

# --- 3. SMART LOADER ---
@st.cache_data
def load_data(file, header_idx):
    if not file: return None
    # Try multiple ways to open file
    methods = [
        ('openpyxl', None), ('xlrd', None), 
        ('python', ','), ('python', ';'), ('python', '\t')
    ]
    for engine, sep in methods:
        try:
            file.seek(0)
            if sep: df = pd.read_csv(file, header=header_idx, sep=sep, engine=engine)
            else: df = pd.read_excel(file, sheet_name=0, header=header_idx, engine=engine)
            
            # Basic validation: must have at least 1 column
            if len(df.columns) > 1: return df
        except: continue
    return None

# --- 4. MAIN APP ---
uploaded_file = st.file_uploader("Upload Report", type=['xlsx', 'xls', 'csv'])

if uploaded_file:
    df = load_data(uploaded_file, header_row)

    if df is not None:
        # --- A. SMART COLUMN DETECTION ---
        cols = df.columns.tolist()
        
        # Helper to find best column match
        def find_col(keywords):
            # 1. Exact match (case insensitive)
            for c in cols:
                if str(c).strip().lower() in keywords: return c
            # 2. Partial match
            for c in cols:
                if any(k in str(c).strip().lower() for k in keywords): return c
            return cols[0]

        # Auto-Select
        default_id = find_col(['serviceorder', 'service order', 'order'])
        default_stat = find_col(['sostatus', 'so status', 'status'])
        default_sale = find_col(['totalsales', 'total sales', 'sales', 'amount', 'total'])

        # Show Selectors (Hidden by default to reduce clutter)
        with st.expander("⚙️ Verify Columns (Click to Edit)", expanded=False):
            c1, c2, c3 = st.columns(3)
            id_col = c1.selectbox("Order ID:", cols, index=cols.index(default_id))
            stat_col = c2.selectbox("SO Status:", cols, index=cols.index(default_stat))
            sales_col = c3.selectbox("Total Sales:", cols, index=cols.index(default_sale))

        # --- B. DATA PROCESSING ---
        
        # 1. Clean Sales (Handle Text/Numbers mixed)
        # Force convert to numeric, turning errors to 0
        df['CleanSales'] = pd.to_numeric(
            df[sales_col].astype(str).str.replace(r'[^\d.,-]', '', regex=True), 
            errors='coerce'
        ).fillna(0)
        
        # 2. Filter Valid Orders (Remove Empty/Quotes)
        df_clean = df.dropna(subset=[id_col])
        df_clean = df_clean[df_clean[id_col].astype(str).str.strip() != '']
        
        # 3. Calculate Grouped Stats
        # Group by Status -> Count Unique IDs, Sum All Sales
        stats = df_clean.groupby(stat_col).agg({
            id_col: 'nunique',
            'CleanSales': 'sum'
        }).reset_index()
        
        stats.columns = ['Status', 'Count', 'Value']
        stats = stats.sort_values('Count', ascending=False)
        
        # Global Totals
        total_unique = df_clean[id_col].nunique()
        total_val = df_clean['CleanSales'].sum()

        # --- C. SIDEBAR SUMMARY ---
        with summary_box:
            st.metric("TOTAL ORDERS", f"{total_unique:,}")
            st.metric("TOTAL VALUE", f"${total_val:,.2f}")
            st.markdown("---")
            for _, row in stats.iterrows():
                st.write(f"**{row['Status']}**")
                st.caption(f"📦 {row['Count']:,} | 💰 ${row['Value']:,.2f}")
                st.write("---")

        # --- D. MAIN DASHBOARD ---
        
        # Filter UI
        st.divider()
        col_filter, col_view = st.columns([1, 3])
        
        with col_filter:
            st.subheader("Filter")
            options = ["Show All"] + stats['Status'].tolist()
            selected_stat = st.radio("Select Status:", options)
            
            # Export
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                stats.to_excel(writer, sheet_name='Summary', index=False)
                df_clean.to_excel(writer, sheet_name='Full_Data', index=False)
            st.download_button("💾 Download Excel", buffer, "Service_Order_Report.xlsx")

        with col_view:
            st.subheader(f"List: {selected_stat}")
            
            # Filter Data
            if selected_stat == "Show All":
                display_df = df_clean
            else:
                display_df = df_clean[df_clean[stat_col] == selected_stat]
                
            # Show Metrics for Selection
            sub_cnt = display_df[id_col].nunique()
            sub_val = display_df['CleanSales'].sum()
            
            m1, m2 = st.columns(2)
            m1.metric("Selected Volume", f"{sub_cnt:,} Orders")
            m2.metric("Selected Value", f"${sub_val:,.2f}")
            
            # Show Table (Simplified Columns)
            # We try to show relevant columns only
            show_cols = [id_col, stat_col, 'CleanSales'] + [c for c in df.columns if c not in [id_col, stat_col, sales_col, 'CleanSales']][:5]
            st.dataframe(display_df[show_cols], use_container_width=True, hide_index=True)
