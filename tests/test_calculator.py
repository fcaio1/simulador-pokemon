"""Tests for src/calculator.py — hypergeometric probability calculator (TDD)."""

import math
import pytest

from src.calculator import (
    mulligan_probability,
    exactly_one_basic_probability,
    two_or_more_basics_probability,
    possible_starter_probability,
    forced_starter_probability,
    prize_probability,
    draw_by_turn_probability,
    supporter_turn1_probability,
    dead_hand_probability,
    specific_card_in_hand_probability,
    searcher_probability,
    card_or_searcher_probability,
    target_card_with_searches_probability,
)

TOLERANCE = 0.0001


# ---------------------------------------------------------------------------
# Known-value tests
# ---------------------------------------------------------------------------


def test_mulligan_probability_known_value() -> None:
    """P(no basic in opening 7) for N=60, b=10 should be ~0.2586."""
    result = mulligan_probability(deck_size=60, total_basics=10)
    assert abs(result - 0.2586) < TOLERANCE


def test_exactly_one_basic_probability_known_value() -> None:
    """P(exactly 1 basic | no mulligan) for N=60, b=10 should be ~0.5550."""
    result = exactly_one_basic_probability(deck_size=60, total_basics=10)
    assert abs(result - 0.5550) < TOLERANCE


def test_two_or_more_basics_probability_known_value() -> None:
    """P(2+ basics | no mulligan) for N=60, b=10 should be ~0.4450."""
    result = two_or_more_basics_probability(deck_size=60, total_basics=10)
    assert abs(result - 0.4450) < TOLERANCE


def test_possible_starter_probability_known_value() -> None:
    """P(at least 1 copy in opening 7 | no mulligan) for N=60, b=10, x=4 should be ~0.5389."""
    result = possible_starter_probability(deck_size=60, total_basics=10, card_copies=4)
    assert abs(result - 0.5389) < TOLERANCE


def test_forced_starter_probability_known_value() -> None:
    """P(at least 1 copy AND 0 other basics | no mulligan) for N=60, b=10, x=4 should be ~0.2697."""
    result = forced_starter_probability(deck_size=60, total_basics=10, card_copies=4)
    assert abs(result - 0.2697) < TOLERANCE


def test_prize_probability_known_value() -> None:
    """P(at least 1 copy in 6 prize cards) for N=60, x=4 should be ~0.3515."""
    result = prize_probability(deck_size=60, card_copies=4)
    assert abs(result - 0.3515) < TOLERANCE


def test_specific_card_in_hand_known_value() -> None:
    """P(at least 1 copy in opening 7) for N=60, x=4 should be ~0.3995."""
    result = specific_card_in_hand_probability(deck_size=60, card_copies=4)
    assert abs(result - 0.3995) < TOLERANCE


def test_supporter_turn1_probability_high() -> None:
    """P(at least 1 supporter in opening 7) for N=60, s=16 should be > 0.9."""
    result = supporter_turn1_probability(deck_size=60, supporter_count=16)
    assert result > 0.9


def test_dead_hand_probability_low() -> None:
    """P(0 supporters AND 0 energy in opening 7) for N=60, s=16, e=12 should be < 0.02."""
    result = dead_hand_probability(deck_size=60, supporter_count=16, energy_count=12)
    assert result < 0.02


def test_card_or_searcher_greater_than_card_alone() -> None:
    """P(card OR searcher) for N=60, x=2, s=8 should exceed P(card alone)."""
    card_alone = specific_card_in_hand_probability(deck_size=60, card_copies=2)
    combined = card_or_searcher_probability(deck_size=60, card_copies=2, searcher_copies=8)
    assert combined > card_alone


# ---------------------------------------------------------------------------
# Relationship / invariant tests
# ---------------------------------------------------------------------------


def test_exactly_one_plus_two_or_more_equals_one() -> None:
    """P(exactly 1) + P(2+) must equal 1.0 (they partition the no-mulligan space)."""
    p1 = exactly_one_basic_probability(deck_size=60, total_basics=10)
    p2 = two_or_more_basics_probability(deck_size=60, total_basics=10)
    assert abs(p1 + p2 - 1.0) < 1e-9


def test_draw_by_turn_1_equals_specific_card_in_hand() -> None:
    """draw_by_turn(turn=1) must match specific_card_in_hand (same 7-card hand formula)."""
    turn1 = draw_by_turn_probability(deck_size=60, card_copies=4, turn=1)
    specific = specific_card_in_hand_probability(deck_size=60, card_copies=4)
    assert abs(turn1 - specific) < 1e-9


def test_draw_by_turn_increases_with_turns() -> None:
    """P(drawn by turn 3) must be strictly greater than P(drawn by turn 1)."""
    turn1 = draw_by_turn_probability(deck_size=60, card_copies=4, turn=1)
    turn3 = draw_by_turn_probability(deck_size=60, card_copies=4, turn=3)
    assert turn3 > turn1


def test_card_or_searcher_ge_specific_card() -> None:
    """P(card OR searcher) >= P(card alone) — adding a searcher never reduces probability."""
    card_alone = specific_card_in_hand_probability(deck_size=60, card_copies=2)
    combined = card_or_searcher_probability(deck_size=60, card_copies=2, searcher_copies=8)
    assert combined >= card_alone


def test_target_card_with_searches_matches_existing_formula() -> None:
    """The target-card helper should match the existing card/searcher calculation."""
    existing = card_or_searcher_probability(deck_size=60, card_copies=3, searcher_copies=4)
    helper = target_card_with_searches_probability(
        deck_size=60, target_card_copies=3, target_search_copies=4
    )
    assert helper == pytest.approx(existing, abs=1e-12)


# ---------------------------------------------------------------------------
# Boundary tests
# ---------------------------------------------------------------------------


def test_possible_starter_zero_copies_returns_zero() -> None:
    """P(at least 1 copy in hand | no mulligan) is 0 when there are 0 copies."""
    result = possible_starter_probability(deck_size=60, total_basics=10, card_copies=0)
    assert result == pytest.approx(0.0, abs=1e-9)


def test_prize_zero_copies_returns_zero() -> None:
    """P(at least 1 copy in prizes) is 0 when there are 0 copies."""
    result = prize_probability(deck_size=60, card_copies=0)
    assert result == pytest.approx(0.0, abs=1e-9)


def test_specific_card_in_hand_zero_copies_returns_zero() -> None:
    """P(at least 1 copy in opening 7) is 0 when there are 0 copies."""
    result = specific_card_in_hand_probability(deck_size=60, card_copies=0)
    assert result == pytest.approx(0.0, abs=1e-9)


def test_specific_card_in_hand_full_deck_approaches_one() -> None:
    """P(at least 1 copy in opening 7) approaches 1.0 when x equals deck_size."""
    result = specific_card_in_hand_probability(deck_size=60, card_copies=60)
    assert result == pytest.approx(1.0, abs=1e-9)


def test_prize_full_deck_approaches_one() -> None:
    """P(at least 1 copy in prizes) approaches 1.0 when x equals deck_size."""
    result = prize_probability(deck_size=60, card_copies=60)
    assert result == pytest.approx(1.0, abs=1e-9)


def test_mulligan_no_basics_returns_one() -> None:
    """P(mulligan) is 1.0 when there are 0 basics in a 60-card deck."""
    result = mulligan_probability(deck_size=60, total_basics=0)
    assert result == pytest.approx(1.0, abs=1e-9)


def test_mulligan_all_basics_returns_zero() -> None:
    """P(mulligan) is 0.0 when every card is a basic Pokemon."""
    result = mulligan_probability(deck_size=60, total_basics=60)
    assert result == pytest.approx(0.0, abs=1e-9)
