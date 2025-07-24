import requests, os
from dotenv import load_dotenv

load_dotenv()  
CLIENT_ID     = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REDIRECT_URI  = os.getenv("ZOHO_REDIRECT_URI")
AUTH_CODE     = "1000.32ae4af76c75acc1abe3b6d9170565b9.fdb56074f848c7c6b48a81c8a546de99"

data = {
    "code":          AUTH_CODE,
    "client_id":     CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "redirect_uri":  REDIRECT_URI,
    "grant_type":    "authorization_code",
}

# If you’re on the Indian Zoho Books endpoint, use accounts.zoho.in
token_url = "https://accounts.zoho.com/oauth/v2/token"

resp = requests.post(token_url, data=data)

# print status and body to see what happened
print("HTTP", resp.status_code)
print(resp.json())
