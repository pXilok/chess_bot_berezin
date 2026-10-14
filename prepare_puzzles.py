import os
import csv
import chess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT = r"C:\Users\Academy\Desktop\lichess_db_puzzle.csv"
OUTPUT = os.path.join(SCRIPT_DIR, "puzzles.csv")

if not os.path.exists(INPUT):
    print("ERROR: not found:", INPUT)
    exit(1)

print("Reading", INPUT, "...")
count = 0
with open(INPUT, "r", encoding="utf-8") as fin, \
     open(OUTPUT, "w", encoding="utf-8", newline="") as fout:
    reader = csv.DictReader(fin)
    writer = csv.writer(fout)
    writer.writerow(["FEN", "Moves", "Rating"])

    for row in reader:
        themes = row.get("Themes", "")
        if "mateIn1" not in themes:
            continue
        try:
            rating = int(row.get("Rating", "9999"))
        except:
            continue
        if rating > 1400:
            continue

        fen = row["FEN"]
        moves = row["Moves"]

        try:
            b = chess.Board(fen)
            b.push_uci(moves.split()[0])
        except:
            continue

        writer.writerow([fen, moves, rating])
        count += 1
        if count % 50 == 0:
            print("Found:", count)
        if count >= 300:
            break

print("\nDONE!", count, "puzzles saved to puzzles.csv")