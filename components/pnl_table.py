import streamlit as st
import pandas as pd
from typing import Dict, List, Any
import json

def format_currency(amount: float) -> str:
    """Format amount as currency with proper formatting"""
    if amount == 0:
        return "$0.00"
    elif amount > 0:
        return f"${amount:,.2f}"
    else:
        return f"(${abs(amount):,.2f})"

def create_pnl_dataframe(pnl_data: List[Dict[str, Any]]) -> pd.DataFrame:
    """Convert P&L data to a structured DataFrame"""
    
    rows = []
    
    def process_section(section: Dict[str, Any], level: int = 0):
        name = section.get('name', '')
        total = float(section.get('total', 0))
        
        # Add main section
        rows.append({
            'Account': '  ' * level + name,
            'Amount': total,
            'Formatted': format_currency(total),
            'Level': level,
            'Type': 'section'
        })
        
        # Process sub-accounts
        for account in section.get('account_transactions', []):
            account_name = account.get('name', '')
            account_total = float(account.get('total', 0))
            
            rows.append({
                'Account': '  ' * (level + 1) + account_name,
                'Amount': account_total,
                'Formatted': format_currency(account_total),
                'Level': level + 1,
                'Type': 'account'
            })
            
            # Process sub-account transactions
            for sub_account in account.get('account_transactions', []):
                sub_name = sub_account.get('name', '')
                sub_total = float(sub_account.get('total', 0))
                
                rows.append({
                    'Account': '  ' * (level + 2) + sub_name,
                    'Amount': sub_total,
                    'Formatted': format_currency(sub_total),
                    'Level': level + 2,
                    'Type': 'sub_account'
                })
    
    # Process each main section
    for section in pnl_data:
        process_section(section)
    
    return pd.DataFrame(rows)

def display_pnl_table(pnl_data: List[Dict[str, Any]], date_range: str):
    """Display P&L data in a beautiful table format"""
    
    df = create_pnl_dataframe(pnl_data)
    
    # Create styled table
    st.subheader(f"Profit & Loss Statement - {date_range}")
    
    # Display summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    # Calculate key metrics
    gross_profit = next((float(section.get('total', 0)) for section in pnl_data if section.get('name') == 'Gross Profit'), 0)
    operating_profit = next((float(section.get('total', 0)) for section in pnl_data if section.get('name') == 'Operating Profit'), 0)
    net_profit = next((float(section.get('total', 0)) for section in pnl_data if section.get('name') == 'Net Profit/Loss'), 0)
    
    with col1:
        st.metric(
            label="Gross Profit",
            value=format_currency(gross_profit),
            delta=None
        )
    
    with col2:
        st.metric(
            label="Operating Profit",
            value=format_currency(operating_profit),
            delta=None
        )
    
    with col3:
        st.metric(
            label="Net Profit/Loss",
            value=format_currency(net_profit),
            delta=None
        )
    
    with col4:
        # Calculate total expenses
        total_expenses = sum(
            float(account.get('total', 0))
            for section in pnl_data
            for account in section.get('account_transactions', [])
            if 'Expense' in account.get('name', '')
        )
        st.metric(
            label="Total Expenses",
            value=format_currency(total_expenses),
            delta=None
        )
    
    # Display the detailed table
    st.subheader("Detailed P&L Statement")
    
    # Apply custom styling
    def highlight_rows(row):
        if row['Level'] == 0:
            return ['background-color: #f0f8ff; font-weight: bold;'] * len(row)
        elif row['Level'] == 1:
            return ['background-color: #f8f8ff; font-weight: bold;'] * len(row)
        else:
            return [''] * len(row)
    
    # Display as a styled dataframe
    styled_df = df[['Account', 'Formatted']].copy()
    styled_df.columns = ['Account', 'Amount']
    
    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Account": st.column_config.TextColumn(
                "Account",
                width="medium"
            ),
            "Amount": st.column_config.TextColumn(
                "Amount",
                width="small"
            )
        }
    )
    
    # Add download button
    csv = df.to_csv(index=False)
    st.download_button(
        label="Download P&L Data as CSV",
        data=csv,
        file_name=f"pnl_statement_{date_range.replace(' ', '_')}.csv",
        mime="text/csv"
    )

def display_pnl_json(pnl_data: Dict[str, Any]):
    """Display raw JSON data for debugging"""
    
    with st.expander("Raw P&L Data (JSON)"):
        st.json(pnl_data) 