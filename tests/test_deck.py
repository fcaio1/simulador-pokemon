from src.deck import Card, Deck


def make_test_deck() -> Deck:
    cards = [
        Card(4, "Abra", "MEG", "54", "pokemon", "basic"),
        Card(2, "Kadabra", "MEG", "55", "pokemon", "other"),
        Card(3, "Buddy-Buddy Poffin", "TEF", "144", "trainer", "item"),
        Card(1, "Buddy-Buddy Poffin", "ASC", "184", "trainer", "item"),
        Card(4, "Poké Pad", "POR", "81", "trainer", "item"),
    ]
    return Deck(cards)


def test_quantity_of_sums_same_name_across_entries() -> None:
    deck = make_test_deck()
    assert deck.quantity_of("Buddy-Buddy Poffin") == 4


def test_quantity_of_returns_zero_for_missing_card() -> None:
    deck = make_test_deck()
    assert deck.quantity_of("Alakazam") == 0


def test_quantity_of_names_sums_multiple_cards() -> None:
    deck = make_test_deck()
    assert deck.quantity_of_names(["Abra", "Buddy-Buddy Poffin"]) == 8
