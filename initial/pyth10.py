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
    _token_cache["access_token"] = token
    _token_cache["expires_at"] = time.time() + expires_in - 60
    return token

def get_access_token():
    if not _token_cache["access_token"] or time.time() >= _token_cache["expires_at"]:
        return _refresh_access_token()
    return _token_cache["access_token"]

# --- Fetch Functions ---
def fetch_all_bills(status_filter="all"):
    headers = {"Authorization": f"Zoho-oauthtoken {get_access_token()}"}
    bills = []
    page, per_page = 1, 200
    while True:
        params = {"status": status_filter, "organization_id": ORG_ID, "page": page, "per_page": per_page}
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

def fetch_payments_for_bills(bill_ids):
    headers = {"Authorization": f"Zoho-oauthtoken {get_access_token()}"}
    rows = []
    for bill_id in bill_ids:
        resp = requests.get(f"{API_BASE}/vendorpayments", headers=headers, params={"organization_id": ORG_ID, "bill_id": bill_id})
        resp.raise_for_status()
        for p in resp.json().get("vendorpayments", []):
            rows.append({"bill_id": bill_id, "paid_amount": float(p.get("amount", 0))})
    return pd.DataFrame(rows)

def fetch_credits_for_bills(bill_ids):
    headers = {"Authorization": f"Zoho-oauthtoken {get_access_token()}"}
    rows = []
    resp = requests.get(f"{API_BASE}/vendorcredits", headers=headers, params={"organization_id": ORG_ID})
    resp.raise_for_status()
    for vc in resp.json().get("vendorcredits", []):
        vc_id = vc["vendor_credit_id"]
        r2 = requests.get(f"{API_BASE}/vendorcredits/{vc_id}/bills", headers=headers, params={"organization_id": ORG_ID})
        r2.raise_for_status()
        for b in r2.json().get("bills", []):
            if b["bill_id"] in bill_ids:
                rows.append({"bill_id": b["bill_id"], "credit_amount": float(b.get("credit_amount", 0))})
    return pd.DataFrame(rows)

def fetch_invoices(start, end):
    headers = {"Authorization": f"Zoho-oauthtoken {get_access_token()}"}
    resp = requests.get(f"{API_BASE}/invoices", headers=headers, params={"organization_id": ORG_ID, "date_start": start, "date_end": end, "status": "paid"})
    resp.raise_for_status()
    return resp.json().get("invoices", [])

def fetch_creditnotes(start, end):
    headers = {"Authorization": f"Zoho-oauthtoken {get_access_token()}"}
    resp = requests.get(f"{API_BASE}/creditnotes", headers=headers, params={"organization_id": ORG_ID, "date_start": start, "date_end": end})
    resp.raise_for_status()
    return resp.json().get("creditnotes", [])

def fetch_customer_payments(start, end):
    headers = {"Authorization": f"Zoho-oauthtoken {get_access_token()}"}
    resp = requests.get(f"{API_BASE}/customerpayments", headers=headers, params={"organization_id": ORG_ID, "date_start": start, "date_end": end})
    resp.raise_for_status()
    return resp.json().get("customerpayments", [])

def fetch_vendor_payments(start, end):
    headers = {"Authorization": f"Zoho-oauthtoken {get_access_token()}"}
    resp = requests.get(f"{API_BASE}/vendorpayments", headers=headers, params={"organization_id": ORG_ID, "date_start": start, "date_end": end})
    resp.raise_for_status()
    return resp.json().get("vendorpayments", [])

def fetch_bank_accounts():
    headers = {"Authorization": f"Zoho-oauthtoken {get_access_token()}"}
    resp = requests.get(f"{API_BASE}/chartofaccounts", headers=headers, params={"organization_id": ORG_ID})
    resp.raise_for_status()
    return [a for a in resp.json().get("chartofaccounts", []) if a.get("group","") == "Bank"]

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

@st.cache_data
def load_data():
    today = datetime.today()
    start = today.replace(day=1).strftime("%Y-%m-%d")
    end   = today.strftime("%Y-%m-%d")

    # AP Data
    bills = fetch_all_bills()
    df = bills_to_dataframe(bills)
    ids = df["bill_id"].tolist()
    df_pay = fetch_payments_for_bills(ids)
    df_cred = fetch_credits_for_bills(ids)
    paid_sum = df_pay.groupby("bill_id")["paid_amount"].sum() if not df_pay.empty else pd.Series(0, index=ids)
    credit_sum = df_cred.groupby("bill_id")["credit_amount"].sum() if not df_cred.empty else pd.Series(0, index=ids)
    df = df.set_index("bill_id").assign(total_paid=paid_sum, total_credit=credit_sum).fillna(0).reset_index()
    df["amount_due"] = df["total"] - df["total_paid"] - df["total_credit"]
    df["days_to_due"] = (df["due_date"] - today).dt.days
    df["aging_bucket"] = df["days_to_due"].apply(assign_aging_bucket)

    # P&L Metrics
    invs = fetch_invoices(start, end)
    revenue = sum(float(i.get("total", 0)) for i in invs)
    crs = fetch_creditnotes(start, end)
    returns = sum(float(c.get("total", 0)) for c in crs)
    expenses = df["total"].sum()
    accrual_pl = revenue - returns - expenses
    cust_pmts = fetch_customer_payments(start, end)
    vend_pmts = fetch_vendor_payments(start, end)
    cash_in = sum(float(c.get("amount", 0)) for c in cust_pmts)
    cash_out = sum(float(v.get("amount", 0)) for v in vend_pmts)
    cash_pl = cash_in - cash_out
    banks = fetch_bank_accounts()
    bank_balance = sum(float(b.get("current_balance", 0)) for b in banks)
    open_payables = df["amount_due"].sum()
    free_cash = bank_balance - open_payables

    summary = df.groupby("aging_bucket").agg(total_due=("amount_due","sum"),count=("bill_id","count")).reset_index()

    # Coverage Table with Amounts
    coverage = pd.DataFrame([
        {"Category": "Net Sales",      "Amount": revenue - returns,       "Includes": "Paid Invoices – Credit Notes"},
        {"Category": "COGS/Expenses",  "Amount": expenses,                "Includes": "Total Bills/Expenses"},
        {"Category": "Accrual P&L",    "Amount": accrual_pl,              "Includes": "Net Sales – COGS/Expenses"},
        {"Category": "Cash Inflows",   "Amount": cash_in,                 "Includes": "Customer Payments"},
        {"Category": "Cash Outflows",  "Amount": cash_out,                "Includes": "Vendor Payments"},
        {"Category": "Cash P&L",       "Amount": cash_pl,                 "Includes": "Cash Inflows – Cash Outflows"},
        {"Category": "Bank Balance",   "Amount": bank_balance,            "Includes": "All Bank Account Balances"},
        {"Category": "Free Cash",      "Amount": free_cash,               "Includes": "Bank Balance – Open Payables"},
    ])

    return {"df": df, "summary": summary, "accrual_pl": accrual_pl, "cash_pl": cash_pl,
            "bank_balance": bank_balance, "free_cash": free_cash, "coverage": coverage}


def main():
    st.title("Accounts Payable & P&L Dashboard")
    data = load_data()
    df = data["df"]

    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Accrual P&L",    f"{data['accrual_pl']:,.2f}")
    col2.metric("Cash P&L",       f"{data['cash_pl']:,.2f}")
    col3.metric("Bank Balance",   f"{data['bank_balance']:,.2f}")
    col4.metric("Free Cash",      f"{data['free_cash']:,.2f}")

    # P&L Coverage Table
    st.subheader("P&L Coverage Details")
    st.table(data["coverage"])

    # Filters
    st.sidebar.header("Filters")
    sel_vendor = st.sidebar.multiselect("Vendor", options=df["vendor_name"].unique())
    sel_status = st.sidebar.multiselect("Status", options=df["status"].unique())
    if sel_vendor:
        df = df[df["vendor_name"].isin(sel_vendor)]
    if sel_status:
        df = df[df["status"].isin(sel_status)]

    # Detailed Bills
    st.subheader("Detailed Bills")
    st.dataframe(df[["bill_id","vendor_name","due_date","total","total_paid","total_credit","amount_due","aging_bucket"]], use_container_width=True)

    # Aging Summary
    st.subheader("Aging Summary")
    st.bar_chart(data["summary"].set_index("aging_bucket")["total_due"])
    st.table(data["summary"])

if __name__ == "__main__":
    main()
