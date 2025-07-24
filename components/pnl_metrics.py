import streamlit as st
import pandas as pd
from typing import Dict, List, Any
import plotly.graph_objects as go

def calculate_pnl_metrics(pnl_data: List[Dict[str, Any]]) -> Dict[str, float]:
    """Calculate key P&L metrics"""
    
    metrics = {}
    
    # Extract key values
    for section in pnl_data:
        name = section.get('name', '')
        total = float(section.get('total', 0))
        
        if name == 'Gross Profit':
            metrics['gross_profit'] = total
        elif name == 'Operating Profit':
            metrics['operating_profit'] = total
        elif name == 'Net Profit/Loss':
            metrics['net_profit'] = total
    
    # Calculate additional metrics
    total_revenue = 0
    total_expenses = 0
    
    for section in pnl_data:
        for account in section.get('account_transactions', []):
            account_name = account.get('name', '')
            account_total = float(account.get('total', 0))
            
            if 'Income' in account_name:
                total_revenue += account_total
            elif 'Expense' in account_name or 'Cost' in account_name:
                total_expenses += account_total
    
    metrics['total_revenue'] = total_revenue
    metrics['total_expenses'] = total_expenses
    
    # Calculate ratios
    if total_revenue > 0:
        metrics['gross_margin'] = (metrics.get('gross_profit', 0) / total_revenue) * 100
        metrics['operating_margin'] = (metrics.get('operating_profit', 0) / total_revenue) * 100
        metrics['net_margin'] = (metrics.get('net_profit', 0) / total_revenue) * 100
    else:
        metrics['gross_margin'] = 0
        metrics['operating_margin'] = 0
        metrics['net_margin'] = 0
    
    return metrics

def display_key_metrics(pnl_data: List[Dict[str, Any]]):
    """Display key P&L metrics in a beautiful format"""
    
    metrics = calculate_pnl_metrics(pnl_data)
    
    st.subheader("📊 Key Performance Indicators")
    
    # Create metric cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="💰 Net Profit/Loss",
            value=f"${metrics.get('net_profit', 0):,.2f}",
            delta=f"{metrics.get('net_margin', 0):.1f}% margin"
        )
    
    with col2:
        st.metric(
            label="📈 Gross Profit",
            value=f"${metrics.get('gross_profit', 0):,.2f}",
            delta=f"{metrics.get('gross_margin', 0):.1f}% margin"
        )
    
    with col3:
        st.metric(
            label="⚙️ Operating Profit",
            value=f"${metrics.get('operating_profit', 0):,.2f}",
            delta=f"{metrics.get('operating_margin', 0):.1f}% margin"
        )
    
    with col4:
        st.metric(
            label="💸 Total Expenses",
            value=f"${metrics.get('total_expenses', 0):,.2f}",
            delta=None
        )
    
    # Display margin breakdown
    st.subheader("📊 Margin Analysis")
    
    margin_data = {
        'Margin Type': ['Gross Margin', 'Operating Margin', 'Net Margin'],
        'Percentage': [
            metrics.get('gross_margin', 0),
            metrics.get('operating_margin', 0),
            metrics.get('net_margin', 0)
        ]
    }
    
    margin_df = pd.DataFrame(margin_data)
    
    # Create margin chart
    fig = go.Figure(data=[
        go.Bar(
            x=margin_df['Margin Type'],
            y=margin_df['Percentage'],
            marker_color=['#2E8B57', '#4682B4', '#DC143C'],
            text=[f"{p:.1f}%" for p in margin_df['Percentage']],
            textposition='auto',
        )
    ])
    
    fig.update_layout(
        title="Profit Margins",
        xaxis_title="Margin Type",
        yaxis_title="Percentage (%)",
        template="plotly_white",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

def display_profit_loss_waterfall(pnl_data: List[Dict[str, Any]]):
    """Create a waterfall chart showing profit/loss breakdown"""
    
    # Extract data for waterfall chart
    categories = []
    values = []
    colors = []
    
    # Start with revenue
    total_revenue = 0
    for section in pnl_data:
        for account in section.get('account_transactions', []):
            if 'Income' in account.get('name', ''):
                total_revenue += float(account.get('total', 0))
    
    if total_revenue > 0:
        categories.append('Revenue')
        values.append(total_revenue)
        colors.append('#2E8B57')  # Green
    
    # Add expenses
    for section in pnl_data:
        for account in section.get('account_transactions', []):
            account_name = account.get('name', '')
            account_total = float(account.get('total', 0))
            
            if ('Expense' in account_name or 'Cost' in account_name) and account_total > 0:
                categories.append(account_name)
                values.append(-account_total)  # Negative for expenses
                colors.append('#DC143C')  # Red
    
    # Add net profit
    net_profit = sum(values)
    categories.append('Net Profit/Loss')
    values.append(net_profit)
    colors.append('#4682B4' if net_profit >= 0 else '#DC143C')
    
    # Create waterfall chart
    fig = go.Figure(go.Waterfall(
        name="P&L Breakdown",
        orientation="h",
        measure=["relative", "relative", "relative", "relative", "relative", "relative", "total"],
        x=values,
        textposition="outside",
        text=[f"${abs(v):,.0f}" for v in values],
        y=categories,
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        decreasing={"marker": {"color": "#DC143C"}},
        increasing={"marker": {"color": "#2E8B57"}},
        totals={"marker": {"color": "#4682B4"}}
    ))
    
    fig.update_layout(
        title="Profit & Loss Waterfall Chart",
        showlegend=False,
        height=400,
        template="plotly_white"
    )
    
    st.plotly_chart(fig, use_container_width=True) 