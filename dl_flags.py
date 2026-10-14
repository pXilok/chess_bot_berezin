import urllib.request
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(SCRIPT_DIR, "flags"), exist_ok=True)

CODES = ["lv", "cu", "us", "ru", "no"]

for code in CODES:
    url = f"https://flagcdn.com/w160/{code}.png"
    dest = os.path.join(SCRIPT_DIR, "flags", code + ".png")
    print(f"Downloading {code}...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ChessTrainer/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r, open(dest, "wb") as f:
            f.write(r.read())
        print(f"  OK: {code}.png")
    except Exception as e:
        print(f"  FAILED: {code}: {e}")

print("\nDone! Check flags/ folder")