from treys import Card, Deck, Evaluator
import math
import random
import numpy as np
#import time
from functools import lru_cache
from montecarlo_loop import montecarlo_loop_cython
from create_postflop_range_database import create_postflop_all_hands_cython

def debug(msg):
    import os, sys
    print(f"[PID {os.getpid()}] {msg}", flush=True, file=sys.stdout)

# ==========================================================
# PARAMÈTRES TABLE
# ==========================================================

# Proba call adj
lambda_ = 0.2

# Tighness adv modele 1
delta = 0.8

# Equity param
EPSILON_equity = 0.05
MAX_SIMS = 10000

# ==========================================================
# MONTE CARLO ÉQUITÉ
# ==========================================================

def confidence_interval(p, n):
    return 1.96 * math.sqrt(p * (1 - p) / n)

def equity_monte_carlo(hero, board, n_players):
    evaluator = Evaluator()
    wins = ties = n = 0

    while True:
        for _ in range(500):
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

        n += 500
        equity = wins / n + ties / n / (n_players + 1)

        if confidence_interval(equity, n) <= EPSILON_equity or n >= MAX_SIMS:
            return equity

# ==========================================================
# RANGE DATABASE #PYTHON #C
# ==========================================================

def hand_to_str(hand):
    from treys import Card

    ranks = "23456789TJQKA"

    r1 = Card.get_rank_int(hand[0])
    r2 = Card.get_rank_int(hand[1])

    s1 = Card.get_suit_int(hand[0])
    s2 = Card.get_suit_int(hand[1])

    rank1 = ranks[r1]
    rank2 = ranks[r2]

    if r1 > r2:
        high, low = rank1, rank2
    else:
        high, low = rank2, rank1

    if r1 == r2:
        return high + low

    if s1 == s2:
        return high + low + "s"
    else:
        return high + low + "o"

@lru_cache(maxsize=1)
def load_preflop_bibliotheque():
    with open("preflop_librairy.txt", "r") as f:
        return [line.strip() for line in f if line.strip()]

def range_database(hero, board, range_strength):
    evaluator = Evaluator()
    base_deck = Deck()
    base_cards = [c for c in Deck().cards if c not in hero + board]
    all_hands = []

    if len(board)==0 :

        deck_cards = base_cards
        all_possible_hands = []

        for i in range(len(deck_cards)):
            for j in range(i+1, len(deck_cards)):
                all_possible_hands.append([deck_cards[i], deck_cards[j]])

        preflop_bibliotheque = load_preflop_bibliotheque()

        ranking_dict = {hand: i for i, hand in enumerate(preflop_bibliotheque)}
        ranked_hands = []

        for hand in all_possible_hands:
            h = hand_to_str(hand)
            if h in ranking_dict:
                ranked_hands.append((ranking_dict[h], hand))

        ranked_hands.sort(key=lambda x: x[0])
        cutoff = int(len(ranked_hands) * range_strength)
        range_villain = [hand for _, hand in ranked_hands[:cutoff]]

    else:

        # remplacer en c dans le fichier : "create_postflop_range_database
        # (for _ in range(1000):
        #     remaining_base = base_cards
        #     hand = random.sample(remaining_base, 2)
        #     remaining_after_hand = [c for c in remaining_base if c not in hand]
        #
        #     scores = []
        #
        #     for _ in range(50):
        #         draw = random.sample(remaining_after_hand, 5 - len(board) + 2)
        #         board_complete = board + draw[:5 - len(board)]
        #         score = evaluator.evaluate(board_complete, hand)
        #         scores.append(score)
        #
        #     avg_score = sum(scores) / len(scores)
        #     all_hands.append((avg_score, hand.copy())))

        all_hands = all_hands = create_postflop_all_hands_cython(base_cards, board, evaluator, 500, 30)
        all_hands.sort(key=lambda x: x[0])
        cutoff = int(len(all_hands) * range_strength)
        range_villain = [hand for _, hand in all_hands[:cutoff]]

    return range_villain

# ==========================================================
# MONTE CARLO ÉQUITÉ ADJ #PYTHON #C
# ==========================================================

def confidence_interval_adj(p, n):
    return 1.96 * math.sqrt(p * (1 - p) / n)

def pioche_database(deck, range_villain):
    while True:
        hand = random.choice(range_villain)
        c1, c2 = hand

        if len(range_villain)==0:
            debug("error range len")

        if c1 in deck.cards and c2 in deck.cards:
            deck.cards.remove(c1)
            deck.cards.remove(c2)
            return hand

def equity_monte_carlo_adj(hero, board, n_players, range_strength, range_database):

    evaluator = Evaluator()
    wins = ties = n = 0
    deck_initial = Deck()

    for c in hero + board:
        deck_initial.cards.remove(c)

    range_villain = range_database

    liste_cartes_range_villain = []

    for hand in range_villain:
        c1, c2 = hand
        liste_cartes_range_villain.append(c1)
        liste_cartes_range_villain.append(c2)

    cartes_disponibles = set(deck_initial.cards)
    main_possible = False

    for hand in range_villain:
        c1, c2 = hand

        if c1 in cartes_disponibles and c2 in cartes_disponibles:
            main_possible = True
            break

    if not main_possible:
        print("ERROR: aucune main de range_villain disponible dans le deck")
        print("hero:", hero)
        print("board:", board)
        #print("n_players:", n_players)
        print("range_strength:", range_strength)
        #print("len(range_villain):", len(range_villain))
        #print("liste_cartes_range_villain:", liste_cartes_range_villain)

        return 0.0666

    while True:

        # # remplacer en C dans le fichier monte carlo boucle boucle en anglaisd :
        # (for _ in range(100):
        #     deck = Deck()
        #     deck.cards = deck_initial.cards.copy()
        #     villains = [pioche_database(deck, range_villain) for _ in range(n_players)]
        #     full_board = board + deck.draw(5 - len(board))
        #     hero_score = evaluator.evaluate(full_board, hero)
        #     best_villain = float("inf")
        #
        #     for v in villains:
        #         score = evaluator.evaluate(full_board, v)
        #         if score < best_villain:
        #             best_villain = score
        #         if score < hero_score:
        #             break
        #
        #     if hero_score < best_villain:
        #         wins += 1
        #     elif hero_score == best_villain:
        #         ties += 1)

        w, t = montecarlo_loop_cython(deck_initial.cards, range_villain, board, hero, evaluator, n_players, 100); wins += w; ties += t
        n += 100
        equity = wins / n + ties / n / (n_players + 1)

        if confidence_interval_adj(equity, n) <= EPSILON_equity or n >= MAX_SIMS:
            return equity

# ==========================================================
# EV
# ==========================================================

# Modele 1 (plus complexe mais plus remunerateur)
def compute_ev_exploit(hero, board, pot, bet, n_after):

    MDF = (pot / (pot + bet)) * delta
    range_database_local = range_database(hero, board, MDF)

    ev = 0
    n_adv_max = 4

    if n_after == 4:

        for k in range(n_after + 1):

            p_call = 1 - (1 - MDF)**(1 / n_after)
            f = 1 - p_call

            # probabilité que k joueurs call
            prob = math.comb(n_after, k) * (p_call ** k) * (f ** (n_after - k))
            prob *= math.exp(-lambda_ * k * (k - 1) / 2)

            # tout le monde fold k = 0
            if k == 0:
                ev_k = pot

            else:
                # EV si k joueurs call
                equity = equity_monte_carlo_adj(hero, board, (k + 1), MDF, range_database_local)
                ev_k = equity * (pot + (k + 1) * bet) - bet

            ev += prob * ev_k

    else:

        n_players_already_call = n_adv_max - n_after

        if n_after != 0:
            p_call = 1 - (1 - MDF)**(1 / n_after)
            f = 1 - p_call

        else:
            p_call = 0
            f =0

        probs = []

        # 1. calcul des probas non normalisées
        for k in range(n_after + 1):
            prob = math.comb(n_after, k) * (p_call ** k) * (f ** (n_after - k))
            prob *= math.exp(-lambda_ * k * (k - 1) / 2)
            probs.append(prob)

        # 2. normalisation
        Z = sum(probs)
        probs = [p / Z for p in probs]

        # 3. calcul EV
        for k in range(n_after + 1):

            prob = probs[k]
            eq = equity_monte_carlo_adj(hero, board, (1 + n_players_already_call + k), MDF, range_database_local)
            final_pot = pot + (n_players_already_call + k + 1) * bet

            ev_k = eq * final_pot - bet

            ev += prob * ev_k

    return ev


# Modele 2 (moins complexe mais moins remunerateur)
def compute_ev_gto(hero, board, pot, bet, n_after):

    MDF = pot / (pot + bet)
    range_database_local = range_database(hero, board, MDF)

    ev = 0
    n_adv_max = 4

    if n_after == 4:

        for k in range(n_after + 1):

            p_call = 1 - (1 - MDF)**(1 / n_after)
            f = 1 - p_call

            # probabilité que k joueurs call
            prob = math.comb(n_after, k) * (p_call ** k) * (f ** (n_after - k))
            prob *= math.exp(-lambda_ * k * (k - 1) / 2)

            # tout le monde fold k = 0
            if k == 0:
                ev_k = pot

            else:
                # EV si k joueurs call
                equity = equity_monte_carlo_adj(hero, board, (k + 1), MDF, range_database_local)
                ev_k = equity * (pot + (k + 1) * bet) - bet

            ev += prob * ev_k

    else:

        n_players_already_call = n_adv_max - n_after

        if n_after != 0:
            p_call = 1 - (1 - MDF)**(1 / n_after)
            f = 1 - p_call

        else:
            p_call = 0
            f =0

        probs = []

        # 1. calcul des probas non normalisées
        for k in range(n_after + 1):
            prob = math.comb(n_after, k) * (p_call ** k) * (f ** (n_after - k))
            prob *= math.exp(-lambda_ * k * (k - 1) / 2)
            probs.append(prob)

        # 2. normalisation
        Z = sum(probs)
        probs = [p / Z for p in probs]

        # 3. calcul EV
        for k in range(n_after + 1):
            prob = probs[k]
            eq = equity_monte_carlo_adj(hero, board, (1 + n_players_already_call + k), MDF, range_database_local)
            final_pot = pot + (n_players_already_call + k + 1) * bet
            ev_k = eq * final_pot - bet
            ev += prob * ev_k

    return ev


# ==========================================================
# PLOT
# ==========================================================

def compute_exploit(hero, board, pot, n_adv, bets):
    results = {}
    best_ev = -1e9
    best_bet = 0

    for k in range(n_adv, -1, -1):
        evs = [compute_ev_exploit(hero, board, pot, b, k) for b in bets]
        idx = np.argmax(evs)

        results[k] = (evs, idx)

        if evs[idx] > best_ev:
            best_ev = evs[idx]
            best_bet = bets[idx]

    return results, best_ev, best_bet

def compute_gto(hero, board, pot, n_adv, bets):
    results = {}
    best_ev = -1e9
    best_bet = 0

    for k in range(n_adv, -1, -1):
        evs = [compute_ev_gto(hero, board, pot, b, k) for b in bets]
        idx = np.argmax(evs)

        results[k] = (evs, idx)

        if evs[idx] > best_ev:
            best_ev = evs[idx]
            best_bet = bets[idx]

    return results, best_ev, best_bet

def compute_equity(hero, board, n_adv):
    range_database_local_100 = range_database(hero, board, 1)
    range_database_local_075 = range_database(hero, board, 0.75)
    range_database_local_050 = range_database(hero, board, 0.5)
    range_database_local_025 = range_database(hero, board, 0.25)
    range_database_local_005 = range_database(hero, board, 0.05)

    return {
        "eq_non_adj": equity_monte_carlo(hero, board, n_adv),
        "eq100": equity_monte_carlo_adj(hero, board, n_adv, 1, range_database_local_100),
        "eq75": equity_monte_carlo_adj(hero, board, n_adv, 0.75, range_database_local_075),
        "eq50": equity_monte_carlo_adj(hero, board, n_adv, 0.5, range_database_local_050),
        "eq25": equity_monte_carlo_adj(hero, board, n_adv, 0.25, range_database_local_025),
        "eq5": equity_monte_carlo_adj(hero, board, n_adv, 0.05, range_database_local_005),
    }

def worker_block(args):
    func, params = args

    return func(*params)

def compute_all_functions(hero, board, pot, n_adv, bets, pool):

    tasks = [
        (compute_exploit, (hero, board, pot, n_adv, bets)),
        (compute_gto, (hero, board, pot, n_adv, bets)),
        (compute_equity, (hero, board, n_adv)),
    ]

    results = pool.map(worker_block, tasks)
    exploit_res = results[0]
    gto_res = results[1]
    equity_res = results[2]

    return exploit_res, gto_res, equity_res

def plot_ev(hero, board, pot, n_adv, pretty_board, pretty_hero):

    ax_plot_ev_gto.clear()
    ax_plot_ev_exploit.clear()
    ax_text.clear()

    if pot <= 0:
        return

    if abs(pot - round(pot, 2)) > 0:
        pot = pot - 0.004

    elif pot > 10:
        pot = pot - 10

    if pot > 60:
        pot = pot - 60

        if pot > 10:
            pot = pot - 10

    # -------------------------
    # PARAMS PLOT
    # -------------------------
    taille_pot_max = 2
    factor_taille_pot_max = 20
    granularity_curve = 6

    bets = np.linspace(0.001, min(taille_pot_max, pot*20), granularity_curve)
    ks = list(range(n_adv, -1, -1))
    colors = plt.cm.viridis(np.linspace(0, 1, n_adv+1))

    # -------------------------
    # MULTIPROCESSING (LES 3 BLOCS)
    # -------------------------
    print('start multi process')
    print(datetime.now().strftime('%H:%M:%S'))
    exploit_res, gto_res, equity_res = compute_all_functions(
        hero, board, pot, n_adv, bets, pool
    )
    print('end multi process')
    print(datetime.now().strftime('%H:%M:%S'))
    # =========================
    # PLOT EXPLOIT
    # =========================
    exploit_dict, best_ev_exploit, best_bet_exploit = exploit_res

    for i, k in enumerate(ks):
        evs, idx = exploit_dict[k]

        ax_plot_ev_exploit.plot(bets, evs, label=f"{k} joueurs après",
                               color=colors[i], linewidth=2)

        ax_plot_ev_exploit.scatter(bets[idx], evs[idx],
                                  color=colors[i], s=30,
                                  edgecolors="black", zorder=3)

        ax_plot_ev_exploit.axvline(bets[idx], linestyle="--", alpha=0.6)

        for j in range(len(evs)-1):
            if evs[j] * evs[j+1] < 0:
                ax_plot_ev_exploit.axvline(
                    bets[j], color="white", linestyle=":", alpha=0.8
                )

    ax_plot_ev_exploit.axhline(0)
    ax_plot_ev_exploit.set_xlabel("Mise (€)")
    ax_plot_ev_exploit.set_ylabel("EV exploit (€)")
    ax_plot_ev_exploit.set_title("EV exploit vs Mise")
    ax_plot_ev_exploit.grid(True, linestyle="--", alpha=0.5)

    # =========================
    # PLOT GTO
    # =========================
    gto_dict, best_ev_gto, best_bet_gto = gto_res

    for i, k in enumerate(ks):
        evs, idx = gto_dict[k]

        ax_plot_ev_gto.plot(bets, evs, label=f"{k} joueurs après",
                           color=colors[i], linewidth=2)

        ax_plot_ev_gto.scatter(bets[idx], evs[idx],
                              color=colors[i], s=30,
                              edgecolors="black", zorder=3)

        ax_plot_ev_gto.axvline(bets[idx], linestyle="--", alpha=0.6)

        for j in range(len(evs)-1):
            if evs[j] * evs[j+1] < 0:
                ax_plot_ev_gto.axvline(
                    bets[j], color="white", linestyle=":", alpha=0.8
                )

    ax_plot_ev_gto.axhline(0)
    ax_plot_ev_gto.set_xlabel("Mise (€)")
    ax_plot_ev_gto.set_ylabel("EV gto (€)")
    ax_plot_ev_gto.set_title("EV gto vs Mise")
    ax_plot_ev_gto.grid(True, linestyle="--", alpha=0.5)

    # =========================
    # TEXTE (EQUITY)
    # =========================
    equity_non_adj = equity_res["eq_non_adj"]
    equity_100 = equity_res["eq100"]
    equity_75 = equity_res["eq75"]
    equity_50 = equity_res["eq50"]
    equity_25 = equity_res["eq25"]
    equity_5 = equity_res["eq5"]

    text = (
        "ÉTAT DU JEU\n\n"
        f"Hero : {pretty_hero}\n"
        f"Board: {pretty_board}\n"
        f"Pot  : {round(pot,2)}\n"
        f"Adv  : {n_adv}\n\n"
        f"Equity_non_adj : {round(equity_non_adj*100,1)} %\n"
        f"Equity_100% : {round(equity_100*100,1)} %\n"
        f"Equity_75%  : {round(equity_75*100,1)} %\n"
        f"Equity_50%  : {round(equity_50*100,1)} %\n"
        f"Equity_25%  : {round(equity_25*100,1)} %\n"
        f"Equity_5%   : {round(equity_5*100,1)} %\n"
    )

    ax_text.text(
        0.05, 0.9, text,
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

    print("start recup data game")
    print(datetime.now().strftime('%H:%M:%S'))

    hero, board, pot, n_adv = read_game_state()
    #hero, board, pot, n_adv = [Card.new("Ah"), Card.new("Kd")], [Card.new("6d"), Card.new("As"), Card.new("Ad")], 0.3, 2
    #hero, board, pot, n_adv = [Card.new("6h"), Card.new("8d")], [], 0.01, 2
    #hero, board, pot, n_adv = [], [], 0.01, 2

    print("recup data game done")
    print(datetime.now().strftime('%H:%M:%S'))

    if n_adv is None or n_adv < 1:
        n_adv = 1

    if pot is None:
        pot = 0.0

    pretty_hero = [Card.int_to_str(c) for c in hero]
    pretty_board = [Card.int_to_str(c) for c in board]

    if len(hero) == 2 and pot > 0:

        plot_ev(hero, board, pot, n_adv, pretty_board, pretty_hero)

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
    root.after(50, auto_loop)  # relance dans 50 ms


# ==========================================================
# MAIN
# ==========================================================

if __name__ == "__main__":

    import matplotlib.pyplot as plt
    import time
    from datetime import datetime
    import os
    import tkinter as tk
    import threading
    import multiprocessing as mp
    from get_game_data import read_game_state
    pool = None

    pool = mp.Pool(mp.cpu_count() - 1)
    plt.ion()
    plt.style.use("dark_background")

    fig = plt.figure(figsize=(8,8))

    manager = plt.get_current_fig_manager()
    manager.window.wm_geometry("+2000-400")

    ax_plot_ev_exploit = fig.add_subplot(3,1,1)
    ax_plot_ev_gto = fig.add_subplot(3,1,2)
    ax_text = fig.add_subplot(3,1,3)
    fig.subplots_adjust(hspace=0.6)
    pos = ax_plot_ev_exploit.get_position()
    ax_text.set_position([pos.x0, pos.y0-0.52, pos.width, pos.height])

    root = tk.Tk()
    root.withdraw()
    root.after(50, auto_loop)
    root.mainloop()