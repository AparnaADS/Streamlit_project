import os
import time
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# --- Token Management Module ---
CLIENT_ID     = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")
TOKEN_URL     = os.getenv("ZOHO_TOKEN_URL", "https://accounts.zoho.com/oauth/v2/token")

_token_cache = {"access_token": os.getenv("ZOHO_ACCESS_TOKEN"), "expires_at": 0}

def _refresh_access_token():
    resp = requests.post(TOKEN_URL, data={
        "refresh_token": REFRESH_TOKEN,
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type":    "refresh_token",
    })
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

# --- Fetch Bills Module ---
ORG_ID   = os.getenv("ZOHO_ORG_ID")
API_BASE = "https://www.zohoapis.com/books/v3"

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
            "vendor_id":   b["vendor_id"],
            "vendor_name": b.get("vendor_name", ""),
            "due_date":    pd.to_datetime(b.get("due_date")),
            "total":       float(b.get("total", 0)),
            "status":      b.get("status", ""),
        })
    return pd.DataFrame(rows)

# --- Fetch Enrichments Module ---
def fetch_payments_for_bills(bill_ids):
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
                "paid_amount": float(p.get("amount", 0)),
                "paid_date":   pd.to_datetime(p.get("payment_date"))
            })
    return pd.DataFrame(rows)

def fetch_credits_for_bills(bill_ids):
    headers = {"Authorization": f"Zoho-oauthtoken {get_access_token()}"}
    rows = []
    # 1) List all vendor credits
    resp = requests.get(
        f"{API_BASE}/vendorcredits",
        headers=headers,
        params={"organization_id": ORG_ID}
    )
    resp.raise_for_status()
    for vc in resp.json().get("vendorcredits", []):
        vc_id = vc["vendor_credit_id"]
        # 2) List bills credited by this vendor credit
        r2 = requests.get(
            f"{API_BASE}/vendorcredits/{vc_id}/bills",
            headers=headers,
            params={"organization_id": ORG_ID}
        )
        r2.raise_for_status()
        for b in r2.json().get("bills", []):
            if b["bill_id"] in bill_ids:
                rows.append({
                    "bill_id":      b["bill_id"],
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

# --- Main Script ---
if __name__ == "__main__":
    # 1. Fetch all bills
    bills = fetch_all_bills()
    df_bills = bills_to_dataframe(bills)

    # 2. Fetch payments
    bill_ids    = df_bills["bill_id"].tolist()
    df_payments = fetch_payments_for_bills(bill_ids)

    # 3. Fetch credits
    df_credits = fetch_credits_for_bills(bill_ids)

    # 4. Aggregate sums safely
    if df_payments.empty:
        paid_sum = pd.Series(0, index=df_bills["bill_id"], name="paid_amount")
    else:
        paid_sum = df_payments.groupby("bill_id")["paid_amount"].sum()

    if df_credits.empty:
        credit_sum = pd.Series(0, index=df_bills["bill_id"], name="credit_amount")
    else:
        credit_sum = df_credits.groupby("bill_id")["credit_amount"].sum()

    # 5. Merge back and compute outstanding
    df_bills = df_bills.set_index("bill_id")
    df_bills["total_paid"]   = paid_sum
    df_bills["total_credit"] = credit_sum
    df_bills = df_bills.fillna(0).reset_index()
    df_bills["amount_due"]   = (
        df_bills["total"]
        - df_bills["total_paid"]
        - df_bills["total_credit"]
    )

    # 6. Compute aging buckets
    today = pd.Timestamp.today()
    df_bills["days_to_due"]  = (df_bills["due_date"] - today).dt.days
    df_bills["aging_bucket"] = df_bills["days_to_due"].apply(assign_aging_bucket)

    # 7. Summary by bucket
    df_summary = (
        df_bills
        .groupby("aging_bucket")
        .agg(
            total_due=("amount_due","sum"),
            count=("bill_id","count")
        )
        .reset_index()
    )

    # 8. Print outputs
    print("Bills:\n", df_bills)
    print("\nPayments:\n", df_payments)
    print("\nCredits:\n", df_credits)
    print("\nOutstanding Amounts:\n",
          df_bills[["bill_id","vendor_name","total","total_paid","total_credit","amount_due"]]
    )
    print("\nAging Summary:\n", df_summary)
