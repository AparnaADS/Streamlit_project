import os
import time
import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from dotenv import load_dotenv

# ——————— Load environment variables ———————
load_dotenv()
CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")
TOKEN_URL = os.getenv("ZOHO_TOKEN_URL", "https://accounts.zoho.com/oauth/v2/token")
ORG_ID = os.getenv("ZOHO_ORG_ID")  # Fetch Organization ID from .env
API_BASE = "https://www.zohoapis.com/books/v3"  # Correct API base URL

_token_cache = {"access_token": os.getenv("ZOHO_ACCESS_TOKEN"), "expires_at": 0}

def _refresh_access_token():
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
    if not _token_cache.get("access_token") or time.time() >= _token_cache["expires_at"]:
        return _refresh_access_token()
    return _token_cache["access_token"]

def fetch_data_from_zoho(endpoint, params):
    url = f"{API_BASE}/{endpoint}"
    headers = {"Authorization": f"Zoho-oauthtoken {get_access_token()}"}
    
    response = requests.get(url, headers=headers, params=params)

    # Check if response is successful
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return {}

def fetch_balance_sheet_4cols(start_date, end_date=None):
    # If no end_date is provided, set it to start_date
    if not end_date:
        end_date = start_date  # Or datetime.today().strftime('%Y-%m-%d') for today's date
    
    # Define parameters for transactions (fetch data for the specified date range)
    params = {
        "organization_id": ORG_ID,
        "date_start": start_date,
        "date_end": end_date,
    }

    # Fetch sales data (Invoices)
    invoices_data = fetch_data_from_zoho("invoices", params)
    total_sales = sum([invoice["total"] for invoice in invoices_data.get("invoices", [])])

    # Fetch expense data (Bills) for Liabilities (Accounts Payable)
    bills_data = fetch_data_from_zoho("bills", params)
    total_expenses = sum([bill["total"] for bill in bills_data.get("bills", [])])

    # Fetch payment data (Payments)
    customer_payments = fetch_data_from_zoho("customerpayments", params)
    total_customer_payments = sum([payment["amount"] for payment in customer_payments.get("customerpayments", [])])

    vendor_payments = fetch_data_from_zoho("vendorpayments", params)
    total_vendor_payments = sum([payment["amount"] for payment in vendor_payments.get("vendorpayments", [])])

    # Calculate Liabilities (Accounts Payable)
    liabilities = total_expenses - total_vendor_payments  # Using bills and vendor payments

    # Calculate balance sheet values
    assets = total_sales + total_customer_payments  # Example refinement: Add sales and customer payments for assets
    equity = assets - liabilities  # Adjust as needed

    return {
        "Assets": assets,
        "Liabilities": liabilities,
        "Equity": equity,
        "Total Sales": total_sales,
        "Total Expenses": total_expenses,
        "Customer Payments": total_customer_payments,
        "Vendor Payments": total_vendor_payments
    }

def calculate_dates_based_on_filter(selected_filter):
    today = datetime.today()

    if selected_filter == "Today":
        start_date = today.strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
    elif selected_filter == "This Week":
        start_date = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
        end_date = (today + timedelta(days=6 - today.weekday())).strftime("%Y-%m-%d")
    elif selected_filter == "This Month":
        start_date = today.replace(day=1).strftime("%Y-%m-%d")
        end_date = today.replace(day=28).strftime("%Y-%m-%d")  # Approximate end of the month
    elif selected_filter == "This Quarter":
        month = today.month
        if month in [1, 2, 3]:
            start_date = today.replace(month=1, day=1).strftime("%Y-%m-%d")
            end_date = today.replace(month=3, day=31).strftime("%Y-%m-%d")
        elif month in [4, 5, 6]:
            start_date = today.replace(month=4, day=1).strftime("%Y-%m-%d")
            end_date = today.replace(month=6, day=30).strftime("%Y-%m-%d")
        elif month in [7, 8, 9]:
            start_date = today.replace(month=7, day=1).strftime("%Y-%m-%d")
            end_date = today.replace(month=9, day=30).strftime("%Y-%m-%d")
        else:
            start_date = today.replace(month=10, day=1).strftime("%Y-%m-%d")
            end_date = today.replace(month=12, day=31).strftime("%Y-%m-%d")
    elif selected_filter == "This Year":
        start_date = today.replace(month=1, day=1).strftime("%Y-%m-%d")
        end_date = today.replace(month=12, day=31).strftime("%Y-%m-%d")
    elif selected_filter == "Yesterday":
        start_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        end_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    elif selected_filter == "Previous Week":
        start_date = (today - timedelta(weeks=1) - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
        end_date = (today - timedelta(weeks=1) + timedelta(days=6 - today.weekday())).strftime("%Y-%m-%d")
    elif selected_filter == "Previous Month":
        start_date = (today.replace(month=today.month - 1, day=1) if today.month != 1 else today.replace(year=today.year - 1, month=12, day=1)).strftime("%Y-%m-%d")
        end_date = (today.replace(month=today.month, day=1) - timedelta(days=1)).strftime("%Y-%m-%d")
    elif selected_filter == "Previous Year":
        start_date = today.replace(year=today.year - 1, month=1, day=1).strftime("%Y-%m-%d")
        end_date = today.replace(year=today.year - 1, month=12, day=31).strftime("%Y-%m-%d")
    else:  # Custom range
        start_date = st.date_input("Start Date").strftime("%Y-%m-%d")
        end_date = st.date_input("End Date").strftime("%Y-%m-%d")

    return start_date, end_date

# ——————— Streamlit App ———————
def main():
    st.set_page_config(page_title="Balance Sheet", layout="wide")
    st.title("Balance Sheet – 4 Columns")

    # Dropdown for selecting date filter
    selected_filter = st.selectbox(
        "Select a Date Range:",
        ["Today", "This Week", "This Month", "This Quarter", "This Year", "Yesterday", "Previous Week", "Previous Month", "Previous Quarter", "Previous Year", "Custom"]
    )

    # Get the corresponding start and end date
    start_date, end_date = calculate_dates_based_on_filter(selected_filter)

    # Fetch the balance sheet for the selected date range
    balance_sheet = fetch_balance_sheet_4cols(start_date, end_date)

    # Displaying the balance sheet in a readable format
    if balance_sheet.empty:
        st.error(f"Unable to fetch balance sheet for {start_date} to {end_date}. Please try again.")
    else:
        st.subheader(f"Balance Sheet from {start_date} to {end_date}")

        # Creating the balance sheet table with the proper columns
        st.dataframe(balance_sheet)

if __name__ == "__main__":
    main()
