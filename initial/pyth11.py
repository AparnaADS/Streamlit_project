import os
import time
import requests
import pandas as pd
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
CLIENT_ID     = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")
TOKEN_URL     = os.getenv("ZOHO_TOKEN_URL", "https://accounts.zoho.com/oauth/v2/token")
_token_cache  = {"access_token": os.getenv("ZOHO_ACCESS_TOKEN"), "expires_at": 0}
ORG_ID        = os.getenv("ZOHO_ORG_ID")
API_BASE      = "https://www.zohoapis.com/books/v3"

# --- OAuth Token Management ---
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
    _token_cache.update({"access_token": token, "expires_at": time.time()+expires_in-60})
    return token

def get_access_token():
    if not _token_cache.get("access_token") or time.time() >= _token_cache.get("expires_at",0):
        return _refresh_access_token()
    return _token_cache["access_token"]

# --- Fetch Helpers ---
def fetch_paginated(endpoint, params):
    headers = {"Authorization": f"Zoho-oauthtoken {get_access_token()}"}
    items = []
    page, per_page = 1, 200
    while True:
        p = params.copy()
        p.update({"page": page, "per_page": per_page})
        resp = requests.get(f"{API_BASE}/{endpoint}", headers=headers, params=p)
        resp.raise_for_status()
        batch = resp.json().get(endpoint, []) if isinstance(resp.json().get(endpoint), list) else resp.json().get(endpoint + "s", [])
        if not batch:
            break
        items.extend(batch)
        if len(batch) < per_page:
            break
        page += 1
    return items

# Specific fetchers
fetch_all_bills = lambda: fetch_paginated("bills", {"status": "all", "organization_id": ORG_ID})
fetch_expenses  = lambda start,end: fetch_paginated("expenses", {"organization_id": ORG_ID, "date_start": start, "date_end": end})
fetch_invoices = lambda start,end: fetch_paginated("invoices", {"organization_id": ORG_ID, "date_start": start, "date_end": end, "status": "paid"})
fetch_creditnotes = lambda start,end: fetch_paginated("creditnotes", {"organization_id": ORG_ID, "date_start": start, "date_end": end})
fetch_cust_pmts = lambda start,end: fetch_paginated("customerpayments", {"organization_id": ORG_ID, "date_start": start, "date_end": end})
fetch_vend_pmts = lambda start,end: fetch_paginated("vendorpayments", {"organization_id": ORG_ID, "date_start": start, "date_end": end})
fetch_bank_accounts = lambda: [a for a in requests.get(
    f"{API_BASE}/chartofaccounts", headers={"Authorization": f"Zoho-oauthtoken {get_access_token()}"},
    params={"organization_id": ORG_ID}
).json().get("chartofaccounts", []) if a.get("group","")=="Bank"]

# Aging bucket
assign_bucket = lambda d: "Overdue" if d<0 else "0–30 days" if d<=30 else "31–60 days" if d<=60 else "61–90 days" if d<=90 else ">90 days"

@st.cache_data
def load_data():
    today = datetime.today()
    start = "2025-06-01"
    end = today.strftime("%Y-%m-%d")

    # 1) AP Aging data
    bills = pd.DataFrame(fetch_all_bills())
    bills_df = bills.assign(
        due_date=lambda df: pd.to_datetime(df["due_date"]),
        total=lambda df: df["total"].astype(float)
    )
    bills_df["amount_due"] = bills_df["balance"].astype(float)
    bills_df["days_to_due"] = (bills_df["due_date"] - today).dt.days
    bills_df["aging_bucket"] = bills_df["days_to_due"].apply(assign_bucket)

    # 2) P&L accrual: sales & returns
    invs = fetch_invoices(start, end)
    sales_total = sum(float(i["total"]) for i in invs)
    crs = fetch_creditnotes(start, end)
    returns_total = sum(float(c["total"]) for c in crs)

    # 3) COGS from bills
    cogs_total = bills_df["total"].sum()

    # 4) Operating expenses
    exps = fetch_expenses(start, end)
    opex_total = sum(float(e.get("amount", e.get("total",0))) for e in exps)

    accrual_pl = sales_total - returns_total - cogs_total - opex_total

    # 5) Cash P&L
    cash_in  = sum(float(c.get("amount")) for c in fetch_cust_pmts(start,end))
    cash_out = sum(float(v.get("amount")) for v in fetch_vend_pmts(start,end))
    cash_pl = cash_in - cash_out

    # 6) Bank balance & free cash
    bank_balance = sum(float(b.get("current_balance",0)) for b in fetch_bank_accounts())
    free_cash = bank_balance - bills_df["amount_due"].sum()

    # 7) Coverage breakdown
    coverage = pd.DataFrame([
        {"Category":"Sales (Accrual)", "Amount":sales_total,   "Notes":"Paid Invoices"},
        {"Category":"Returns",          "Amount":returns_total,"Notes":"Credit Notes"},
        {"Category":"COGS",             "Amount":cogs_total,   "Notes":"All Bills"},
        {"Category":"Operating Exp.",   "Amount":opex_total,   "Notes":"Expense Transactions"},
        {"Category":"Accrual P&L",      "Amount":accrual_pl,    "Notes":"Sales - Returns - COGS - Opex"},
        {"Category":"Cash Inflows",     "Amount":cash_in,       "Notes":"Customer Payments"},
        {"Category":"Cash Outflows",    "Amount":cash_out,      "Notes":"Vendor Payments"},
        {"Category":"Cash P&L",         "Amount":cash_pl,       "Notes":"Inflows - Outflows"},
        {"Category":"Bank Balance",     "Amount":bank_balance,  "Notes":"Sum of Bank Accounts"},
        {"Category":"Free Cash",        "Amount":free_cash,     "Notes":"Bank Balance - Open Payables"},
    ])

    return bills_df, coverage

# --- Streamlit App ---
def main():
    st.title("Zoho Books P&L & AP Dashboard")
    bills_df, coverage = load_data()

    # Show coverage table
    st.subheader("P&L Coverage")
    st.table(coverage)

    # Show AP aging
    st.subheader("Accounts Payable Aging")
    st.dataframe(bills_df[["bill_id","vendor_name","due_date","total","amount_due","aging_bucket"]])

if __name__ == "__main__":
    main()
