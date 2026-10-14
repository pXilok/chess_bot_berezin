import urllib.request
import os

PIECES = {
    "wK": "Chess_klt45.svg", "wQ": "Chess_qlt45.svg", "wR": "Chess_rlt45.svg",
    "wB": "Chess_blt45.svg", "wN": "Chess_nlt45.svg", "wP": "Chess_plt45.svg",
    "bK": "Chess_kdt45.svg", "bQ": "Chess_qdt45.svg", "bR": "Chess_rdt45.svg",
    "bB": "Chess_bdt45.svg", "bN": "Chess_ndt45.svg", "bP": "Chess_pdt45.svg",
}

os.makedirs("pieces", exist_ok=True)
for name, fname in PIECES.items():
    # Special:FilePath отдаёт png-превью нужного размера
    url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{fname}?width=240"
    path = os.path.join("pieces", name + ".png")
    print(f"Downloading {name}...")
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'ChessTrainer/1.0 (educational project)'
        })
        with urllib.request.urlopen(req) as response, open(path, 'wb') as f:
            data = response.read()
            if len(data) < 100:
                print(f"  WARNING: file too small ({len(data)} bytes)")
            f.write(data)
    except Exception as e:
        print(f"  FAILED: {e}")

print("\nCheck pieces/ folder")
for f in os.listdir("pieces"):
    size = os.path.getsize(os.path.join("pieces", f))
    print(f"  {f}: {size} bytes")