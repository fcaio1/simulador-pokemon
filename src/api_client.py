"""TCGDex API client with local JSON cache for enriching parsed deck cards."""

import json
import logging
import urllib.error
import urllib.request
from pathlib import Path

from src.deck import Card
from src.set_mapping import SET_CODE_MAP

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


def _fetch_by_id(tcgdex_id: str, set_number: str) -> dict | None:
    """Fetch a card by its TCGDex set ID and zero-padded number.

    Uses zero-padded (3 digits) as TCGDex expects (e.g. me01-054, sv09-120).

    Args:
        tcgdex_id: TCGDex set ID (e.g. "me01", "sv02").
        set_number: Card number within the set (e.g. "54", "269").

    Returns:
        Card dict from API or None if not found.
    """
    padded = set_number.zfill(3)
    url = f"{_BASE_URL}/{tcgdex_id}-{padded}"
    return _get_json(url)


def _fetch_by_name(name: str, set_number: str) -> dict | None:
    """Search cards by name and filter by matching set number (ignoring zero-padding).

    Args:
        name: Card name to search for.
        set_number: Set number to match (e.g. "54", "054").

    Returns:
        First matching card dict or None if not found.
    """
    encoded = urllib.request.quote(name)
    url = f"{_BASE_URL}?name={encoded}"
    result = _get_json(url)

    if not isinstance(result, list) or not result:
        return None

    normalized_number = set_number.lstrip("0") or "0"
    for card in result:
        local_id = str(card.get("localId", ""))
        if local_id.lstrip("0") == normalized_number:
            return card

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
        return trainer_type if trainer_type in ("item", "supporter", "stadium", "tool") else "unknown"

    if category == "Energy":
        return "special_energy" if api_data.get("energyType") == "Special" else "basic_energy"

    return "unknown"


# ---------------------------------------------------------------------------
# Card lookup (with cache)
# ---------------------------------------------------------------------------

def _lookup_card(
    name: str, set_code: str, set_number: str, cache: dict, cache_path: str
) -> str:
    """Return subcategory for one card, using cache or API.

    Strategy:
      1. Cache check: return cached result if present.
      2. Primary: if set_code in SET_CODE_MAP → ID-based lookup (zero-padded).
      3. Fallback: name-search endpoint, filter by matching localId.
      4. Not found: log warning and return 'unknown'.

    Args:
        name: Card name (used for name-based API search).
        set_code: PTCG Live set code (e.g. "MEG", "PAL").
        set_number: Card number within the set (e.g. "54").
        cache: Mutable cache dict (updated in-place on miss).
        cache_path: Path to JSON cache file on disk.

    Returns:
        Subcategory string (e.g. 'basic', 'supporter', 'basic_energy', 'unknown').
    """
    cache_key = f"{set_code.upper()}-{set_number}"

    if cache_key in cache:
        return _map_subcategory(cache[cache_key])

    api_data: dict | None = None

    # Primary: ID-based lookup via SET_CODE_MAP
    if set_code.upper() in SET_CODE_MAP:
        tcgdex_id = SET_CODE_MAP[set_code.upper()]
        api_data = _fetch_by_id(tcgdex_id, set_number)

    # Fallback: name search
    if api_data is None:
        api_data = _fetch_by_name(name, set_number)

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
        subcategory = _lookup_card(
            name=card_dict["name"],
            set_code=card_dict["set_code"],
            set_number=card_dict["set_number"],
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
