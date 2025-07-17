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
        "expires_at":   time.time() + expires_in - 60
    })
    return token

def get_access_token():
    if not _token_cache.get("access_token") or time.time() >= _token_cache["expires_at"]:
        return _refresh_access_token()
    return _token_cache["access_token"]

def fetch_balance_sheet_4cols(as_of_date: str) -> pd.DataFrame:
    """
    Returns a DataFrame with columns:
      - Account
      - First Total   (leaf nodes)
      - Sub Total     (grouping nodes except top-level)
      - Grand Total   (top-level sheet sections)
    """
    # fetch raw sheet
    resp = requests.get(
        f"{API_BASE}/reports/balancesheet",
        headers={"Authorization": f"Zoho-oauthtoken {get_access_token()}"},
        params={"organization_id": ORG_ID, "date": as_of_date}
    )
    resp.raise_for_status()
    sheet = resp.json().get("balance_sheet", [])

    # extract "Other Current Assets" from under "Assets"->"Current Assets"
    # and insert it as its own top‑level section right after "Assets"
    other_current = None
    for sec in sheet:
        if sec.get("name") == "Assets":
            for child in sec.get("account_transactions", []):
                if child.get("name") == "Other Current Assets":
                    other_current = child
                    sec["account_transactions"].remove(child)
                    break
            break
    if other_current:
        idx = next(i for i,sec in enumerate(sheet) if sec.get("name")=="Assets")
        sheet.insert(idx+1, other_current)

    # recurse and classify
    records = []
    def recurse(node: dict, depth: int):
        name     = node.get("name") or node.get("total_label")
        total    = float(node.get("total", 0))
        children = node.get("account_transactions", [])

        if name:
            row = {
                "Account":     name,
                "First Total": None,
                "Sub Total":   None,
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

    # kick off each top‑level section
    for section in sheet:
        recurse(section, 0)

    return pd.DataFrame(records)

# ——————— Streamlit App ———————
def main():
    st.set_page_config(page_title="Balance Sheet", layout="wide")
    st.title("Balance Sheet – 4 Columns")

    selected_date = st.date_input("As of date", datetime.today())
    as_of = selected_date.strftime("%Y-%m-%d")

    df = fetch_balance_sheet_4cols(as_of)
    st.subheader(f"Balance Sheet as of {as_of}")
    st.dataframe(
        df,
        column_config={
            "Account":     st.column_config.TextColumn("Account"),
            "First Total": st.column_config.NumberColumn("First Total"),
            "Sub Total":   st.column_config.NumberColumn("Sub Total"),
            "Grand Total": st.column_config.NumberColumn("Grand Total"),
        },
        use_container_width=True
    )

if __name__ == "__main__":
    main()
