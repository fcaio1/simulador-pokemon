"""PTCG Live deck list parser."""

KNOWN_SECTIONS = {
    "Pokemon:": "pokemon",
    "Pokémon:": "pokemon",
    "PokÃ©mon:": "pokemon",
    "Trainer:": "trainer",
    "Energy:": "energy",
}


def _parse_card_line(line: str, category: str) -> dict:
    """Parse a single card line into a card dict.

    Raises:
        ValueError: If the line has fewer than 3 tokens (missing set info)
            or if quantity is less than 1.
    """
    tokens = line.split()
    if len(tokens) < 3:
        raise ValueError(
            f"Card line missing set info (expected at least 3 tokens): {line!r}"
        )
    quantity = int(tokens[0])
    if quantity < 1:
        raise ValueError(f"Card quantity must be at least 1, got {quantity}")
    set_number = tokens[-1]
    set_code = tokens[-2]
    name = " ".join(tokens[1:-2])
    return {
        "quantity": quantity,
        "name": name,
        "set_code": set_code,
        "set_number": set_number,
        "category": category,
        "subcategory": "unknown",
    }


def _detect_section(line: str) -> str | None:
    """Return the category name if line is a known section header, else None."""
    for header, category in KNOWN_SECTIONS.items():
        if line.startswith(header):
            return category
    return None


def parse_deck_list(text: str) -> list[dict]:
    """Parse PTCG Live deck list text into a list of card dicts.

    Returns list of dicts with keys:
        quantity, name, set_code, set_number, category, subcategory
    subcategory is always 'unknown' (filled later by api_client).

    Raises:
        ValueError: If a card line is missing set code or set number.
    """
    cards: list[dict] = []
    current_category: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        section = _detect_section(line)
        if section is not None:
            current_category = section
            continue

        if current_category is None:
            continue

        # Lines that look like headers for unknown sections have no digits leading
        # them; skip any line whose first token is not a digit.
        if not line[0].isdigit():
            continue

        cards.append(_parse_card_line(line, current_category))

    return cards
