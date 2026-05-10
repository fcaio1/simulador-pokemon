"""Helpers to turn a deck list into frontend-friendly simulator tables."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src import calculator as calc
from src import monte_carlo as mc
from src.api_client import enrich_deck
from src.deck import Deck
from src.parser import parse_deck_list

SAMPLE_DECK_LIST = """Pokémon: 20
1 Alakazam MEP 9
2 Alakazam MEG 56
4 Kadabra MEG 55
4 Abra MEG 54
3 Dudunsparce PRE 80
2 Dunsparce JTG 120
1 Dunsparce TEF 128
1 Psyduck MEP 7
1 Fezandipiti ex SFA 38
1 Shaymin DRI 10

Trainer: 33
1 Boss's Orders ASC 256
1 Boss's Orders PAL 265
1 Boss's Orders MEG 114
3 Rare Candy MEG 175
2 Battle Cage PFL 116
2 Battle Cage PFL 85
1 Sacred Ash POR 115
1 Eri TEF 146
3 Buddy-Buddy Poffin TEF 144
1 Buddy-Buddy Poffin ASC 184
2 Enhanced Hammer TWM 224
3 Poké Pad POR 81
1 Poké Pad POR 113
1 Lana's Aid TWM 155
4 Hilda WHT 84
4 Dawn PFL 87
1 Night Stretcher SFA 61
1 Wondrous Patch POR 117

Energy: 7
1 Enriching Energy SSP 191
4 Telepathic Psychic Energy POR 88
2 Psychic Energy MEE 5
"""


@dataclass
class SimulationReport:
    deck: Deck
    unknown_cards: list[str]
    opening_df: pd.DataFrame
    breakdown_df: pd.DataFrame
    starters_df: pd.DataFrame
    prizes_df: pd.DataFrame
    draw_df: pd.DataFrame
    support_df: pd.DataFrame
    target_df: pd.DataFrame
    comparison_df: pd.DataFrame | None


def _pct(value: float) -> str:
    return f"{value:.2%}"


def _quantity_for_name(deck: Deck, name: str) -> int:
    return sum(card.quantity for card in deck.cards if card.name == name)


def _quantity_for_names(deck: Deck, names: list[str]) -> int:
    wanted_names = set(names)
    return sum(card.quantity for card in deck.cards if card.name in wanted_names)


def build_deck(deck_list_text: str, cache_path: str = "card_cache.json") -> tuple[Deck, list[str]]:
    """Parse, enrich and return a Deck plus any unresolved card names."""
    parsed = parse_deck_list(deck_list_text)
    cards = enrich_deck(parsed, cache_path=cache_path)
    deck = Deck(cards)
    unknown_cards = [card.name for card in deck.cards if card.subcategory == "unknown"]
    return deck, unknown_cards


def build_report(
    deck: Deck,
    target_card_names: list[str],
    target_search_names: list[str],
    mc_simulations: int = 0,
    mc_seed: int = 42,
    mc_combo: list[str] | None = None,
) -> SimulationReport:
    """Build the simulator tables used by the frontend."""
    deck_size = deck.total_cards
    total_basics = deck.total_basics
    total_supporters = sum(
        card.quantity for card in deck.cards if card.subcategory == "supporter"
    )
    total_energy = sum(card.quantity for card in deck.cards if card.category == "energy")

    def _poke_stage(stage_val: str) -> int:
        return sum(
            card.quantity for card in deck.cards
            if card.category == "pokemon" and card.stage == stage_val
        )

    n_basic_poke  = _poke_stage("Basic")
    n_stage1      = _poke_stage("Stage1")
    n_stage2      = _poke_stage("Stage2")
    n_other_poke  = sum(
        card.quantity for card in deck.cards
        if card.category == "pokemon" and card.stage not in ("Basic", "Stage1", "Stage2")
    )

    breakdown_rows = [
        ("Pokémon", "Basic",    n_basic_poke),
        ("",        "Stage 1",  n_stage1),
        ("",        "Stage 2",  n_stage2),
    ]
    if n_other_poke:
        breakdown_rows.append(("", "Other", n_other_poke))
    breakdown_rows += [
        ("Trainer", "Item",      sum(card.quantity for card in deck.cards if card.subcategory == "item")),
        ("",        "Supporter", sum(card.quantity for card in deck.cards if card.subcategory == "supporter")),
        ("",        "Stadium",   sum(card.quantity for card in deck.cards if card.subcategory == "stadium")),
        ("",        "Tool",      sum(card.quantity for card in deck.cards if card.subcategory == "tool")),
        ("Energy",  "Basic",     sum(card.quantity for card in deck.cards if card.subcategory == "basic_energy")),
        ("",        "Special",   sum(card.quantity for card in deck.cards if card.subcategory == "special_energy")),
    ]

    breakdown_df = pd.DataFrame(breakdown_rows, columns=["Category", "Subcategory", "#"])

    opening_df = pd.DataFrame(
        {
            "Event": [
                "Mulligan (no Basic)",
                "Starting with exactly 1 Basic",
                "Starting with 2 or more Basics",
            ],
            "Probability": [
                _pct(calc.mulligan_probability(deck_size, total_basics)),
                _pct(calc.exactly_one_basic_probability(deck_size, total_basics)),
                _pct(calc.two_or_more_basics_probability(deck_size, total_basics)),
            ],
        }
    )

    starter_rows = []
    for card in deck.basic_pokemon:
        starter_rows.append(
            {
                "Pokémon": f"{card.name} ({card.set_code} #{card.set_number})",
                "Copies": card.quantity,
                "Possible Starter": _pct(
                    calc.possible_starter_probability(deck_size, total_basics, card.quantity)
                ),
                "Forced Starter": _pct(
                    calc.forced_starter_probability(deck_size, total_basics, card.quantity)
                ),
            }
        )
    starters_df = pd.DataFrame(starter_rows)

    prize_rows = []
    for card in deck.cards:
        prize_rows.append(
            {
                "Card": card.name,
                "Copies": card.quantity,
                "P(≥1 Prized)": _pct(calc.prize_probability(deck_size, card.quantity)),
            }
        )
    prizes_df = pd.DataFrame(prize_rows).sort_values(
        by=["Copies", "Card"], ascending=[False, True]
    )

    draw_rows = []
    for card in deck.cards:
        row = {"Card": card.name, "Copies": card.quantity}
        for turn in range(1, 7):
            row[f"Turn {turn}"] = _pct(
                calc.draw_by_turn_probability(deck_size, card.quantity, turn)
            )
        draw_rows.append(row)
    draw_df = pd.DataFrame(draw_rows)

    support_df = pd.DataFrame(
        {
            "Statistic": [
                "Supporter in opening hand",
                "Dead Hand (0 Supporter + 0 Energy)",
            ],
            "Probability": [
                _pct(calc.supporter_turn1_probability(deck_size, total_supporters)),
                _pct(calc.dead_hand_probability(deck_size, total_supporters, total_energy)),
            ],
        }
    )

    total_target_copies = _quantity_for_names(deck, target_card_names)
    target_search_total = _quantity_for_names(deck, target_search_names)

    target_rows = []
    for name in target_card_names:
        copies = _quantity_for_name(deck, name)
        target_rows.append({
            "Statistic": f"P({name} in opening hand)",
            "Probability": _pct(calc.specific_card_in_hand_probability(deck_size, copies)),
        })
    if len(target_card_names) > 1:
        target_rows.append({
            "Statistic": "P(any target in opening hand)",
            "Probability": _pct(
                calc.specific_card_in_hand_probability(deck_size, total_target_copies)
            ),
        })
    searcher_label = (
        f"P(Target search in hand) [{', '.join(target_search_names)}]"
        if target_search_names
        else "P(Target search in hand)"
    )
    target_rows.append({
        "Statistic": searcher_label,
        "Probability": _pct(calc.searcher_probability(deck_size, target_search_total)),
    })
    target_rows.append({
        "Statistic": "P(any target OR target search in hand)",
        "Probability": _pct(
            calc.target_card_with_searches_probability(
                deck_size, total_target_copies, target_search_total
            )
        ),
    })
    target_df = pd.DataFrame(target_rows)

    comparison_df = None
    if mc_simulations > 0:
        sim = mc.simulate(deck, n=mc_simulations, seed=mc_seed, combo=mc_combo or [])
        comparison_rows = [
            {
                "Statistic": "Mulligan rate",
                "Theoretical": f"{calc.mulligan_probability(deck_size, total_basics):.4f}",
                "Simulated": f"{sim['mulligan_rate']:.4f}",
                "Diff": f"{abs(calc.mulligan_probability(deck_size, total_basics) - sim['mulligan_rate']):.4f}",
            },
            {
                "Statistic": "Supporter in hand",
                "Theoretical": f"{calc.supporter_turn1_probability(deck_size, total_supporters):.4f}",
                "Simulated": f"{sim['supporter_in_hand']:.4f}",
                "Diff": f"{abs(calc.supporter_turn1_probability(deck_size, total_supporters) - sim['supporter_in_hand']):.4f}",
            },
            {
                "Statistic": "Dead hand",
                "Theoretical": f"{calc.dead_hand_probability(deck_size, total_supporters, total_energy):.4f}",
                "Simulated": f"{sim['dead_hand_rate']:.4f}",
                "Diff": f"{abs(calc.dead_hand_probability(deck_size, total_supporters, total_energy) - sim['dead_hand_rate']):.4f}",
            },
        ]

        seen_basic_names: set[str] = set()
        for card in deck.basic_pokemon:
            if card.name in seen_basic_names:
                continue
            seen_basic_names.add(card.name)
            theoretical = calc.possible_starter_probability(
                deck_size, total_basics, _quantity_for_name(deck, card.name)
            )
            simulated = sim["possible_starters"].get(card.name, 0.0)
            comparison_rows.append(
                {
                    "Statistic": f"Possible starter: {card.name}",
                    "Theoretical": f"{theoretical:.4f}",
                    "Simulated": f"{simulated:.4f}",
                    "Diff": f"{abs(theoretical - simulated):.4f}",
                }
            )

        if sim["combo_rate"] is not None:
            combo_label = " + ".join(mc_combo)
            comparison_rows.append(
                {
                    "Statistic": f"Combo: {combo_label}",
                    "Theoretical": "—",
                    "Simulated": f"{sim['combo_rate']:.4f}",
                    "Diff": "—",
                }
            )

        comparison_df = pd.DataFrame(comparison_rows)

    return SimulationReport(
        deck=deck,
        unknown_cards=[],
        opening_df=opening_df,
        breakdown_df=breakdown_df,
        starters_df=starters_df,
        prizes_df=prizes_df.reset_index(drop=True),
        draw_df=draw_df,
        support_df=support_df,
        target_df=target_df,
        comparison_df=comparison_df,
    )
