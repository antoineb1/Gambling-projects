from libc.stdlib cimport rand, srand
from libc.time cimport time


cdef bint _seeded = False


cdef void seed_rand_once():
    global _seeded

    if not _seeded:
        srand(<unsigned int>time(NULL))
        _seeded = True


cdef inline int randint_c(int n):
    return rand() % n


cdef int find_card_index(int deck_arr[52], int deck_n, int card):
    cdef int i

    for i in range(deck_n):
        if deck_arr[i] == card:
            return i

    return -1


cdef int remove_card_at_index(int deck_arr[52], int deck_n, int idx):
    deck_arr[idx] = deck_arr[deck_n - 1]
    return deck_n - 1


cpdef tuple montecarlo_loop_cython(
    list deck_initial_cards,
    list range_villain,
    list board,
    list hero,
    object evaluator,
    int n_players,
    int n_sims=100
):
    cdef int initial_n = len(deck_initial_cards)
    cdef int range_n = len(range_villain)
    cdef int board_len = len(board)
    cdef int missing_board_cards = 5 - board_len

    cdef int initial_deck_arr[52]
    cdef int deck_arr[52]

    cdef int sim
    cdef int i, j, k
    cdef int deck_n
    cdef int r
    cdef int idx0, idx1
    cdef int c0, c1
    cdef int attempt
    cdef int max_attempts = 1000

    cdef int hero_score
    cdef int villain_score
    cdef int best_villain

    cdef int wins = 0
    cdef int ties = 0

    cdef bint found_hand
    cdef bint valid_sim

    cdef list villains
    cdef list villain_hand
    cdef list candidate_hand
    cdef list full_board

    seed_rand_once()

    # Copy the initial Python deck into a C array once
    for i in range(initial_n):
        initial_deck_arr[i] = <int>deck_initial_cards[i]

    # Main Monte Carlo loop
    for sim in range(n_sims):

        # Reset deck from the initial deck
        deck_n = initial_n

        for i in range(initial_n):
            deck_arr[i] = initial_deck_arr[i]

        villains = []
        valid_sim = True

        # Draw villain hands from range_villain
        for j in range(n_players):

            found_hand = False

            for attempt in range(max_attempts):

                r = randint_c(range_n)
                candidate_hand = range_villain[r]

                c0 = <int>candidate_hand[0]
                c1 = <int>candidate_hand[1]

                idx0 = find_card_index(deck_arr, deck_n, c0)
                idx1 = find_card_index(deck_arr, deck_n, c1)

                if idx0 != -1 and idx1 != -1:

                    villain_hand = [c0, c1]
                    villains.append(villain_hand)

                    # Remove first villain card from deck
                    idx0 = find_card_index(deck_arr, deck_n, c0)
                    deck_n = remove_card_at_index(deck_arr, deck_n, idx0)

                    # Remove second villain card from deck
                    idx1 = find_card_index(deck_arr, deck_n, c1)
                    deck_n = remove_card_at_index(deck_arr, deck_n, idx1)

                    found_hand = True
                    break

            if not found_hand:
                valid_sim = False
                break

        if not valid_sim:
            continue

        # Complete the board
        full_board = list(board)

        for k in range(missing_board_cards):
            r = randint_c(deck_n)
            full_board.append(deck_arr[r])
            deck_n = remove_card_at_index(deck_arr, deck_n, r)

        # Evaluate hero
        hero_score = evaluator.evaluate(full_board, hero)

        best_villain = 1000000000

        # Evaluate villains
        for villain_hand in villains:
            villain_score = evaluator.evaluate(full_board, villain_hand)

            if villain_score < best_villain:
                best_villain = villain_score

            # Early stop: villain already beats hero
            if villain_score < hero_score:
                break

        if hero_score < best_villain:
            wins += 1

        elif hero_score == best_villain:
            ties += 1

    return wins, ties