import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# Set page config
st.set_page_config(
    page_title="Kroon Beheer Reservations Dashboard",
    page_icon="📊",
    layout="wide"
)

@st.cache_data
def load_data():
    """Load and process the CSV data from the URL"""
    url = "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/Reservations%20Kroon%20Beheer%20BV%20-%20Kroon%20Beheer%20Client%20Info%20-oceEo2u6q6oDwnLyd8QoSnJqzEPSTa.csv"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        # Save content to a temporary file-like object
        from io import StringIO
        csv_content = StringIO(response.text)
        
        # Read CSV
        df = pd.read_csv(csv_content)
        
        # Clean column names
        df.columns = df.columns.str.strip()
        
        return df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

def process_date_columns(df):
    """Process and identify date columns"""
    date_columns = []
    
    for col in df.columns:
        if df[col].dtype == 'object':
            # Try to convert to datetime
            try:
                pd.to_datetime(df[col], errors='raise')
                date_columns.append(col)
                df[col] = pd.to_datetime(df[col])
            except:
                pass
    
    return df, date_columns

def main():
    st.title("📊 Kroon Beheer Reservations Dashboard")
    st.markdown("---")
    
    # Load data
    with st.spinner("Loading reservation data..."):
        df = load_data()
    
    if df is None:
        st.stop()
    
    # Process dates
    df, date_columns = process_date_columns(df)
    
    # Sidebar filters
    st.sidebar.header("🔍 Filters")
    
    # Show basic info
    st.sidebar.metric("Total Records", len(df))
    st.sidebar.metric("Total Columns", len(df.columns))
    
    # Column selection for display
    display_columns = st.sidebar.multiselect(
        "Select Columns to Display",
        options=df.columns.tolist(),
        default=df.columns.tolist()[:10] if len(df.columns) > 10 else df.columns.tolist()
    )
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📋 Reservations Grid")
        
        if display_columns:
            # Display the filtered dataframe
            filtered_df = df[display_columns]
            
            # Add search functionality
            search_term = st.text_input("🔍 Search in data:", placeholder="Enter search term...")
            
            if search_term:
                # Search across all string columns
                mask = filtered_df.astype(str).apply(
                    lambda x: x.str.contains(search_term, case=False, na=False)
                ).any(axis=1)
                filtered_df = filtered_df[mask]
            
            # Display data with pagination
            st.dataframe(
                filtered_df,
                use_container_width=True,
                height=500
            )
            
            # Download button
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Filtered Data",
                data=csv,
                file_name=f"kroon_beheer_reservations_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    with col2:
        st.header("📈 Quick Stats")
        
        # Client profile stats if available
        if 'Kroon Beheer Client Profile' in df.columns:
            client_counts = df['Kroon Beheer Client Profile'].value_counts().head(10)
            
            st.subheader("Top Client Profiles")
            for profile, count in client_counts.items():
                st.metric(profile[:30] + "..." if len(profile) > 30 else profile, count)
        
        # Date-based stats
        if date_columns:
            st.subheader("📅 Date Analysis")
            
            for date_col in date_columns[:2]:  # Show first 2 date columns
                if not df[date_col].isna().all():
                    st.write(f"**{date_col}:**")
                    
                    # Date range
                    min_date = df[date_col].min()
                    max_date = df[date_col].max()
                    
                    if pd.notna(min_date) and pd.notna(max_date):
                        st.write(f"From: {min_date.strftime('%Y-%m-%d')}")
                        st.write(f"To: {max_date.strftime('%Y-%m-%d')}")
                        
                        # Monthly distribution
                        monthly_counts = df[date_col].dt.to_period('M').value_counts().sort_index()
                        
                        if len(monthly_counts) > 0:
                            fig = px.bar(
                                x=monthly_counts.index.astype(str),
                                y=monthly_counts.values,
                                title=f"Monthly Distribution - {date_col}",
                                labels={'x': 'Month', 'y': 'Count'}
                            )
                            fig.update_layout(height=300)
                            st.plotly_chart(fig, use_container_width=True)
    
    # Additional analysis section
    st.markdown("---")
    st.header("🔍 Detailed Analysis")
    
    # Create tabs for different views
    tab1, tab2, tab3 = st.tabs(["📊 Summary Statistics", "📅 Date Insights", "🔍 Data Quality"])
    
    with tab1:
        st.subheader("Column Summary")
        
        # Create summary stats
        summary_data = []
        for col in df.columns:
            col_info = {
                'Column': col,
                'Type': str(df[col].dtype),
                'Non-Null Count': df[col].count(),
                'Null Count': df[col].isnull().sum(),
                'Unique Values': df[col].nunique()
            }
            
            if df[col].dtype in ['int64', 'float64']:
                col_info['Mean'] = df[col].mean()
                col_info['Min'] = df[col].min()
                col_info['Max'] = df[col].max()
            
            summary_data.append(col_info)
        
        summary_df = pd.DataFrame(summary_data)
        st.dataframe(summary_df, use_container_width=True)
    
    with tab2:
        if date_columns:
            st.subheader("Date Column Analysis")
            
            for date_col in date_columns:
                st.write(f"**Analysis for {date_col}:**")
                
                # Remove null dates for analysis
                valid_dates = df[date_col].dropna()
                
                if len(valid_dates) > 0:
                    col_a, col_b = st.columns(2)
                    
                    with col_a:
                        st.metric("Valid Dates", len(valid_dates))
                        st.metric("Date Range (Days)", (valid_dates.max() - valid_dates.min()).days)
                    
                    with col_b:
                        # Day of week distribution
                        dow_counts = valid_dates.dt.day_name().value_counts()
                        fig = px.pie(
                            values=dow_counts.values,
                            names=dow_counts.index,
                            title=f"Day of Week Distribution - {date_col}"
                        )
                        st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No date columns detected in the dataset.")
    
    with tab3:
        st.subheader("Data Quality Overview")
        
        # Missing data heatmap
        missing_data = df.isnull().sum()
        missing_pct = (missing_data / len(df)) * 100
        
        quality_df = pd.DataFrame({
            'Column': missing_data.index,
            'Missing Count': missing_data.values,
            'Missing Percentage': missing_pct.values
        }).sort_values('Missing Percentage', ascending=False)
        
        st.dataframe(quality_df, use_container_width=True)
        
        # Visualization of missing data
        if missing_pct.sum() > 0:
            fig = px.bar(
                quality_df.head(10),
                x='Column',
                y='Missing Percentage',
                title="Top 10 Columns with Missing Data",
                color='Missing Percentage',
                color_continuous_scale='Reds'
            )
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
