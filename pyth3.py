# zohotokens.py
import os, time, requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID     = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")

TOKEN_URL = "https://accounts.zoho.com/oauth/v2/token"

# In-memory cache of token + expiry
_cached = {"access_token": os.getenv("ZOHO_ACCESS_TOKEN"),
           "expires_at": 0}

def _refresh_access_token():
    """Use the refresh_token to get a fresh access_token."""
    resp = requests.post(TOKEN_URL, data={
        "refresh_token":  REFRESH_TOKEN,
        "client_id":      CLIENT_ID,
        "client_secret":  CLIENT_SECRET,
        "grant_type":     "refresh_token",
    })
    data = resp.json()
    token = data["access_token"]
    # expires_in is in seconds
    _cached["access_token"] = token
    _cached["expires_at"] = time.time() + data.get("expires_in", 3600) - 60
    return token

def get_access_token():
    """Return a valid access_token, refreshing if needed."""
    if not _cached["access_token"] or time.time() > _cached["expires_at"]:
        return _refresh_access_token()
    return _cached["access_token"]
if __name__ == "__main__":
    token = get_access_token()
    print("Here’s your access token:", token)
