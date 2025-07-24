import os
import time
import requests
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Load environment variables
dotenv_path = os.path.join(os.getcwd(), '.env')
load_dotenv(dotenv_path)

# --- Token Management Module ---
CLIENT_ID     = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")
TOKEN_URL     = os.getenv("ZOHO_TOKEN_URL", "https://accounts.zoho.com/oauth/v2/token")
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
    _token_cache["access_token"] = token
    _token_cache["expires_at"] = time.time() + expires_in - 60
    return token

def get_access_token():
    if not _token_cache["access_token"] or time.time() >= _token_cache["expires_at"]:
        return _refresh_access_token()
    return _token_cache["access_token"]

# --- Zoho API Config ---
ORG_ID   = os.getenv("ZOHO_ORG_ID")
API_BASE = "https://www.zohoapis.com/books/v3"

# --- Fetch & Transform Functions ---
def fetch_all_bills(status_filter="all"):
    headers = {"Authorization": f"Zoho-oauthtoken {get_access_token()}"}
    bills = []
    page, per_page = 1, 200
    while True:
        params = {
            "status":          status_filter,
            "organization_id": ORG_ID,
            "page":            page,
            "per_page":        per_page
        }
        resp = requests.get(f"{API_BASE}/bills", headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json().get("bills", [])
        if not data:
            break
        bills.extend(data)
        if len(data) < per_page:
            break
        page += 1
    return bills

def bills_to_dataframe(bills):
    rows = []
    for b in bills:
        rows.append({
            "bill_id":     b["bill_id"],
            "vendor_name": b.get("vendor_name", ""),
            "due_date":    pd.to_datetime(b.get("due_date")),
            "total":       float(b.get("total", 0)),
            "status":      b.get("status", ""),
        })
    return pd.DataFrame(rows)

def fetch_payments(bill_ids):
    headers = {"Authorization": f"Zoho-oauthtoken {get_access_token()}"}
    rows = []
    for bill_id in bill_ids:
        resp = requests.get(
            f"{API_BASE}/vendorpayments",
            headers=headers,
            params={"organization_id": ORG_ID, "bill_id": bill_id}
        )
        resp.raise_for_status()
        for p in resp.json().get("vendorpayments", []):
            rows.append({
                "bill_id":     bill_id,
                "paid_amount": float(p.get("amount", 0))
            })
    return pd.DataFrame(rows)

def fetch_credits(bill_ids):
    headers = {"Authorization": f"Zoho-oauthtoken {get_access_token()}"}
    rows = []
    # 1) list all vendor credits
    resp = requests.get(
        f"{API_BASE}/vendorcredits",
        headers=headers,
        params={"organization_id": ORG_ID}
    )
    resp.raise_for_status()
    for vc in resp.json().get("vendorcredits", []):
        vc_id = vc["vendor_credit_id"]
        # 2) list bills credited by this vendor credit
        r2 = requests.get(
            f"{API_BASE}/vendorcredits/{vc_id}/bills",
            headers=headers,
            params={"organization_id": ORG_ID}
        )
        r2.raise_for_status()
        for b in r2.json().get("bills", []):
            if b["bill_id"] in bill_ids:
                rows.append({
                    "bill_id":       b["bill_id"],
                    "credit_amount": float(b.get("credit_amount", 0))
                })
    return pd.DataFrame(rows)

# --- Aging Bucket Helper ---
def assign_aging_bucket(days):
    if days < 0:
        return "Overdue"
    if days <= 30:
        return "0–30 days"
    if days <= 60:
        return "31–60 days"
    if days <= 90:
        return "61–90 days"
    return ">90 days"

# --- Data Loading with Caching ---
@st.cache_data
def load_data():
    # fetch bills
    bills = fetch_all_bills()
    df = bills_to_dataframe(bills)
    ids = df["bill_id"].tolist()

    # fetch enrichments
    df_pay = fetch_payments(ids)
    df_cred = fetch_credits(ids)

    # sum payments/credits
    if df_pay.empty:
        paid_sum = pd.Series(0, index=ids, name="paid_amount")
    else:
        paid_sum = df_pay.groupby("bill_id")["paid_amount"].sum()

    if df_cred.empty:
        credit_sum = pd.Series(0, index=ids, name="credit_amount")
    else:
        credit_sum = df_cred.groupby("bill_id")["credit_amount"].sum()

    # merge back
    df = df.set_index("bill_id")
    df["total_paid"]   = paid_sum
    df["total_credit"] = credit_sum
    df = df.fillna(0).reset_index()
    df["amount_due"]   = df["total"] - df["total_paid"] - df["total_credit"]

    # aging
    today = pd.Timestamp.today()
    df["days_to_due"]   = (df["due_date"] - today).dt.days
    df["aging_bucket"]  = df["days_to_due"].apply(assign_aging_bucket)
    return df

# --- Streamlit App ---
def main():
    st.title("Accounts Payable Dashboard")
    df = load_data()

    # sidebar filters
    st.sidebar.header("Filters")
    sel_vendor = st.sidebar.multiselect("Vendor", options=df["vendor_name"].unique())
    sel_status = st.sidebar.multiselect("Status", options=df["status"].unique())

    if sel_vendor:
        df = df[df["vendor_name"].isin(sel_vendor)]
    if sel_status:
        df = df[df["status"].isin(sel_status)]

    # detailed table
    st.subheader("Detailed Bills")
    st.dataframe(
        df[[
            "bill_id","vendor_name","due_date","total",
            "total_paid","total_credit","amount_due","aging_bucket"
        ]],
        use_container_width=True
    )

    # aging summary
    summary = (
        df.groupby("aging_bucket")
          .agg(total_due=("amount_due","sum"), count=("bill_id","count"))
          .reset_index()
    )
    st.subheader("Aging Summary")
    st.bar_chart(summary.set_index("aging_bucket")["total_due"])
    st.table(summary)

if __name__ == "__main__":
    main()
