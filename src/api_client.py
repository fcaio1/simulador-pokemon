"""TCGDex API client with local JSON cache for enriching parsed deck cards."""

import json
import logging
import urllib.error
import urllib.request
from pathlib import Path

from src.deck import Card

_BASE_URL = "https://api.tcgdex.net/v2/en/cards"
_TIMEOUT = 10

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _load_cache(cache_path: str) -> dict:
    """Load JSON cache from disk; return empty dict if file does not exist."""
    try:
        return json.loads(Path(cache_path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except Exception as exc:
        logger.warning(f"Could not read cache at {cache_path}: {exc}")
        return {}


def _save_cache(cache: dict, cache_path: str) -> None:
    """Persist cache dict to disk as JSON."""
    try:
        Path(cache_path).write_text(
            json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as exc:
        logger.warning(f"Could not save cache to {cache_path}: {exc}")


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _get_json(url: str) -> dict | list | None:
    """Fetch JSON from *url*; return None on 404, raise on other errors."""
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def _fetch_by_id(set_id: str, local_id: str) -> dict | None:
    """Fetch card by set_id-local_id from primary endpoint."""
    url = f"{_BASE_URL}/{set_id}-{local_id}"
    return _get_json(url)


def _fetch_by_name(name: str) -> dict | None:
    """Fetch card by name using search endpoint; return first result or None."""
    encoded = urllib.request.quote(name)
    url = f"{_BASE_URL}?name={encoded}"
    result = _get_json(url)
    if isinstance(result, list) and result:
        return result[0]
    return None


# ---------------------------------------------------------------------------
# Subcategory mapping
# ---------------------------------------------------------------------------

def _map_subcategory(api_data: dict) -> str:
    """Derive subcategory string from TCGDex API response dict."""
    category = api_data.get("category", "")

    if category == "Pokemon":
        return "basic" if api_data.get("stage") == "Basic" else "other"

    if category == "Trainer":
        trainer_type = api_data.get("trainerType", "").lower()
        mapping = {
            "item": "item",
            "supporter": "supporter",
            "stadium": "stadium",
            "tool": "tool",
        }
        return mapping.get(trainer_type, "unknown")

    if category == "Energy":
        energy_type = api_data.get("energyType", "") or api_data.get("energy_type", "")
        if energy_type == "Special":
            return "special_energy"
        return "basic_energy"

    return "unknown"


# ---------------------------------------------------------------------------
# Card lookup (with cache)
# ---------------------------------------------------------------------------

def _lookup_card(
    name: str, set_id: str, local_id: str, cache: dict, cache_path: str
) -> str:
    """Return subcategory for one card, using cache or API."""
    cache_key = f"{set_id}-{local_id}"

    if cache_key in cache:
        return _map_subcategory(cache[cache_key])

    api_data = _fetch_by_id(set_id, local_id)

    if api_data is None:
        api_data = _fetch_by_name(name)

    if api_data is None:
        logger.warning(f"Card not found: {name} ({cache_key})")
        return "unknown"

    cache[cache_key] = api_data
    _save_cache(cache, cache_path)
    return _map_subcategory(api_data)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def enrich_deck(
    parsed_cards: list[dict],
    cache_path: str = "card_cache.json",
) -> list[Card]:
    """Look up each card on TCGDex API and return list of Card objects with subcategory filled.

    Args:
        parsed_cards: Output of parse_deck_list — list of card dicts.
        cache_path: Path to JSON cache file (created if absent).

    Returns:
        List of Card dataclass instances with subcategory populated.
    """
    cache = _load_cache(cache_path)
    result: list[Card] = []

    for card_dict in parsed_cards:
        set_id = card_dict["set_code"].lower()
        local_id = card_dict["set_number"]
        subcategory = _lookup_card(
            name=card_dict["name"],
            set_id=set_id,
            local_id=local_id,
            cache=cache,
            cache_path=cache_path,
        )
        result.append(
            Card(
                quantity=card_dict["quantity"],
                name=card_dict["name"],
                set_code=card_dict["set_code"],
                set_number=card_dict["set_number"],
                category=card_dict["category"],
                subcategory=subcategory,
            )
        )

    return result
