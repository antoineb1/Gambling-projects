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


cpdef list create_postflop_all_hands_cython(
    list base_cards,
    list board,
    object evaluator,
    int n_hands=1000,
    int n_sims=50
):
    cdef int n_base = len(base_cards)
    cdef int board_len = len(board)
    cdef int missing_cards = 5 - board_len

    cdef int base_arr[52]
    cdef int remaining_arr[52]
    cdef int temp_arr[52]

    cdef int i, j, k, sim
    cdef int idx1, idx2
    cdef int hand0, hand1
    cdef int remaining_n
    cdef int temp_n
    cdef int r
    cdef int tmp

    cdef double total_score
    cdef double avg_score

    cdef list all_hands = []
    cdef list hand
    cdef list draw_cards
    cdef list board_complete

    seed_rand_once()

    # Convertit base_cards en tableau C
    for i in range(n_base):
        base_arr[i] = <int>base_cards[i]

    # Equivalent de : for _ in range(1000)
    for i in range(n_hands):

        # Tire 2 cartes différentes pour la main adverse
        idx1 = randint_c(n_base)
        idx2 = randint_c(n_base - 1)

        if idx2 >= idx1:
            idx2 += 1

        hand0 = base_arr[idx1]
        hand1 = base_arr[idx2]

        hand = [hand0, hand1]

        # Equivalent de :
        # remaining_after_hand = [c for c in base_cards if c not in hand]
        remaining_n = 0

        for j in range(n_base):
            if j != idx1 and j != idx2:
                remaining_arr[remaining_n] = base_arr[j]
                remaining_n += 1

        total_score = 0.0

        # Si le board est déjà complet
        if missing_cards == 0:
            avg_score = evaluator.evaluate(board, hand)

        else:

            # Equivalent de : for _ in range(50)
            for sim in range(n_sims):

                # On copie le deck restant pour faire un tirage sans remise
                temp_n = remaining_n

                for j in range(remaining_n):
                    temp_arr[j] = remaining_arr[j]

                draw_cards = []

                # Equivalent de :
                # draw = random.sample(remaining_after_hand, 5 - len(board))
                for k in range(missing_cards):
                    r = randint_c(temp_n)

                    draw_cards.append(temp_arr[r])

                    # Retire la carte tirée du deck temporaire
                    tmp = temp_arr[r]
                    temp_arr[r] = temp_arr[temp_n - 1]
                    temp_arr[temp_n - 1] = tmp

                    temp_n -= 1

                board_complete = board + draw_cards

                score = evaluator.evaluate(board_complete, hand)
                total_score += score

            avg_score = total_score / n_sims

        all_hands.append((avg_score, hand.copy()))

    return all_hands