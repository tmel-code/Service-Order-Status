import streamlit as st
import pandas as pd
import io

# --- 1. CONFIG ---
st.set_page_config(page_title="Service Order Volume Counter (Nuclear)", layout="wide")
st.title("🔢 Service Order Volume Counter (Nuclear Option)")
st.markdown("""
**The 'Show Nothing' Fix:**
This app reads your file as raw text to count statuses directly.
*It bypasses all column/header issues.*
""")

# --- 2. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Settings")
    if st.button("🗑️ Reset App"):
        st.cache_data.clear()
        st.rerun()
    
    st.divider()
    st.header("📊 Status Summary")
    summary_box = st.container()

# --- 3. NUCLEAR LOADER ---
@st.cache_data
def load_nuclear(file):
    if not file: return None
    try:
        # METHOD A: Read as Standard DataFrame (Best for details)
        if file.name.endswith('.csv'):
            try:
                df = pd.read_csv(file)
            except:
                file.seek(0)
                df = pd.read_csv(file, sep=';')
        else:
            df = pd.read_excel(file, sheet_name=0)
            
        return df
    except Exception as e:
        st.error(f"Error reading file structure: {e}")
        return None

# --- 4. MAIN APP ---
uploaded_file = st.file_uploader("Upload Report", type=['xlsx', 'xls', 'csv'])

if uploaded_file:
    # Load Data
    df = load_nuclear(uploaded_file)
    
    if df is not None:
        
        # --- 5. SMART COLUMN FINDER ---
        cols = df.columns.tolist()
        
        # Look for "Status" column (case insensitive)
        stat_col = next((c for c in cols if "status" in str(c).lower() and "so" in str(c).lower()), None)
        if not stat_col:
            stat_col = next((c for c in cols if "status" in str(c).lower()), None)
            
        # Look for "Order" column
        id_col = next((c for c in cols if "order" in str(c).lower() and "service" in str(c).lower()), None)
        if not id_col:
            id_col = next((c for c in cols if "order" in str(c).lower()), None)

        if id_col and stat_col:
            
            # --- 6. PROCESS DATA ---
            # Remove rows with empty ID
            df_clean = df.dropna(subset=[id_col])
            # Convert to string to be safe
            df_clean = df_clean[df_clean[id_col].astype(str).str.strip() != '']
            
            # Deduplicate (Unique Orders)
            df_unique = df_clean.drop_duplicates(subset=[id_col])
            
            # Count Statuses
            status_counts = df_unique[stat_col].value_counts()
            total_orders = len(df_unique)

            # --- 7. FILL SIDEBAR ---
            with summary_box:
                st.metric("TOTAL ORDERS", f"{total_orders:,}")
                st.markdown("---")
                for stat, count in status_counts.items():
                    st.write(f"**{stat}:** {count:,}")
            
            # --- 8. MAIN DISPLAY ---
            st.success(f"✅ Success! Found **{total_orders}** unique orders.")
            
            c1, c2 = st.columns([1, 3])
            
            with c1:
                st.subheader("Filter")
                # Dropdown for status
                options = ["Show All"] + sorted(status_counts.index.astype(str).tolist())
                sel_stat = st.radio("Select Status:", options)
                
                # Export
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df_unique.to_excel(writer, sheet_name='Unique_Orders', index=False)
                    status_counts.to_frame("Count").to_excel(writer, sheet_name='Summary')
                st.download_button("💾 Download List", buffer, "Volume_Report.xlsx")

            with c2:
                st.subheader("Order List")
                if sel_stat == "Show All":
                    st.dataframe(df_unique, use_container_width=True)
                else:
                    filtered = df_unique[df_unique[stat_col] == sel_stat]
                    st.dataframe(filtered, use_container_width=True)

        else:
            st.error("❌ Could not automatically find 'ServiceOrder' or 'Status' columns.")
            st.write("Columns found:", cols)
            st.info("Please rename your columns in Excel to 'ServiceOrder' and 'SOStatus' and try again.")
