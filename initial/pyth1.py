from urllib.parse import urlencode
params = {
  "scope": "ZohoBooks.fullaccess.all",
  "client_id":'1000.U8LNL6P2DI97DGMN3Z6QXVJ3BPE5EM',
  "response_type": "code",
  "redirect_uri": 'http://localhost:8501',
  "access_type": "offline"
}
auth_url = f"https://accounts.zoho.com/oauth/v2/auth?{urlencode(params)}"
print("Go here:", auth_url)
