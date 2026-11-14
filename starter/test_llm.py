
import json
import os
import urllib.request
import urllib.error
from pathlib import Path
from dotenv import load_dotenv

# Load .env của Day 7
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(env_path, override=True)

api_key = os.environ["OPENROUTER_API_KEY"].strip()
base_url = os.environ["OPENROUTER_URL"].rstrip("/")
model = os.environ["OPENROUTER_MODEL"]

payload = {
    "model": model,
    "messages": [
        {"role": "user", "content": "Reply with OK"}
    ],
    "temperature": 0
}

request = urllib.request.Request(
    base_url + "/chat/completions",
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    },
    method="POST"
)

try:
    with urllib.request.urlopen(request, timeout=60) as response:
        result = json.load(response)
        print("SUCCESS")
        print(result["choices"][0]["message"]["content"])

except urllib.error.HTTPError as exc:
    print("HTTP STATUS:", exc.code)
    print(
        "ERROR:",
        exc.read().decode("utf-8", errors="replace")[:500]
    )

except Exception as exc:
    print("ERROR TYPE:", type(exc).__name__)
    print("ERROR:", str(exc))
