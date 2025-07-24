#!/usr/bin/env python3
"""
Print Zoho Books Balance Sheet (raw JSON only) for any date.

Usage:
  python bs_raw.py 2025-07-23        # accrual by default
  python bs_raw.py 2025-07-23 Cash   # cash basis
  python bs_raw.py                   # today, accrual

Needs .env with:
  ZOHO_CLIENT_ID
  ZOHO_CLIENT_SECRET
  ZOHO_REFRESH_TOKEN
  ZOHO_ORG_ID
Optional:
  ZOHO_TOKEN_URL   (default https://accounts.zoho.com/oauth/v2/token)
  ZOHO_API_BASE    (default https://www.zohoapis.com/books/v3)
"""

import os, time, sys, json, requests
from datetime import datetime
from dotenv import load_dotenv

# --- env ---
load_dotenv()
CLIENT_ID     = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")
ORG_ID        = os.getenv("ZOHO_ORG_ID")
TOKEN_URL     = os.getenv("ZOHO_TOKEN_URL", "https://accounts.zoho.com/oauth/v2/token")
API_BASE      = os.getenv("ZOHO_API_BASE", "https://www.zohoapis.com/books/v3")

for k,v in {"ZOHO_CLIENT_ID":CLIENT_ID,"ZOHO_CLIENT_SECRET":CLIENT_SECRET,
            "ZOHO_REFRESH_TOKEN":REFRESH_TOKEN,"ZOHO_ORG_ID":ORG_ID}.items():
    if not v:
        sys.exit(f"Missing env var: {k}")

_cache = {"token": None, "exp": 0}

def refresh_token():
    r = requests.post(
        TOKEN_URL,
        data={
            "refresh_token": REFRESH_TOKEN,
            "client_id":     CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type":    "refresh_token",
        },
        timeout=30,
    )
    r.raise_for_status()
    j = r.json()
    _cache["token"] = j["access_token"]
    _cache["exp"]   = time.time() + j.get("expires_in", 3600) - 60
    return _cache["token"]

def token():
    if not _cache["token"] or time.time() >= _cache["exp"]:
        return refresh_token()
    return _cache["token"]

def fetch_bs(date_str: str, basis: str = "Accrual") -> dict:
    params = {
        "organization_id": ORG_ID,
        "filter_by": "TransactionDate.CustomDate",
        "from_date": date_str,
        "to_date":   date_str,
        "report_basis": basis,
        "show_rows": "non_zero"
    }
    url = f"{API_BASE}/reports/balancesheet"
    hdr = {"Authorization": f"Zoho-oauthtoken {token()}"}
    r = requests.get(url, headers=hdr, params=params, timeout=60)
    if r.status_code == 401:
        refresh_token()
        hdr["Authorization"] = f"Zoho-oauthtoken {token()}"
        r = requests.get(url, headers=hdr, params=params, timeout=60)
    r.raise_for_status()
    return r.json()

if __name__ == "__main__":
    # args
    if len(sys.argv) >= 2:
        date_str = sys.argv[1]
    else:
        date_str = datetime.today().strftime("%Y-%m-%d")

    basis = sys.argv[2] if len(sys.argv) >= 3 else "Accrual"

    data = fetch_bs(date_str, basis)
    print(json.dumps(data, indent=2, ensure_ascii=False))
