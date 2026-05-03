"""Hypergeometric probability calculator for Pokemon TCG deck statistics."""

import math


def _at_least_one(deck_size: int, card_copies: int, draw_size: int) -> float:
    """P(at least 1 copy of card_copies cards drawn in draw_size draws from deck_size)."""
    if card_copies <= 0:
        return 0.0
    if card_copies >= deck_size:
        return 1.0
    return 1.0 - math.comb(deck_size - card_copies, draw_size) / math.comb(deck_size, draw_size)


def mulligan_probability(deck_size: int, total_basics: int) -> float:
    """P(no basic in opening 7)."""
    if total_basics >= deck_size:
        return 0.0
    return math.comb(deck_size - total_basics, 7) / math.comb(deck_size, 7)


def exactly_one_basic_probability(deck_size: int, total_basics: int) -> float:
    """P(exactly 1 basic in opening 7 | no mulligan)."""
    p_no_mulligan = 1.0 - mulligan_probability(deck_size, total_basics)
    p_exactly_one_raw = (
        math.comb(total_basics, 1)
        * math.comb(deck_size - total_basics, 6)
        / math.comb(deck_size, 7)
    )
    return p_exactly_one_raw / p_no_mulligan


def two_or_more_basics_probability(deck_size: int, total_basics: int) -> float:
    """P(2+ basics in opening 7 | no mulligan)."""
    return 1.0 - exactly_one_basic_probability(deck_size, total_basics)


def possible_starter_probability(
    deck_size: int, total_basics: int, card_copies: int
) -> float:
    """P(at least 1 copy of this basic in opening 7 | no mulligan)."""
    if card_copies <= 0:
        return 0.0
    p_no_mulligan = 1.0 - mulligan_probability(deck_size, total_basics)
    p_raw = _at_least_one(deck_size, card_copies, 7)
    return p_raw / p_no_mulligan


def forced_starter_probability(
    deck_size: int, total_basics: int, card_copies: int
) -> float:
    """P(at least 1 copy of this basic AND 0 other basics in opening 7 | no mulligan)."""
    p_no_mulligan = 1.0 - mulligan_probability(deck_size, total_basics)
    other_basics = total_basics - card_copies
    limit = min(card_copies, 7)
    p_raw = sum(
        math.comb(card_copies, k) * math.comb(deck_size - total_basics, 7 - k)
        for k in range(1, limit + 1)
    ) / math.comb(deck_size, 7)
    # Subtract cases where other basics appear alongside this card
    # The formula already excludes other basics via C(N-b, 7-k): non-basic slots
    return p_raw / p_no_mulligan


def prize_probability(deck_size: int, card_copies: int) -> float:
    """P(at least 1 copy in prize cards — 6 cards drawn from deck)."""
    return _at_least_one(deck_size, card_copies, 6)


def draw_by_turn_probability(deck_size: int, card_copies: int, turn: int) -> float:
    """P(at least 1 copy drawn by turn T). Turn 1 = opening hand (7 cards seen)."""
    cards_seen = 6 + turn
    return _at_least_one(deck_size, card_copies, cards_seen)


def supporter_turn1_probability(deck_size: int, supporter_count: int) -> float:
    """P(at least 1 supporter in opening 7)."""
    return _at_least_one(deck_size, supporter_count, 7)


def dead_hand_probability(
    deck_size: int, supporter_count: int, energy_count: int
) -> float:
    """P(0 supporters AND 0 energy in opening 7)."""
    non_supporters_non_energy = deck_size - supporter_count - energy_count
    return math.comb(non_supporters_non_energy, 7) / math.comb(deck_size, 7)


def specific_card_in_hand_probability(deck_size: int, card_copies: int) -> float:
    """P(at least 1 copy of specific card in opening 7)."""
    return _at_least_one(deck_size, card_copies, 7)


def searcher_probability(deck_size: int, searcher_copies: int) -> float:
    """P(at least 1 searcher card in opening 7)."""
    return _at_least_one(deck_size, searcher_copies, 7)


def card_or_searcher_probability(
    deck_size: int, card_copies: int, searcher_copies: int
) -> float:
    """P(at least 1 copy of target card OR at least 1 searcher in opening 7)."""
    p_card = _at_least_one(deck_size, card_copies, 7)
    p_searcher = _at_least_one(deck_size, searcher_copies, 7)

    # P(card AND searcher) via inclusion-exclusion
    denom = math.comb(deck_size, 7)
    p_both_raw = sum(
        math.comb(card_copies, j)
        * math.comb(searcher_copies, k)
        * math.comb(deck_size - card_copies - searcher_copies, 7 - j - k)
        / denom
        for j in range(1, min(card_copies, 7) + 1)
        for k in range(1, min(searcher_copies, 7 - j) + 1)
    )
    return p_card + p_searcher - p_both_raw
