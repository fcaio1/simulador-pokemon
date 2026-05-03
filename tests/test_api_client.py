"""Tests for src/api_client.py — TCGDex API client with cache (TDD)."""

import json
import logging
from unittest.mock import MagicMock, patch

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


def _make_http_response(body: dict, status: int = 200) -> MagicMock:
    """Return a mock that behaves like urllib.request.urlopen context manager."""
    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.read.return_value = json.dumps(body).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def _make_404_response() -> MagicMock:
    """Return a mock that raises urllib.error.HTTPError with code 404."""
    import urllib.error
    error = urllib.error.HTTPError(url="", code=404, msg="Not Found", hdrs=None, fp=None)
    mock_urlopen = MagicMock(side_effect=error)
    return mock_urlopen


# ---------------------------------------------------------------------------
# Test 1 — Cache hit: no HTTP request when card is in cache
# ---------------------------------------------------------------------------

def test_cache_hit_no_http_request(tmp_path):
    """If the card is already cached, no HTTP request is made."""
    cache_file = tmp_path / "cache.json"
    cached_data = {
        "meg-54": {"category": "Pokemon", "stage": "Basic", "name": "Abra"}
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
# Test 2 — Cache miss: HTTP request made and cache file updated
# ---------------------------------------------------------------------------

def test_cache_miss_saves_to_cache(tmp_path):
    """Cache miss triggers HTTP request; result is saved to cache file."""
    cache_file = tmp_path / "cache.json"
    api_body = {"category": "Pokemon", "stage": "Basic", "name": "Abra"}

    parsed_cards = [_make_parsed_card()]

    with patch("urllib.request.urlopen", return_value=_make_http_response(api_body)):
        result = enrich_deck(parsed_cards, cache_path=str(cache_file))

    assert len(result) == 1
    assert result[0].subcategory == "basic"

    saved = json.loads(cache_file.read_text())
    assert "meg-54" in saved
    assert saved["meg-54"]["stage"] == "Basic"


# ---------------------------------------------------------------------------
# Test 3 — 404 primary → fallback by name search succeeds
# ---------------------------------------------------------------------------

def test_404_primary_uses_fallback_by_name(tmp_path):
    """When primary endpoint returns 404, fallback name search is used."""
    import urllib.error

    cache_file = tmp_path / "cache.json"
    fallback_body = [{"category": "Pokemon", "stage": "Stage1", "name": "Kadabra"}]

    primary_error = urllib.error.HTTPError(
        url="", code=404, msg="Not Found", hdrs=None, fp=None
    )

    def side_effect(request, timeout=10):
        url = request.full_url if hasattr(request, "full_url") else str(request)
        if "meg-54" in url:
            raise primary_error
        return _make_http_response(fallback_body)

    parsed_cards = [_make_parsed_card()]

    with patch("urllib.request.urlopen", side_effect=side_effect):
        result = enrich_deck(parsed_cards, cache_path=str(cache_file))

    assert len(result) == 1
    assert result[0].subcategory == "other"


# ---------------------------------------------------------------------------
# Test 4 — Card not found → subcategory='unknown' + warning logged
# ---------------------------------------------------------------------------

def test_card_not_found_logs_warning_and_returns_unknown(tmp_path, caplog):
    """When both primary and fallback return 404, subcategory is 'unknown'."""
    import urllib.error

    cache_file = tmp_path / "cache.json"

    primary_error = urllib.error.HTTPError(
        url="", code=404, msg="Not Found", hdrs=None, fp=None
    )
    fallback_error = urllib.error.HTTPError(
        url="", code=404, msg="Not Found", hdrs=None, fp=None
    )

    call_count = {"n": 0}

    def side_effect(request, timeout=10):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise primary_error
        raise fallback_error

    parsed_cards = [_make_parsed_card()]

    with caplog.at_level(logging.WARNING, logger="src.api_client"):
        with patch("urllib.request.urlopen", side_effect=side_effect):
            result = enrich_deck(parsed_cards, cache_path=str(cache_file))

    assert len(result) == 1
    assert result[0].subcategory == "unknown"
    assert any("Abra" in record.message for record in caplog.records)


# ---------------------------------------------------------------------------
# Test 5 — Basic Pokemon classification
# ---------------------------------------------------------------------------

def test_basic_pokemon_subcategory(tmp_path):
    """Pokemon with stage='Basic' maps to subcategory='basic'."""
    cache_file = tmp_path / "cache.json"
    api_body = {"category": "Pokemon", "stage": "Basic", "name": "Abra"}

    parsed_cards = [_make_parsed_card()]

    with patch("urllib.request.urlopen", return_value=_make_http_response(api_body)):
        result = enrich_deck(parsed_cards, cache_path=str(cache_file))

    assert result[0].subcategory == "basic"


# ---------------------------------------------------------------------------
# Test 6 — Stage1 Pokemon classification
# ---------------------------------------------------------------------------

def test_stage1_pokemon_subcategory(tmp_path):
    """Pokemon with stage != 'Basic' maps to subcategory='other'."""
    cache_file = tmp_path / "cache.json"
    api_body = {"category": "Pokemon", "stage": "Stage1", "name": "Kadabra"}

    parsed_cards = [_make_parsed_card(name="Kadabra", set_code="MEG", set_number="55")]

    with patch("urllib.request.urlopen", return_value=_make_http_response(api_body)):
        result = enrich_deck(parsed_cards, cache_path=str(cache_file))

    assert result[0].subcategory == "other"


# ---------------------------------------------------------------------------
# Test 7 — Supporter classification
# ---------------------------------------------------------------------------

def test_supporter_trainer_subcategory(tmp_path):
    """Trainer with trainerType='Supporter' maps to subcategory='supporter'."""
    cache_file = tmp_path / "cache.json"
    api_body = {"category": "Trainer", "trainerType": "Supporter", "name": "Iono"}

    parsed_cards = [
        _make_parsed_card(
            name="Iono", set_code="PAL", set_number="269", category="trainer"
        )
    ]

    with patch("urllib.request.urlopen", return_value=_make_http_response(api_body)):
        result = enrich_deck(parsed_cards, cache_path=str(cache_file))

    assert result[0].subcategory == "supporter"


# ---------------------------------------------------------------------------
# Test 8 — Basic Energy classification
# ---------------------------------------------------------------------------

def test_basic_energy_subcategory(tmp_path):
    """Energy card without special energyType maps to subcategory='basic_energy'."""
    cache_file = tmp_path / "cache.json"
    api_body = {"category": "Energy", "name": "Basic Psychic Energy"}

    parsed_cards = [
        _make_parsed_card(
            name="Basic Psychic Energy", set_code="SVE", set_number="5", category="energy"
        )
    ]

    with patch("urllib.request.urlopen", return_value=_make_http_response(api_body)):
        result = enrich_deck(parsed_cards, cache_path=str(cache_file))

    assert result[0].subcategory == "basic_energy"
