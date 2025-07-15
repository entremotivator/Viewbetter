import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from io import StringIO

# Page configuration
st.set_page_config(
    page_title="Kroon Beheer Reservations",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.5rem;
        font-weight: bold;
        color: #2E86AB;
        text-align: center;
        margin-bottom: 1rem;
        padding: 1rem;
        background: linear-gradient(90deg, #f0f8ff, #e6f3ff);
        border-radius: 10px;
        border-left: 5px solid #2E86AB;
    }
    
    .metric-container {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #2E86AB;
        margin: 0.5rem 0;
    }
    
    .stDataFrame {
        border: 2px solid #e1e5e9;
        border-radius: 8px;
        overflow: hidden;
    }
    
    .grid-header {
        background: #2E86AB;
        color: white;
        padding: 0.5rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 1rem;
        border-radius: 5px;
    }
    
    .sidebar .stSelectbox > div > div {
        background-color: #f0f8ff;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_reservation_data():
    """Load reservation data from CSV URL"""
    url = "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/Reservations%20Kroon%20Beheer%20BV%20-%20Kroon%20Beheer%20Client%20Info%20-oceEo2u6q6oDwnLyd8QoSnJqzEPSTa.csv"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Read CSV data
        df = pd.read_csv(StringIO(response.text))
        
        # Clean column names
        df.columns = df.columns.str.strip()
        
        # Process date columns
        for col in df.columns:
            if df[col].dtype == 'object':
                # Try to detect date columns
                sample_values = df[col].dropna().head(10)
                if len(sample_values) > 0:
                    try:
                        pd.to_datetime(sample_values, errors='raise')
                        df[col] = pd.to_datetime(df[col], errors='coerce')
                    except:
                        pass
        
        return df, None
        
    except Exception as e:
        return None, str(e)

def create_enhanced_grid(df, search_term="", selected_columns=None):
    """Create an enhanced data grid with filtering"""
    
    if selected_columns:
        display_df = df[selected_columns].copy()
    else:
        display_df = df.copy()
    
    # Apply search filter
    if search_term:
        mask = display_df.astype(str).apply(
            lambda x: x.str.contains(search_term, case=False, na=False)
        ).any(axis=1)
        display_df = display_df[mask]
    
    return display_df

def main():
    # Main title
    st.markdown('<div class="main-title">🏢 Kroon Beheer BV - Reservations Management</div>', unsafe_allow_html=True)
    
    # Load data
    with st.spinner("🔄 Loading reservation data..."):
        df, error = load_reservation_data()
    
    if error:
        st.error(f"❌ Error loading data: {error}")
        st.stop()
    
    if df is None or df.empty:
        st.warning("⚠️ No reservation data available")
        st.stop()
    
    # Sidebar configuration
    st.sidebar.markdown("### 🔧 Configuration")
    
    # Data overview metrics
    st.sidebar.markdown("### 📊 Data Overview")
    st.sidebar.metric("Total Reservations", len(df))
    st.sidebar.metric("Data Columns", len(df.columns))
    
    # Date range if date columns exist
    date_columns = [col for col in df.columns if df[col].dtype.name.startswith('datetime')]
    if date_columns:
        st.sidebar.metric("Date Columns", len(date_columns))
        
        for date_col in date_columns[:2]:
            valid_dates = df[date_col].dropna()
            if len(valid_dates) > 0:
                st.sidebar.write(f"**{date_col}:**")
                st.sidebar.write(f"From: {valid_dates.min().strftime('%Y-%m-%d')}")
                st.sidebar.write(f"To: {valid_dates.max().strftime('%Y-%m-%d')}")
    
    # Column selection
    st.sidebar.markdown("### 📋 Column Selection")
    all_columns = df.columns.tolist()
    
    # Default selection - show first 8 columns or all if less than 8
    default_cols = all_columns[:8] if len(all_columns) > 8 else all_columns
    
    selected_columns = st.sidebar.multiselect(
        "Choose columns to display:",
        options=all_columns,
        default=default_cols,
        help="Select which columns to show in the grid"
    )
    
    # Search functionality
    st.sidebar.markdown("### 🔍 Search & Filter")
    search_term = st.sidebar.text_input(
        "Search in data:",
        placeholder="Enter search term...",
        help="Search across all visible columns"
    )
    
    # Grid display options
    st.sidebar.markdown("### ⚙️ Display Options")
    show_index = st.sidebar.checkbox("Show row numbers", value=False)
    grid_height = st.sidebar.slider("Grid height", 300, 800, 500, 50)
    
    # Main content area
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown('<div class="grid-header">📋 RESERVATIONS DATA GRID</div>', unsafe_allow_html=True)
        
        if not selected_columns:
            st.warning("⚠️ Please select at least one column to display")
        else:
            # Create enhanced grid
            display_df = create_enhanced_grid(df, search_term, selected_columns)
            
            # Show filtered results count
            if search_term:
                st.info(f"🔍 Showing {len(display_df)} results for '{search_term}'")
            
            # Display the data grid with enhanced styling
            st.dataframe(
                display_df,
                use_container_width=True,
                height=grid_height,
                hide_index=not show_index,
                column_config={
                    col: st.column_config.TextColumn(
                        col,
                        width="medium",
                        help=f"Data from column: {col}"
                    ) for col in display_df.columns
                }
            )
            
            # Export options
            st.markdown("### 💾 Export Data")
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                csv_data = display_df.to_csv(index=False)
                st.download_button(
                    "📥 Download CSV",
                    data=csv_data,
                    file_name=f"kroon_beheer_reservations_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            with col_b:
                if st.button("🔄 Refresh Data", use_container_width=True):
                    st.cache_data.clear()
                    st.rerun()
            
            with col_c:
                st.write(f"**Records:** {len(display_df)}")
    
    with col2:
        st.markdown("### 📈 Quick Analytics")
        
        # Column statistics
        if selected_columns:
            for col in selected_columns[:3]:  # Show stats for first 3 columns
                with st.expander(f"📊 {col}", expanded=False):
                    col_data = df[col]
                    
                    # Basic stats
                    st.metric("Non-null values", col_data.count())
                    st.metric("Unique values", col_data.nunique())
                    
                    if col_data.dtype == 'object':
                        # For text columns, show top values
                        top_values = col_data.value_counts().head(5)
                        if not top_values.empty:
                            st.write("**Top values:**")
                            for val, count in top_values.items():
                                st.write(f"• {str(val)[:30]}{'...' if len(str(val)) > 30 else ''}: {count}")
                    
                    elif col_data.dtype.name.startswith('datetime'):
                        # For date columns
                        valid_dates = col_data.dropna()
                        if len(valid_dates) > 0:
                            st.metric("Date range (days)", (valid_dates.max() - valid_dates.min()).days)
        
        # Data quality overview
        st.markdown("### 🔍 Data Quality")
        
        missing_data = df.isnull().sum()
        total_missing = missing_data.sum()
        
        if total_missing > 0:
            st.metric("Missing values", total_missing)
            
            # Show columns with missing data
            missing_cols = missing_data[missing_data > 0]
            if not missing_cols.empty:
                st.write("**Columns with missing data:**")
                for col, count in missing_cols.items():
                    pct = (count / len(df)) * 100
                    st.write(f"• {col}: {count} ({pct:.1f}%)")
        else:
            st.success("✅ No missing values!")
        
        # Duplicate check
        duplicates = df.duplicated().sum()
        if duplicates > 0:
            st.warning(f"⚠️ {duplicates} duplicate rows found")
        else:
            st.success("✅ No duplicates!")
    
    # Bottom section - Visualizations
    if date_columns and len(date_columns) > 0:
        st.markdown("---")
        st.markdown("### 📅 Date Analysis")
        
        # Create tabs for different date visualizations
        tabs = st.tabs([f"📊 {col}" for col in date_columns[:3]])
        
        for i, date_col in enumerate(date_columns[:3]):
            with tabs[i]:
                valid_dates = df[date_col].dropna()
                
                if len(valid_dates) > 0:
                    col_x, col_y = st.columns(2)
                    
                    with col_x:
                        # Monthly distribution
                        monthly_data = valid_dates.dt.to_period('M').value_counts().sort_index()
                        
                        if len(monthly_data) > 0:
                            fig_monthly = px.bar(
                                x=monthly_data.index.astype(str),
                                y=monthly_data.values,
                                title=f"Monthly Distribution - {date_col}",
                                labels={'x': 'Month', 'y': 'Count'},
                                color=monthly_data.values,
                                color_continuous_scale='Blues'
                            )
                            fig_monthly.update_layout(height=400, showlegend=False)
                            st.plotly_chart(fig_monthly, use_container_width=True)
                    
                    with col_y:
                        # Day of week distribution
                        dow_data = valid_dates.dt.day_name().value_counts()
                        
                        fig_dow = px.pie(
                            values=dow_data.values,
                            names=dow_data.index,
                            title=f"Day of Week - {date_col}",
                            color_discrete_sequence=px.colors.qualitative.Set3
                        )
                        fig_dow.update_layout(height=400)
                        st.plotly_chart(fig_dow, use_container_width=True)
                else:
                    st.info(f"No valid dates found in {date_col}")

if __name__ == "__main__":
    main()
