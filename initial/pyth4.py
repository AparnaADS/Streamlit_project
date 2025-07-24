# fetch_bills.py
import requests, pandas as pd
from pyth3 import get_access_token
import os

ORG_ID = os.getenv("ZOHO_ORG_ID")
API_BASE = "https://www.zohoapis.com/books/v3"

def fetch_all_open_bills():
    headers = {"Authorization": f"Zoho-oauthtoken {get_access_token()}"}
    bills = []
    page = 1
    per_page = 200

    while True:
        params = {
          "status":          "all",
          "organization_id": ORG_ID,
          "page":            page,
          "per_page":        per_page
        }
        resp = requests.get(f"{API_BASE}/bills", headers=headers, params=params)
        print("URL →", resp.url)
        print("HTTP", resp.status_code, resp.json())

        data = resp.json().get("bills", [])
        if not data:
            break
        bills.extend(data)
        # stop if fewer than per_page returned
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
          "vendor_name": b["vendor_name"],
          "due_date":    pd.to_datetime(b["due_date"]),
          "total":       float(b["total"])
        })
    return pd.DataFrame(rows)

if __name__ == "__main__":
    all_bills = fetch_all_open_bills()
    df = bills_to_dataframe(all_bills)
    print(df.head())
