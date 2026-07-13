"""Tests for client.py — DdClient init and tag utilities."""

from __future__ import annotations

from client import API_NAMES, APIS, DdClient, _tag_list, _tags


class TestApiRegistry:
    def test_all_apis_have_required_keys(self) -> None:
        for name, cfg in APIS.items():
            assert "service" in cfg, f"{name} missing 'service'"
            assert "env" in cfg, f"{name} missing 'env'"

    def test_api_names_match_dict_keys(self) -> None:
        assert set(API_NAMES) == set(APIS.keys())

    def test_at_least_one_api(self) -> None:
        assert len(API_NAMES) >= 1


class TestTags:
    def test_tags_returns_comma_separated(self) -> None:
        result = _tags("api-gateway")
        assert "service:api-gateway" in result
        assert "env:prod" in result
        assert result.count(",") >= 2

    def test_tag_list_returns_list(self) -> None:
        result = _tag_list("api-gateway")
        assert isinstance(result, list)
        assert all(":" in t for t in result)

    def test_unknown_api_falls_back_sensibly(self) -> None:
        result = _tags("non-existent")
        assert "service:non-existent" in result
        assert "env:dev" in result

    def test_tag_list_unknown_api(self) -> None:
        result = _tag_list("non-existent")
        assert "service:non-existent" in result


class TestDdClientInit:
    def test_explicit_api_key_is_required(self) -> None:
        client = DdClient(api_key="test-key-123")
        assert client.api_key == "test-key-123"

    def test_default_site(self) -> None:
        client = DdClient(api_key="key")
        assert client.site == "datadoghq.com"

    def test_custom_site(self) -> None:
        client = DdClient(api_key="key", site="us5.datadoghq.com")
        assert client.site == "us5.datadoghq.com"

    def test_default_api_name(self) -> None:
        client = DdClient(api_key="key")
        assert client.api_name == "api-gateway"

    def test_custom_api_name(self) -> None:
        client = DdClient(api_key="key", api_name="payment-service")
        assert client.api_name == "payment-service"

    def test_default_app_key_is_empty_string(self) -> None:
        client = DdClient(api_key="key")
        assert client.app_key == ""
