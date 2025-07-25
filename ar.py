import os
import time
import requests
import pandas as pd
import streamlit as st

from datetime import datetime
from dotenv import load_dotenv

# ————— Load configuration from .env —————
load_dotenv()
CLIENT_ID     = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")
TOKEN_URL     = os.getenv("ZOHO_TOKEN_URL", "https://accounts.zoho.com/oauth/v2/token")
ORG_ID        = os.getenv("ZOHO_ORG_ID")
API_BASE      = "https://www.zohoapis.com/books/v3"

# ————— OAuth token caching & refresh —————
_token_cache = {"access_token": None, "expires_at": 0}

def _refresh_token():
    resp = requests.post(
        TOKEN_URL,
        data={
            "refresh_token": REFRESH_TOKEN,
            "client_id":     CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type":    "refresh_token"
        },
        timeout=30
    )
    resp.raise_for_status()
    data = resp.json()
    token = data["access_token"]
    expires_in = data.get("expires_in", 3600)
    _token_cache["access_token"] = token
    _token_cache["expires_at"]   = time.time() + expires_in - 60
    return token

def get_token():
    if not _token_cache["access_token"] or time.time() >= _token_cache["expires_at"]:
        return _refresh_token()
    return _token_cache["access_token"]

# ————— Fetch open invoices for AR —————
def fetch_open_invoices():
    all_inv = []
    page = 1
    while True:
        resp = requests.get(
            f"{API_BASE}/invoices",
            headers={"Authorization": f"Zoho-oauthtoken {get_token()}"},
            params={
                "organization_id": ORG_ID,
                "filter_by":       "Status.All",
                "per_page":        200,
                "page":            page
            },
            timeout=30
        )
        resp.raise_for_status()
        batch = resp.json().get("invoices", [])
        if not batch:
            break
        all_inv.extend(batch)
        page += 1

    df = pd.DataFrame(all_inv)
    df["balance"] = df["balance"].astype(float)
    df["status"]  = df["status"].str.lower()
    # keep only outstanding invoices
    df = df[
        (~df["status"].isin(["draft", "void", "paid"]))
        & (df["balance"] > 0)
    ]
    return df

# ————— Fetch open bills for AP —————
def fetch_open_bills():
    all_bills = []
    page = 1
    while True:
        resp = requests.get(
            f"{API_BASE}/bills",
            headers={"Authorization": f"Zoho-oauthtoken {get_token()}"},
            params={
                "organization_id": ORG_ID,
                "filter_by":       "Status.All",
                "per_page":        200,
                "page":            page
            },
            timeout=30
        )
        resp.raise_for_status()
        batch = resp.json().get("bills", [])
        if not batch:
            break
        all_bills.extend(batch)
        page += 1

    df = pd.DataFrame(all_bills)
    df["balance"] = df["balance"].astype(float)
    df["status"]  = df["status"].str.lower()
    # keep only outstanding bills
    df = df[
        (~df["status"].isin(["draft", "void", "paid"]))
        & (df["balance"] > 0)
    ]
    return df

# ————— Compute aging buckets —————
def compute_aging(df: pd.DataFrame, as_of: pd.Timestamp) -> pd.DataFrame:
    # 1) parse due_date
    df["due_date"]     = pd.to_datetime(df["due_date"])

    # 2) **drop future‐due** documents
    df = df[df["due_date"] <= as_of]

    # 3) compute days overdue
    df["days_overdue"] = (as_of - df["due_date"]).dt.days

    # 4) bucket exactly as before
    bins   = [-1, 0, 15, 30, 45, float("inf")]
    labels = ["Current","1-15 days","16-30 days","31-45 days",">45 days"]
    df["Bucket"] = pd.cut(df["days_overdue"], bins=bins, labels=labels)

    # 5) FCY balance
    if "exchange_rate" in df.columns:
        df["fcy_balance"] = df["balance"] / df["exchange_rate"]
    else:
        df["fcy_balance"] = df["balance"]

    return df


# ————— Streamlit UI —————
st.set_page_config(page_title="AR & AP Aging Summary", layout="wide")
st.title("Accounts Receivable & Payable Aging Summary")

# As-of date selector
asof_date = st.date_input("As of Date", datetime.today())
asof_ts   = pd.to_datetime(asof_date)

# --- AR Aging ---
with st.spinner("Loading open invoices..."):
    ar_invoices = fetch_open_invoices()
ar_aging = compute_aging(ar_invoices, asof_ts)

# Pivot AR by customer
ar_pivot_bal = ar_aging.pivot_table(
    index="customer_name",
    columns="Bucket",
    values="balance",
    aggfunc="sum",
    fill_value=0
)
ar_pivot_fcy = ar_aging.pivot_table(
    index="customer_name",
    columns="Bucket",
    values="fcy_balance",
    aggfunc="sum",
    fill_value=0
)

# enforce bucket order
buckets = ["Current","1-15 days","16-30 days","31-45 days",">45 days"]
ar_pivot_bal = ar_pivot_bal.reindex(columns=buckets, fill_value=0)
ar_pivot_fcy = ar_pivot_fcy.reindex(columns=buckets, fill_value=0)

# add totals
ar_pivot_bal["Total"]       = ar_pivot_bal.sum(axis=1).round(2)
ar_pivot_fcy["Total (FCY)"] = ar_pivot_fcy.sum(axis=1).round(2)

# combine and rename
ar_summary = ar_pivot_bal.copy()
ar_summary.insert(0, "Total (FCY)", ar_pivot_fcy["Total (FCY)"])
ar_summary = ar_summary.reset_index().rename(columns={"customer_name": "Customer Name"})

# display AR
st.subheader(f"AR Aging Summary as of {asof_date.strftime('%d/%m/%Y')}")
st.dataframe(ar_summary, use_container_width=True)
ar_csv = ar_summary.to_csv(index=False).encode("utf-8")
st.download_button("Download AR Aging CSV", ar_csv, file_name=f"ar_aging_{asof_date}.csv", mime="text/csv")

# --- AP Aging ---
with st.spinner("Loading open bills..."):
    ap_bills = fetch_open_bills()
ap_aging = compute_aging(ap_bills, asof_ts)

# Pivot AP by vendor
ap_pivot_bal = ap_aging.pivot_table(
    index="vendor_name",
    columns="Bucket",
    values="balance",
    aggfunc="sum",
    fill_value=0
)
ap_pivot_fcy = ap_aging.pivot_table(
    index="vendor_name",
    columns="Bucket",
    values="fcy_balance",
    aggfunc="sum",
    fill_value=0
)

# enforce bucket order and totals
ap_pivot_bal = ap_pivot_bal.reindex(columns=buckets, fill_value=0)
ap_pivot_bal["Total"]       = ap_pivot_bal.sum(axis=1).round(2)
ap_pivot_fcy = ap_pivot_fcy.reindex(columns=buckets, fill_value=0)
ap_pivot_fcy["Total (FCY)"] = ap_pivot_fcy.sum(axis=1).round(2)

ap_summary = ap_pivot_bal.copy()
ap_summary.insert(0, "Total (FCY)", ap_pivot_fcy["Total (FCY)"])
ap_summary = ap_summary.reset_index().rename(columns={"vendor_name": "Vendor Name"})

# display AP
st.subheader(f"AP Aging Summary as of {asof_date.strftime('%d/%m/%Y')}")
st.dataframe(ap_summary, use_container_width=True)
ap_csv = ap_summary.to_csv(index=False).encode("utf-8")
st.download_button("Download AP Aging CSV", ap_csv, file_name=f"ap_aging_{asof_date}.csv", mime="text/csv")
