import streamlit as st
import pandas as pd
import io

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="Service Order Manager v30", layout="wide")
st.title("💰 Service Order Manager (UI Fix)")

# --- 2. ROBUST LOADER ---
@st.cache_data
def load_data(file, header_idx):
    if not file: return None
    methods = [('openpyxl', None), ('xlrd', None), ('python', ','), ('python', ';')]
    for engine, sep in methods:
        try:
            file.seek(0)
            if sep: return pd.read_csv(file, header=header_idx, sep=sep, engine=engine)
            else: return pd.read_excel(file, sheet_name=0, header=header_idx, engine=engine)
        except: continue
    return None

# --- 3. SIDEBAR (HEADER CONTROL) ---
with st.sidebar:
    st.header("1. File Setup")
    if st.button("🔄 Reset App"):
        st.cache_data.clear()
        st.rerun()
    
    st.info("👇 Adjust this until the Table Preview shows correct headers.")
    header_row = st.number_input("Header Row Number:", value=0, min_value=0)
    
    st.divider()
    st.header("📊 Summary")
    summary_box = st.container()

# --- 4. MAIN APP ---
uploaded_file = st.file_uploader("Upload Report", type=['xlsx', 'xls', 'csv'])

if uploaded_file:
    df = load_data(uploaded_file, header_row)

    if df is not None:
        
        # --- STEP 1: VISUAL CONFIRMATION ---
        st.subheader("Step 1: Verify Headers")
        st.write("Do the **bold headers** below look like 'ServiceOrder', 'SOStatus', 'TotalSales'?")
        st.dataframe(df.head(3), use_container_width=True)
        
        # Check if headers look like data (common error)
        first_col = str(df.columns[0])
        if "Unnamed" in first_col or len(first_col) > 50:
            st.error("⚠️ The headers look wrong. Increase 'Header Row Number' in the sidebar!")
        else:
            st.success("✅ Headers look good. Proceed below.")

        # --- STEP 2: COLUMN MAPPING ---
        st.divider()
        st.subheader("Step 2: Column Setup")
        
        cols = df.columns.tolist()
        
        # Auto-find columns
        def find_col(keywords):
            for c in cols:
                if any(k in str(c).lower() for k in keywords): return c
            return cols[0]

        c1, c2, c3 = st.columns(3)
        id_col = c1.selectbox("Order ID:", cols, index=cols.index(find_col(['serviceorder', 'order'])))
        stat_col = c2.selectbox("SO Status:", cols, index=cols.index(find_col(['sostatus', 'status'])))
        sales_col = c3.selectbox("Total Sales:", cols, index=cols.index(find_col(['totalsales', 'sales', 'amount'])))

        # --- STEP 3: CALCULATION LOGIC ---
        
        # A. Clean Sales (Convert text to numbers)
        df['CleanSales'] = pd.to_numeric(
            df[sales_col].astype(str).str.replace(r'[^\d.,-]', '', regex=True), 
            errors='coerce'
        ).fillna(0)

        # B. Filter Processed vs Non-Processed
        # We assume if ID is missing, it's a Quote/Non-Processed
        df_processed = df.dropna(subset=[id_col])
        df_processed = df_processed[df_processed[id_col].astype(str).str.strip() != '']
        
        # C. Calculate Metrics
        # 1. Total Volume (Unique Count)
        total_unique_orders = df_processed[id_col].nunique()
        # 2. Total Value (Sum of all lines)
        total_value = df_processed['CleanSales'].sum()
        
        # D. Group By Status
        status_stats = df_processed.groupby(stat_col).agg({
            id_col: 'nunique',      # Volume (Unique)
            'CleanSales': 'sum'     # Value (Total)
        }).reset_index()
        status_stats.columns = ['Status', 'Order Count', 'Total Value']
        status_stats = status_stats.sort_values('Order Count', ascending=False)

        # --- STEP 4: DISPLAY RESULTS ---
        
        # SIDEBAR SUMMARY
        with summary_box:
            st.metric("TOTAL ORDERS", f"{total_unique_orders:,}")
            st.metric("TOTAL VALUE", f"${total_value:,.2f}")
            st.markdown("---")
            for _, row in status_stats.iterrows():
                st.write(f"**{row['Status']}**")
                st.caption(f"📦 {row['Order Count']:,} | 💰 ${row['Total Value']:,.2f}")
                st.markdown("---")

        # MAIN DASHBOARD
        st.divider()
        st.subheader("Step 3: Filter Data")
        
        col_filter, col_view = st.columns([1, 3])
        
        with col_filter:
            # Filter Options
            options = ["Show All"] + status_stats['Status'].tolist()
            selected_stat = st.radio("Select Status:", options)
            
            # Export
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                status_stats.to_excel(writer, sheet_name='Summary', index=False)
                df_processed.to_excel(writer, sheet_name='Full_Data', index=False)
            st.download_button("💾 Download Excel", buffer, "Service_Order_Report.xlsx")

        with col_view:
            # View Logic
            if selected_stat == "Show All":
                view_df = df_processed
                v_cnt = total_unique_orders
                v_val = total_value
            else:
                view_df = df_processed[df_processed[stat_col] == selected_stat]
                v_cnt = view_df[id_col].nunique()
                v_val = view_df['CleanSales'].sum()
            
            # Selected Metrics
            m1, m2 = st.columns(2)
            m1.metric("Selected Volume", f"{v_cnt:,} Orders")
            m2.metric("Selected Value", f"${v_val:,.2f}")
            
            st.dataframe(view_df, use_container_width=True)
