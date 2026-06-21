import os, requests
from dotenv import load_dotenv
load_dotenv()

key = os.getenv("SERPER_API_KEY")
print("KEY:", key)

res = requests.post("https://google.serper.dev/search",
    headers={"X-API-KEY": key, "Content-Type": "application/json"},
    json={"q": "latest AI news"})

print("STATUS:", res.status_code)
print("RESPONSE:", res.text[:500])