"""Tests for tft.etl.icons."""

import pytest

from tft.etl.icons import icon_url


class TestIconUrl:
    """icon_url() translates CDragon .tex paths to raw PNG URLs."""

    def test_standard_tex_path(self) -> None:
        result = icon_url("ASSETS/Characters/Ahri/HUD/Icons2D/Ahri_Square.tex")
        expected = (
            "https://raw.communitydragon.org/latest/game/"
            "assets/characters/ahri/hud/icons2d/ahri_square.png"
        )
        assert result == expected

    def test_dds_extension(self) -> None:
        result = icon_url("ASSETS/Maps/TFT/Icons/Items/Hexcore/BFSword.dds")
        assert result is not None
        assert result.endswith(".png")
        assert ".dds" not in result

    def test_none_returns_none(self) -> None:
        assert icon_url(None) is None

    def test_empty_string_returns_none(self) -> None:
        assert icon_url("") is None

    def test_path_is_lowercased(self) -> None:
        result = icon_url("ASSETS/UX/TFT/ChampionSplashes/TFT16_Ahri.tex")
        assert result is not None
        assert "ASSETS" not in result
        assert "assets" in result

    @pytest.mark.parametrize("path", ["None", "null", " ", "javascript:alert(1)"])
    def test_invalid_source_values_are_not_image_urls(self, path: str) -> None:
        """Missing asset sentinels and unsupported schemes do not produce requests."""
        assert icon_url(path) is None

    def test_absolute_url_is_not_prefixed_or_lowercased(self) -> None:
        """Already resolved image URLs preserve path case and gain HTTPS."""
        assert icon_url("http://example.com/Assets/Ahri.PNG?version=1") == (
            "https://example.com/Assets/Ahri.PNG?version=1"
        )

    def test_absolute_texture_url_gets_png_extension(self) -> None:
        """Texture normalization also supports already absolute CDN paths."""
        assert icon_url("https://example.com/Assets/Ahri.DDS") == (
            "https://example.com/Assets/Ahri.png"
        )
