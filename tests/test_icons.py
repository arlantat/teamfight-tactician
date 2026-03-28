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
