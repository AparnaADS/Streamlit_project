import os
import time
import requests
import pandas as pd
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv

# ——————— Load environment variables ———————
load_dotenv()
CLIENT_ID     = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")
TOKEN_URL     = os.getenv("ZOHO_TOKEN_URL", "https://accounts.zoho.com/oauth/v2/token")
ORG_ID        = os.getenv("ZOHO_ORG_ID")
API_BASE      = "https://www.zohoapis.com/books/v3"
_token_cache  = {"access_token": os.getenv("ZOHO_ACCESS_TOKEN"), "expires_at": 0}

# ——————— OAuth Token Management ———————
def _refresh_access_token():
    resp = requests.post(
        TOKEN_URL,
        data={
            "refresh_token": REFRESH_TOKEN,
            "client_id":     CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type":    "refresh_token",
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

# ——————— Fetch & Flatten Balance Sheet ———————
def fetch_flat_balance_sheet(as_of_date: str) -> pd.DataFrame:
    """
    Fetches the entire Balance Sheet and flattens it into a DataFrame
    with columns: Account, Balance.
    """
    resp = requests.get(
        f"{API_BASE}/reports/balancesheet",
        headers={"Authorization": f"Zoho-oauthtoken {get_access_token()}"},
        params={"organization_id": ORG_ID, "date": as_of_date}
    )
    resp.raise_for_status()
    sheet = resp.json().get("balance_sheet", [])

    records = []
    def recurse(node: dict):
        name  = node.get("name") or node.get("total_label")
        total = float(node.get("total", 0))
        if name:
            records.append({"Account": name, "Balance": total})
        for child in node.get("account_transactions", []):
            recurse(child)

    for section in sheet:
        recurse(section)

    return pd.DataFrame.from_records(records)

# ——————— Streamlit App ———————
def main():
    st.set_page_config(page_title="Balance Sheet", layout="wide")
    st.title("Flat Balance Sheet")

    # date picker for user
    selected_date = st.date_input("As of date", datetime.today())
    as_of = selected_date.strftime("%Y-%m-%d")

    flat_bs = fetch_flat_balance_sheet(as_of)

    st.subheader(f"Balance Sheet as of {as_of}")
    st.dataframe(
        flat_bs,
        use_container_width=True
    )

if __name__ == "__main__":
    main()
