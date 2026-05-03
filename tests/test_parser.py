"""Tests for src/parser.py â€” PTCG Live deck list parser."""

import pytest

from src.parser import parse_deck_list


SAMPLE_DECK = """\
PokÃ©mon: 20

4 Abra MEG 54
2 Dunsparce JTG 120
2 Dunsparce TEF 128
2 Psyduck MEP 7
1 Fezandipiti ex SFA 38
1 Shaymin DRI 10
1 Mew ex MEW 151
1 Radiant Greninja ASR 46
6 Extra Pokemon XYZ 99

Trainer: 33

4 Nest Ball SVI 181
4 Ultra Ball SVI 196
4 Iono PAL 269
21 Filler Card AAA 1

Energy: 7

2 Basic Psychic Energy SVE 5
5 Reversal Energy PAL 192
"""


def test_single_pokemon_card_line() -> None:
    """Parse a valid single card line in a Pokemon section."""
    text = "PokÃ©mon: 1\n\n1 Abra MEG 54\n"
    cards = parse_deck_list(text)

    assert len(cards) == 1
    card = cards[0]
    assert card["quantity"] == 1
    assert card["name"] == "Abra"
    assert card["set_code"] == "MEG"
    assert card["set_number"] == "54"
    assert card["category"] == "pokemon"
    assert card["subcategory"] == "unknown"


def test_multi_word_card_name() -> None:
    """Parse a card line with a multi-word name."""
    text = "PokÃ©mon: 1\n\n1 Fezandipiti ex SFA 38\n"
    cards = parse_deck_list(text)

    assert len(cards) == 1
    card = cards[0]
    assert card["name"] == "Fezandipiti ex"
    assert card["set_code"] == "SFA"
    assert card["set_number"] == "38"
    assert card["quantity"] == 1


def test_complete_deck_section_counts() -> None:
    """Parse a complete deck list and verify card counts per section."""
    cards = parse_deck_list(SAMPLE_DECK)

    pokemon_cards = [c for c in cards if c["category"] == "pokemon"]
    trainer_cards = [c for c in cards if c["category"] == "trainer"]
    energy_cards = [c for c in cards if c["category"] == "energy"]

    assert len(pokemon_cards) == 9
    assert len(trainer_cards) == 4
    assert len(energy_cards) == 2


def test_total_quantity_60_cards() -> None:
    """Sum of all quantities equals 60 for a standard 60-card deck."""
    text = """\
PokÃ©mon: 4

4 Abra MEG 54

Trainer: 53

53 Nest Ball SVI 181

Energy: 3

3 Basic Psychic Energy SVE 5
"""
    cards = parse_deck_list(text)
    total = sum(c["quantity"] for c in cards)
    assert total == 60


def test_blank_lines_and_headers_not_returned() -> None:
    """Blank lines and section headers produce no card entries."""
    text = "PokÃ©mon: 0\n\nTrainer: 0\n\nEnergy: 0\n"
    cards = parse_deck_list(text)
    assert cards == []


def test_card_line_missing_set_info_raises_value_error() -> None:
    """A card line without set code/number raises ValueError."""
    text = "PokÃ©mon: 4\n\n4 Abra\n"
    with pytest.raises(ValueError):
        parse_deck_list(text)


def test_unknown_section_header_ignored() -> None:
    """An unknown section header causes no crash; its cards are skipped."""
    text = """\
PokÃ©mon: 1

1 Abra MEG 54

Unknown: 5

5 Mystery Card XYZ 99
"""
    cards = parse_deck_list(text)
    assert all(c["category"] in ("pokemon", "trainer", "energy") for c in cards)


def test_lines_before_first_section_are_skipped() -> None:
    """Content before any known section header is ignored."""
    text = "My Deck Name\n\nPokÃ©mon: 1\n\n1 Abra MEG 54\n"
    cards = parse_deck_list(text)
    assert len(cards) == 1
    assert cards[0]["name"] == "Abra"


def test_parser_accepts_unicode_pokemon_header() -> None:
    """The parser should accept a normal accented Pokémon header."""
    text = "Pokémon: 1\n\n1 Abra MEG 54\n"
    cards = parse_deck_list(text)
    assert len(cards) == 1
    assert cards[0]["category"] == "pokemon"
