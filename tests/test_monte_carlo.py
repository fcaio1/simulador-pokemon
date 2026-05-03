"""Tests for src/monte_carlo.py — Monte Carlo simulation validation (TDD)."""

import pytest

from src.deck import Card, Deck
from src.monte_carlo import simulate
from src.calculator import (
    mulligan_probability,
    possible_starter_probability,
    forced_starter_probability,
    prize_probability,
    supporter_turn1_probability,
    dead_hand_probability,
)

TOLERANCE = 0.02
N = 100_000
SEED = 42


def make_test_deck() -> Deck:
    """60-card deck: 4 Abra (basic), 6 other basics, 10 other pokemon, 13 supporters, 20 items, 7 energy."""
    cards = [
        Card(4, "Abra", "MEG", "54", "pokemon", "basic"),
        Card(6, "OtherBasic", "XX", "1", "pokemon", "basic"),
        Card(10, "Stage1", "XX", "2", "pokemon", "other"),
        Card(13, "Iono", "PAL", "269", "trainer", "supporter"),
        Card(20, "Ultra Ball", "SVI", "196", "trainer", "item"),
        Card(7, "Psychic Energy", "SVE", "5", "energy", "basic_energy"),
    ]
    return Deck(cards)


@pytest.fixture(scope="module")
def simulation_result() -> dict:
    """Run simulation once and share across tests."""
    deck = make_test_deck()
    return simulate(deck, n=N, seed=SEED)


def test_dict_keys_exist(simulation_result: dict) -> None:
    """Result dict must contain all required keys."""
    required_keys = {
        "mulligan_rate",
        "exactly_one_basic",
        "two_or_more_basics",
        "possible_starters",
        "forced_starters",
        "prize_rates",
        "supporter_in_hand",
        "dead_hand_rate",
    }
    assert required_keys.issubset(simulation_result.keys())


def test_mulligan_rate_converges(simulation_result: dict) -> None:
    """Empirical mulligan rate must be within ±2% of hypergeometric value."""
    expected = mulligan_probability(60, 10)
    assert abs(simulation_result["mulligan_rate"] - expected) < TOLERANCE


def test_possible_starter_converges(simulation_result: dict) -> None:
    """Empirical possible_starter for Abra (4 copies) must converge within ±2%."""
    expected = possible_starter_probability(60, 10, 4)
    assert abs(simulation_result["possible_starters"]["Abra"] - expected) < TOLERANCE


def test_forced_starter_converges(simulation_result: dict) -> None:
    """Empirical forced_starter for Abra (4 copies) must converge within ±2%."""
    expected = forced_starter_probability(60, 10, 4)
    assert abs(simulation_result["forced_starters"]["Abra"] - expected) < TOLERANCE


def test_prize_rate_converges(simulation_result: dict) -> None:
    """Empirical prize rate for Abra (4 copies) must converge within ±2%."""
    expected = prize_probability(60, 4)
    assert abs(simulation_result["prize_rates"]["Abra"] - expected) < TOLERANCE


def test_supporter_in_hand_converges(simulation_result: dict) -> None:
    """Empirical supporter_in_hand must converge within ±2% of hypergeometric value."""
    deck = make_test_deck()
    total_supporters = sum(
        card.quantity for card in deck.cards if card.subcategory == "supporter"
    )
    expected = supporter_turn1_probability(60, total_supporters)
    assert abs(simulation_result["supporter_in_hand"] - expected) < TOLERANCE


def test_dead_hand_rate_converges(simulation_result: dict) -> None:
    """Empirical dead_hand_rate must converge within ±2% of hypergeometric value."""
    deck = make_test_deck()
    total_supporters = sum(
        card.quantity for card in deck.cards if card.subcategory == "supporter"
    )
    total_energy = sum(
        card.quantity for card in deck.cards if card.category == "energy"
    )
    expected = dead_hand_probability(60, total_supporters, total_energy)
    assert abs(simulation_result["dead_hand_rate"] - expected) < TOLERANCE


def test_seed_reproducibility() -> None:
    """Two calls with the same seed must produce identical results."""
    deck = make_test_deck()
    result_a = simulate(deck, n=10_000, seed=42)
    result_b = simulate(deck, n=10_000, seed=42)
    assert result_a["mulligan_rate"] == result_b["mulligan_rate"]
    assert result_a["possible_starters"]["Abra"] == result_b["possible_starters"]["Abra"]
    assert result_a["forced_starters"]["Abra"] == result_b["forced_starters"]["Abra"]


def test_duplicate_basic_names_do_not_break_probabilities() -> None:
    """Repeated entries of the same basic name should still yield a valid probability."""
    deck = Deck(
        [
            Card(2, "Dunsparce", "JTG", "120", "pokemon", "basic"),
            Card(1, "Dunsparce", "TEF", "128", "pokemon", "basic"),
            Card(7, "OtherBasic", "XX", "1", "pokemon", "basic"),
            Card(10, "Stage1", "XX", "2", "pokemon", "other"),
            Card(13, "Iono", "PAL", "269", "trainer", "supporter"),
            Card(20, "Ultra Ball", "SVI", "196", "trainer", "item"),
            Card(7, "Psychic Energy", "SVE", "5", "energy", "basic_energy"),
        ]
    )
    result = simulate(deck, n=20_000, seed=42)
    expected = possible_starter_probability(60, 10, 3)
    assert abs(result["possible_starters"]["Dunsparce"] - expected) < TOLERANCE
