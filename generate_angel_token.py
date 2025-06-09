import http.client
import json
import os
import pyotp

# Load credentials from environment
clientcode = os.environ['CLIENT_CODE']
password = os.environ['CLIENT_PIN']
totp = pyotp.TOTP(os.environ['TOTP_SECRET']).now()
apikey = os.environ['API_KEY']
local_ip = os.environ['CLIENT_LOCAL_IP']
public_ip = os.environ['CLIENT_PUBLIC_IP']
mac_address = os.environ['MAC_ADDRESS']

# Login payload
payload = json.dumps({
    "clientcode": clientcode,
    "password": password,
    "totp": totp,
    "state": "active"
})

headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'X-UserType': 'USER',
    'X-SourceID': 'WEB',
    'X-ClientLocalIP': local_ip,
    'X-ClientPublicIP': public_ip,
    'X-MACAddress': mac_address,
    'X-PrivateKey': apikey
}

# Login request
conn = http.client.HTTPSConnection("apiconnect.angelone.in")
conn.request("POST", "/rest/auth/angelbroking/user/v1/loginByPassword", payload, headers)
res = conn.getresponse()
data = res.read().decode("utf-8")
print("Login Response:", data)

try:
    response_data = json.loads(data)
    access_token = response_data['data']['jwtToken']

    # ✅ Save to access_token.json
    with open("access_token.json", "w") as f:
        json.dump({"access_token": access_token}, f, indent=2)
    print("✅ Access token saved to access_token.json")

except Exception as e:
    print("❌ Failed to extract access token:", str(e))
    exit()

# Logout request
logout_payload = json.dumps({ "clientcode": clientcode })
logout_headers = headers.copy()
logout_headers["Authorization"] = f"Bearer {access_token}"

conn.request("POST", "/rest/secure/angelbroking/user/v1/logout", logout_payload, logout_headers)
logout_res = conn.getresponse()
logout_data = logout_res.read().decode("utf-8")
print("Logout Response:", logout_data)
conn.close()

