import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

st.set_page_config(page_title="VIDeMI Reservation Manager", layout="wide")
st.title("🏠 VIDeMI Reservation Manager")

st.markdown("""
Welcome to the **VIDeMI Reservations Manager**!  
✅ Upload your reservation CSV.  
✅ Clean and extract only reservation data.  
✅ Edit, Add, Delete rows.  
✅ Export updated CSV.
""")

# --- Step 1: Upload CSV
st.header("📤 1. Upload Your Reservations CSV")
uploaded_file = st.file_uploader("Upload CSV file", type=['csv'])

if uploaded_file:
    raw_df = pd.read_csv(uploaded_file)

    st.subheader("👀 Preview Raw Data (first 10 rows)")
    st.dataframe(raw_df.head(10))

    # --- Step 2: Clean & Extract Reservations Table
    st.header("🧹 2. Extract Reservation Data")
    reservation_cols = [
        'DATE', 'VILLA', 'TYPE CLEAN', 'PAX',
        'START TIME', 'RESERVATION STATUS',
        'LAUNDRY', 'COMMENTS'
    ]

    # Try to filter for only those columns if present
    possible_cols = [col for col in reservation_cols if col in raw_df.columns]
    if not possible_cols:
        st.error("No matching reservation columns found. Please check your CSV.")
        st.stop()

    # Drop obviously bad rows (with all NAs or all 'NONE')
    df = raw_df[possible_cols].copy()
    df = df.dropna(how='all')
    df = df[~df['DATE'].astype(str).str.contains('WEEK|NONE', na=False)]
    df = df.dropna(subset=['DATE', 'VILLA'], how='all')

    st.success(f"Extracted {len(df)} valid reservation rows.")

    st.subheader("✅ Cleaned Reservation Data Preview")
    st.dataframe(df.head(10))

    # --- Step 3: Work Session State
    if 'data' not in st.session_state:
        st.session_state['data'] = df.copy()

    st.header("📋 3. Manage Reservations Table")
    st.markdown("""
    👉 **Edit directly in the table.**  
    👉 **Select a row to delete.**  
    👉 **Add new reservations below.**
    """)

    gb = GridOptionsBuilder.from_dataframe(st.session_state['data'])
    gb.configure_pagination()
    gb.configure_default_column(editable=True, filter=True)
    gb.configure_selection('single', use_checkbox=True)
    grid_options = gb.build()

    grid_response = AgGrid(
        st.session_state['data'],
        gridOptions=grid_options,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        allow_unsafe_jscode=True,
        height=400,
        fit_columns_on_grid_load=True
    )

    updated_df = grid_response['data']

    # Save Changes Button
    if st.button("💾 Save Edits to Session"):
        st.session_state['data'] = updated_df.copy()
        st.success("Changes saved!")

    # --- Step 4: Delete Row
    selected = grid_response['selected_rows']
    if st.button("🗑️ Delete Selected Row") and selected:
        sel_df = pd.DataFrame(selected)
        before = len(st.session_state['data'])
        st.session_state['data'] = st.session_state['data'][~st.session_state['data'].isin(sel_df.iloc[0]).all(axis=1)]
        after = len(st.session_state['data'])
        st.success(f"Deleted 1 row. Remaining rows: {after}")

    # --- Step 5: Add New Row
    st.header("➕ 4. Add New Reservation")
    with st.form("new_reservation_form"):
        st.write("Fill in the new reservation details:")
        new_entry = {}
        cols = st.columns(4)
        for idx, col in enumerate(reservation_cols):
            with cols[idx % 4]:
                new_entry[col] = st.text_input(f"{col}", "")

        submitted = st.form_submit_button("Add Reservation")
        if submitted:
            new_row = pd.DataFrame([new_entry])
            st.session_state['data'] = pd.concat([st.session_state['data'], new_row], ignore_index=True)
            st.success("New reservation added!")

    # --- Step 6: Download Updated CSV
    st.header("⬇️ 5. Download Updated Reservations")
    st.download_button(
        label="Download Updated CSV",
        data=st.session_state['data'].to_csv(index=False).encode('utf-8'),
        file_name='updated_reservations.csv',
        mime='text/csv'
    )

else:
    st.info("👈 Please upload your reservations CSV to begin.")
