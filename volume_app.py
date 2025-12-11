import streamlit as st
import pandas as pd
import io

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="Service Order Manager v31", layout="wide")
st.title("💰 Service Order Manager (Targeted Status)")
st.markdown("Focuses on specific statuses: **Costed, Released, Completed, Planned, Free, Blank**.")

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

# --- 3. SIDEBAR (HEADER CONTROL) ---
with st.sidebar:
    st.header("1. File Setup")
    if st.button("🔄 Reset App"):
        st.cache_data.clear()
        st.rerun()
    header_row = st.number_input("Header Row (0=First Row)", value=0)
    
    st.divider()
    st.header("📊 Target Summary")
    summary_box = st.container()

# --- 4. MAIN APP ---
uploaded_file = st.file_uploader("Upload Report", type=['xlsx', 'xls', 'csv'])

if uploaded_file:
    df = load_data(uploaded_file, header_row)

    if df is not None:
        
        # --- A. COLUMN MAPPING ---
        cols = df.columns.tolist()
        def find_col(keywords):
            for c in cols:
                if any(k in str(c).lower() for k in keywords): return c
            return cols[0]

        # Auto-Select
        id_col = find_col(['serviceorder', 'order'])
        stat_col = find_col(['sostatus', 'status'])
        sales_col = find_col(['totalsales', 'sales', 'amount'])

        # --- B. DATA PROCESSING ---
        
        # 1. Clean Sales (Numbers only)
        df['CleanSales'] = pd.to_numeric(
            df[sales_col].astype(str).str.replace(r'[^\d.,-]', '', regex=True), 
            errors='coerce'
        ).fillna(0)

        # 2. Handle "Blank" Statuses
        # We fill NaN or empty strings with the word "Blank"
        df[stat_col] = df[stat_col].fillna("Blank").astype(str)
        df.loc[df[stat_col].str.strip() == '', stat_col] = "Blank"
        
        # 3. Filter Valid Orders (Must have Order ID)
        df_processed = df.dropna(subset=[id_col])
        df_processed = df_processed[df_processed[id_col].astype(str).str.strip() != '']
        
        # 4. Create Stats (Count & Value)
        # Group by Status
        status_stats = df_processed.groupby(stat_col).agg({
            id_col: 'nunique',      # Volume
            'CleanSales': 'sum'     # Value
        }).reset_index()
        status_stats.columns = ['Status', 'Count', 'Value']

        # --- C. SIDEBAR SUMMARY (TARGET LIST) ---
        target_statuses = ['Costed', 'Released', 'Completed', 'Planned', 'Free', 'Blank']
        
        total_unique_orders = df_processed[id_col].nunique()
        total_value = df_processed['CleanSales'].sum()

        with summary_box:
            st.metric("TOTAL ORDERS", f"{total_unique_orders:,}")
            st.metric("TOTAL VALUE", f"${total_value:,.2f}")
            st.markdown("---")
            
            # Loop through ONLY the target statuses
            for target in target_statuses:
                # Find matching row (case insensitive search)
                match = status_stats[status_stats['Status'].str.lower() == target.lower()]
                
                if not match.empty:
                    cnt = match.iloc[0]['Count']
                    val = match.iloc[0]['Value']
                else:
                    cnt = 0
                    val = 0.0
                
                st.write(f"**{target}**")
                st.caption(f"📦 {cnt:,} | 💰 ${val:,.2f}")
                st.markdown("---")

        # --- D. MAIN DASHBOARD ---
        st.subheader("2. Filter & View")
        
        col_filter, col_view = st.columns([1, 3])
        
        with col_filter:
            # Filter Options (Fixed List + Show All)
            selected_stat = st.radio("Select Status:", ["Show All"] + target_statuses)
            
            # Export
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_processed.to_excel(writer, sheet_name='Full_Data', index=False)
                status_stats.to_excel(writer, sheet_name='Summary', index=False)
            st.download_button("💾 Download Excel", buffer, "Service_Order_Report.xlsx")

        with col_view:
            # Apply Filter
            if selected_stat == "Show All":
                view_df = df_processed
            else:
                # Filter match (case insensitive)
                view_df = df_processed[df_processed[stat_col].str.lower() == selected_stat.lower()]
            
            # Show Metrics for Selection
            v_cnt = view_df[id_col].nunique()
            v_val = view_df['CleanSales'].sum()
            
            m1, m2 = st.columns(2)
            m1.metric(f"Selection Volume", f"{v_cnt:,} Orders")
            m2.metric(f"Selection Value", f"${v_val:,.2f}")
            
            # Show Table
            st.dataframe(view_df, use_container_width=True)
