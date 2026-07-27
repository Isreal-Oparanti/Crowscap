import urllib.request
import json

req = urllib.request.Request(
    "http://127.0.0.1:8000/api/v1/search",
    data=json.dumps({"query": "product"}).encode("utf-8"),
    headers={
        "X-Crowscap-Proxy-Secret": "dev_proxy_secret",
        "X-Crowscap-User-Id": "g_demo_yc_user",
        "X-Crowscap-User-Email": "yc@crowscap.xyz",
        "Content-Type": "application/json"
    },
    method="POST"
)

try:
    with urllib.request.urlopen(req) as res:
        print(res.read().decode())
except Exception as e:
    print(e)
