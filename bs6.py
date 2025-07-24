import os
import time
import requests
import pandas as pd
import streamlit as st
from datetime import datetime
from dateutil.relativedelta import relativedelta  # pip install python-dateutil
from dotenv import load_dotenv

# ---------- ENV & AUTH ----------
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

# ---------- API CALL ----------
def call_bs(date_str: str) -> dict:
    print(f"Fetching Balance Sheet for: {date_str}")  # Debug: print the date for which we are fetching the data
    resp = requests.get(
        f"{API_BASE}/reports/balancesheet",
        headers={"Authorization": f"Zoho-oauthtoken {get_access_token()}"},
        params={"organization_id": ORG_ID, "date": date_str},
        timeout=60
    )
    resp.raise_for_status()
    return resp.json()

# ---------- FLATTEN ----------
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

end_date = st.date_input("End Date", datetime.today())
end_str  = end_date.strftime("%Y-%m-%d")

freq = st.selectbox("Frequency", ["None", "Weekly", "Monthly", "Quarterly", "Yearly"])
num_periods = st.selectbox("Number of Periods", [1,2,3,4])

indent_rows = st.checkbox("Indent hierarchy", True)

# Fetch current period
with st.spinner("Fetching current period..."):
    current_json = call_bs(end_str)
    current_df   = flatten_bs(current_json)
    print(f"Current Period Data: {current_df.head()}")  # Debug: print the first few rows of the current period
    if indent_rows:
        current_df["Account"] = current_df.apply(lambda r: "    "*r["Depth"] + r["Account"], axis=1)
    current_df = current_df.drop(columns=["Depth","IsGroup"])
    current_df = current_df.rename(columns={"Total":"Current"})

# Fetch previous periods (manual)
all_df = current_df.copy()
if freq != "None":
    for i in range(1, num_periods+1):
        prev_end = period_shift(end_date, freq, i)
        prev_str = prev_end.strftime("%Y-%m-%d")
        with st.spinner(f"Fetching period {i}: {prev_str}"):
            js = call_bs(prev_str)
            df_prev = flatten_bs(js)
            print(f"Previous Period {i} Data: {df_prev.head()}")  # Debug: print the first few rows of the previous period data
            if indent_rows:
                df_prev["Account"] = df_prev.apply(lambda r: "    "*r["Depth"] + r["Account"], axis=1)
            df_prev = df_prev.drop(columns=["Depth","IsGroup"])
            colname = f"Prev_{i} ({prev_str})"
            df_prev = df_prev.rename(columns={"Total": colname})
            all_df = all_df.merge(df_prev, on="Account", how="outer")

# Order columns: Account first
cols = ["Account"] + [c for c in all_df.columns if c != "Account"]
all_df = all_df[cols]

st.subheader("Balance Sheet")
st.dataframe(all_df, use_container_width=True)

# Download
csv = all_df.to_csv(index=False).encode("utf-8")
st.download_button("Download CSV", csv, file_name=f"bs_compare_{end_str}.csv", mime="text/csv")
