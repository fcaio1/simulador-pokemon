"""Tests for src/api_client.py — TCGDex API client with cache (TDD)."""

import json
import logging
from unittest.mock import MagicMock, call, patch

import pytest

from src.api_client import enrich_deck
from src.deck import Card


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_parsed_card(
    name: str = "Abra",
    set_code: str = "MEG",
    set_number: str = "54",
    category: str = "pokemon",
    quantity: int = 4,
) -> dict:
    return {
        "quantity": quantity,
        "name": name,
        "set_code": set_code,
        "set_number": set_number,
        "category": category,
        "subcategory": "unknown",
    }


def _make_http_response(body: list | dict, status: int = 200) -> MagicMock:
    """Return a mock that behaves like urllib.request.urlopen context manager."""
    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.read.return_value = json.dumps(body).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def _make_404_error() -> MagicMock:
    """Return an HTTPError mock with status 404."""
    import urllib.error
    err = urllib.error.HTTPError(url="", code=404, msg="Not Found", hdrs=None, fp=None)
    return err


# ---------------------------------------------------------------------------
# Test 1 — Cache hit: no HTTP request when card is in cache
# ---------------------------------------------------------------------------

def test_cache_hit_no_http_request(tmp_path):
    """If the card is already cached, no HTTP request is made."""
    cache_file = tmp_path / "cache.json"
    cached_data = {
        "MEG-54": {"category": "Pokemon", "stage": "Basic", "name": "Abra", "localId": "054"}
    }
    cache_file.write_text(json.dumps(cached_data))

    parsed_cards = [_make_parsed_card()]

    with patch("urllib.request.urlopen") as mock_urlopen:
        result = enrich_deck(parsed_cards, cache_path=str(cache_file))

    mock_urlopen.assert_not_called()
    assert len(result) == 1
    assert isinstance(result[0], Card)
    assert result[0].subcategory == "basic"


# ---------------------------------------------------------------------------
# Test 2 — Cache miss + set in map → ID-based lookup succeeds → saves cache
# ---------------------------------------------------------------------------

def test_cache_miss_set_in_map_id_lookup_succeeds(tmp_path):
    """Cache miss with known set code uses ID-based lookup and saves result to cache."""
    cache_file = tmp_path / "cache.json"
    # MEG → me01, number 54 → zero-padded "054" → me01-054
    api_card = {"category": "Pokemon", "stage": "Basic", "name": "Abra", "localId": "054"}

    parsed_cards = [_make_parsed_card(set_code="MEG", set_number="54")]

    with patch("urllib.request.urlopen", return_value=_make_http_response(api_card)) as mock_urlopen:
        result = enrich_deck(parsed_cards, cache_path=str(cache_file))

    assert len(result) == 1
    assert result[0].subcategory == "basic"

    # Verify the ID-based URL was called (me01-054)
    called_urls = [str(c.args[0].full_url) for c in mock_urlopen.call_args_list]
    assert any("me01-054" in url for url in called_urls)

    # Verify result was saved to cache
    saved = json.loads(cache_file.read_text())
    assert "MEG-54" in saved
    assert saved["MEG-54"]["stage"] == "Basic"


# ---------------------------------------------------------------------------
# Test 3 — Cache miss + set in map → ID-based 404 → name search fallback succeeds
# ---------------------------------------------------------------------------

def test_cache_miss_set_in_map_id_404_falls_back_to_name_search(tmp_path):
    """When ID-based lookup returns 404, name search fallback is used."""
    import urllib.error

    cache_file = tmp_path / "cache.json"
    api_card = {"category": "Pokemon", "stage": "Basic", "name": "Abra", "localId": "054"}

    # First call (ID-based) → 404; second call (name search) → list with card
    http_404 = urllib.error.HTTPError(url="", code=404, msg="Not Found", hdrs=None, fp=None)
    name_search_resp = _make_http_response([api_card])

    parsed_cards = [_make_parsed_card(set_code="MEG", set_number="54")]

    with patch("urllib.request.urlopen", side_effect=[http_404, name_search_resp]):
        result = enrich_deck(parsed_cards, cache_path=str(cache_file))

    assert len(result) == 1
    assert result[0].subcategory == "basic"

    saved = json.loads(cache_file.read_text())
    assert "MEG-54" in saved


# ---------------------------------------------------------------------------
# Test 4 — Cache miss + set NOT in map → name search → succeeds
# ---------------------------------------------------------------------------

def test_cache_miss_set_not_in_map_uses_name_search(tmp_path):
    """When set code is not in SET_CODE_MAP, skip ID lookup and go straight to name search."""
    cache_file = tmp_path / "cache.json"
    # "XYZ" is not in SET_CODE_MAP
    api_card = {"category": "Pokemon", "stage": "Basic", "name": "Abra", "localId": "099"}

    parsed_cards = [_make_parsed_card(set_code="XYZ", set_number="99")]

    with patch("urllib.request.urlopen", return_value=_make_http_response([api_card])) as mock_urlopen:
        result = enrich_deck(parsed_cards, cache_path=str(cache_file))

    assert len(result) == 1
    assert result[0].subcategory == "basic"

    # Only one HTTP call should be made (the name search), no ID-based URL
    assert mock_urlopen.call_count == 1
    called_url = str(mock_urlopen.call_args_list[0].args[0].full_url)
    assert "name=" in called_url
    assert "xyz" not in called_url.lower() or "name=" in called_url

    saved = json.loads(cache_file.read_text())
    assert "XYZ-99" in saved


# ---------------------------------------------------------------------------
# Test 5 — Both lookups fail → unknown + warning logged
# ---------------------------------------------------------------------------

def test_both_lookups_fail_returns_unknown_with_warning(tmp_path, caplog):
    """When both ID-based and name-search lookups fail, subcategory is 'unknown' and a warning is logged."""
    import urllib.error

    cache_file = tmp_path / "cache.json"
    http_404 = urllib.error.HTTPError(url="", code=404, msg="Not Found", hdrs=None, fp=None)
    empty_list_resp = _make_http_response([])

    parsed_cards = [_make_parsed_card(set_code="MEG", set_number="54")]

    with caplog.at_level(logging.WARNING, logger="src.api_client"):
        with patch("urllib.request.urlopen", side_effect=[http_404, empty_list_resp]):
            result = enrich_deck(parsed_cards, cache_path=str(cache_file))

    assert len(result) == 1
    assert result[0].subcategory == "unknown"
    assert any("Abra" in record.message for record in caplog.records)


# ---------------------------------------------------------------------------
# Test 6 — Basic Pokemon classification
# ---------------------------------------------------------------------------

def test_basic_pokemon_subcategory(tmp_path):
    """Pokemon with stage='Basic' maps to subcategory='basic'."""
    cache_file = tmp_path / "cache.json"
    api_card = {"category": "Pokemon", "stage": "Basic", "name": "Abra", "localId": "054"}

    parsed_cards = [_make_parsed_card()]

    with patch("urllib.request.urlopen", return_value=_make_http_response(api_card)):
        result = enrich_deck(parsed_cards, cache_path=str(cache_file))

    assert result[0].subcategory == "basic"


# ---------------------------------------------------------------------------
# Test 7 — Supporter classification
# ---------------------------------------------------------------------------

def test_supporter_trainer_subcategory(tmp_path):
    """Trainer with trainerType='Supporter' maps to subcategory='supporter'."""
    cache_file = tmp_path / "cache.json"
    # PAL → sv02, number 269 → "269" (already 3 digits)
    api_card = {"category": "Trainer", "trainerType": "Supporter", "name": "Iono", "localId": "269"}

    parsed_cards = [
        _make_parsed_card(
            name="Iono", set_code="PAL", set_number="269", category="trainer"
        )
    ]

    with patch("urllib.request.urlopen", return_value=_make_http_response(api_card)):
        result = enrich_deck(parsed_cards, cache_path=str(cache_file))

    assert result[0].subcategory == "supporter"


# ---------------------------------------------------------------------------
# Test 8 — Special Energy classification
# ---------------------------------------------------------------------------

def test_special_energy_subcategory(tmp_path):
    """Energy card with energyType='Special' maps to subcategory='special_energy'."""
    cache_file = tmp_path / "cache.json"
    # PAL → sv02, number 192 → "192"
    api_card = {
        "category": "Energy",
        "energyType": "Special",
        "name": "Reversal Energy",
        "localId": "192",
    }

    parsed_cards = [
        _make_parsed_card(
            name="Reversal Energy", set_code="PAL", set_number="192", category="energy"
        )
    ]

    with patch("urllib.request.urlopen", return_value=_make_http_response(api_card)):
        result = enrich_deck(parsed_cards, cache_path=str(cache_file))

    assert result[0].subcategory == "special_energy"
