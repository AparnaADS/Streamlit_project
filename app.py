import streamlit as st
import os
import time
import requests
import pandas as pd
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Import our custom components
from components.pnl_charts import (
    create_pnl_summary_chart,
    create_profit_loss_gauge,
    create_expense_breakdown_chart,
    create_trend_chart
)
from components.pnl_table import display_pnl_table, display_pnl_json
from components.pnl_metrics import display_key_metrics, display_profit_loss_waterfall

# ——————— Load environment variables ———————
load_dotenv()
CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")
TOKEN_URL = os.getenv("ZOHO_TOKEN_URL", "https://accounts.zoho.com/oauth/v2/token")
ORG_ID = os.getenv("ZOHO_ORG_ID")
API_BASE = "https://www.zohoapis.com/books/v3"

_token_cache = {"access_token": os.getenv("ZOHO_ACCESS_TOKEN"), "expires_at": 0}

def _refresh_access_token():
    """Refresh the access token"""
    resp = requests.post(
        TOKEN_URL,
        data={
            "refresh_token": REFRESH_TOKEN,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "refresh_token",
        }
    )
    resp.raise_for_status()
    data = resp.json()
    token = data["access_token"]
    expires_in = data.get("expires_in", 3600)
    _token_cache.update({
        "access_token": token,
        "expires_at": time.time() + expires_in - 60
    })
    return token

def get_access_token():
    """Get the current access token, refreshing if necessary"""
    if not _token_cache.get("access_token") or time.time() >= _token_cache["expires_at"]:
        return _refresh_access_token()
    return _token_cache["access_token"]

def fetch_pnl_data(from_date: str, to_date: str) -> dict:
    """Fetch P&L data from Zoho Books API"""
    try:
        resp = requests.get(
            f"{API_BASE}/reports/profitandloss",
            headers={"Authorization": f"Zoho-oauthtoken {get_access_token()}"},
            params={"organization_id": ORG_ID, "from_date": from_date, "to_date": to_date}
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"Error fetching P&L data: {str(e)}")
        return None

def load_sample_data() -> dict:
    """Load sample P&L data from JSON file"""
    try:
        with open('profit_and_loss.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading sample data: {str(e)}")
        return None

def main():
    # Page configuration
    st.set_page_config(
        page_title="Profit & Loss Dashboard",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS for better styling
    st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    .stTabs [data-baseweb="tab"] {
        height: 4rem;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0px 0px;
        gap: 1rem;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1f77b4;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown('<h1 class="main-header">📊 Profit & Loss Dashboard</h1>', unsafe_allow_html=True)
    
    # Sidebar for controls
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # Data source selection
        data_source = st.radio(
            "Data Source",
            ["Live API", "Sample Data"],
            help="Choose between live Zoho API data or sample data"
        )
        
        # Date selection
        st.subheader("📅 Date Range")
        
        if data_source == "Live API":
            # Date inputs for live data
            from_date = st.date_input(
                "From Date",
                value=datetime.now().replace(day=1),
                key="from_date"
            )
            to_date = st.date_input(
                "To Date",
                value=datetime.now(),
                key="to_date"
            )
            
            # Convert to string format
            from_date_str = from_date.strftime("%Y-%m-%d")
            to_date_str = to_date.strftime("%Y-%m-%d")
            
            # Fetch data button
            if st.button("🔄 Fetch P&L Data", type="primary"):
                with st.spinner("Fetching data from Zoho Books..."):
                    pnl_data = fetch_pnl_data(from_date_str, to_date_str)
                    if pnl_data:
                        st.session_state.pnl_data = pnl_data
                        st.session_state.date_range = f"{from_date_str} to {to_date_str}"
                        st.success("Data fetched successfully!")
                    else:
                        st.error("Failed to fetch data. Please check your API credentials.")
        else:
            # Sample data
            if st.button("📁 Load Sample Data", type="primary"):
                with st.spinner("Loading sample data..."):
                    pnl_data = load_sample_data()
                    if pnl_data:
                        st.session_state.pnl_data = pnl_data
                        st.session_state.date_range = "Sample Data (July 2025)"
                        st.success("Sample data loaded successfully!")
                    else:
                        st.error("Failed to load sample data.")
        
        # Display current data info
        if hasattr(st.session_state, 'pnl_data'):
            st.success("✅ Data loaded")
            st.info(f"Date Range: {st.session_state.get('date_range', 'N/A')}")
        else:
            st.warning("⚠️ No data loaded")
    
    # Main content area
    if hasattr(st.session_state, 'pnl_data') and st.session_state.pnl_data:
        pnl_data = st.session_state.pnl_data
        date_range = st.session_state.get('date_range', 'N/A')
        
        # Extract P&L data
        profit_and_loss = pnl_data.get('profit_and_loss', [])
        
        if not profit_and_loss:
            st.error("No P&L data found in the response.")
            return
        
        # Create tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Overview", 
            "📋 Detailed Statement", 
            "📈 Charts & Analytics",
            "🔧 Raw Data"
        ])
        
        with tab1:
            st.header("📊 P&L Overview")
            
            # Key metrics
            display_key_metrics(profit_and_loss)
            
            # Gauge chart for net profit
            st.subheader("💰 Net Profit/Loss Gauge")
            net_profit = next((float(section.get('total', 0)) for section in profit_and_loss if section.get('name') == 'Net Profit/Loss'), 0)
            gauge_fig = create_profit_loss_gauge(net_profit)
            st.plotly_chart(gauge_fig, use_container_width=True)
            
            # Summary chart
            st.subheader("📊 P&L Summary")
            summary_fig = create_pnl_summary_chart(profit_and_loss)
            st.plotly_chart(summary_fig, use_container_width=True)
        
        with tab2:
            st.header("📋 Detailed Profit & Loss Statement")
            
            # Display the detailed table
            display_pnl_table(profit_and_loss, date_range)
            
            # Waterfall chart
            st.subheader("🌊 P&L Waterfall Chart")
            display_profit_loss_waterfall(profit_and_loss)
        
        with tab3:
            st.header("📈 Charts & Analytics")
            
            # Create two columns for charts
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🍰 Expense Breakdown")
                expense_fig = create_expense_breakdown_chart(profit_and_loss)
                st.plotly_chart(expense_fig, use_container_width=True)
            
            with col2:
                st.subheader("📈 P&L Trend")
                trend_fig = create_trend_chart(profit_and_loss, date_range)
                st.plotly_chart(trend_fig, use_container_width=True)
            
            # Additional analytics
            st.subheader("📊 Additional Analytics")
            
            # Calculate and display some additional metrics
            total_income = sum(
                float(account.get('total', 0))
                for section in profit_and_loss
                for account in section.get('account_transactions', [])
                if 'Income' in account.get('name', '')
            )
            
            total_expenses = sum(
                float(account.get('total', 0))
                for section in profit_and_loss
                for account in section.get('account_transactions', [])
                if 'Expense' in account.get('name', '') or 'Cost' in account.get('name', '')
            )
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    label="Total Income",
                    value=f"${total_income:,.2f}",
                    delta=None
                )
            
            with col2:
                st.metric(
                    label="Total Expenses",
                    value=f"${total_expenses:,.2f}",
                    delta=None
                )
            
            with col3:
                if total_income > 0:
                    expense_ratio = (total_expenses / total_income) * 100
                    st.metric(
                        label="Expense Ratio",
                        value=f"{expense_ratio:.1f}%",
                        delta=None
                    )
                else:
                    st.metric(
                        label="Expense Ratio",
                        value="N/A",
                        delta=None
                    )
        
        with tab4:
            st.header("🔧 Raw Data & Debugging")
            
            # Display raw JSON data
            display_pnl_json(pnl_data)
            
            # Data validation
            st.subheader("🔍 Data Validation")
            
            if pnl_data.get('code') == 0:
                st.success("✅ API Response: Success")
            else:
                st.error(f"❌ API Response: {pnl_data.get('message', 'Unknown error')}")
            
            # Show page context info
            page_context = pnl_data.get('page_context', {})
            if page_context:
                st.subheader("📄 Page Context")
                st.json(page_context)
    
    else:
        # Welcome screen when no data is loaded
        st.markdown("""
        ## 🎯 Welcome to the Profit & Loss Dashboard!
        
        This dashboard provides comprehensive analysis of your Profit & Loss statements with:
        
        - 📊 **Interactive Charts**: Visualize your P&L data with beautiful charts
        - 📋 **Detailed Statements**: View formatted P&L statements
        - 📈 **Key Metrics**: Track important financial KPIs
        - 🔧 **Data Export**: Download your data in CSV format
        
        ### Getting Started:
        
        1. **Choose your data source** from the sidebar
        2. **Select a date range** for your analysis
        3. **Click the fetch/load button** to get your data
        4. **Explore different tabs** to view various aspects of your P&L
        
        ### Features:
        
        - ✅ Real-time data from Zoho Books API
        - ✅ Sample data for testing
        - ✅ Beautiful visualizations
        - ✅ Export capabilities
        - ✅ Responsive design
        """)
        
        # Show sample data structure
        with st.expander("📋 Sample Data Structure"):
            st.json({
                "profit_and_loss": [
                    {
                        "name": "Gross Profit",
                        "total": -3400,
                        "account_transactions": [...]
                    }
                ]
            })

if __name__ == "__main__":
    main()
