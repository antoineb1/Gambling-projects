import cv2
import numpy as np
import mss
import pytesseract
import time
import win32gui
from ultralytics import YOLO
import match_templates

# ==========================================================
# CHARGEMENT MODÈLES
# ==========================================================

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ==========================================================
# CONFIGURATION FENÊTRE & ROI
# ==========================================================

WINDOW_NAME = "Playground"

ROI_board_1= (260, 270, 35, 60)
ROI_board_2= (340, 270, 30, 60)
ROI_board_3= (415, 270, 30, 60)
ROI_board_4= (492, 270, 30, 60)
ROI_board_5= (568, 270, 30, 60)

ROI_hero_1 = (398, 493, 35, 56)
ROI_hero_2 = (428, 493, 35, 56)

ROI_player_1= (60, 375, 110, 60)
ROI_player_2= (190, 80, 110, 60)
ROI_player_3= (600, 80, 110, 60)
ROI_player_4= (730, 375, 110, 60)

ROI_pot = (440, 395, 100, 45)

# faire roi players et dossier players

REFRESH_SEC = 0.1
UPSCALE = 2.0
CONF = 0.45

# ==========================================================
# OUTILS FENÊTRE WINDOWS
# ==========================================================

def get_window_rect(window_name):
    hwnd = win32gui.FindWindow(None, window_name)
    if hwnd == 0:
        return None
    return win32gui.GetWindowRect(hwnd)

# ==========================================================
# CAPTURE ROI DANS FENÊTRE
# ==========================================================

def capture_window_roi(window_name, roi):
    rect = get_window_rect(window_name)
    if rect is None:
        print("❌ Fenêtre non trouvée :", window_name)
        return None

    win_left, win_top, win_right, win_bottom = rect
    x, y, w, h = roi

    with mss.mss() as sct:
        monitor = {
            "left": win_left + x,
            "top":  win_top + y,
            "width": w,
            "height": h
        }
        img = np.array(sct.grab(monitor))
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

# ==========================================================
# DÉTECTION CARTES (YOLO + UPSCALE)
# ==========================================================

def detect_cards(img,template_dir, scales, threshold, draw):


    detected_cards,_, best_symbol = match_templates.match_templates(
        img,
        template_dir,
        scales,
        threshold,
        draw
    )

    return detected_cards , best_symbol



# ==========================================================
# OCR POT
# ==========================================================

def read_pot(img):

    if img is None:
        return None

    # Convertir en HSV
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Masque pixels lumineux (blanc + orange clair)
    lower = (0, 0, 150)
    upper = (180, 255, 255)
    mask = cv2.inRange(hsv, lower, upper)

    # Agrandir pour OCR
    mask = cv2.resize(mask, None, fx=2, fy=2)

    # OCR
    text = pytesseract.image_to_string(
        mask,
        config="--psm 7 -c tessedit_char_whitelist=0123456789.,"
    ).strip()

    try:
        return float(text.replace(",", "."))
    except:
        return None


# ==========================================================
# NORMES
# ==========================================================
from treys import Card

SUIT_MAP = {
    "pic": "s",
    "coeur": "h",
    "carreau": "d",
    "trefle": "c"
}

def clean_rank(r):
    if r is None:
        return None
    return r.split("_")[0]

def build_cards(numbers, symbols):
    cards = []

    for n, s in zip(numbers, symbols):
        if n is None or s is None:
            continue

        rank = clean_rank(n)
        suit = SUIT_MAP.get(s)

        if rank and suit:
            try:
                cards.append(Card.new(rank + suit))
            except:
                pass

    return cards



# ==========================================================
# LECTURE ÉTAT JEU
# ==========================================================

def read_game_state():
    # =============================
    # CAPTURE HERO
    # =============================
    img_hero_1 = capture_window_roi(WINDOW_NAME, ROI_hero_1)
    img_hero_2 = capture_window_roi(WINDOW_NAME, ROI_hero_2)

    hero_1, symbol_h1 = detect_cards(
        img_hero_1, "templates_color",
        scales=np.linspace(0.35, 0.95, 90),
        threshold=0.80, draw=True
    )

    hero_2, symbol_h2 = detect_cards(
        img_hero_2, "templates_color",
        scales=np.linspace(0.35, 0.95, 90),
        threshold=0.80, draw=True
    )

    hero_1, number_h1 = detect_cards(
        img_hero_1, "templates_number",
        scales=np.linspace(0.25, 0.95, 90),
        threshold=0.70, draw=True
    )

    hero_2, number_h2 = detect_cards(
        img_hero_2, "templates_number",
        scales=np.linspace(0.25, 0.95, 90),
        threshold=0.70, draw=True
    )

    if symbol_h1 == "carreau_hero":
        symbol_h1 = "carreau"

    if symbol_h2 == "carreau_hero":
        symbol_h2 = "carreau"

    hero_symbol = [symbol_h1, symbol_h2]
    hero_number = [number_h1, number_h2]

    # =============================
    # CAPTURE BOARD
    # =============================
    img_board_1 = capture_window_roi(WINDOW_NAME, ROI_board_1)
    img_board_2 = capture_window_roi(WINDOW_NAME, ROI_board_2)
    img_board_3 = capture_window_roi(WINDOW_NAME, ROI_board_3)
    img_board_4 = capture_window_roi(WINDOW_NAME, ROI_board_4)
    img_board_5 = capture_window_roi(WINDOW_NAME, ROI_board_5)

    board_imgs = [img_board_1, img_board_2, img_board_3, img_board_4, img_board_5]
    board_number = []
    board_symbol = []

    for img in board_imgs:
        cards, number = detect_cards(
            img, "templates_number",
            scales=np.linspace(0.25, 0.95, 90),
            threshold=0.70,
            draw=True
        )
        board_number.append(number)

    board_symbol = []

    for img in board_imgs:
        cards, symbol = detect_cards(
            img, "templates_color",
            scales=np.linspace(0.35, 0.95, 90),
            threshold=0.80,
            draw=True
        )
        board_symbol.append(symbol)

    # =============================
    # CAPTURE PLAYERS CALL
    # =============================
    img_player_1 = capture_window_roi(WINDOW_NAME, ROI_player_1)
    img_player_2 = capture_window_roi(WINDOW_NAME, ROI_player_2)
    img_player_3 = capture_window_roi(WINDOW_NAME, ROI_player_3)
    img_player_4 = capture_window_roi(WINDOW_NAME, ROI_player_4)

    board_imgs = [img_player_1, img_player_2, img_player_3, img_player_4]
    player_call = []

    for img in board_imgs:
        cards, call = detect_cards(
            img, "templates_call",
            scales=np.linspace(0.25, 0.95, 90),
            threshold=0.8,
            draw=True
        )
        player_call.append(call)

    # =============================
    # POT
    # =============================
    img_pot = capture_window_roi(WINDOW_NAME, ROI_pot)
    pot = read_pot(img_pot)

    if pot is None:
        pot = 0.0

    if abs(pot - round(pot, 2)) > 0:
        pot = pot - 0.004

    elif pot > 10:
        pot = pot - 10

    if pot > 60:
        pot = pot - 60

    # =============================
    # PRINT
    # =============================
    # print(board_number)
    # print(board_symbol)
    # print(hero_number)
    # print(hero_symbol)
    # print(pot)
    # print(player_call)
    # print("\n")

    # =============================
    # RETOUR ET MISE NORME
    # =============================
    hero = build_cards(hero_number, hero_symbol)
    board = build_cards(board_number, board_symbol)
    n_adv = sum(1 for p in player_call if p == "call")

    return hero, board, pot, n_adv

# ==========================================================
# MAIN LOOP
# ==========================================================

if __name__ == "__main__":

    print("📸 Capture Playground – appuie sur 'q' pour quitter")

    while True:
        read_game_state()

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

        time.sleep(REFRESH_SEC)

    cv2.destroyAllWindows()
