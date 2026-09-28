"""Coordinate local composition analytics and write a Markdown report."""

import logging
from pathlib import Path

import pandas as pd

from tft.analysis.behavior import compute_behavioral_deltas
from tft.analysis.classification import classify_comp_v2
from tft.analysis.data import load_data, load_lookups
from tft.analysis.highrolls import compute_exodia_report
from tft.analysis.models import AnalysisResult
from tft.analysis.report import build_comp_popularity, format_report
from tft.config import ANALYSIS_REPORT_PATH, ANALYSIS_TIERS, DB_PATH

log = logging.getLogger(__name__)

__all__ = [
    "analyze",
    "classify_comp_v2",
    "compute_behavioral_deltas",
    "compute_exodia_report",
    "format_report",
    "load_data",
    "run",
]


def analyze(
    db_path: Path | None = None,
    game_version: str | None = None,
) -> AnalysisResult:
    """Analyze stored boards without changing the database or writing a report.

    Args:
        db_path: Existing database; defaults to the configured database.
        game_version: Exact stored game version to compare, or all versions.

    Returns:
        Comparison tables, represented game versions, and tracked sample size.
    """
    path = db_path or DB_PATH
    df = load_data(path, game_version)
    population = pd.DataFrame()
    behavioral = pd.DataFrame()
    highrolls = pd.DataFrame()
    sample_count = 0
    if not df.empty:
        lookups = load_lookups(path)
        boards = [
            classify_comp_v2(row, lookups.champions, lookups.traits) for _, row in df.iterrows()
        ]
        enriched = pd.concat([df, pd.DataFrame(boards, index=df.index)], axis=1)
        ranked = enriched[enriched["tier"].isin(ANALYSIS_TIERS)]
        sample_count = len(ranked)
        population = build_comp_popularity(ranked)
        highrolls = compute_exodia_report(enriched, lookups.champions)
        behavioral = compute_behavioral_deltas(
            ranked,
            lookups.champions,
            lookups.items,
            ct=lookups.champion_traits,
            tl=lookups.traits,
        )
    else:
        log.info("No match data available for analysis.")
    versions = sorted(df["game_version"].unique()) if not df.empty else []
    return AnalysisResult(versions, sample_count, population, behavioral, highrolls)


def run(
    db_path: Path | None = None,
    output_path: Path | None = None,
    game_version: str | None = None,
) -> Path:
    """Analyze stored matches and save a report without requiring a Riot key.

    Args:
        db_path: Existing database; defaults to the configured database.
        output_path: Report destination; defaults to the configured report.
        game_version: Exact stored game version to compare, or all versions.

    Returns:
        Path to the generated Markdown report.
    """
    result = analyze(db_path, game_version)
    report = format_report(
        result.behavioral,
        result.highrolls,
        result.population,
        versions=result.versions,
    )
    destination = output_path or ANALYSIS_REPORT_PATH
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(report, encoding="utf-8")
    log.info("Report written to %s", destination)
    return destination
