import numpy as np
import matplotlib.pyplot as plt
from treys import Card, Deck, Evaluator
import math
import time
import tkinter as tk
import threading
from get_game_data import read_game_state

# ==========================================================
# PARAMÈTRES TABLE
# ==========================================================

#Ancien modele
# alpha = 3
# beta = 0.85
EPSILON = 0.01
MAX_SIMS = 10_000

# ==========================================================
# MONTE CARLO ÉQUITÉ
# ==========================================================

def confidence_interval(p, n):
    return 1.96 * math.sqrt(p * (1 - p) / n)

def equity_monte_carlo(hero, board, n_players):
    evaluator = Evaluator()
    wins = ties = n = 0

    while True:
        for _ in range(1000):
            deck = Deck()

            for c in hero + board:
                deck.cards.remove(c)

            villains = [deck.draw(2) for _ in range(n_players)]
            full_board = board + deck.draw(5 - len(board))

            hero_score = evaluator.evaluate(full_board, hero)
            villain_scores = [evaluator.evaluate(full_board, v) for v in villains]

            best = min(villain_scores)

            if hero_score < best:
                wins += 1
            elif hero_score == best:
                ties += 1

        n += 1000
        equity = wins / n + ties / n / (n_players + 1)

        if confidence_interval(equity, n) <= EPSILON or n >= MAX_SIMS:
            return equity

# ==========================================================
# EV
# ==========================================================

# Ancien modele (plus complexe mais plus remunerateur)
# def compute_ev(equity, pot, bet, n_adv):
#
#     p_call = 1 / (1 + math.exp(alpha * (bet - beta)))
#     f = 1 - p_call   # probabilité qu'un joueur fold
#
#     ev = 0
#
#     for k in range(n_adv + 1):
#
#         # probabilité que k joueurs call
#         prob = math.comb(n_adv, k) * (p_call ** k) * (f ** (n_adv - k))
#
#         # EV si k joueurs call
#         ev_k = equity * (pot + (k + 1) * bet) - bet
#
#         ev += prob * ev_k
#
#     return ev

def compute_ev(equity, pot, bet, n_after):

    if bet <= 0:
        return equity * pot

    # joueurs derrière qui peuvent encore call
    q = 1 - bet / (pot + bet)

    # pot final attendu
    pot_final = pot + bet * (1 + n_after * q)

    # EV
    ev = equity * pot_final - bet

    return ev

# ==========================================================
# PLOT
# ==========================================================

plt.ion()
plt.style.use("dark_background")

fig = plt.figure(figsize=(8,6))

manager = plt.get_current_fig_manager()
manager.window.wm_geometry("+2000-600")

ax_plot = fig.add_subplot(2,1,1)
ax_text = fig.add_subplot(2,1,2)

def plot_ev(equity, pot, n_adv, pretty_board, pretty_hero):

    ax_plot.clear()
    ax_text.clear()

    if pot <= 0:
        return

    # if abs(pot - round(pot, 2)) > 0:
    #     pot = pot - 0.004
    #
    # elif pot > 10:
    #     pot = pot - 10
    #
    # if pot > 60:
    #     pot = pot - 60
    #
    #     if pot > 10:
    #         pot = pot - 100

    # -------------------------
    # CALCUL EV
    # -------------------------

    bets = np.linspace(0.01, pot * 3, 300)
    colors = plt.cm.viridis(np.linspace(0,1,n_adv+1))

    for i, k in enumerate(range(n_adv, -1, -1)):

        evs = [compute_ev(equity, pot, b, k) for b in bets]

        idx = np.argmax(evs)

        ax_plot.plot(bets, evs, label=f"{k} joueurs après", color=colors[i], linewidth=2)

        ax_plot.scatter(bets[idx], evs[idx], color=colors[i], s=30, edgecolors="black", zorder=3)


    ax_plot.axhline(0)

    ax_plot.set_xlabel("Mise (€)")
    ax_plot.set_ylabel("EV (€)")
    ax_plot.set_title("EV vs Mise")
    ax_plot.grid(True, color="blue", linestyle="--", alpha=0.5)

    # -------------------------
    # ETAT DU JEU
    # -------------------------

    text = (
        "ÉTAT DU JEU\n\n"
        f"Hero : {pretty_hero}\n"
        f"Board: {pretty_board}\n"
        f"Pot  : {pot}\n"
        f"Adv  : {n_adv}\n"
        f"Equity : {round(equity*100,1)} %"
    )

    ax_text.text(
        0.05,
        0.9,
        text,
        fontsize=12,
        verticalalignment='top',
        family='monospace'
    )

    ax_text.axis("off")

    fig.canvas.draw()
    plt.pause(0.001)

# ==========================================================
# FONCTION EQUITY
# ==========================================================

def run_equity():

    global manual_pot_value

    hero, board, pot, n_adv = read_game_state()

    if n_adv is None or n_adv < 1:
        n_adv = 1

    if pot is None:
        pot = 0.0

    pretty_hero = [Card.int_to_str(c) for c in hero]
    pretty_board = [Card.int_to_str(c) for c in board]

    if len(hero) == 2 and pot > 0:

        equity = equity_monte_carlo(hero, board, n_adv)
        #print(f"Équité : {equity:.2%}")

        plot_ev(equity, pot, n_adv, pretty_board, pretty_hero)

    else:
        print('manque data')

        print("\n--- ÉTAT ACTUEL ---")
        print("Hero :", pretty_hero)
        print("Board:", pretty_board)
        print("Pot  :", pot)
        print("Adv  :", n_adv)

# ==========================================================
# LOOP AUTOMATIQUE (1 seconde)
# ==========================================================

def auto_loop():
    run_equity()
    root.after(50, auto_loop)  # relance dans 1000 ms


root = tk.Tk()
root.withdraw()
root.after(50, auto_loop)
root.mainloop()