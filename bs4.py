import os
import time
import requests
import pandas as pd
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv

# ——————— Load environment variables ———————
load_dotenv()
CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")
ORG_ID = os.getenv("ZOHO_ORG_ID")  # Fetch Organization ID from .env
TOKEN_URL = os.getenv("ZOHO_TOKEN_URL", "https://accounts.zoho.com/oauth/v2/token")
API_BASE = "https://www.zohoapis.com/books/v3"  # Correct API base URL

_token_cache = {"token": None, "expires": 0}

def get_access_token():
    if not _token_cache["token"] or time.time() >= _token_cache["expires"]:
        # Refresh token request
        r = requests.post(
            TOKEN_URL,
            data={
                "refresh_token": REFRESH_TOKEN,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "grant_type": "refresh_token",
            }
        )
        r.raise_for_status()  # Check if the request was successful
        j = r.json()
        _token_cache["token"] = j["access_token"]
        _token_cache["expires"] = time.time() + j.get("expires_in", 3600) - 60
    return _token_cache["token"]

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

def calculate_balance_sheet(start_date, end_date=None):
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

# ——————— Streamlit App ———————
def main():
    st.set_page_config(page_title="Balance Sheet", layout="wide")
    st.title("Balance Sheet – 4 Columns")

    # Date input from user for selecting date
    selected_date = st.date_input("Select Date for Balance Sheet", datetime.today())
    as_of = selected_date.strftime("%Y-%m-%d")

    # Fetch the balance sheet for the selected date
    balance_sheet = calculate_balance_sheet(as_of)

    # Displaying the balance sheet in a readable format
    if balance_sheet:
        st.subheader(f"Balance Sheet as of {as_of}")
        
        # Creating the balance sheet table with the proper columns
        data = [
            {"Account": "Assets", "First Total": balance_sheet['Assets'], "Sub Total": None, "Grand Total": balance_sheet['Assets']},
            {"Account": "Liabilities", "First Total": balance_sheet['Liabilities'], "Sub Total": None, "Grand Total": balance_sheet['Liabilities']},
            {"Account": "Equity", "First Total": balance_sheet['Equity'], "Sub Total": None, "Grand Total": balance_sheet['Equity']},
            {"Account": "Total Sales", "First Total": balance_sheet['Total Sales'], "Sub Total": None, "Grand Total": balance_sheet['Total Sales']},
            {"Account": "Total Expenses", "First Total": balance_sheet['Total Expenses'], "Sub Total": None, "Grand Total": balance_sheet['Total Expenses']},
            {"Account": "Customer Payments", "First Total": balance_sheet['Customer Payments'], "Sub Total": None, "Grand Total": balance_sheet['Customer Payments']},
            {"Account": "Vendor Payments", "First Total": balance_sheet['Vendor Payments'], "Sub Total": None, "Grand Total": balance_sheet['Vendor Payments']},
        ]

        # Create a DataFrame
        df = pd.DataFrame(data)

        st.dataframe(df)
    else:
        st.error(f"Unable to fetch balance sheet for {as_of}. Please try again.")

if __name__ == "__main__":
    main()
