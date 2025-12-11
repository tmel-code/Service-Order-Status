import streamlit as st
import pandas as pd
import io

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="Service Order Volume Counter", layout="wide")
st.title("🔢 Service Order Volume Counter")
st.markdown("This app counts **Unique Orders** (Volume) and summarizes them by Status.")

# --- 2. ROBUST LOADER ---
@st.cache_data
def load_data(file, header_idx):
    if not file: return None
    # Try multiple engines (Unbreakable method)
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

# --- 3. MAIN APP STRUCTURE ---

# A. UPLOAD SECTION (Top of Main Page)
uploaded_file = st.file_uploader("Upload Report",
