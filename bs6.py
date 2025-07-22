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

def fetch_balance_sheet_4cols(as_of_date: str, compare_period: str = None) -> pd.DataFrame:
    """
    Fetches Balance Sheet and includes comparison if needed.
    """
    params = {
        "organization_id": ORG_ID,
        "date": as_of_date,
    }
    if compare_period:
        params["compare_period"] = compare_period  # Add the compare period if selected
    
    resp = requests.get(
        f"{API_BASE}/reports/balancesheet",
        headers={"Authorization": f"Zoho-oauthtoken {get_access_token()}"},
        params=params
    )
    resp.raise_for_status()
    sheet = resp.json().get("balance_sheet", [])
    records = []
    def recurse(node: dict, depth: int):
        name = node.get("name") or node.get("total_label")
        total = float(node.get("total", 0))
        children = node.get("account_transactions", [])
        if name:
            row = {
                "Account": name,
                "First Total": None,
                "Sub Total": None,
                "Grand Total": None
            }
            if depth == 0:
                row["Grand Total"] = total
            elif children:
                row["Sub Total"] = total
            else:
                row["First Total"] = total
            records.append(row)
        for child in children:
            recurse(child, depth + 1)

    # Process top-level sections of the balance sheet
    for section in sheet:
        recurse(section, 0)

    return pd.DataFrame(records)

# ——————— Streamlit App ———————
def main():
    st.set_page_config(page_title="Balance Sheet Comparison", layout="wide")
    st.title("Balance Sheet – Compare Periods")

    # Date input for selecting the date range
    selected_date = st.date_input("Select Date for Balance Sheet", datetime.today(), key="selected_date")
    as_of = selected_date.strftime("%Y-%m-%d")

    # Add comparison options
    compare_options = ["None", "Previous Period", "Previous Month", "Previous Quarter", "Previous Year"]
    comparison = st.selectbox("Compare With", compare_options, index=0)

    if comparison == "Previous Period":
        compare_period = "PreviousPeriod"
    elif comparison == "Previous Month":
        compare_period = "PreviousMonth"
    elif comparison == "Previous Quarter":
        compare_period = "PreviousQuarter"
    elif comparison == "Previous Year":
        compare_period = "PreviousYear"
    else:
        compare_period = None

    # Fetch and display Balance Sheet with or without comparison
    balance_sheet_df = fetch_balance_sheet_4cols(as_of, compare_period)
    
    if not balance_sheet_df.empty:
        st.subheader(f"Balance Sheet as of {as_of}")
        st.dataframe(balance_sheet_df, use_container_width=True)
    else:
        st.error(f"No Balance Sheet data available for the given date: {as_of}")

if __name__ == "__main__":
    main()
