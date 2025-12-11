import streamlit as st
import pandas as pd
import io

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="Service Order Volume & Value", layout="wide")
st.title("💰 Service Order Volume & Value Counter")
st.markdown("""
**Goal:** Track **Volume** (Unique Orders) AND **Value** (Total $ including all lines).
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

# Sidebar Placeholder
with st.sidebar:
    st.header("⚙️ Settings")
    if st.button("🗑️ Reset App"):
        st.cache_data.clear()
        st.rerun()
    header_row = st.number_input("Header Row (0=First Row)", value=0)
    
    st.divider()
    st.header("📊 Summary")
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

        st.subheader("1. Confirm Columns")
        c1, c2, c3 = st.columns(3)
        id_col = c1.selectbox("Order ID:", cols, index=cols.index(get_col(['ServiceOrder', 'Order'])))
        stat_col = c2.selectbox("Status:", cols, index=cols.index(get_col(['SOStatus', 'Status'])))
        sales_col = c3.selectbox("Sales/Value:", cols, index=cols.index(get_col(['TotalSales', 'Sales', 'Amount', 'Total'])))

        # --- 5. PROCESS DATA ---
        
        # A. Clean Sales (Remove $ and ,)
        df['CleanSales'] = pd.to_numeric(df[sales_col].astype(str).str.replace(r'[^\d.,-]', '', regex=True), errors='coerce').fillna(0)
        
        # B. Remove Empty IDs (Quotes)
        df_clean = df.dropna(subset=[id_col])
        df_clean = df_clean[df_clean[id_col].astype(str).str.strip() != '']
        
        # C. Calculate Metrics
        
        # 1. TOTALS
        total_unique = df_clean[id_col].nunique()
        total_value = df_clean['CleanSales'].sum()
        
        # 2. GROUP BY STATUS
        # Count = Unique IDs
        # Value = Sum of All Lines (duplicates included)
        status_stats = df_clean.groupby(stat_col).agg({
            id_col: 'nunique',
            'CleanSales': 'sum'
        }).reset_index()
        
        status_stats.columns = ['Status', 'Count', 'Value']
        status_stats = status_stats.sort_values('Count', ascending=False)

        # --- 6. FILL SIDEBAR ---
        with summary_box:
            st.metric("Total Count", f"{total_unique:,}")
            st.metric("Total Value", f"${total_value:,.2f}")
            st.markdown("---")
            st.write("**Breakdown:**")
            for index, row in status_stats.iterrows():
                st.write(f"**{row['Status']}**")
                st.caption(f"Count: {row['Count']:,} | ${row['Value']:,.2f}")
                st.markdown("---")

        # --- 7. MAIN DISPLAY ---
        st.divider()
        st.subheader("2. Filter & Export")
        
        col_filter, col_view = st.columns([1, 3])
        
        with col_filter:
            # Filter Options
            options = ["Show All"] + status_stats['Status'].tolist()
            selected_status = st.radio("Select Status:", options)
            
            # Export Logic
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                # Export Summary
                status_stats.to_excel(writer, sheet_name='Summary', index=False)
                # Export Clean List
                df_clean.to_excel(writer, sheet_name='Full_Data', index=False)
            
            st.download_button("💾 Download Excel", buffer, "Volume_Value_Report.xlsx")

        with col_view:
            if selected_status == "Show All":
                display_df = df_clean
                current_val = total_value
                current_cnt = total_unique
            else:
                display_df = df_clean[df_clean[stat_col] == selected_status]
                current_val = display_df['CleanSales'].sum()
                current_cnt = display_df[id_col].nunique()

            # Show Top Metrics for Selection
            m1, m2 = st.columns(2)
            m1.metric(f"{selected_status} Orders", f"{current_cnt:,}")
            m2.metric(f"{selected_status} Value", f"${current_val:,.2f}")
            
            # Show Table
            st.dataframe(display_df, use_container_width=True)
