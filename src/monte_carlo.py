"""Monte Carlo simulation for Pokemon TCG opening hand statistics."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from src.deck import Deck


def _build_deck_list(deck: "Deck") -> list[str]:
    """Build a flat list of card names repeated by quantity (60 items)."""
    return [card.name for card in deck.cards for _ in range(card.quantity)]


def _build_category_sets(deck: "Deck") -> tuple[set[str], set[str], set[str]]:
    """Return sets of basic pokemon names, supporter names, and energy names."""
    basics = {card.name for card in deck.cards if card.subcategory == "basic"}
    supporters = {
        card.name for card in deck.cards if card.subcategory == "supporter"
    }
    energies = {card.name for card in deck.cards if card.category == "energy"}
    return basics, supporters, energies


def _simulate_hand(
    deck_array: np.ndarray,
    rng: np.random.Generator,
    basics: set[str],
    supporters: set[str],
    energies: set[str],
) -> dict:
    """Simulate one opening hand and return condition flags."""
    shuffled = rng.permutation(deck_array)
    prize_list = list(shuffled[:6])
    hand = list(shuffled[6:13])

    hand_basics = [c for c in hand if c in basics]
    is_mulligan = len(hand_basics) == 0

    hand_supporters = [c for c in hand if c in supporters]
    hand_energies = [c for c in hand if c in energies]

    return {
        "is_mulligan": is_mulligan,
        "hand_basics": hand_basics,
        "hand_names": set(hand),
        "has_supporter": len(hand_supporters) > 0,
        "is_dead_hand": len(hand_supporters) == 0 and len(hand_energies) == 0,
        "prizes": prize_list,
    }


def simulate(deck: "Deck", n: int = 100_000, seed: int = 42, combo: list[str] | None = None) -> dict:
    """
    Simulate n opening hands and return empirical probabilities.

    Returns dict with keys:
        mulligan_rate        - fraction of hands with no basic
        exactly_one_basic    - fraction (of non-mulligan hands) with exactly 1 basic
        two_or_more_basics   - fraction (of non-mulligan hands) with 2+ basics
        possible_starters    - dict: {pokemon_name: fraction} for each basic pokemon
        forced_starters      - dict: {pokemon_name: fraction} for each basic pokemon
        prize_rates          - dict: {card_name: fraction} at least 1 prized
        supporter_in_hand    - fraction of hands with at least 1 supporter
        dead_hand_rate       - fraction of hands with 0 supporters AND 0 energy
    """
    deck_list = _build_deck_list(deck)
    deck_array = np.array(deck_list)
    basics, supporters, energies = _build_category_sets(deck)
    all_card_names = list({card.name for card in deck.cards})
    basic_names = list(dict.fromkeys(
        card.name for card in deck.cards if card.subcategory == "basic"
    ))

    rng = np.random.default_rng(seed)
    combo_set = set(combo) if combo else set()

    mulligan_count = 0
    exactly_one_count = 0
    two_or_more_count = 0
    possible_starter_counts: dict[str, int] = {name: 0 for name in basic_names}
    forced_starter_counts: dict[str, int] = {name: 0 for name in basic_names}
    # Counts hands where at least 1 copy was prized (not total copies prized)
    prize_counts: dict[str, int] = {name: 0 for name in all_card_names}
    supporter_count = 0
    dead_hand_count = 0
    combo_hit_count = 0
    non_mulligan = 0

    for _ in range(n):
        result = _simulate_hand(deck_array, rng, basics, supporters, energies)

        # Prize rates and supporter/dead_hand are tracked over ALL simulations
        prized_names = set(result["prizes"])
        for name in prized_names:
            if name in prize_counts:
                prize_counts[name] += 1

        if result["has_supporter"]:
            supporter_count += 1
        if result["is_dead_hand"]:
            dead_hand_count += 1
        if combo_set and not result["is_mulligan"] and combo_set.issubset(result["hand_names"]):
            combo_hit_count += 1

        if result["is_mulligan"]:
            mulligan_count += 1
            continue

        non_mulligan += 1
        hand_basics = result["hand_basics"]
        unique_basics_in_hand = set(hand_basics)

        if len(hand_basics) == 1:
            exactly_one_count += 1
        else:
            two_or_more_count += 1

        for name in basic_names:
            if name in unique_basics_in_hand:
                possible_starter_counts[name] += 1
                if len(unique_basics_in_hand) == 1:
                    forced_starter_counts[name] += 1

    denom = non_mulligan if non_mulligan > 0 else 1

    return {
        "mulligan_rate": mulligan_count / n,
        "exactly_one_basic": exactly_one_count / denom,
        "two_or_more_basics": two_or_more_count / denom,
        "possible_starters": {
            name: possible_starter_counts[name] / denom for name in basic_names
        },
        "forced_starters": {
            name: forced_starter_counts[name] / denom for name in basic_names
        },
        "prize_rates": {name: prize_counts[name] / n for name in all_card_names},
        "supporter_in_hand": supporter_count / n,
        "dead_hand_rate": dead_hand_count / n,
        "combo_rate": combo_hit_count / denom if combo_set else None,
    }
