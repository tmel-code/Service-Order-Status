import streamlit as st
import pandas as pd
import io

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="Volume & Value v28", layout="wide")
st.title("💰 Service Order Volume & Value (Diagnostic)")
st.markdown("""
**Troubleshooting Mode:**
1. Upload your file.
2. **Look at the 'Raw Data Preview' below.** 3. If the first row is junk text, increase **'Header Row'** in the sidebar until you see correct column names.
""")

# --- 2. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Settings")
    if st.button("🗑️ Reset App"):
        st.cache_data.clear()
        st.rerun()
    header_row = st.number_input("Header Row (0=First Row)", value=0)

# --- 3. ROBUST LOADER ---
@st.cache_data
def load_data(file, header_idx):
    if not file: return None
    # Unbreakable loader logic
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

# --- 4. MAIN APP ---
uploaded_file = st.file_uploader("Upload Report", type=['xlsx', 'xls', 'csv'])

if uploaded_file:
    df = load_data(uploaded_file, header_row)

    if df is not None:
        # --- A. DIAGNOSTIC PREVIEW ---
        st.divider()
        st.subheader("1. Raw Data Preview (Check Headers)")
        st.write("Do these columns look correct? If not, change 'Header Row' in Sidebar.")
        st.dataframe(df.head(3), use_container_width=True)

        # --- B. SELECT COLUMNS ---
        st.divider()
        st.subheader("2. Select Columns")
        cols = df.columns.tolist()
        
        # Helper to find column index
        def get_idx(keywords):
            for i, c in enumerate(cols):
                if any(k in str(c) for k in keywords): return i
            return 0

        c1, c2, c3 = st.columns(3)
        id_col = c1.selectbox("Order ID:", cols, index=get_idx(['ServiceOrder', 'Order']))
        stat_col = c2.selectbox("Status:", cols, index=get_idx(['SOStatus', 'Status']))
        sales_col = c3.selectbox("Sales Value:", cols, index=get_idx(['TotalSales', 'Sales', 'Amount']))

        # --- C. CALCULATE ---
        
        # 1. Clean Sales (Handle $ and ,)
        df['CleanSales'] = pd.to_numeric(
            df[sales_col].astype(str).str.replace(r'[^\d.,-]', '', regex=True), 
            errors='coerce'
        ).fillna(0)
        
        # 2. Filter Valid IDs (Remove Quotes/Empty)
        df_clean = df.dropna(subset=[id_col])
        df_clean = df_clean[df_clean[id_col].astype(str).str.strip() != '']
        
        # 3. Calculate Logic
        # Group by Status
        # - Count: Unique Order IDs
        # - Value: Sum of CleanSales (All lines)
        summary = df_clean.groupby(stat_col).agg({
            id_col: 'nunique',
            'CleanSales': 'sum'
        }).reset_index()
        
        summary.columns = ['Status', 'Count', 'Value']
        summary = summary.sort_values('Count', ascending=False)
        
        # Totals
        total_unique = df_clean[id_col].nunique()
        total_val = df_clean['CleanSales'].sum()

        # --- D. DISPLAY RESULTS ---
        st.divider()
        st.subheader("3. Results")
        
        # Top Metrics
        m1, m2 = st.columns(2)
        m1.metric("TOTAL UNIQUE ORDERS", f"{total_unique:,}")
        m2.metric("TOTAL VALUE", f"${total_val:,.2f}")
        
        # Sidebar Summary (As requested)
        with st.sidebar:
            st.divider()
            st.header("📊 Breakdown")
            for _, row in summary.iterrows():
                st.write(f"**{row['Status']}**")
                st.caption(f"📦 {row['Count']:,} | 💰 ${row['Value']:,.2f}")
                st.write("---")

        # --- E. FILTER & VIEW ---
        c_left, c_right = st.columns([1, 2])
        
        with c_left:
            st.write("### Filter")
            sel_stat = st.radio("Select Status:", ["Show All"] + summary['Status'].tolist())
            
            # Export
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                summary.to_excel(writer, sheet_name='Summary', index=False)
                df_clean.to_excel(writer, sheet_name='Full_Data', index=False)
            st.download_button("💾 Download Excel", buffer, "Volume_Value_Report.xlsx")

        with c_right:
            st.write(f"### Order List: {sel_stat}")
            if sel_stat == "Show All":
                st.dataframe(df_clean, use_container_width=True)
            else:
                filtered = df_clean[df_clean[stat_col] == sel_stat]
                st.dataframe(filtered, use_container_width=True)
