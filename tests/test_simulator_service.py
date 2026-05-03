"""Tests for simulator_service build_report with multiple target cards."""

import pytest
from src.deck import Card, Deck
from src.simulator_service import build_report


def _make_deck() -> Deck:
    """Minimal 60-card deck for testing."""
    cards = [
        Card(quantity=4, name="Riolu", set_code="MEG", set_number="76",
             category="pokemon", subcategory="basic"),
        Card(quantity=3, name="Mega Lucario ex", set_code="MEG", set_number="77",
             category="pokemon", subcategory="other"),
        Card(quantity=5, name="Makuhita", set_code="MEG", set_number="72",
             category="pokemon", subcategory="basic"),
        Card(quantity=4, name="Ultra Ball", set_code="MEG", set_number="131",
             category="trainer", subcategory="item"),
        Card(quantity=4, name="Supporter Card", set_code="MEG", set_number="1",
             category="trainer", subcategory="supporter"),
        Card(quantity=40, name="Fighting Energy", set_code="MEE", set_number="6",
             category="energy", subcategory="basic_energy"),
    ]
    return Deck(cards)


def test_build_report_single_target_produces_three_rows():
    """Single target produces: P(target), P(searcher), P(target OR searcher)."""
    deck = _make_deck()
    report = build_report(
        deck=deck,
        target_card_names=["Riolu"],
        target_search_names=["Ultra Ball"],
        mc_simulations=0,
    )
    assert len(report.target_df) == 3
    assert "Riolu" in report.target_df.iloc[0]["Statistic"]


def test_build_report_multiple_targets_produces_extra_combined_row():
    """Two targets produce: P(A), P(B), P(any target), P(searcher), P(any OR searcher)."""
    deck = _make_deck()
    report = build_report(
        deck=deck,
        target_card_names=["Riolu", "Makuhita"],
        target_search_names=["Ultra Ball"],
        mc_simulations=0,
    )
    assert len(report.target_df) == 5
    statistics = list(report.target_df["Statistic"])
    assert any("Riolu" in s for s in statistics)
    assert any("Makuhita" in s for s in statistics)
    assert any("any target" in s for s in statistics)


def test_build_report_multiple_targets_combined_probability_is_higher():
    """P(any target) with 2 cards must be >= P of either alone."""
    deck = _make_deck()
    report_single = build_report(
        deck=deck,
        target_card_names=["Riolu"],
        target_search_names=[],
        mc_simulations=0,
    )
    report_multi = build_report(
        deck=deck,
        target_card_names=["Riolu", "Makuhita"],
        target_search_names=[],
        mc_simulations=0,
    )

    def _parse_pct(s: str) -> float:
        return float(s.strip("%")) / 100

    single_prob = _parse_pct(report_single.target_df.iloc[0]["Probability"])
    combined_row = report_multi.target_df[
        report_multi.target_df["Statistic"].str.contains("any target")
    ]
    combined_prob = _parse_pct(combined_row.iloc[0]["Probability"])
    assert combined_prob > single_prob


def test_build_report_empty_target_list_handled():
    """Empty target list should not crash — returns searcher rows only."""
    deck = _make_deck()
    report = build_report(
        deck=deck,
        target_card_names=[],
        target_search_names=["Ultra Ball"],
        mc_simulations=0,
    )
    assert report.target_df is not None
    assert len(report.target_df) >= 1
