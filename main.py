import pygame
import chess
import chess.engine
import os
import random
import csv
import json
import threading
import time
import math
import queue
import urllib.request
import urllib.error

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ============ НАСТРОЙКИ ============
SETTINGS_FILE = os.path.join(SCRIPT_DIR, "settings.json")
settings = {"theme": "Classic", "fullscreen": False, "sound": False}

THEMES = {
    "Classic": {"LIGHT": (238,238,210), "DARK": (118,150,86), "BG_TOP": (44,40,36), "BG_BOT": (22,20,18), "ACCENT": (255,200,50)},
    "Blue":    {"LIGHT": (222,227,230), "DARK": (79,121,168), "BG_TOP": (30,40,55),  "BG_BOT": (15,20,30), "ACCENT": (120,180,255)},
    "Brown":   {"LIGHT": (240,217,181), "DARK": (181,136,99), "BG_TOP": (50,40,30),  "BG_BOT": (26,20,15), "ACCENT": (255,180,90)},
    "Dark":    {"LIGHT": (160,160,170), "DARK": (70,70,85),   "BG_TOP": (18,18,22),  "BG_BOT": (8,8,10),   "ACCENT": (180,200,255)},
}

def load_settings():
    global settings
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings.update(json.load(f))
        except: pass
    settings["sound"] = False
    if settings.get("theme") not in THEMES:
        settings["theme"] = "Classic"

def save_settings():
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except: pass

load_settings()
theme = THEMES[settings["theme"]]
LIGHT = theme["LIGHT"]; DARK = theme["DARK"]
BG_TOP = theme["BG_TOP"]; BG_BOT = theme["BG_BOT"]
HINT_COLOR = theme["ACCENT"]

def make_gradient(w, h, c1, c2):
    surf = pygame.Surface((w, h))
    for y in range(h):
        t = y / max(1, h - 1)
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        pygame.draw.line(surf, (r, g, b), (0, y), (w, y))
    return surf

def apply_theme(name):
    global LIGHT, DARK, BG_TOP, BG_BOT, HINT_COLOR, BG_GRADIENT, MENU_GRADIENT, theme
    if name not in THEMES: return
    settings["theme"] = name
    save_settings()
    theme = THEMES[name]
    LIGHT = theme["LIGHT"]; DARK = theme["DARK"]
    BG_TOP = theme["BG_TOP"]; BG_BOT = theme["BG_BOT"]
    HINT_COLOR = theme["ACCENT"]
    BG_GRADIENT = make_gradient(WIDTH, HEIGHT, BG_TOP, BG_BOT)
    MENU_GRADIENT = make_gradient(WIDTH, HEIGHT, (32,30,40), (16,14,22))

# ============ ОКНО ============
WIDTH, HEIGHT = 1280, 960
TILE = 92
BOARD_X = 130
BOARD_Y = 150
EVAL_BAR_X = 60
EVAL_BAR_W = 34
HIST_X = BOARD_X + 8 * TILE + 30
HIST_W = WIDTH - HIST_X - 30

SEL = (255, 220, 60, 200)
MOVE_DOT = (30, 30, 30, 130)
LAST_MOVE_HL = (255, 240, 100, 140)
CHECK_HL = (255, 70, 70, 180)
TEXT = (245, 245, 245)
BTN_BG = (60, 65, 85)
BTN_BG_HOVER = (90, 100, 130)
BTN_BORDER = (140, 150, 180)
PANEL_BG = (34, 32, 40)
PANEL_BORDER = (90, 90, 110)
GOLD = (255, 200, 80)

pygame.init()
try: pygame.mixer.quit()
except: pass
MIXER_OK = False

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Chess Trainer")

font_huge = pygame.font.SysFont("Segoe UI", 58, bold=True)
font_title = pygame.font.SysFont("Segoe UI", 30, bold=True)
font_big = pygame.font.SysFont("Segoe UI", 24, bold=True)
font_mid = pygame.font.SysFont("Segoe UI", 20, bold=True)
font_small = pygame.font.SysFont("Segoe UI", 16)
font_tiny = pygame.font.SysFont("Segoe UI", 14)
font_coord = pygame.font.SysFont("Segoe UI", 15, bold=True)
font_mono = pygame.font.SysFont("Consolas", 18, bold=True)
font_flag = pygame.font.SysFont("Segoe UI", 20, bold=True)

BG_GRADIENT = make_gradient(WIDTH, HEIGHT, BG_TOP, BG_BOT)
MENU_GRADIENT = make_gradient(WIDTH, HEIGHT, (32,30,40), (16,14,22))

# ============ ЗВУКИ ============
import array

SOUNDS = {}
MIXER_OK = False


def generate_sound(freq_start, freq_end, duration, volume=0.35, sample_rate=22050, harmonic=0.3):
    try:
        n = int(sample_rate * duration)
        samples = array.array('h')
        for i in range(n):
            t = i / sample_rate
            progress = i / max(1, n - 1)
            freq = freq_start + (freq_end - freq_start) * progress
            if progress < 0.03:
                env = progress / 0.03
            elif progress < 0.15:
                env = 1.0 - 0.3 * ((progress - 0.03) / 0.12)
            elif progress < 0.8:
                env = 0.7
            else:
                env = 0.7 * (1 - (progress - 0.8) / 0.2)
            val = math.sin(2 * math.pi * freq * t) * (1 - harmonic)
            val += math.sin(2 * math.pi * freq * 2 * t) * harmonic
            s = int(32767 * volume * max(0, env) * val)
            samples.append(max(-32768, min(32767, s)))
        return samples
    except:
        return None


def init_sounds():
    global MIXER_OK
    try:
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.mixer.init()
        MIXER_OK = True
    except Exception as e:
        print(f"[SOUND] mixer failed: {e}")
        MIXER_OK = False
        return
    specs = {
        "move":    (523, 659, 0.08, 0.25),
        "capture": (440, 220, 0.15, 0.35),
        "check":   (880, 1100, 0.20, 0.30),
        "correct": (784, 1046, 0.30, 0.35),
        "wrong":   (300, 200, 0.25, 0.35),
        "win":     (523, 1046, 0.50, 0.35),
        "lose":    (400, 200, 0.50, 0.30),
    }
    for name, (f1, f2, dur, vol) in specs.items():
        samples = generate_sound(f1, f2, dur, vol)
        if samples:
            try:
                SOUNDS[name] = pygame.mixer.Sound(buffer=samples)
            except: pass
    print(f"[SOUND] loaded {len(SOUNDS)} sounds")


def play_sound(name):
    if not MIXER_OK: return
    snd = SOUNDS.get(name)
    if snd:
        try: snd.play()
        except: pass


def play_move_sound(captured):
    if board.is_checkmate():
        winner_black = board.turn == chess.BLACK
        you_won = (winner_black and player_color == chess.WHITE) or \
                  (not winner_black and player_color == chess.BLACK)
        play_sound("win" if you_won else "lose")
    elif board.is_check():
        play_sound("check")
    elif captured:
        play_sound("capture")
    else:
        play_sound("move")


def play(s): pass

# ============ ФЛАГИ (рисуем как текст в цветном кружке) ============
FLAGS = {
    "LV": {"code": "LV", "color": (140, 30, 50)},      # Латвия
    "CU": {"code": "CU", "color": (200, 40, 40)},      # Куба
    "US": {"code": "US", "color": (40, 60, 140)},      # США
    "RU": {"code": "RU", "color": (30, 60, 140)},      # Россия
    "NO": {"code": "NO", "color": (180, 30, 40)},      # Норвегия
    "AI": {"code": "AI", "color": (80, 80, 100)},      # Stockfish
}

def draw_flag(x, y, size, code):
    """Кружок с кодом страны как флаг"""
    info = FLAGS.get(code, {"color": (100, 100, 120)})
    pygame.draw.circle(screen, info["color"], (x + size // 2, y + size // 2), size // 2)
    pygame.draw.circle(screen, (240, 240, 240), (x + size // 2, y + size // 2), size // 2, 2)
    t = font_flag.render(info["code"], True, (255, 255, 255))
    screen.blit(t, (x + size // 2 - t.get_width() // 2,
                    y + size // 2 - t.get_height() // 2))

# ============ ЛЕГЕНДЫ ШАХМАТ (real peak ELO) ============
BOTS = [
    {"name": "Mikhail Tal", "keys": ["tal"],
     "peak_elo": 2705, "play_elo": 1600,
     "flag": "LV", "style": "Attacking", "icon": "[+]",
     "years": "1936-1992", "bio": "The Magician from Riga",
     "color": (200, 140, 220), "avatar": None},

    {"name": "Jose Capablanca", "keys": ["capablanca", "kapablanca"],
     "peak_elo": 2877, "play_elo": 1800,
     "flag": "CU", "style": "Positional", "icon": "[=]",
     "years": "1888-1942", "bio": "The Chess Machine",
     "color": (140, 200, 160), "avatar": None},

    {"name": "Bobby Fischer", "keys": ["fischer"],
     "peak_elo": 2785, "play_elo": 2000,
     "flag": "US", "style": "Sharp", "icon": "[!]",
     "years": "1943-2008", "bio": "The American Genius",
     "color": (220, 180, 120), "avatar": None},

    {"name": "Garry Kasparov", "keys": ["kasparov"],
     "peak_elo": 2851, "play_elo": 2200,
     "flag": "RU", "style": "Aggressive", "icon": "[#]",
     "years": "1963-", "bio": "The Beast from Baku",
     "color": (200, 120, 120), "avatar": None},

    {"name": "Magnus Carlsen", "keys": ["carlsen"],
     "peak_elo": 2882, "play_elo": 2400,
     "flag": "NO", "style": "Universal", "icon": "[*]",
     "years": "1990-", "bio": "The Mozart of Chess",
     "color": (120, 180, 240), "avatar": None},

    {"name": "Hikaru Nakamura", "keys": ["nakamura"],
     "peak_elo": 2816, "play_elo": 2500,
     "flag": "US", "style": "Blitz King", "icon": "[~]",
     "years": "1987-", "bio": "The Speed Demon",
     "color": (240, 200, 100), "avatar": None},
]

# ============ STOCKFISH УРОВНИ ============
STOCKFISH_LEVELS = [
    {"name": "Beginner",     "elo": 1320, "color": (100, 200, 100)},
    {"name": "Intermediate", "elo": 1600, "color": (150, 200, 100)},
    {"name": "Advanced",     "elo": 2000, "color": (240, 200, 100)},
    {"name": "Master",       "elo": 2500, "color": (240, 120, 120)},
]

current_bot_idx = 0
current_stockfish_idx = 0
play_mode = "legend"  # "legend" или "stockfish"
PLAYER_AVATAR = None

def make_circular_avatar(img, size):
    try:
        img = pygame.transform.smoothscale(img.convert_alpha(), (size, size))
    except:
        try:
            img = pygame.transform.smoothscale(img, (size, size)).convert_alpha()
        except:
            return None
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    surface.fill((0, 0, 0, 0))
    pygame.draw.circle(surface, (255, 255, 255, 255), (size // 2, size // 2), size // 2)
    img.blit(surface, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return img

def load_avatars():
    global PLAYER_AVATAR
    avatar_dir = os.path.join(SCRIPT_DIR, "avatars")
    if not os.path.isdir(avatar_dir):
        print(f"[AVATAR] no folder: {avatar_dir}")
        return
    files = os.listdir(avatar_dir)
    print(f"[AVATAR] found: {files}")
    for bot in BOTS:
        bot["avatar"] = None
        for f in files:
            fname_low = f.lower()
            if fname_low.startswith("you"):
                continue
            for key in bot["keys"]:
                if key in fname_low:
                    try:
                        path = os.path.join(avatar_dir, f)
                        raw = pygame.image.load(path)
                        av = make_circular_avatar(raw, 56)
                        if av:
                            bot["avatar"] = av
                            print(f"[AVATAR] {bot['name']} <- {f}")
                        break
                    except Exception as e:
                        print(f"[AVATAR] fail {f}: {e}")
            if bot["avatar"] is not None:
                break
    PLAYER_AVATAR = None
    for f in files:
        fname_low = f.lower()
        if fname_low.startswith("you") or "player" in fname_low:
            try:
                path = os.path.join(avatar_dir, f)
                PLAYER_AVATAR = make_circular_avatar(pygame.image.load(path), 56)
                print(f"[AVATAR] player <- {f}")
                break
            except: pass

def get_current_opponent():
    if play_mode == "stockfish":
        lvl = STOCKFISH_LEVELS[current_stockfish_idx]
        return {
            "name": f"Stockfish {lvl['name']}",
            "elo": lvl["elo"],
            "peak_elo": lvl["elo"],
            "flag": "AI",
            "style": "Engine",
            "icon": "AI",
            "bio": f"Level {current_stockfish_idx + 1}",
            "color": lvl["color"],
            "avatar": None,
        }
    else:
        return BOTS[current_bot_idx]

PIECE_IMAGES = {}
def load_pieces():
    init_sounds()
    names = {'K':'wK','Q':'wQ','R':'wR','B':'wB','N':'wN','P':'wP',
             'k':'bK','q':'bQ','r':'bR','b':'bB','n':'bN','p':'bP'}
    for sym, fname in names.items():
        path = os.path.join(SCRIPT_DIR, "pieces", fname + ".png")
        img = pygame.image.load(path).convert_alpha()
        img = pygame.transform.smoothscale(img, (TILE - 8, TILE - 8))
        PIECE_IMAGES[sym] = img
        PIECE_IMAGES[sym + "_big"] = pygame.transform.smoothscale(
            img, (int((TILE - 8) * 1.12), int((TILE - 8) * 1.12)))

engine = None
engine_lock = threading.Lock()
STOCKFISH_PATH = os.path.join(SCRIPT_DIR, "stockfish.exe")
try:
    if os.path.exists(STOCKFISH_PATH):
        engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
        print("Stockfish loaded")
except Exception as e:
    print("Engine error:", e)

# ============ AI ПОТОКИ ============
ai_result_queue = queue.Queue()
ai_thread = None
ai_generation = 0

def ai_think_worker(gen, board_copy, think_time):
    try:
        with engine_lock:
            result = engine.play(board_copy, chess.engine.Limit(time=think_time))
        ai_result_queue.put((gen, result.move))
    except Exception as e:
        print("AI error:", e)
        ai_result_queue.put((gen, None))

eval_result_queue = queue.Queue()
eval_thread_active = False

def eval_worker(board_copy):
    global eval_thread_active
    try:
        with engine_lock:
            info = engine.analyse(board_copy, chess.engine.Limit(time=0.25))
        score = info["score"].pov(chess.WHITE)
        if score.is_mate():
            eval_result_queue.put((score.mate(), True))
        else:
            eval_result_queue.put((score.score(), False))
    except Exception as e:
        eval_result_queue.put((0, False))
    finally:
        eval_thread_active = False

def request_eval():
    global eval_thread_active
    if eval_thread_active or engine is None: return
    eval_thread_active = True
    try: b = board.copy()
    except: return
    threading.Thread(target=eval_worker, args=(b,), daemon=True).start()

# ============ СТАТЫ ============
STATS_FILE = os.path.join(SCRIPT_DIR, "stats.json")
stats = {"puzzles_solved": 0, "best_streak": 0, "current_streak": 0,
         "games_won": 0, "games_lost": 0, "solved_puzzle_ids": []}

def load_stats():
    global stats
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                stats.update(json.load(f))
        except: pass
    if "solved_puzzle_ids" not in stats:
        stats["solved_puzzle_ids"] = []

def save_stats():
    try:
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)
    except: pass

# ============ СОСТОЯНИЯ ============
STATE_MENU = "MENU"
STATE_SETUP_LEGENDS = "SETUP_LEGENDS"
STATE_SETUP_STOCKFISH = "SETUP_STOCKFISH"
STATE_PUZZLE = "PUZZLE"
STATE_VS_AI = "VS_AI"
STATE_STATS = "STATS"
STATE_SETTINGS = "SETTINGS"
STATE_ANALYSIS = "ANALYSIS"
state = STATE_MENU

MODE_PUZZLE = "PUZZLE"
MODE_NORMAL = "NORMAL"
mode = MODE_PUZZLE

board = chess.Board()
history_start_fen = chess.STARTING_FEN

selected_square = None
legal_targets = []
last_move = None
ai_thinking = False

difficulty = 2
white_time = 600.0
black_time = 600.0
last_tick = 0.0
game_started = False
player_color = chess.WHITE

current_eval_cp = 0
eval_mate = None
analysis_records = []

hist_scroll = 0
HIST_LINE_H = 24
HIST_MAX_LINES = 28

puzzles = []
current_moves = []
move_index = 0
puzzle_status = ""
puzzle_score = 0
puzzle_total_answered = 0
current_rating = 0
current_puzzle_id = None
solved = False

flash_color = None
flash_timer = 0.0
popup_text = ""
popup_timer = 0.0

animations = []
arrows = []
check_pulse = 0.0
flipped = False

# Анимация для карточек
card_hover = {}

# ============ УТИЛИТЫ ============
def start_anim(piece_sym, from_sq, to_sq, captured_sym=None):
    animations.append({
        'piece': piece_sym, 'from': from_sq, 'to': to_sq,
        't': 0.0, 'dur': 0.28, 'captured': captured_sym,
    })

def square_center(sq):
    x = chess.square_file(sq); y = 7 - chess.square_rank(sq)
    if flipped: x = 7 - x; y = 7 - y
    return BOARD_X + x * TILE + TILE / 2, BOARD_Y + y * TILE + TILE / 2

def square_top_left(sq):
    x = chess.square_file(sq); y = 7 - chess.square_rank(sq)
    if flipped: x = 7 - x; y = 7 - y
    return BOARD_X + x * TILE, BOARD_Y + y * TILE

def xy_to_square(mx, my):
    if mx < BOARD_X or my < BOARD_Y: return None
    x = (mx - BOARD_X) // TILE; y = (my - BOARD_Y) // TILE
    if x < 0 or x > 7 or y < 0 or y > 7: return None
    if flipped: x = 7 - x; y = 7 - y
    return chess.square(x, 7 - y)

def show_popup(text, timer=1.8):
    global popup_text, popup_timer
    popup_text = text; popup_timer = timer

def format_time(sec):
    if sec < 0: sec = 0
    if sec >= 60: return f"{int(sec // 60)}:{int(sec % 60):02d}"
    return f"{sec:.1f}"

def ease_in_out(t):
    if t < 0.5: return 4 * t * t * t
    return 1 - pow(-2 * t + 2, 3) / 2

PIECE_VALUES = {'P': 1, 'N': 3, 'B': 3, 'R': 5, 'Q': 9, 'K': 0}

def compute_material():
    w = 0; b = 0
    for sq in chess.SQUARES:
        p = board.piece_at(sq)
        if p is None: continue
        v = PIECE_VALUES.get(p.symbol().upper(), 0)
        if p.color == chess.WHITE: w += v
        else: b += v
    return w - b

def load_puzzles():
    global puzzles
    path = os.path.join(SCRIPT_DIR, "puzzles.csv")
    if not os.path.exists(path):
        print(f"[PUZZLES] file not found: {path}")
        return
    good = 0; bad = 0
    with open(path, "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                fen = row["FEN"].strip()
                moves = row["Moves"].split()
                if len(moves) < 2: bad += 1; continue
                try: tmp = chess.Board(fen)
                except: bad += 1; continue
                try: setup = chess.Move.from_uci(moves[0])
                except: bad += 1; continue
                if setup not in tmp.legal_moves: bad += 1; continue
                tmp.push(setup)
                valid = True
                for mv_str in moves[1:]:
                    try: mv = chess.Move.from_uci(mv_str)
                    except: valid = False; break
                    if mv not in tmp.legal_moves: valid = False; break
                    tmp.push(mv)
                if not valid: bad += 1; continue
                rating = int(row.get("Rating", "1000"))
                puzzles.append((fen, moves, rating))
                good += 1
            except: bad += 1; continue
    print(f"[PUZZLES] loaded={good} skipped={bad}")


def fetch_lichess_puzzle():
    """Получает случайную задачу с Lichess API (онлайн)."""
    try:
        import io
        import chess.pgn
        url = "https://lichess.org/api/puzzle/next"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'ChessTrainer/1.0',
            'Accept': 'application/json'
        })
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))

        pgn_text = data["game"]["pgn"]
        game = chess.pgn.read_game(io.StringIO(pgn_text))
        b = game.board()
        for move in game.mainline_moves():
            b.push(move)

        puzzle = data["puzzle"]
        return {
            "fen": b.fen(),
            "moves": puzzle["solution"],
            "rating": puzzle["rating"],
            "themes": puzzle.get("themes", []),
            "id": puzzle["id"],
        }
    except Exception as e:
        print(f"[LICHESS] error: {e}")
        return None


def load_lichess_puzzle():
    """Загружает задачу с Lichess. Возвращает True если успешно."""
    global current_moves, move_index, board, selected_square, legal_targets
    global puzzle_status, solved, last_move, animations, current_rating
    global current_eval_cp, eval_mate, current_puzzle_id, player_color, arrows
    global history_start_fen

    print("[LICHESS] fetching...")
    p = fetch_lichess_puzzle()
    if p is None:
        return False

    try:
        new_board = chess.Board(p["fen"])
        moves = p["moves"]

        history_start_fen = p["fen"]
        board = new_board
        animations.clear();
        arrows.clear()
        current_moves = moves
        move_index = 0
        selected_square = None
        legal_targets = []
        solved = False
        player_color = board.turn
        current_rating = p["rating"]
        current_puzzle_id = p["id"]

        themes = ", ".join(p["themes"][:3]) if p["themes"] else ""
        puzzle_status = f"Lichess #{p['id'][:6]}  rating {p['rating']}  {themes}"
        current_eval_cp = 0;
        eval_mate = None
        return True
    except Exception as e:
        print(f"[LICHESS] parse: {e}")
        return False


def load_next_puzzle():
    global current_moves, move_index, board, selected_square, legal_targets
    global puzzle_status, solved, last_move, animations, current_rating
    global current_eval_cp, eval_mate, current_puzzle_id, player_color, arrows
    global history_start_fen

    if not puzzles:
        puzzle_status = "No puzzles loaded"
        return False

    for attempt in range(30):
        try:
            idx = random.randint(0, len(puzzles) - 1)
            fen, moves, rating = puzzles[idx]
            new_board = chess.Board(fen)
            setup = chess.Move.from_uci(moves[0])
            if setup not in new_board.legal_moves: continue
            piece_before = new_board.piece_at(setup.from_square)
            if piece_before is None: continue
            piece_sym = piece_before.symbol()
            cap = new_board.piece_at(setup.to_square)
            cap_sym = cap.symbol() if cap else None
            history_start_fen = fen
            new_board.push(setup)

            current_puzzle_id = idx
            current_moves = moves
            current_rating = rating
            board = new_board
            animations.clear(); arrows.clear()
            start_anim(piece_sym, setup.from_square, setup.to_square, cap_sym)
            last_move = setup
            move_index = 1
            selected_square = None
            legal_targets = []
            solved = False
            player_color = board.turn
            puzzle_status = f"Find the best move!  (rating {rating})"
            current_eval_cp = 0; eval_mate = None
            return True
        except: continue
    puzzle_status = "Failed to load puzzle"
    return False

def start_vs_ai():
    global board, selected_square, legal_targets, last_move, animations, ai_thinking
    global white_time, black_time, game_started, analysis_records
    global current_eval_cp, eval_mate, hist_scroll, arrows, ai_generation
    global history_start_fen, flipped
    ai_generation += 1
    while not ai_result_queue.empty():
        try: ai_result_queue.get_nowait()
        except: break
    board = chess.Board()
    history_start_fen = chess.STARTING_FEN
    selected_square = None; legal_targets = []
    last_move = None; animations.clear(); arrows.clear()
    base = 600
    white_time = float(base); black_time = float(base)
    game_started = True
    analysis_records.clear()
    current_eval_cp = 0; eval_mate = None
    hist_scroll = 0
    flipped = (player_color == chess.BLACK)

    # Настроить Stockfish под противника
    if engine:
        try:
            if play_mode == "stockfish":
                elo = STOCKFISH_LEVELS[current_stockfish_idx]["elo"]
            else:
                elo = BOTS[current_bot_idx]["play_elo"]
            engine.configure({"UCI_LimitStrength": True, "UCI_Elo": elo})
        except: pass

    ai_thinking = (board.turn != player_color)
    request_eval()

# ============ РИСОВАНИЕ ============
def draw_board_bg():
    shadow = pygame.Surface((TILE * 8 + 12, TILE * 8 + 12), pygame.SRCALPHA)
    pygame.draw.rect(shadow, (0, 0, 0, 100), shadow.get_rect(), border_radius=10)
    screen.blit(shadow, (BOARD_X - 6 + 3, BOARD_Y - 6 + 6))
    for y in range(8):
        for x in range(8):
            color = LIGHT if (x + y) % 2 == 0 else DARK
            pygame.draw.rect(screen, color,
                (BOARD_X + x * TILE, BOARD_Y + y * TILE, TILE, TILE))

def draw_highlights():
    global check_pulse
    if last_move:
        for sq in (last_move.from_square, last_move.to_square):
            x, y = chess.square_file(sq), 7 - chess.square_rank(sq)
            if flipped: x = 7 - x; y = 7 - y
            s = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
            s.fill(LAST_MOVE_HL)
            screen.blit(s, (BOARD_X + x * TILE, BOARD_Y + y * TILE))
    if board.is_check():
        ksq = board.king(board.turn)
        if ksq is not None:
            x, y = chess.square_file(ksq), 7 - chess.square_rank(ksq)
            if flipped: x = 7 - x; y = 7 - y
            pulse = 0.6 + 0.4 * math.sin(check_pulse * 6)
            s = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
            c = CHECK_HL
            s.fill((c[0], c[1], c[2], int(c[3] * pulse)))
            screen.blit(s, (BOARD_X + x * TILE, BOARD_Y + y * TILE))
    if selected_square is not None:
        x, y = chess.square_file(selected_square), 7 - chess.square_rank(selected_square)
        if flipped: x = 7 - x; y = 7 - y
        s = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
        s.fill(SEL)
        screen.blit(s, (BOARD_X + x * TILE, BOARD_Y + y * TILE))
    for sq in legal_targets:
        cx, cy = square_center(sq)
        if board.piece_at(sq):
            pygame.draw.circle(screen, (30, 30, 30, 200), (cx, cy), TILE // 2 - 3, 6)
        else:
            for r in range(14, 8, -1):
                alpha = int(60 + (14 - r) * 15)
                s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                pygame.draw.circle(s, (30, 30, 30, alpha), (r, r), r)
                screen.blit(s, (cx - r, cy - r))
    for (from_sq, to_sq) in arrows:
        fx, fy = square_center(from_sq)
        tx, ty = square_center(to_sq)
        s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.line(s, (255, 100, 100, 180), (fx, fy), (tx, ty), 8)
        angle = math.atan2(ty - fy, tx - fx)
        ah = 22; aw = 16
        p1 = (tx - ah * math.cos(angle) + aw * math.sin(angle),
              ty - ah * math.sin(angle) - aw * math.cos(angle))
        p2 = (tx - ah * math.cos(angle) - aw * math.sin(angle),
              ty - ah * math.sin(angle) + aw * math.cos(angle))
        pygame.draw.polygon(s, (255, 100, 100, 180), [(tx, ty), p1, p2])
        screen.blit(s, (0, 0))

def draw_pieces():
    anim_to = {a['to'] for a in animations}
    for sq in chess.SQUARES:
        if sq in anim_to: continue
        piece = board.piece_at(sq)
        if piece is None: continue
        if sq == selected_square:
            img = PIECE_IMAGES.get(piece.symbol() + "_big")
            if img:
                x, y = square_top_left(sq)
                sh = pygame.Surface((TILE - 4, TILE - 4), pygame.SRCALPHA)
                sh.fill((0, 0, 0, 80))
                screen.blit(sh, (x + 4 + 2, y + 4 + 6))
                screen.blit(img, (x + 4 - 4, y + 4 - 4))
                continue
        img = PIECE_IMAGES.get(piece.symbol())
        if img:
            x, y = square_top_left(sq)
            sh = pygame.Surface((TILE - 8, TILE - 8), pygame.SRCALPHA)
            sh.fill((0, 0, 0, 60))
            screen.blit(sh, (x + 4 + 2, y + 4 + 4))
            screen.blit(img, (x + 4, y + 4))
    for a in animations:
        raw_t = min(1.0, a['t'] / a['dur'])
        t = ease_in_out(raw_t)
        fx, fy = square_center(a['from'])
        tx, ty = square_center(a['to'])
        cx = fx + (tx - fx) * t
        cy = fy + (ty - fy) * t
        if a['captured']:
            cap_img = PIECE_IMAGES.get(a['captured'])
            if cap_img:
                fade = max(0, 1 - raw_t * 2)
                scale = 1.0 - raw_t * 0.5
                if fade > 0 and scale > 0:
                    w = int(cap_img.get_width() * scale)
                    h = int(cap_img.get_height() * scale)
                    if w > 0 and h > 0:
                        cs = pygame.transform.smoothscale(cap_img, (w, h))
                        cs.set_alpha(int(255 * fade))
                        rx, ry = square_top_left(a['to'])
                        screen.blit(cs, (rx + 4 + (cap_img.get_width() - w) // 2,
                                         ry + 4 + (cap_img.get_height() - h) // 2))
        img = PIECE_IMAGES.get(a['piece'])
        if img:
            shadow_offset = int(6 * (1 - raw_t))
            sh = pygame.Surface((img.get_width(), img.get_height()), pygame.SRCALPHA)
            sh.fill((0, 0, 0, 70))
            screen.blit(sh, (cx - img.get_width() / 2 + 2,
                            cy - img.get_height() / 2 + shadow_offset + 2))
            screen.blit(img, (cx - img.get_width() / 2, cy - img.get_height() / 2))

def draw_board_labels():
    for i in range(8):
        file_idx = i if not flipped else 7 - i
        rank_idx = i if not flipped else 7 - i
        letter = font_coord.render(chr(ord('a') + file_idx), True, (200, 200, 200))
        screen.blit(letter, (BOARD_X + i * TILE + TILE // 2 - 6, BOARD_Y + TILE * 8 + 8))
        num = font_coord.render(str(8 - rank_idx), True, (200, 200, 200))
        screen.blit(num, (BOARD_X - 22, BOARD_Y + i * TILE + TILE // 2 - 9))

def draw_material_bar():
    if state == STATE_PUZZLE: return
    diff = compute_material()
    total_h = TILE * 8
    x = EVAL_BAR_X + EVAL_BAR_W + 6
    y = BOARD_Y
    if diff == 0: label = "="; col = (200, 200, 200)
    elif diff > 0: label = f"+{diff}"; col = (240, 240, 240)
    else: label = f"{diff}"; col = (200, 200, 200)
    pygame.draw.rect(screen, (30, 30, 40), (x, y + total_h - 40, 38, 40), border_radius=6)
    pygame.draw.rect(screen, PANEL_BORDER, (x, y + total_h - 40, 38, 40), 2, border_radius=6)
    t = font_big.render(label, True, col)
    screen.blit(t, (x + 19 - t.get_width() // 2, y + total_h - 32))

def draw_eval_bar():
    if state == STATE_PUZZLE: return
    total_h = TILE * 8
    x = EVAL_BAR_X; y = BOARD_Y
    pygame.draw.rect(screen, (40, 40, 40), (x, y, EVAL_BAR_W, total_h))
    if eval_mate is not None:
        pct = 1.0 if eval_mate > 0 else 0.0
    else:
        pct = 0.5 + 0.5 * math.tanh(current_eval_cp / 400.0)
    white_h = int(total_h * pct)
    for i in range(white_h):
        t = i / max(1, total_h - 1)
        c = int(250 - 20 * t)
        pygame.draw.line(screen, (c, c, c), (x, y + i), (x + EVAL_BAR_W, y + i))
    pygame.draw.rect(screen, (100, 100, 110), (x, y, EVAL_BAR_W, total_h), 2)
    pygame.draw.line(screen, (180, 180, 180), (x, y + total_h // 2),
                     (x + EVAL_BAR_W, y + total_h // 2), 1)
    if eval_mate is not None:
        label = f"M{eval_mate}" if eval_mate > 0 else f"-M{abs(eval_mate)}"
    else:
        val = current_eval_cp / 100.0
        label = f"{val:+.1f}"
    lab = font_tiny.render(label, True, HINT_COLOR)
    screen.blit(lab, (x + EVAL_BAR_W // 2 - lab.get_width() // 2, y - 22))
    draw_material_bar()

def get_move_pairs():
    moves = []
    try:
        try: tmp = chess.Board(history_start_fen)
        except: tmp = chess.Board()
        for m in board.move_stack:
            try: san = tmp.san(m)
            except:
                try: san = m.uci()
                except: san = "?"
            moves.append(san)
            try: tmp.push(m)
            except: break
    except: pass
    pairs = []
    for i in range(0, len(moves), 2):
        num = i // 2 + 1
        w = moves[i]
        b = moves[i+1] if i+1 < len(moves) else ""
        pairs.append((num, w, b))
    return pairs

def draw_move_history():
    global hist_scroll
    x = HIST_X; y = BOARD_Y; h = TILE * 8
    pygame.draw.rect(screen, PANEL_BG, (x, y, HIST_W, h), border_radius=10)
    pygame.draw.rect(screen, PANEL_BORDER, (x, y, HIST_W, h), 2, border_radius=10)
    title = font_small.render("MOVE HISTORY", True, (180, 180, 200))
    screen.blit(title, (x + 14, y + 10))
    hint = font_tiny.render("scroll: wheel", True, (120, 120, 140))
    screen.blit(hint, (x + HIST_W - hint.get_width() - 12, y + 12))
    pairs = get_move_pairs()
    total = len(pairs)
    visible = HIST_MAX_LINES
    max_scroll = max(0, total - visible)
    if hist_scroll > max_scroll: hist_scroll = max_scroll
    if hist_scroll < 0: hist_scroll = 0
    start = max(0, total - visible - hist_scroll) if total > visible else 0
    end = min(total, start + visible)
    line_y = y + 36
    for i in range(start, end):
        num, w, b = pairs[i]
        n = font_mono.render(f"{num:2d}.", True, (140, 140, 160))
        screen.blit(n, (x + 12, line_y))
        wt = font_mono.render(w, True, (240, 240, 240))
        screen.blit(wt, (x + 55, line_y))
        bt = font_mono.render(b, True, (200, 200, 210))
        screen.blit(bt, (x + 140, line_y))
        line_y += HIST_LINE_H
    if total > visible:
        bar_x = x + HIST_W - 10
        bar_top = y + 36
        bar_h = h - 46
        thumb_h = max(20, bar_h * visible // total)
        thumb_y = bar_top + (bar_h - thumb_h) * (max_scroll - hist_scroll) // max(1, max_scroll)
        pygame.draw.rect(screen, (60, 60, 75), (bar_x, bar_top, 6, bar_h), border_radius=3)
        pygame.draw.rect(screen, (140, 140, 170), (bar_x, thumb_y, 6, thumb_h), border_radius=3)

def draw_timers():
    bw, bh = 300, 80
    bx = BOARD_X + TILE * 4 - bw // 2
    by_top = BOARD_Y - 90
    by_bot = BOARD_Y + TILE * 8 + 28

    opp = get_current_opponent()

    if flipped:
        top_color = chess.WHITE if player_color == chess.BLACK else chess.BLACK
    else:
        top_color = chess.BLACK if player_color == chess.WHITE else chess.WHITE
    top_time = white_time if top_color == chess.WHITE else black_time
    is_top = board.turn == top_color and game_started

    # === Верхний таймер (соперник) ===
    color_bg = (60, 60, 90) if is_top else (30, 30, 40)
    pygame.draw.rect(screen, color_bg, (bx, by_top, bw, bh), border_radius=12)
    border_col = GOLD if is_top else PANEL_BORDER
    pygame.draw.rect(screen, border_col, (bx, by_top, bw, bh), 3 if is_top else 2, border_radius=12)

    av_size = 60
    av_x = bx + 10
    av_y = by_top + (bh - av_size) // 2

    if opp.get("avatar"):
        screen.blit(opp["avatar"], (av_x, av_y))
        pygame.draw.circle(screen, (200, 200, 200),
                           (av_x + av_size // 2, av_y + av_size // 2), av_size // 2, 2)
    else:
        # Stockfish — рисуем иконку
        pygame.draw.circle(screen, opp.get("color", (120, 120, 160)),
                           (av_x + av_size // 2, av_y + av_size // 2), av_size // 2)
        pygame.draw.circle(screen, (200, 200, 200),
                           (av_x + av_size // 2, av_y + av_size // 2), av_size // 2, 2)
        # Начальная буква
        letter = opp["name"][0] if opp["name"] else "?"
        lt = font_huge.render(letter, True, (255, 255, 255))
        screen.blit(lt, (av_x + av_size // 2 - lt.get_width() // 2,
                         av_y + av_size // 2 - lt.get_height() // 2))

    # Имя и стиль
    name_surf = font_small.render(opp["name"], True, (240, 240, 240))
    screen.blit(name_surf, (bx + 82, by_top + 12))

    # Флаг-кружок рядом с именем (справа от имени)
    flag_x = bx + 82 + name_surf.get_width() + 8
    draw_flag(flag_x, by_top + 12, 20, opp.get("flag", "AI"))

    style_surf = font_tiny.render(f"{opp.get('style', '')}  |  {opp.get('bio', '')}", True, (180, 180, 200))
    screen.blit(style_surf, (bx + 82, by_top + 42))

    time_col = GOLD if is_top else TEXT
    time_surf = font_big.render(format_time(top_time), True, time_col)
    screen.blit(time_surf, (bx + bw - time_surf.get_width() - 14,
                            by_top + bh // 2 - time_surf.get_height() // 2))

    # === Нижний таймер (игрок) ===
    bot_color = player_color
    bot_time = white_time if bot_color == chess.WHITE else black_time
    is_me = board.turn == bot_color and game_started

    color_bg = (90, 90, 60) if is_me else (30, 30, 40)
    pygame.draw.rect(screen, color_bg, (bx, by_bot, bw, bh), border_radius=12)
    border_col = GOLD if is_me else PANEL_BORDER
    pygame.draw.rect(screen, border_col, (bx, by_bot, bw, bh), 3 if is_me else 2, border_radius=12)

    if PLAYER_AVATAR:
        screen.blit(PLAYER_AVATAR, (av_x, by_bot + (bh - av_size) // 2))
        pygame.draw.circle(screen, (200, 200, 200),
                           (av_x + av_size // 2, by_bot + (bh - av_size) // 2 + av_size // 2),
                           av_size // 2, 2)
    else:
        pygame.draw.circle(screen, (100, 150, 100),
                           (av_x + av_size // 2, by_bot + (bh - av_size) // 2 + av_size // 2),
                           av_size // 2)
        pygame.draw.circle(screen, (200, 200, 200),
                           (av_x + av_size // 2, by_bot + (bh - av_size) // 2 + av_size // 2),
                           av_size // 2, 2)
        you_t = font_huge.render("Y", True, (255, 255, 255))
        screen.blit(you_t, (av_x + av_size // 2 - you_t.get_width() // 2,
                            by_bot + (bh - av_size) // 2 + av_size // 2 - you_t.get_height() // 2))

    you_name = font_small.render("You", True, (240, 240, 240))
    screen.blit(you_name, (bx + 82, by_bot + 12))
    side_txt = font_tiny.render(f"{'WHITE' if player_color == chess.WHITE else 'BLACK'}  |  Player", True, (180, 180, 200))
    screen.blit(side_txt, (bx + 82, by_bot + 42))

    time_col = GOLD if is_me else TEXT
    time_surf = font_big.render(format_time(bot_time), True, time_col)
    screen.blit(time_surf, (bx + bw - time_surf.get_width() - 14,
                            by_bot + bh // 2 - time_surf.get_height() // 2))

def draw_topbar():
    title_text = {
        STATE_STATS: "STATISTICS",
        STATE_SETTINGS: "SETTINGS",
        STATE_ANALYSIS: "GAME ANALYSIS",
    }.get(state, "CHESS TRAINER")
    title = font_title.render(title_text, True, HINT_COLOR)
    screen.blit(title, (26, 22))
    menu_btn_rect = pygame.Rect(WIDTH - 130, 22, 110, 38)
    mouse = pygame.mouse.get_pos()
    hover = menu_btn_rect.collidepoint(mouse)
    color = BTN_BG_HOVER if hover else BTN_BG
    pygame.draw.rect(screen, color, menu_btn_rect, border_radius=10)
    pygame.draw.rect(screen, BTN_BORDER, menu_btn_rect, 2, border_radius=10)
    mt = font_small.render("< MENU", True, TEXT)
    screen.blit(mt, (menu_btn_rect.centerx - mt.get_width()//2,
                     menu_btn_rect.centery - mt.get_height()//2))
    if state in (STATE_PUZZLE, STATE_VS_AI):
        flip_rect = pygame.Rect(WIDTH - 240, 22, 100, 38)
        hover = flip_rect.collidepoint(mouse)
        color = BTN_BG_HOVER if hover else BTN_BG
        pygame.draw.rect(screen, color, flip_rect, border_radius=10)
        pygame.draw.rect(screen, BTN_BORDER, flip_rect, 2, border_radius=10)
        ft = font_small.render("FLIP (F)", True, TEXT)
        screen.blit(ft, (flip_rect.centerx - ft.get_width()//2,
                         flip_rect.centery - ft.get_height()//2))

def go_to_menu():
    global state, game_started, ai_generation
    state = STATE_MENU
    game_started = False
    ai_generation += 1
    while not ai_result_queue.empty():
        try: ai_result_queue.get_nowait()
        except: break

def draw_flash():
    if flash_color and flash_timer > 0:
        t = flash_timer / 0.5
        alpha = int(min(160, t * 200))
        s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        s.fill((*flash_color, alpha))
        screen.blit(s, (0, 0))

def draw_popup():
    if popup_timer > 0:
        alpha = int(min(230, popup_timer * 400))
        pt = font_big.render(popup_text, True, HINT_COLOR)
        pad = 14
        surf = pygame.Surface((pt.get_width() + pad*2, pt.get_height() + pad),
                              pygame.SRCALPHA)
        surf.fill((40, 30, 10, alpha))
        bx = WIDTH // 2 - surf.get_width() // 2
        by = 80
        screen.blit(surf, (bx, by))
        screen.blit(pt, (bx + pad, by + pad // 2))

# ============ МЕНЮ ============
    MENU_BUTTONS = [ ]
def draw_menu():
    global MENU_BUTTONS
    screen.blit(MENU_GRADIENT, (0, 0))
    title = font_huge.render("CHESS TRAINER", True, HINT_COLOR)
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 40))
    subtitle = font_mid.render("Play against the greatest minds in chess history", True, (150, 150, 170))
    screen.blit(subtitle, (WIDTH // 2 - subtitle.get_width() // 2, 115))
    bw, bh = 420, 62
    bx = WIDTH // 2 - bw // 2
    by = 320
    gap = 18
    MENU_BUTTONS = [
        ("ONLINE PUZZLES (LICHESS)", bx, by - 80, bw, bh, "LICHESS"),
        ("PUZZLE TRAINING (300)", bx, by, bw, bh, STATE_PUZZLE),
        ("PLAY vs STOCKFISH", bx, by + (bh + gap) * 1, bw, bh, STATE_SETUP_STOCKFISH),
        ("PLAY vs LEGENDS", bx, by + (bh + gap) * 2, bw, bh, STATE_SETUP_LEGENDS),
        ("STATISTICS", bx, by + (bh + gap) * 3, bw, bh, STATE_STATS),
        ("SETTINGS", bx, by + (bh + gap) * 4, bw, bh, STATE_SETTINGS),
        ("QUIT", bx, by + (bh + gap) * 5, bw, bh, "QUIT"),
    ]
    mouse = pygame.mouse.get_pos()
    for label, x, y, w, h, action in MENU_BUTTONS:
        rect = pygame.Rect(x, y, w, h)
        hover = rect.collidepoint(mouse)
        color = BTN_BG_HOVER if hover else BTN_BG
        if hover:
            sh = pygame.Surface((w + 8, h + 8), pygame.SRCALPHA)
            pygame.draw.rect(sh, (0, 0, 0, 100), sh.get_rect(), border_radius=18)
            screen.blit(sh, (x - 4, y - 4 + 6))
        pygame.draw.rect(screen, color, rect, border_radius=14)
        pygame.draw.rect(screen, GOLD if hover else BTN_BORDER, rect, 2, border_radius=14)
        t = font_big.render(label, True, TEXT)
        screen.blit(t, (rect.centerx - t.get_width()//2,
                        rect.centery - t.get_height()//2))
    hint = font_small.render("F11: fullscreen", True, (120, 120, 140))
    screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 40))

def draw_setup_legends():
    global state, mode, current_bot_idx
    screen.blit(MENU_GRADIENT, (0, 0))
    title = font_huge.render("CHOOSE A LEGEND", True, GOLD)
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 25))
    sub = font_mid.render("Play against the greatest chess players of all time", True, (200, 200, 220))
    screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 95))

    card_w = 380
    card_h = 175
    gap_x = 30
    gap_y = 18
    total_w = 3 * card_w + 2 * gap_x
    bx_start = WIDTH // 2 - total_w // 2
    by_start = 145

    mouse = pygame.mouse.get_pos()
    pressed = pygame.mouse.get_pressed()[0]

    for i, bot in enumerate(BOTS):
        row = i // 3
        col = i % 3
        cx = bx_start + col * (card_w + gap_x)
        cy = by_start + row * (card_h + gap_y)
        rect = pygame.Rect(cx, cy, card_w, card_h)
        hover = rect.collidepoint(mouse)
        selected = (current_bot_idx == i)

        # Тень под карточкой (если hover или selected)
        if hover or selected:
            sh = pygame.Surface((card_w + 10, card_h + 10), pygame.SRCALPHA)
            pygame.draw.rect(sh, (0, 0, 0, 100), sh.get_rect(), border_radius=18)
            screen.blit(sh, (cx - 5, cy - 5 + 8))

        if selected:
            bg = (60, 90, 60)
        elif hover:
            bg = BTN_BG_HOVER
        else:
            bg = BTN_BG
        pygame.draw.rect(screen, bg, rect, border_radius=16)
        border_col = GOLD if selected else (BTN_BORDER if not hover else (200, 200, 220))
        pygame.draw.rect(screen, border_col, rect, 4 if selected else 2, border_radius=16)

        # Аватарка
        av_size = 110
        av_x = cx + 18
        av_y = cy + (card_h - av_size) // 2
        if bot.get("avatar"):
            big_av = pygame.transform.smoothscale(bot["avatar"], (av_size, av_size))
            screen.blit(big_av, (av_x, av_y))
            pygame.draw.circle(screen, (200, 200, 200),
                               (av_x + av_size // 2, av_y + av_size // 2),
                               av_size // 2, 2)
        else:
            pygame.draw.circle(screen, bot.get("color", (120, 120, 160)),
                               (av_x + av_size // 2, av_y + av_size // 2),
                               av_size // 2)
            pygame.draw.circle(screen, (200, 200, 200),
                               (av_x + av_size // 2, av_y + av_size // 2),
                               av_size // 2, 2)
            lt = font_huge.render(bot["name"][0], True, (255, 255, 255))
            screen.blit(lt, (av_x + av_size // 2 - lt.get_width() // 2,
                             av_y + av_size // 2 - lt.get_height() // 2))

        # Флаг рядом с аватаркой (в правом нижнем углу фото)
        flag_x = av_x + av_size - 32
        flag_y = av_y + av_size - 32
        draw_flag(flag_x, flag_y, 32, bot["flag"])

        # Имя и инфо
        name_x = cx + 145
        nm = font_big.render(bot["name"], True, (255, 255, 255))
        screen.blit(nm, (name_x, cy + 14))

        # Пиковый рейтинг
        peak_t = font_small.render(f"Peak ELO  {bot['peak_elo']}", True, GOLD)
        screen.blit(peak_t, (name_x, cy + 46))

        # Стиль игры
        style_t = font_tiny.render(f"{bot['style']}  •  {bot['years']}", True, (200, 200, 210))
        screen.blit(style_t, (name_x, cy + 74))

        # Короткое био
        bio_t = font_tiny.render(bot["bio"], True, (150, 150, 170))
        screen.blit(bio_t, (name_x, cy + 98))

        # Уровень игры в скобках
        play_t = font_tiny.render(f"Plays at ~{bot['play_elo']} ELO", True, (180, 200, 220))
        screen.blit(play_t, (name_x, cy + 122))

        if hover and pressed:
            current_bot_idx = i

    # Time control
    tt = font_big.render("TIME CONTROL", True, (200, 200, 220))
    screen.blit(tt, (WIDTH // 2 - tt.get_width() // 2, by_start + 2*(card_h + gap_y) + 25))
    tby = by_start + 2*(card_h + gap_y) + 65
    tw, th = 220, 50
    total_tw = 4 * tw + 3 * 15
    tbx = WIDTH // 2 - total_tw // 2
    time_names = ["Bullet", "Blitz", "Rapid", "Classical"]
    for i in range(4):
        rect = pygame.Rect(tbx + i * (tw + 15), tby, tw, th)
        hover = rect.collidepoint(mouse)
        selected = (i == 2)  # у нас всегда Rapid
        color = (90, 130, 90) if selected else (BTN_BG_HOVER if hover else BTN_BG)
        pygame.draw.rect(screen, color, rect, border_radius=10)
        pygame.draw.rect(screen, BTN_BORDER, rect, 2, border_radius=10)
        t = font_small.render(time_names[i], True, TEXT)
        screen.blit(t, (rect.centerx - t.get_width()//2,
                        rect.centery - t.get_height()//2))

    start_rect = pygame.Rect(WIDTH // 2 - 240, HEIGHT - 80, 220, 55)
    back_rect = pygame.Rect(WIDTH // 2 + 20, HEIGHT - 80, 220, 55)
    hover = start_rect.collidepoint(mouse)
    color = (100, 160, 100) if hover else (70, 120, 70)
    pygame.draw.rect(screen, color, start_rect, border_radius=10)
    pygame.draw.rect(screen, GOLD if hover else BTN_BORDER, start_rect, 2, border_radius=10)
    st2 = font_big.render("START", True, TEXT)
    screen.blit(st2, (start_rect.centerx - st2.get_width()//2,
                      start_rect.centery - st2.get_height()//2))
    if hover and pressed:
        global play_mode
        play_mode = "legend"
        start_vs_ai()
        mode = MODE_NORMAL
        state = STATE_VS_AI

    hover = back_rect.collidepoint(mouse)
    color = BTN_BG_HOVER if hover else BTN_BG
    pygame.draw.rect(screen, color, back_rect, border_radius=10)
    pygame.draw.rect(screen, BTN_BORDER, back_rect, 2, border_radius=10)
    bt = font_big.render("BACK", True, TEXT)
    screen.blit(bt, (back_rect.centerx - bt.get_width()//2,
                     back_rect.centery - bt.get_height()//2))
    if hover and pressed: go_to_menu()

def draw_setup_stockfish():
    global state, mode, current_stockfish_idx
    screen.blit(MENU_GRADIENT, (0, 0))
    title = font_huge.render("PLAY vs STOCKFISH", True, (150, 200, 255))
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 40))
    sub = font_mid.render("Choose engine difficulty", True, (180, 180, 200))
    screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 115))

    card_w = 260
    card_h = 220
    gap = 22
    total_w = 4 * card_w + 3 * gap
    bx_start = WIDTH // 2 - total_w // 2
    by = 180

    mouse = pygame.mouse.get_pos()
    pressed = pygame.mouse.get_pressed()[0]

    for i, lvl in enumerate(STOCKFISH_LEVELS):
        cx = bx_start + i * (card_w + gap)
        rect = pygame.Rect(cx, by, card_w, card_h)
        hover = rect.collidepoint(mouse)
        selected = (current_stockfish_idx == i)

        # Тень
        if hover or selected:
            sh = pygame.Surface((card_w + 10, card_h + 10), pygame.SRCALPHA)
            pygame.draw.rect(sh, (0, 0, 0, 100), sh.get_rect(), border_radius=18)
            screen.blit(sh, (cx - 5, by - 5 + 8))

        if selected:
            bg = (50, 70, 100)
        elif hover:
            bg = BTN_BG_HOVER
        else:
            bg = BTN_BG
        pygame.draw.rect(screen, bg, rect, border_radius=16)
        border_col = (150, 200, 255) if selected else (BTN_BORDER if not hover else (200, 200, 220))
        pygame.draw.rect(screen, border_col, rect, 4 if selected else 2, border_radius=16)

        # Иконка робота
        cy_icon = by + 50
        pygame.draw.circle(screen, lvl["color"], (cx + card_w // 2, cy_icon), 40)
        pygame.draw.circle(screen, (240, 240, 240), (cx + card_w // 2, cy_icon), 40, 3)
        num = font_huge.render(str(i + 1), True, (255, 255, 255))
        screen.blit(num, (cx + card_w // 2 - num.get_width() // 2,
                          cy_icon - num.get_height() // 2))

        # Название
        nm = font_big.render(lvl["name"], True, (255, 255, 255))
        screen.blit(nm, (cx + card_w // 2 - nm.get_width() // 2, by + 100))

        # ELO
        elo_t = font_mid.render(f"ELO {lvl['elo']}", True, GOLD)
        screen.blit(elo_t, (cx + card_w // 2 - elo_t.get_width() // 2, by + 135))

        # Уровень
        lvl_t = font_tiny.render(f"Difficulty {i+1} of 4", True, (180, 180, 200))
        screen.blit(lvl_t, (cx + card_w // 2 - lvl_t.get_width() // 2, by + 170))

        if hover and pressed:
            current_stockfish_idx = i

    start_rect = pygame.Rect(WIDTH // 2 - 240, HEIGHT - 80, 220, 55)
    back_rect = pygame.Rect(WIDTH // 2 + 20, HEIGHT - 80, 220, 55)
    hover = start_rect.collidepoint(mouse)
    color = (100, 160, 100) if hover else (70, 120, 70)
    pygame.draw.rect(screen, color, start_rect, border_radius=10)
    pygame.draw.rect(screen, (150, 200, 255) if hover else BTN_BORDER, start_rect, 2, border_radius=10)
    st2 = font_big.render("START", True, TEXT)
    screen.blit(st2, (start_rect.centerx - st2.get_width()//2,
                      start_rect.centery - st2.get_height()//2))
    if hover and pressed:
        global play_mode
        play_mode = "stockfish"
        start_vs_ai()
        mode = MODE_NORMAL
        state = STATE_VS_AI

    hover = back_rect.collidepoint(mouse)
    color = BTN_BG_HOVER if hover else BTN_BG
    pygame.draw.rect(screen, color, back_rect, border_radius=10)
    pygame.draw.rect(screen, BTN_BORDER, back_rect, 2, border_radius=10)
    bt = font_big.render("BACK", True, TEXT)
    screen.blit(bt, (back_rect.centerx - bt.get_width()//2,
                     back_rect.centery - bt.get_height()//2))
    if hover and pressed: go_to_menu()

def draw_stats():
    screen.blit(MENU_GRADIENT, (0, 0))
    title = font_huge.render("STATISTICS", True, HINT_COLOR)
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 80))
    lines = [
        f"Puzzles solved:       {stats.get('puzzles_solved', 0)} / {len(puzzles)}",
        f"Best streak:          {stats.get('best_streak', 0)}",
        f"Current streak:       {stats.get('current_streak', 0)}",
        f"Games won:            {stats.get('games_won', 0)}",
        f"Games lost:           {stats.get('games_lost', 0)}",
    ]
    y = 220
    for line in lines:
        t = font_big.render(line, True, TEXT)
        screen.blit(t, (WIDTH // 2 - t.get_width()//2, y))
        y += 55
    back_rect = pygame.Rect(WIDTH // 2 - 100, HEIGHT - 110, 200, 55)
    mouse = pygame.mouse.get_pos()
    hover = back_rect.collidepoint(mouse)
    color = BTN_BG_HOVER if hover else BTN_BG
    pygame.draw.rect(screen, color, back_rect, border_radius=10)
    pygame.draw.rect(screen, BTN_BORDER, back_rect, 2, border_radius=10)
    bt = font_mid.render("BACK", True, TEXT)
    screen.blit(bt, (back_rect.centerx - bt.get_width()//2,
                     back_rect.centery - bt.get_height()//2))
    if hover and pygame.mouse.get_pressed()[0]: go_to_menu()

def draw_settings():
    screen.blit(MENU_GRADIENT, (0, 0))
    title = font_huge.render("SETTINGS", True, HINT_COLOR)
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 80))
    t = font_big.render("THEME", True, (200, 200, 220))
    screen.blit(t, (WIDTH // 2 - t.get_width() // 2, 190))
    theme_names = list(THEMES.keys())
    mouse = pygame.mouse.get_pos()
    pressed = pygame.mouse.get_pressed()[0]
    bw = 200; bh = 80; gap = 20
    total_w = len(theme_names) * bw + (len(theme_names) - 1) * gap
    bx = WIDTH // 2 - total_w // 2
    by = 240
    for i, name in enumerate(theme_names):
        rect = pygame.Rect(bx + i * (bw + gap), by, bw, bh)
        hover = rect.collidepoint(mouse)
        selected = (settings["theme"] == name)
        th = THEMES[name]
        preview_size = 20
        pv_y = rect.y + 6
        pv_x = rect.x + bw // 2 - preview_size * 3 // 2
        for py in range(3):
            for px in range(3):
                c = th["LIGHT"] if (px + py) % 2 == 0 else th["DARK"]
                pygame.draw.rect(screen, c,
                    (pv_x + px * preview_size, pv_y + py * preview_size,
                     preview_size, preview_size))
        color_border = HINT_COLOR if selected else (BTN_BORDER if not hover else (200, 200, 220))
        pygame.draw.rect(screen, color_border, rect, 3, border_radius=10)
        nt = font_mid.render(name, True, TEXT)
        screen.blit(nt, (rect.centerx - nt.get_width()//2, rect.y + 70))
        if hover and pressed:
            apply_theme(name); show_popup(f"Theme: {name}")
    fs_y = by + bh + 60
    fs_label = "FULLSCREEN: " + ("ON" if settings.get("fullscreen") else "OFF")
    fs_rect = pygame.Rect(WIDTH // 2 - 200, fs_y, 400, 55)
    hover = fs_rect.collidepoint(mouse)
    color = (100, 160, 100) if settings.get("fullscreen") else (BTN_BG_HOVER if hover else BTN_BG)
    pygame.draw.rect(screen, color, fs_rect, border_radius=10)
    pygame.draw.rect(screen, BTN_BORDER, fs_rect, 2, border_radius=10)
    ft = font_big.render(fs_label, True, TEXT)
    screen.blit(ft, (fs_rect.centerx - ft.get_width()//2,
                     fs_rect.centery - ft.get_height()//2))
    if hover and pressed: toggle_fullscreen()
    back_rect = pygame.Rect(WIDTH // 2 - 100, HEIGHT - 90, 200, 55)
    hover = back_rect.collidepoint(mouse)
    color = BTN_BG_HOVER if hover else BTN_BG
    pygame.draw.rect(screen, color, back_rect, border_radius=10)
    pygame.draw.rect(screen, BTN_BORDER, back_rect, 2, border_radius=10)
    bt = font_mid.render("BACK", True, TEXT)
    screen.blit(bt, (back_rect.centerx - bt.get_width()//2,
                     back_rect.centery - bt.get_height()//2))
    if hover and pressed: go_to_menu()

def classify_loss(loss_cp):
    if loss_cp < 20: return "BEST", (120, 240, 120)
    if loss_cp < 50: return "EXCELLENT", (160, 240, 120)
    if loss_cp < 100: return "GOOD", (200, 240, 140)
    if loss_cp < 200: return "INACCURACY", (240, 220, 80)
    if loss_cp < 350: return "MISTAKE", (240, 160, 60)
    return "BLUNDER", (240, 80, 80)

def draw_analysis():
    screen.blit(MENU_GRADIENT, (0, 0))
    title = font_huge.render("GAME ANALYSIS", True, HINT_COLOR)
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 30))
    if not analysis_records:
        t = font_big.render("No moves analyzed.", True, (180, 180, 180))
        screen.blit(t, (WIDTH // 2 - t.get_width()//2, 200))
    else:
        hdr = font_small.render("#    Move      Eval       Verdict", True, (180, 180, 200))
        screen.blit(hdr, (280, 110))
        y = 140
        for rec in analysis_records:
            if y > HEIGHT - 100: break
            num, san, color, eval_b, eval_a, loss, verdict, vcolor = rec
            prefix = f"{num}." if color == chess.WHITE else f"{num}..."
            txt1 = font_mono.render(f"{prefix:>6} {san:<8}", True, (240, 240, 240))
            screen.blit(txt1, (280, y))
            txt2 = font_mono.render(f"{eval_a/100:+.1f}", True, (200, 200, 220))
            screen.blit(txt2, (510, y))
            txt3 = font_small.render(verdict, True, vcolor)
            screen.blit(txt3, (680, y))
            y += 26
    back_rect = pygame.Rect(WIDTH // 2 - 100, HEIGHT - 80, 200, 55)
    mouse = pygame.mouse.get_pos()
    hover = back_rect.collidepoint(mouse)
    color = BTN_BG_HOVER if hover else BTN_BG
    pygame.draw.rect(screen, color, back_rect, border_radius=10)
    pygame.draw.rect(screen, BTN_BORDER, back_rect, 2, border_radius=10)
    bt = font_mid.render("BACK", True, TEXT)
    screen.blit(bt, (back_rect.centerx - bt.get_width()//2,
                     back_rect.centery - bt.get_height()//2))
    if hover and pygame.mouse.get_pressed()[0]: go_to_menu()

def draw_puzzle_progress_bar():
    total = len(puzzles)
    if total == 0: return
    solved_count = stats.get('puzzles_solved', 0)
    pct = min(1.0, solved_count / total)
    bar_w = WIDTH - 80
    bar_h = 16
    bar_x = 40
    bar_y = HEIGHT - 24
    pygame.draw.rect(screen, (40, 40, 50), (bar_x, bar_y, bar_w, bar_h), border_radius=8)
    pygame.draw.rect(screen, (100, 200, 100),
                     (bar_x, bar_y, int(bar_w * pct), bar_h), border_radius=8)
    pygame.draw.rect(screen, PANEL_BORDER, (bar_x, bar_y, bar_w, bar_h), 2, border_radius=8)
    txt = font_tiny.render(f"PUZZLES SOLVED: {solved_count} / {total}", True, TEXT)
    screen.blit(txt, (bar_x + 10, bar_y - 20))

def draw_puzzle_ui():
    mt = font_mid.render("PUZZLE", True, HINT_COLOR)
    screen.blit(mt, (WIDTH - mt.get_width() - 350, 26))
    hint = font_small.render(
        "P: puzzle  N: vs AI  SPACE: next  F: flip  ESC: menu",
        True, (160, 160, 170))
    screen.blit(hint, (26, 64))
    if solved:
        st_text = "SOLVED! Press SPACE for next"
        st_color = (120, 240, 120)
    else:
        st_text = puzzle_status
        st_color = TEXT
    st = font_mid.render(st_text, True, st_color)
    screen.blit(st, (26, HEIGHT - 60))
    sc = font_mid.render(f"Score: {puzzle_score} / {puzzle_total_answered}",
                         True, HINT_COLOR)
    screen.blit(sc, (WIDTH - sc.get_width() - 26, HEIGHT - 60))
    draw_puzzle_progress_bar()

def draw_undo_button():
    rect = pygame.Rect(BOARD_X, BOARD_Y + TILE * 8 + 75, 140, 46)
    mouse = pygame.mouse.get_pos()
    hover = rect.collidepoint(mouse)
    can_undo = len(board.move_stack) > 0 and not ai_thinking and not board.is_game_over()
    color = (BTN_BG_HOVER if hover else BTN_BG) if can_undo else (40, 40, 50)
    pygame.draw.rect(screen, color, rect, border_radius=10)
    pygame.draw.rect(screen, BTN_BORDER if can_undo else (60, 60, 70), rect, 2, border_radius=10)
    t = font_small.render("UNDO (U)", True, TEXT if can_undo else (110, 110, 120))
    screen.blit(t, (rect.centerx - t.get_width() // 2,
                    rect.centery - t.get_height() // 2))

def draw_vs_ai_ui():
    opp = get_current_opponent()
    mt = font_mid.render("VS AI", True, (150, 200, 255))
    screen.blit(mt, (WIDTH - mt.get_width() - 350, 26))
    diff_surf = font_small.render(
        f"{opp['name']}  |  You: {'WHITE' if player_color == chess.WHITE else 'BLACK'}",
        True, HINT_COLOR)
    screen.blit(diff_surf, (WIDTH - diff_surf.get_width() - 26, 64))
    hint = font_small.render(
        "N: setup  U: undo  R: restart  F: flip  RMB: arrow  ESC: menu",
        True, (160, 160, 170))
    screen.blit(hint, (26, 64))
    if board.is_game_over():
        if board.is_checkmate():
            winner_black = board.turn == chess.BLACK
            you_won = (winner_black and player_color == chess.WHITE) or \
                      (not winner_black and player_color == chess.BLACK)
            st = f"CHECKMATE! You beat {opp['name']}!" if you_won else f"CHECKMATE! {opp['name']} won."
            col = (120, 240, 120) if you_won else (240, 100, 100)
        elif board.is_stalemate(): st, col = "Stalemate - draw", TEXT
        elif board.is_insufficient_material(): st, col = "Draw", TEXT
        else: st, col = "Game over", TEXT
    elif white_time <= 0 or black_time <= 0:
        you_lost = (white_time <= 0 and player_color == chess.WHITE) or \
                   (black_time <= 0 and player_color == chess.BLACK)
        st, col = ("TIME OUT! You lost.", (240, 100, 100)) if you_lost else \
                  ("TIME OUT! You won!", (120, 240, 120))
    elif board.is_check(): st, col = "CHECK!", (255, 120, 120)
    elif ai_thinking: st, col = f"{opp['name']} thinking...", (200, 200, 220)
    else: st, col = "Your move!", TEXT
    s = font_mid.render(st, True, col)
    screen.blit(s, (26, HEIGHT - 60))

def record_move_for_analysis(san, color, eval_before):
    analysis_records.append((board.fullmove_number, san, color,
                              eval_before, eval_before, 0, "…", (180, 180, 180)))

def undo_move():
    global board, last_move, selected_square, legal_targets, ai_thinking
    global eval_mate, current_eval_cp, arrows, ai_generation
    if ai_thinking: return
    if len(board.move_stack) == 0: return
    ai_generation += 1
    while not ai_result_queue.empty():
        try: ai_result_queue.get_nowait()
        except: break
    if len(board.move_stack) >= 2:
        board.pop(); board.pop()
    else:
        board.pop()
    last_move = None
    selected_square = None
    legal_targets = []
    arrows.clear()
    eval_mate = None; current_eval_cp = 0
    request_eval()
    show_popup("Undo")

def try_move(from_sq, to_sq):
    global board, last_move, selected_square, legal_targets, solved
    global puzzle_score, puzzle_total_answered, flash_color, flash_timer, move_index
    global puzzle_status, animations, stats
    global white_time, black_time, game_started
    global current_eval_cp, eval_mate, player_color, arrows

    candidates = [chess.Move(from_sq, to_sq),
                  chess.Move(from_sq, to_sq, promotion=chess.QUEEN)]
    chosen = None
    for m in candidates:
        if m in board.legal_moves:
            chosen = m; break
    if chosen is None: return False
    piece_before = board.piece_at(from_sq)
    if piece_before is None: return False
    piece_sym = piece_before.symbol()
    cap = board.piece_at(to_sq)
    cap_sym = cap.symbol() if cap else None
    try: san = board.san(chosen)
    except: san = chosen.uci()
    color = board.turn
    eval_before = current_eval_cp
    arrows.clear()

    if mode == MODE_PUZZLE and not solved:
        expected = current_moves[move_index] if move_index < len(current_moves) else None
        if chosen.uci() == expected:
            board.push(chosen)
            last_move = chosen
            selected_square = None; legal_targets = []
            start_anim(piece_sym, from_sq, to_sq, cap_sym)
            play_move_sound(cap_sym is not None)
            flash_color = (100, 240, 100); flash_timer = 0.5
            move_index += 1
            if move_index >= len(current_moves):
                solved = True; puzzle_status = "CORRECT!"
                puzzle_score += 1; puzzle_total_answered += 1
                stats['puzzles_solved'] = stats.get('puzzles_solved', 0) + 1
                stats['current_streak'] = stats.get('current_streak', 0) + 1
                if stats['current_streak'] > stats.get('best_streak', 0):
                    stats['best_streak'] = stats['current_streak']
                if current_puzzle_id is not None and \
                   current_puzzle_id not in stats['solved_puzzle_ids']:
                    stats['solved_puzzle_ids'].append(current_puzzle_id)
                save_stats()
            else:
                try:
                    opp = chess.Move.from_uci(current_moves[move_index])
                    if opp in board.legal_moves:
                        op_piece = board.piece_at(opp.from_square)
                        op_cap = board.piece_at(opp.to_square)
                        op_sym = op_piece.symbol() if op_piece else 'P'
                        op_cap_sym = op_cap.symbol() if op_cap else None
                        board.push(opp); last_move = opp
                        start_anim(op_sym, opp.from_square, opp.to_square, op_cap_sym)
                        move_index += 1
                        if move_index >= len(current_moves):
                            solved = True; puzzle_status = "CORRECT!"
                            puzzle_score += 1; puzzle_total_answered += 1
                            stats['puzzles_solved'] = stats.get('puzzles_solved', 0) + 1
                            if current_puzzle_id is not None and \
                               current_puzzle_id not in stats['solved_puzzle_ids']:
                                stats['solved_puzzle_ids'].append(current_puzzle_id)
                            save_stats()
                        else:
                            puzzle_status = "Correct! Keep going..."
                except: pass
            return True
        else:
            flash_color = (240, 60, 60); flash_timer = 0.5
            puzzle_status = "Wrong move. Try again."
            stats['current_streak'] = 0; save_stats()
            return True
    else:
        board.push(chosen)
        last_move = chosen
        selected_square = None; legal_targets = []
        start_anim(piece_sym, from_sq, to_sq, cap_sym)
        play_move_sound(cap_sym is not None)
        if game_started:
            record_move_for_analysis(san, color, eval_before)
        inc = 2
        if color == chess.WHITE: white_time += inc
        else: black_time += inc
        request_eval()
        return True

def finalize_analysis():
    global analysis_records
    if engine is None: return
    try:
        try: tmp = chess.Board(history_start_fen)
        except: tmp = chess.Board()
        new_records = []
        for m in board.move_stack:
            try: san = tmp.san(m)
            except:
                try: san = m.uci()
                except: san = "?"
            color = tmp.turn
            num = tmp.fullmove_number
            try:
                with engine_lock:
                    info = engine.analyse(tmp, chess.engine.Limit(time=0.15))
                sc = info["score"].pov(chess.WHITE)
                eval_before = sc.score(mate_score=10000) if not sc.is_mate() else (10000 if sc.mate()>0 else -10000)
            except: eval_before = 0
            try: tmp.push(m)
            except: break
            try:
                with engine_lock:
                    info = engine.analyse(tmp, chess.engine.Limit(time=0.15))
                sc = info["score"].pov(chess.WHITE)
                eval_after = sc.score(mate_score=10000) if not sc.is_mate() else (10000 if sc.mate()>0 else -10000)
            except: eval_after = 0
            if color == chess.WHITE: loss = max(0, eval_before - eval_after)
            else: loss = max(0, eval_after - eval_before)
            verdict, vcolor = classify_loss(loss)
            new_records.append((num, san, color, eval_before, eval_after,
                                loss, verdict, vcolor))
        analysis_records = new_records
    except Exception as e:
        print("finalize_analysis error:", e)

def toggle_fullscreen():
    global screen
    settings["fullscreen"] = not settings.get("fullscreen", False)
    save_settings()
    if settings["fullscreen"]:
        screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
    else:
        screen = pygame.display.set_mode((WIDTH, HEIGHT))

# ============ MAIN ============
def main():
    global selected_square, legal_targets, animations, flash_timer, flash_color
    global state, mode, board, last_move, ai_thinking, popup_timer, solved
    global white_time, black_time, last_tick, game_started
    global current_eval_cp, eval_mate, analysis_records, hist_scroll, player_color
    global screen, check_pulse, arrows, ai_thread, ai_generation, flipped

    load_pieces()
    load_avatars()
    load_puzzles()
    load_stats()
    last_tick = time.time()

    if settings.get("fullscreen"):
        try: screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
        except: pass

    clock = pygame.time.Clock()
    running = True
    right_click_start = None

    while running:
        dt = clock.tick(60) / 1000.0
        now = time.time()
        real_dt = now - last_tick
        last_tick = now
        check_pulse += dt

        for a in animations[:]:
            a['t'] += dt
            if a['t'] >= a['dur']:
                animations.remove(a)

        if flash_timer > 0: flash_timer -= dt
        if popup_timer > 0: popup_timer -= dt

        while not eval_result_queue.empty():
            try:
                val, is_mate = eval_result_queue.get_nowait()
                if is_mate:
                    eval_mate = val
                    current_eval_cp = 10000 if val > 0 else -10000
                else:
                    eval_mate = None
                    current_eval_cp = val
            except: break

        if state == STATE_VS_AI and game_started and not board.is_game_over():
            if board.turn == chess.WHITE:
                white_time -= real_dt
                if white_time <= 0:
                    white_time = 0
                    if player_color == chess.WHITE: stats['games_lost'] = stats.get('games_lost', 0) + 1
                    else: stats['games_won'] = stats.get('games_won', 0) + 1
                    save_stats()
            else:
                black_time -= real_dt
                if black_time <= 0:
                    black_time = 0
                    if player_color == chess.BLACK: stats['games_lost'] = stats.get('games_lost', 0) + 1
                    else: stats['games_won'] = stats.get('games_won', 0) + 1
                    save_stats()
        check_and_save_finished_game()
        if state == STATE_VS_AI and ai_thinking:
            if not ai_result_queue.empty():
                try: gen, mv = ai_result_queue.get_nowait()
                except: gen, mv = -1, None
                if gen == ai_generation and mv is not None and not board.is_game_over():
                    p = board.piece_at(mv.from_square)
                    c = board.piece_at(mv.to_square)
                    ps = p.symbol() if p else 'P'
                    cs = c.symbol() if c else None
                    try: san = board.san(mv)
                    except: san = mv.uci()
                    color = board.turn
                    eval_before = current_eval_cp
                    board.push(mv)
                    last_move = mv
                    start_anim(ps, mv.from_square, mv.to_square, cs)
                    play_move_sound(cs is not None)
                    inc = 2
                    if color == chess.WHITE: white_time += inc
                    else: black_time += inc
                    if game_started:
                        record_move_for_analysis(san, color, eval_before)
                    request_eval()
                    if board.is_game_over() and board.is_checkmate():
                        winner_black = board.turn == chess.BLACK
                        you_won = (winner_black and player_color == chess.WHITE) or \
                                  (not winner_black and player_color == chess.BLACK)
                        if you_won: stats['games_won'] = stats.get('games_won', 0) + 1
                        else: stats['games_lost'] = stats.get('games_lost', 0) + 1
                        save_stats()
                ai_thinking = False
            else:
                if ai_thread is None or not ai_thread.is_alive():
                    think_time = 0.3
                    if play_mode == "stockfish":
                        if current_stockfish_idx <= 1: think_time = 0.15
                        else: think_time = 0.6
                    else:
                        if current_bot_idx <= 2: think_time = 0.2
                        else: think_time = 0.5
                    ai_thread = threading.Thread(
                        target=ai_think_worker,
                        args=(ai_generation, board.copy(), think_time),
                        daemon=True)
                    ai_thread.start()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                toggle_fullscreen()
            if event.type == pygame.MOUSEWHEEL:
                if state in (STATE_PUZZLE, STATE_VS_AI):
                    hist_scroll += event.y
                    pairs = get_move_pairs()
                    max_scroll = max(0, len(pairs) - HIST_MAX_LINES)
                    hist_scroll = max(0, min(max_scroll, hist_scroll))

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if state in (STATE_PUZZLE, STATE_VS_AI, STATE_SETUP_LEGENDS,
                                 STATE_SETUP_STOCKFISH, STATE_STATS,
                                 STATE_SETTINGS, STATE_ANALYSIS):
                        go_to_menu()
                    else:
                        running = False
                if event.key == pygame.K_f and state in (STATE_PUZZLE, STATE_VS_AI):
                    flipped = not flipped
                if event.key == pygame.K_a and state == STATE_VS_AI:
                    if board.is_game_over():
                        finalize_analysis(); state = STATE_ANALYSIS
                if event.key == pygame.K_n and state in (STATE_PUZZLE, STATE_VS_AI):
                    mode = MODE_NORMAL; state = STATE_SETUP_LEGENDS
                if event.key == pygame.K_p and state in (STATE_PUZZLE, STATE_VS_AI):
                    mode = MODE_PUZZLE
                    puzzle_score = 0; puzzle_total_answered = 0
                    if load_next_puzzle():
                        state = STATE_PUZZLE
                if event.key == pygame.K_r and state in (STATE_PUZZLE, STATE_VS_AI):
                    if mode == MODE_PUZZLE: load_next_puzzle()
                    else: start_vs_ai()
                if event.key == pygame.K_u and state == STATE_VS_AI:
                    undo_move()
                if event.key == pygame.K_SPACE and state == STATE_PUZZLE and solved:
                    load_next_puzzle()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if state == STATE_MENU:
                    for label, x, y, w, h, action in MENU_BUTTONS:
                        if pygame.Rect(x, y, w, h).collidepoint(mx, my):
                            if action == "QUIT":
                                running = False
                            elif action == "LICHESS":
                                mode = MODE_PUZZLE
                                puzzle_score = 0
                                puzzle_total_answered = 0
                                show_popup("Loading from Lichess...", 2.0)
                                if load_lichess_puzzle():
                                    state = STATE_PUZZLE
                                else:
                                    show_popup("No internet or Lichess error", 2.5)
                            elif action == STATE_PUZZLE:
                                mode = MODE_PUZZLE
                                puzzle_score = 0; puzzle_total_answered = 0
                                if load_next_puzzle():
                                    state = STATE_PUZZLE
                                else:
                                    show_popup("Failed to load puzzle", 3.0)
                            elif action == STATE_SETUP_LEGENDS:
                                state = STATE_SETUP_LEGENDS
                            elif action == STATE_SETUP_STOCKFISH:
                                state = STATE_SETUP_STOCKFISH
                            elif action == STATE_STATS: state = STATE_STATS
                            elif action == STATE_SETTINGS: state = STATE_SETTINGS
                            break
                elif state in (STATE_STATS, STATE_SETTINGS, STATE_ANALYSIS):
                    back_rect = pygame.Rect(WIDTH // 2 - 100, HEIGHT - 110, 200, 55)
                    if back_rect.collidepoint(mx, my): go_to_menu()
                elif state in (STATE_PUZZLE, STATE_VS_AI):
                    menu_rect = pygame.Rect(WIDTH - 130, 22, 110, 38)
                    if menu_rect.collidepoint(mx, my):
                        go_to_menu(); continue
                    flip_rect = pygame.Rect(WIDTH - 240, 22, 100, 38)
                    if flip_rect.collidepoint(mx, my):
                        flipped = not flipped; continue
                    if state == STATE_VS_AI:
                        undo_rect = pygame.Rect(BOARD_X, BOARD_Y + TILE * 8 + 75, 140, 46)
                        if undo_rect.collidepoint(mx, my):
                            undo_move(); continue
                        if board.is_game_over():
                            btn = pygame.Rect(BOARD_X + 160, BOARD_Y + TILE*8 + 75, 320, 46)
                            if btn.collidepoint(mx, my):
                                finalize_analysis(); state = STATE_ANALYSIS; continue
                    if animations: continue
                    if state == STATE_VS_AI and ai_thinking: continue
                    if state == STATE_VS_AI and board.is_game_over(): continue
                    if state == STATE_PUZZLE and solved: continue
                    if state == STATE_VS_AI and board.turn != player_color: continue
                    sq = xy_to_square(mx, my)
                    if sq is None: continue
                    if selected_square is None:
                        piece = board.piece_at(sq)
                        if piece and piece.color == board.turn:
                            selected_square = sq
                            legal_targets = [m.to_square for m in board.legal_moves
                                             if m.from_square == sq]
                    else:
                        if sq == selected_square:
                            selected_square = None; legal_targets = []
                        else:
                            ok = try_move(selected_square, sq)
                            if not ok:
                                piece = board.piece_at(sq)
                                if piece and piece.color == board.turn:
                                    selected_square = sq
                                    legal_targets = [m.to_square for m in board.legal_moves
                                                     if m.from_square == sq]
                                else:
                                    selected_square = None; legal_targets = []
                            if state == STATE_VS_AI and board.turn != player_color \
                               and not board.is_game_over():
                                ai_thinking = True

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                if state in (STATE_PUZZLE, STATE_VS_AI):
                    sq = xy_to_square(event.pos[0], event.pos[1])
                    if sq is not None: right_click_start = sq
            if event.type == pygame.MOUSEBUTTONUP and event.button == 3:
                if state in (STATE_PUZZLE, STATE_VS_AI) and right_click_start is not None:
                    sq = xy_to_square(event.pos[0], event.pos[1])
                    if sq is not None and sq != right_click_start:
                        arrows.append((right_click_start, sq))
                    right_click_start = None
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if arrows: arrows.clear()

        if state == STATE_MENU: draw_menu()
        elif state == STATE_SETUP_LEGENDS: draw_setup_legends()
        elif state == STATE_SETUP_STOCKFISH: draw_setup_stockfish()
        elif state == STATE_STATS: draw_stats()
        elif state == STATE_SETTINGS: draw_settings()
        elif state == STATE_ANALYSIS: draw_analysis()
        elif state in (STATE_PUZZLE, STATE_VS_AI):
            screen.blit(BG_GRADIENT, (0, 0))
            draw_topbar()
            if state == STATE_PUZZLE: draw_puzzle_ui()
            else: draw_vs_ai_ui()
            draw_board_bg()
            draw_highlights()
            draw_pieces()
            draw_board_labels()
            draw_eval_bar()
            draw_move_history()
            if state == STATE_VS_AI:
                draw_timers()
                draw_undo_button()
                if board.is_game_over():
                    btn = pygame.Rect(BOARD_X + 160, BOARD_Y + TILE*8 + 75, 320, 46)
                    mouse = pygame.mouse.get_pos()
                    hover = btn.collidepoint(mouse)
                    color = BTN_BG_HOVER if hover else BTN_BG
                    pygame.draw.rect(screen, color, btn, border_radius=10)
                    pygame.draw.rect(screen, BTN_BORDER, btn, 2, border_radius=10)
                    bt = font_mid.render("GAME ANALYSIS", True, TEXT)
                    screen.blit(bt, (btn.centerx - bt.get_width()//2,
                                     btn.centery - bt.get_height()//2))
            draw_flash()
            draw_popup()

        pygame.display.flip()

    if engine: engine.quit()
    pygame.quit()
# ============ ОТПРАВКА НА СЕРВЕР ============
_last_saved_game_token = None

def save_game_to_server(opponent_name, result, moves_str):
    """Отправляет партию на сервер в БД."""
    try:
        import json
        data = json.dumps({
            "player_name": "You",
            "opponent": opponent_name,
        }).encode('utf-8')
        req = urllib.request.Request(
            "http://127.0.0.1:8000/api/v1/games",
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            print(f"[SERVER] Game saved! Status {resp.status}")
            return True
    except Exception as e:
        print(f"[SERVER] Save failed: {e}")
        return Fals
def check_and_save_finished_game():
    global _last_saved_game_token
    if state != STATE_VS_AI:
        return
    if not board.is_game_over():
        return
    token = len(board.move_stack)
    if token == 0:
        return
    if _last_saved_game_token == token:
        return
    _last_saved_game_token = token

    try:
        opponent_name = get_current_opponent()["name"]
        moves_str = " ".join([m.uci() for m in board.move_stack])
        success = save_game_to_server(opponent_name, "finished", moves_str)
        if success:
            show_popup("Game saved to server!", 2.5)
        else:
            show_popup("Server offline", 2.5)
    except Exception as e:
        print(f"[SERVER] check error: {e}")


if __name__ == "__main__":
    main()