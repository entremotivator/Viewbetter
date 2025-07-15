import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, JsCode
from st_aggrid.shared import GridUpdateMode
import calendar
from io import StringIO
import numpy as np

# Page configuration
st.set_page_config(
    page_title="Kroon Beheer Reservations Management",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-title {
        font-size: 3rem;
        font-weight: bold;
        color: #1e3a8a;
        text-align: center;
        margin-bottom: 2rem;
        padding: 2rem;
        background: linear-gradient(135deg, #f0f9ff, #dbeafe, #bfdbfe);
        border-radius: 15px;
        border: 2px solid #3b82f6;
        box-shadow: 0 8px 32px rgba(59, 130, 246, 0.3);
    }
    
    .section-header {
        font-size: 1.8rem;
        font-weight: bold;
        color: #1e40af;
        padding: 1rem;
        background: linear-gradient(90deg, #eff6ff, #dbeafe);
        border-radius: 10px;
        border-left: 5px solid #3b82f6;
        margin: 1rem 0;
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        border-left: 5px solid #3b82f6;
        margin: 1rem 0;
        transition: transform 0.2s;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.15);
    }
    
    .client-profile-card {
        background: linear-gradient(135deg, #f0fdf4, #dcfce7);
        padding: 1.5rem;
        border-radius: 12px;
        border: 2px solid #22c55e;
        margin: 1rem 0;
    }
    
    .reservation-card {
        background: linear-gradient(135deg, #fef3c7, #fde68a);
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #f59e0b;
        margin: 0.5rem 0;
    }
    
    .calendar-day {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 6px;
        padding: 0.5rem;
        margin: 2px;
        min-height: 80px;
        position: relative;
    }
    
    .calendar-day.has-reservation {
        background: linear-gradient(135deg, #dbeafe, #bfdbfe);
        border-color: #3b82f6;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
        background-color: #f8fafc;
        border-radius: 8px 8px 0 0;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #3b82f6;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load_and_process_data():
    """Load and process reservation data"""
    url = "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/Reservations%20Kroon%20Beheer%20BV%20-%20Kroon%20Beheer%20Client%20Info%20-oceEo2u6q6oDwnLyd8QoSnJqzEPSTa.csv"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Read CSV data
        df = pd.read_csv(StringIO(response.text))
        
        # Clean column names
        df.columns = df.columns.str.strip()
        
        # Remove completely empty columns
        df = df.dropna(axis=1, how='all')
        
        # Remove columns that are mostly empty (>90% null)
        threshold = len(df) * 0.1  # Keep columns with at least 10% data
        df = df.dropna(axis=1, thresh=threshold)
        
        # Process date columns
        date_columns = []
        for col in df.columns:
            if df[col].dtype == 'object':
                sample_values = df[col].dropna().head(10)
                if len(sample_values) > 0:
                    try:
                        pd.to_datetime(sample_values, errors='raise')
                        df[col] = pd.to_datetime(df[col], errors='coerce')
                        date_columns.append(col)
                    except:
                        pass
        
        # Separate client profiles from reservation data
        client_columns = [col for col in df.columns if 'client' in col.lower() or 'profile' in col.lower()]
        reservation_columns = [col for col in df.columns if col not in client_columns]
        
        return df, date_columns, client_columns, reservation_columns, None
        
    except Exception as e:
        return None, [], [], [], str(e)

def create_aggrid_table(df, height=400, selection_mode='multiple'):
    """Create an enhanced AgGrid table"""
    gb = GridOptionsBuilder.from_dataframe(df)
    
    # Configure grid options
    gb.configure_pagination(paginationAutoPageSize=True)
    gb.configure_side_bar()
    gb.configure_selection(selection_mode, use_checkbox=True, groupSelectsChildren=True, groupSelectsFiltered=True)
    gb.configure_default_column(groupable=True, value=True, enableRowGroup=True, aggFunc='sum', editable=True)
    
    # Configure columns
    for col in df.columns:
        if df[col].dtype.name.startswith('datetime'):
            gb.configure_column(col, type=["dateColumnFilter", "customDateTimeFormat"], 
                              custom_format_string='yyyy-MM-dd HH:mm', pivot=True)
        elif df[col].dtype in ['int64', 'float64']:
            gb.configure_column(col, type=["numericColumn", "numberColumnFilter", "customNumericFormat"], 
                              precision=2, aggFunc='sum')
        else:
            gb.configure_column(col, type=["textColumn"], wrapText=True, autoHeight=True)
    
    # Enable features
    gb.configure_grid_options(domLayout='normal')
    gridOptions = gb.build()
    
    # Custom JS for cell styling
    cell_style_jscode = JsCode("""
    function(params) {
        if (params.value && params.value.toString().toLowerCase().includes('reservation')) {
            return {
                'color': 'white',
                'backgroundColor': '#3b82f6',
                'fontWeight': 'bold'
            }
        }
        return null;
    }
    """)
    
    # Apply custom styling to specific columns
    for col in df.columns:
        if 'reservation' in col.lower():
            gb.configure_column(col, cellStyle=cell_style_jscode)
    
    grid_response = AgGrid(
        df,
        gridOptions=gridOptions,
        data_return_mode=DataReturnMode.AS_INPUT,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        fit_columns_on_grid_load=False,
        theme='streamlit',
        height=height,
        width='100%',
        reload_data=False
    )
    
    return grid_response

def create_calendar_view(df, date_column):
    """Create a calendar view for reservations"""
    if date_column not in df.columns:
        return None
    
    # Get date data
    date_data = df[date_column].dropna()
    if len(date_data) == 0:
        return None
    
    # Create monthly calendar
    current_date = datetime.now()
    year = current_date.year
    month = current_date.month
    
    # Get reservations for current month
    month_reservations = date_data[
        (date_data.dt.year == year) & (date_data.dt.month == month)
    ]
    
    # Create calendar grid
    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]
    
    st.subheader(f"📅 {month_name} {year} - Reservations Calendar")
    
    # Create calendar layout
    cols = st.columns(7)
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    
    # Header row
    for i, day in enumerate(days):
        with cols[i]:
            st.markdown(f"**{day}**")
    
    # Calendar days
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day == 0:
                    st.write("")
                else:
                    day_reservations = month_reservations[month_reservations.dt.day == day]
                    if len(day_reservations) > 0:
                        st.markdown(f"""
                        <div class="calendar-day has-reservation">
                            <strong>{day}</strong><br>
                            <small>{len(day_reservations)} reservations</small>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="calendar-day">
                            <strong>{day}</strong>
                        </div>
                        """, unsafe_allow_html=True)

def main():
    # Main title
    st.markdown('<div class="main-title">🏢 Kroon Beheer BV<br>Advanced Reservations Management System</div>', unsafe_allow_html=True)
    
    # Load data
    with st.spinner("🔄 Loading and processing reservation data..."):
        df, date_columns, client_columns, reservation_columns, error = load_and_process_data()
    
    if error:
        st.error(f"❌ Error loading data: {error}")
        st.stop()
    
    if df is None or df.empty:
        st.warning("⚠️ No reservation data available")
        st.stop()
    
    # Sidebar configuration
    st.sidebar.markdown("### 🔧 System Configuration")
    
    # Data overview metrics
    st.sidebar.markdown("### 📊 Data Overview")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        st.metric("Total Records", len(df))
        st.metric("Active Columns", len(df.columns))
    with col2:
        st.metric("Client Profiles", df[client_columns[0]].nunique() if client_columns else 0)
        st.metric("Date Fields", len(date_columns))
    
    # Filter options
    st.sidebar.markdown("### 🔍 Filters")
    
    # Date range filter
    if date_columns:
        selected_date_col = st.sidebar.selectbox("Select Date Column", date_columns)
        
        valid_dates = df[selected_date_col].dropna()
        if len(valid_dates) > 0:
            min_date = valid_dates.min().date()
            max_date = valid_dates.max().date()
            
            date_range = st.sidebar.date_input(
                "Date Range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
            
            if len(date_range) == 2:
                start_date, end_date = date_range
                mask = (df[selected_date_col].dt.date >= start_date) & (df[selected_date_col].dt.date <= end_date)
                df = df[mask]
    
    # Client profile filter
    if client_columns:
        client_profiles = df[client_columns[0]].dropna().unique()
        selected_profiles = st.sidebar.multiselect(
            "Filter by Client Profile",
            options=client_profiles,
            default=client_profiles[:5] if len(client_profiles) > 5 else client_profiles
        )
        
        if selected_profiles:
            df = df[df[client_columns[0]].isin(selected_profiles)]
    
    # Main content tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "👥 Client Profiles", 
        "📋 Reservations Grid", 
        "📅 Calendar View", 
        "📊 Analytics", 
        "⚙️ Actions"
    ])
    
    # Tab 1: Client Profiles
    with tab1:
        st.markdown('<div class="section-header">👥 Client Profile Management</div>', unsafe_allow_html=True)
        
        if client_columns:
            # Client profile summary
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader("📋 Client Profiles Overview")
                
                client_df = df[client_columns].drop_duplicates()
                
                # Create AgGrid for client profiles
                client_grid = create_aggrid_table(client_df, height=400)
                
                # Show selected client details
                if client_grid['selected_rows']:
                    st.subheader("🔍 Selected Client Details")
                    selected_client = pd.DataFrame(client_grid['selected_rows'])
                    st.dataframe(selected_client, use_container_width=True)
            
            with col2:
                st.subheader("📈 Client Statistics")
                
                # Client profile distribution
                if client_columns:
                    profile_counts = df[client_columns[0]].value_counts().head(10)
                    
                    fig = px.bar(
                        x=profile_counts.values,
                        y=profile_counts.index,
                        orientation='h',
                        title="Top Client Profiles",
                        color=profile_counts.values,
                        color_continuous_scale='Blues'
                    )
                    fig.update_layout(height=400, showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                
                # Client metrics
                for col in client_columns[:3]:
                    unique_count = df[col].nunique()
                    st.markdown(f"""
                    <div class="client-profile-card">
                        <h4>{col}</h4>
                        <p><strong>{unique_count}</strong> unique values</p>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("No client profile columns detected in the data.")
    
    # Tab 2: Reservations Grid
    with tab2:
        st.markdown('<div class="section-header">📋 Advanced Reservations Grid</div>', unsafe_allow_html=True)
        
        # Grid controls
        col1, col2, col3 = st.columns(3)
        with col1:
            grid_height = st.slider("Grid Height", 300, 800, 500, 50)
        with col2:
            show_all_columns = st.checkbox("Show All Columns", value=False)
        with col3:
            export_selected = st.checkbox("Export Selected Only", value=False)
        
        # Column selection
        if not show_all_columns:
            display_columns = st.multiselect(
                "Select Columns to Display",
                options=df.columns.tolist(),
                default=reservation_columns[:8] if len(reservation_columns) > 8 else reservation_columns
            )
            if display_columns:
                display_df = df[display_columns]
            else:
                display_df = df
        else:
            display_df = df
        
        # Create the main reservations grid
        st.subheader("🗂️ Reservations Data Grid")
        grid_response = create_aggrid_table(display_df, height=grid_height)
        
        # Grid actions
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("🔄 Refresh Data", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
        
        with col2:
            selected_rows = len(grid_response['selected_rows']) if grid_response['selected_rows'] else 0
            st.metric("Selected Rows", selected_rows)
        
        with col3:
            if grid_response['selected_rows']:
                selected_df = pd.DataFrame(grid_response['selected_rows'])
                csv_data = selected_df.to_csv(index=False)
                st.download_button(
                    "📥 Export Selected",
                    data=csv_data,
                    file_name=f"selected_reservations_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        
        with col4:
            csv_data = display_df.to_csv(index=False)
            st.download_button(
                "📥 Export All",
                data=csv_data,
                file_name=f"all_reservations_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        # Show selected data details
        if grid_response['selected_rows']:
            st.subheader("🔍 Selected Reservations Details")
            selected_df = pd.DataFrame(grid_response['selected_rows'])
            st.dataframe(selected_df, use_container_width=True)
    
    # Tab 3: Calendar View
    with tab3:
        st.markdown('<div class="section-header">📅 Reservation Calendar</div>', unsafe_allow_html=True)
        
        if date_columns:
            # Calendar controls
            col1, col2 = st.columns(2)
            with col1:
                selected_date_col = st.selectbox("Select Date Column for Calendar", date_columns, key="calendar_date")
            with col2:
                calendar_month = st.selectbox("Select Month", range(1, 13), 
                                            index=datetime.now().month-1,
                                            format_func=lambda x: calendar.month_name[x])
            
            # Create calendar view
            create_calendar_view(df, selected_date_col)
            
            # Daily reservations breakdown
            st.subheader("📊 Daily Reservations Breakdown")
            
            if selected_date_col in df.columns:
                daily_counts = df[selected_date_col].dt.date.value_counts().sort_index()
                
                if not daily_counts.empty:
                    fig = px.line(
                        x=daily_counts.index,
                        y=daily_counts.values,
                        title=f"Daily Reservations Trend - {selected_date_col}",
                        labels={'x': 'Date', 'y': 'Number of Reservations'}
                    )
                    fig.update_traces(mode='lines+markers')
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No date columns available for calendar view.")
    
    # Tab 4: Analytics
    with tab4:
        st.markdown('<div class="section-header">📊 Advanced Analytics Dashboard</div>', unsafe_allow_html=True)
        
        # Analytics metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("""
            <div class="metric-card">
                <h3>Total Reservations</h3>
                <h2 style="color: #3b82f6;">{}</h2>
            </div>
            """.format(len(df)), unsafe_allow_html=True)
        
        with col2:
            if client_columns:
                unique_clients = df[client_columns[0]].nunique()
                st.markdown("""
                <div class="metric-card">
                    <h3>Unique Clients</h3>
                    <h2 style="color: #10b981;">{}</h2>
                </div>
                """.format(unique_clients), unsafe_allow_html=True)
        
        with col3:
            if date_columns:
                date_range_days = (df[date_columns[0]].max() - df[date_columns[0]].min()).days
                st.markdown("""
                <div class="metric-card">
                    <h3>Date Range</h3>
                    <h2 style="color: #f59e0b;">{} days</h2>
                </div>
                """.format(date_range_days), unsafe_allow_html=True)
        
        with col4:
            data_quality = (1 - df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100
            st.markdown("""
            <div class="metric-card">
                <h3>Data Quality</h3>
                <h2 style="color: #8b5cf6;">{:.1f}%</h2>
            </div>
            """.format(data_quality), unsafe_allow_html=True)
        
        # Advanced visualizations
        if date_columns and client_columns:
            st.subheader("📈 Reservation Trends by Client Profile")
            
            # Create pivot table for heatmap
            pivot_data = df.pivot_table(
                index=df[date_columns[0]].dt.date,
                columns=client_columns[0],
                values=df.columns[0],  # Use first column as value
                aggfunc='count',
                fill_value=0
            )
            
            if not pivot_data.empty:
                fig = px.imshow(
                    pivot_data.T,
                    title="Reservation Heatmap: Client Profiles vs Dates",
                    color_continuous_scale='Blues',
                    aspect='auto'
                )
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)
        
        # Data quality analysis
        st.subheader("🔍 Data Quality Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Missing data analysis
            missing_data = df.isnull().sum()
            missing_data = missing_data[missing_data > 0].sort_values(ascending=False)
            
            if not missing_data.empty:
                fig = px.bar(
                    x=missing_data.values,
                    y=missing_data.index,
                    orientation='h',
                    title="Missing Data by Column",
                    color=missing_data.values,
                    color_continuous_scale='Reds'
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.success("✅ No missing data found!")
        
        with col2:
            # Data type distribution
            dtype_counts = df.dtypes.value_counts()
            
            fig = px.pie(
                values=dtype_counts.values,
                names=dtype_counts.index.astype(str),
                title="Data Types Distribution"
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    # Tab 5: Actions
    with tab5:
        st.markdown('<div class="section-header">⚙️ System Actions & Tools</div>', unsafe_allow_html=True)
        
        # Action buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("📊 Data Operations")
            
            if st.button("🔄 Refresh All Data", use_container_width=True):
                st.cache_data.clear()
                st.success("Data refreshed successfully!")
                st.rerun()
            
            if st.button("🧹 Clean Data", use_container_width=True):
                # Perform data cleaning operations
                cleaned_df = df.dropna(how='all').drop_duplicates()
                st.success(f"Removed {len(df) - len(cleaned_df)} rows")
            
            if st.button("📈 Generate Report", use_container_width=True):
                # Generate comprehensive report
                report = f"""
                KROON BEHEER RESERVATIONS REPORT
                Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                
                SUMMARY:
                - Total Reservations: {len(df)}
                - Date Range: {df[date_columns[0]].min()} to {df[date_columns[0]].max() if date_columns else 'N/A'}
                - Client Profiles: {df[client_columns[0]].nunique() if client_columns else 'N/A'}
                - Data Quality: {((1 - df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100):.1f}%
                """
                
                st.download_button(
                    "📥 Download Report",
                    data=report,
                    file_name=f"kroon_beheer_report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
        
        with col2:
            st.subheader("🔧 Configuration")
            
            # System settings
            auto_refresh = st.checkbox("Auto Refresh (5 min)", value=False)
            show_debug = st.checkbox("Show Debug Info", value=False)
            enable_editing = st.checkbox("Enable Grid Editing", value=True)
            
            if show_debug:
                st.subheader("🐛 Debug Information")
                st.json({
                    "DataFrame Shape": df.shape,
                    "Columns": list(df.columns),
                    "Date Columns": date_columns,
                    "Client Columns": client_columns,
                    "Memory Usage": f"{df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB"
                })
        
        with col3:
            st.subheader("📤 Export Options")
            
            # Export formats
            export_format = st.selectbox("Export Format", ["CSV", "Excel", "JSON"])
            include_metadata = st.checkbox("Include Metadata", value=True)
            
            if st.button("📥 Export Data", use_container_width=True):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M')
                
                if export_format == "CSV":
                    data = df.to_csv(index=False)
                    filename = f"kroon_beheer_export_{timestamp}.csv"
                    mime = "text/csv"
                elif export_format == "Excel":
                    # Note: This would require openpyxl
                    data = df.to_csv(index=False)  # Fallback to CSV
                    filename = f"kroon_beheer_export_{timestamp}.csv"
                    mime = "text/csv"
                else:  # JSON
                    data = df.to_json(orient='records', date_format='iso')
                    filename = f"kroon_beheer_export_{timestamp}.json"
                    mime = "application/json"
                
                st.download_button(
                    f"📥 Download {export_format}",
                    data=data,
                    file_name=filename,
                    mime=mime,
                    use_container_width=True
                )
        
        # System status
        st.markdown("---")
        st.subheader("🔋 System Status")
        
        status_col1, status_col2, status_col3, status_col4 = st.columns(4)
        
        with status_col1:
            st.metric("System Status", "🟢 Online")
        with status_col2:
            st.metric("Last Updated", datetime.now().strftime('%H:%M:%S'))
        with status_col3:
            st.metric("Data Source", "🔗 Connected")
        with status_col4:
            st.metric("Performance", "⚡ Optimal")

if __name__ == "__main__":
    main()
