from dataclasses import dataclass
from typing import Optional


@dataclass
class Card:
    """Represents a single Pokemon Trading Card Game card."""

    quantity: int
    name: str
    set_code: str  # e.g. "MEG"
    set_number: str  # e.g. "54"
    category: str  # 'pokemon' | 'trainer' | 'energy'
    subcategory: str = "unknown"  # see table below
    image: str = ""
    stage: str = ""       # 'Basic' | 'Stage1' | 'Stage2' | 'VMAX' | etc.
    evolve_from: str = ""  # name of the Pokémon this card evolves from


@dataclass
class Deck:
    """Represents a Pokemon TCG deck with card management and statistics."""

    cards: list[Card]

    @property
    def total_cards(self) -> int:
        """Get the total number of cards in the deck."""
        return sum(card.quantity for card in self.cards)

    def quantity_of(self, card_name: str) -> int:
        """Get the total quantity of a card in the deck by exact name."""
        return sum(card.quantity for card in self.cards if card.name == card_name)

    def quantity_of_names(self, card_names: list[str]) -> int:
        """Get the combined total quantity for a list of card names."""
        wanted_names = set(card_names)
        return sum(card.quantity for card in self.cards if card.name in wanted_names)

    @property
    def basic_pokemon(self) -> list[Card]:
        """Get all basic Pokemon cards."""
        return [card for card in self.cards if card.subcategory == "basic"]

    @property
    def total_basics(self) -> int:
        """Get the total quantity of basic Pokemon cards."""
        return sum(card.quantity for card in self.basic_pokemon)

    @property
    def trainers_by_subtype(self) -> dict[str, int]:
        """Get trainer cards grouped by subtype with total quantities."""
        trainer_cards = [
            card for card in self.cards if card.category == "trainer"
        ]
        subtype_totals = {}
        for card in trainer_cards:
            if card.subcategory in ("item", "supporter", "stadium", "tool"):
                subtype_totals[card.subcategory] = (
                    subtype_totals.get(card.subcategory, 0) + card.quantity
                )
        return subtype_totals

    @property
    def energies_by_subtype(self) -> dict[str, int]:
        """Get energy cards grouped by subtype with total quantities."""
        energy_cards = [
            card for card in self.cards if card.category == "energy"
        ]
        subtype_totals = {}
        for card in energy_cards:
            if card.subcategory in ("basic_energy", "special_energy"):
                subtype_totals[card.subcategory] = (
                    subtype_totals.get(card.subcategory, 0) + card.quantity
                )
        return subtype_totals
