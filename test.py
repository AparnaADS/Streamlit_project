import os, requests
from dotenv import load_dotenv

load_dotenv()
BASE  = "https://www.zohoapis.com/books/v3"
ORG   = os.getenv("891157676")
TOKEN = "1000.b221f6928d0ef7bbc62e49a16b04c70f.a6cad0e9ee9590214fdc3061ecb5e61d"

r = requests.get(
    f"{BASE}/reports/balance_sheet",
    headers={"Authorization": f"Zoho-oauthtoken {TOKEN}"},
    params={"organization_id": ORG, "date": "2025-07-16"}
)
print(r.status_code, r.text)
# → 200 + JSON payload if correct
