import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Dict, List, Any

def create_pnl_summary_chart(pnl_data: List[Dict[str, Any]]) -> go.Figure:
    """Create a summary chart showing the main P&L components"""
    
    # Extract main sections
    sections = []
    values = []
    colors = []
    
    for section in pnl_data:
        name = section.get('name', '')
        total = float(section.get('total', 0))
        
        sections.append(name)
        values.append(total)
        
        # Color coding based on section type
        if 'Profit' in name or 'Income' in name:
            colors.append('#2E8B57')  # Sea Green for positive
        elif 'Loss' in name or 'Expense' in name:
            colors.append('#DC143C')  # Crimson for negative
        else:
            colors.append('#4682B4')  # Steel Blue for neutral
    
    fig = go.Figure(data=[
        go.Bar(
            x=sections,
            y=values,
            marker_color=colors,
            text=[f"${abs(v):,.2f}" for v in values],
            textposition='auto',
        )
    ])
    
    fig.update_layout(
        title="Profit & Loss Summary",
        xaxis_title="P&L Sections",
        yaxis_title="Amount ($)",
        template="plotly_white",
        height=400
    )
    
    return fig

def create_profit_loss_gauge(net_profit: float) -> go.Figure:
    """Create a gauge chart for net profit/loss"""
    
    # Determine gauge range and colors
    abs_value = abs(net_profit)
    max_range = max(abs_value * 1.2, 100000)  # 20% buffer or 100k minimum
    
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = net_profit,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Net Profit/Loss"},
        delta = {'reference': 0},
        gauge = {
            'axis': {'range': [-max_range, max_range]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [-max_range, 0], 'color': "lightcoral"},
                {'range': [0, max_range], 'color': "lightgreen"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 0
            }
        }
    ))
    
    fig.update_layout(
        height=300,
        template="plotly_white"
    )
    
    return fig

def create_expense_breakdown_chart(pnl_data: List[Dict[str, Any]]) -> go.Figure:
    """Create a pie chart showing expense breakdown"""
    
    expenses = []
    amounts = []
    
    for section in pnl_data:
        if 'Expense' in section.get('name', ''):
            for account in section.get('account_transactions', []):
                if account.get('total', 0) > 0:
                    expenses.append(account.get('name', 'Unknown'))
                    amounts.append(float(account.get('total', 0)))
    
    if not expenses:
        # Create empty chart
        fig = go.Figure()
        fig.add_annotation(
            text="No expense data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        fig.update_layout(height=300)
        return fig
    
    fig = px.pie(
        values=amounts,
        names=expenses,
        title="Expense Breakdown",
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    
    fig.update_layout(
        height=400,
        template="plotly_white"
    )
    
    return fig

def create_trend_chart(pnl_data: List[Dict[str, Any]], date_range: str) -> go.Figure:
    """Create a trend chart (placeholder for future implementation)"""
    
    fig = go.Figure()
    
    # Add placeholder data
    fig.add_trace(go.Scatter(
        x=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
        y=[0, 0, 0, 0, 0, 0],
        mode='lines+markers',
        name='Net Profit Trend',
        line=dict(color='blue', width=3)
    ))
    
    fig.update_layout(
        title=f"P&L Trend - {date_range}",
        xaxis_title="Month",
        yaxis_title="Amount ($)",
        height=300,
        template="plotly_white"
    )
    
    return fig 