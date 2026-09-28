"""Tests for changing response shapes and authenticated client cleanup."""

from unittest.mock import Mock

import pytest
import requests

from tft.exceptions import RiotApiError
from tft.riot.client import RiotClient


def test_client_rejects_legacy_league_entry_without_puuid() -> None:
    """Old summoner IDs must never be interpreted as current player IDs."""
    with RiotClient(api_key="test") as client:
        client._get = Mock(return_value={"entries": [{"summonerId": "old"}]})
        with pytest.raises(RiotApiError, match="PUUID"):
            client.get_league("challenger")


def test_client_closes_session_on_exception() -> None:
    """Auth sessions must close on both successful and failed harvest paths."""
    client = RiotClient(api_key="test")
    client._session.close = Mock()
    with pytest.raises(ValueError):
        with client:
            raise ValueError("failure")
    client._session.close.assert_called_once()


def test_http_failure_is_specific_and_does_not_expose_credentials() -> None:
    """Only safe status information escapes a failed HTTP request."""
    with RiotClient(api_key="test") as client:
        response = Mock(status_code=403)
        response.raise_for_status.side_effect = requests.HTTPError("unsafe details", response=response)
        client._session.get = Mock(return_value=response)
        with pytest.raises(RiotApiError, match=r"Riot request failed \(403\)") as error:
            client.get_match("NA1_18")
        assert "unsafe details" not in str(error.value)
        response.close.assert_called_once()


def test_match_history_rejects_error_objects() -> None:
    """An unexpected successful-status error body cannot become match IDs."""
    with RiotClient(api_key="test") as client:
        client._get = Mock(return_value={"status": "error"})
        with pytest.raises(RiotApiError, match="match ID strings"):
            client.get_match_ids("a")
