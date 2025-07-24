<<<<<<< HEAD


=======
>>>>>>> 00751ce23ad4f78e05d5255eac8d31ec1958d0b4
import os
import time
import requests
import pandas as pd
import streamlit as st
<<<<<<< HEAD
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv


load_dotenv()
CLIENT_ID     = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")
TOKEN_URL     = os.getenv("ZOHO_TOKEN_URL", "https://accounts.zoho.com/oauth/v2/token")
ORG_ID        = os.getenv("ZOHO_ORG_ID")
API_BASE      = "https://www.zohoapis.com/books/v3"

_token_cache = {"access_token": None, "expires_at": 0}

def _refresh_access_token():
    r = requests.post(
        TOKEN_URL,
        data={
            "refresh_token": REFRESH_TOKEN,
            "client_id":     CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type":    "refresh_token",
        },
        timeout=30
    )
    r.raise_for_status()
    j = r.json()
    _token_cache["access_token"] = j["access_token"]
    _token_cache["expires_at"]   = time.time() + j.get("expires_in", 3600) - 60
    return _token_cache["access_token"]

def get_access_token():
    if not _token_cache["access_token"] or time.time() >= _token_cache["expires_at"]:
        return _refresh_access_token()
    return _token_cache["access_token"]


def call_bs(date_str: str) -> dict:
    print(f"Fetching Balance Sheet for: {date_str}")  
    resp = requests.get(
        f"{API_BASE}/reports/balancesheet",
        headers={"Authorization": f"Zoho-oauthtoken {get_access_token()}"},
        params={"organization_id": ORG_ID, "date": date_str},
        timeout=60
    )
    resp.raise_for_status()
    return resp.json()


def flatten_bs(json_obj: dict) -> pd.DataFrame:
    sheet = json_obj.get("balance_sheet", [])
    rows = []

    def rec(node, depth):
        name = node.get("name") or node.get("total_label")
        total = float(node.get("total", 0) or 0)
        children = node.get("account_transactions", []) or []

        if name:
            rows.append({
                "Account": name,
                "Depth": depth,
                "Total": total,
                "IsGroup": bool(children)
            })
        for ch in children:
            rec(ch, depth + 1)

    for sec in sheet:
        rec(sec, 0)

    return pd.DataFrame(rows)

# ---------- PERIOD HELPERS ----------
def period_shift(end_dt: datetime, freq: str, n: int) -> datetime:
    """Return end date n periods before based on freq."""
    if freq == "Weekly":
        return end_dt - relativedelta(weeks=n)
    if freq == "Monthly":
        return end_dt - relativedelta(months=n)
    if freq == "Quarterly":
        return end_dt - relativedelta(months=3*n)
    if freq == "Yearly":
        return end_dt - relativedelta(years=n)
    return end_dt

# ---------- STREAMLIT ----------
st.set_page_config(layout="wide")
st.title("Balance Sheet – Comparison")


date_filter = st.selectbox("As Of", ["Today", "This Week", "This Month", "This Year"])
end_date = None
if date_filter == "Today":
    end_date = datetime.today()
elif date_filter == "This Week":
    end_date = datetime.today() - timedelta(days=datetime.today().weekday())
elif date_filter == "This Month":
    end_date = datetime.today().replace(day=1)
elif date_filter == "This Year":
    end_date = datetime.today().replace(month=1, day=1)

end_str = end_date.strftime("%Y-%m-%d")


freq = st.selectbox("Frequency", ["None", "Weekly", "Monthly", "Quarterly", "Yearly"])


num_periods = st.selectbox("Number of Periods", [1, 2, 3, 4])


indent_rows = st.checkbox("Indent hierarchy", True)


with st.spinner("Fetching current period..."):
    current_json = call_bs(end_str)
    current_df   = flatten_bs(current_json)
    if indent_rows:
        current_df["Account"] = current_df.apply(lambda r: "    "*r["Depth"] + r["Account"], axis=1)
    current_df = current_df.drop(columns=["Depth", "IsGroup"])
    current_df = current_df.rename(columns={"Total": "Current"})


all_df = current_df.copy()
if freq != "None":
    for i in range(1, num_periods + 1):
        prev_end = period_shift(end_date, freq, i)
        prev_str = prev_end.strftime("%Y-%m-%d")
        with st.spinner(f"Fetching period {i}: {prev_str}"):
            js = call_bs(prev_str)
            df_prev = flatten_bs(js)
            if indent_rows:
                df_prev["Account"] = df_prev.apply(lambda r: "    "*r["Depth"] + r["Account"], axis=1)
            df_prev = df_prev.drop(columns=["Depth", "IsGroup"])
            colname = f"Prev_{i} ({prev_str})"
            df_prev = df_prev.rename(columns={"Total": colname})
            all_df = all_df.merge(df_prev, on="Account", how="outer")


cols = ["Account"] + [c for c in all_df.columns if c != "Account"]
all_df = all_df[cols]


st.subheader("Balance Sheet")
st.dataframe(all_df, use_container_width=True)


csv = all_df.to_csv(index=False).encode("utf-8")
st.download_button("Download CSV", csv, file_name=f"bs_compare_{end_str}.csv", mime="text/csv")
=======
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

# Fetch Balance Sheet data
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

# Fetch Profit and Loss data
def fetch_profit_and_loss(from_date: str, to_date: str) -> pd.DataFrame:
    """
    Fetches the profit and loss data for the specified date range and formats it into a DataFrame.
    """
    resp = requests.get(
        f"{API_BASE}/reports/profitandloss",
        headers={"Authorization": f"Zoho-oauthtoken {get_access_token()}"},
        params={"organization_id": ORG_ID, "from_date": from_date, "to_date": to_date}
    )
    resp.raise_for_status()
    data = resp.json()

    records = []
    for section in data.get("profit_and_loss", []):
        account = section.get("name")
        first_total = section.get("total", 0)
        # Iterate through account transactions (nested)
        for sub_account in section.get("account_transactions", []):
            records.append({
                "Account": sub_account.get("name"),
                "First Total": sub_account.get("total", 0),
                "Sub Total": None,
                "Grand Total": None
            })
        
        records.append({
            "Account": account,
            "First Total": first_total,
            "Sub Total": None,
            "Grand Total": None
        })
        
    return pd.DataFrame(records)

# ——————— Streamlit App ———————
def main():
    st.set_page_config(page_title="Balance Sheet and Profit & Loss", layout="wide")
    st.title("Balance Sheet and Profit & Loss Reports")

    # Date input for selecting the date range for P&L report
    from_date_picker = st.date_input("Select Start Date for P&L", datetime.today(), key="from_date_picker")
    from_date = from_date_picker.strftime("%Y-%m-%d")
    to_date_picker = st.date_input("Select End Date for P&L", datetime.today(), key="to_date_picker")
    to_date = to_date_picker.strftime("%Y-%m-%d")

    # Fetch Balance Sheet data
    balance_sheet_df = fetch_balance_sheet_4cols(from_date)

    # Display the Balance Sheet data first
    if not balance_sheet_df.empty:
        st.subheader(f"Balance Sheet as of {from_date}")
        st.dataframe(balance_sheet_df, use_container_width=True)
    else:
        st.error(f"No Balance Sheet data available for the given date: {from_date}")

    # Fetch Profit and Loss data
    pnl_df = fetch_profit_and_loss(from_date, to_date)

    # Display the P&L data
    if not pnl_df.empty:
        st.subheader(f"P&L Report from {from_date} to {to_date}")
        st.dataframe(pnl_df, use_container_width=True)
    else:
        st.error(f"No data available for the given date range: {from_date} to {to_date}")
    

if __name__ == "__main__":
    main()
>>>>>>> 00751ce23ad4f78e05d5255eac8d31ec1958d0b4
