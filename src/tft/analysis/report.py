"""Composition popularity tables and Markdown report presentation."""

import pandas as pd
from tabulate import tabulate

from tft.config import ANALYSIS_TIERS, ANALYSIS_TOP_COMPOSITIONS


def build_comp_popularity(df: pd.DataFrame) -> pd.DataFrame:
    """Build per-tier play rates for the most frequent compositions.

    Args:
        df: Classified participant rows.

    Returns:
        A table of composition counts and percentages for tracked tiers.
    """
    if df.empty:
        return pd.DataFrame()
    ranked = df[df["tier"].isin(ANALYSIS_TIERS)]
    if ranked.empty:
        return pd.DataFrame()
    counts = ranked.groupby(["comp_group", "tier"]).size().unstack(fill_value=0)
    counts = counts.reindex(columns=ANALYSIS_TIERS, fill_value=0)
    total_c = int(counts["CHALLENGER"].sum())
    total_g = int(counts["GRANDMASTER"].sum())
    total_all = total_c + total_g
    pop = pd.DataFrame(
        {
            "Comp": counts.index,
            "C Games": counts["CHALLENGER"].values,
            "C %": [f"{v / total_c:.1%}" if total_c else "—" for v in counts["CHALLENGER"]],
            "G Games": counts["GRANDMASTER"].values,
            "G %": [f"{v / total_g:.1%}" if total_g else "—" for v in counts["GRANDMASTER"]],
            "Total": counts.sum(axis=1).values,
            "Total %": [f"{v / total_all:.1%}" for v in counts.sum(axis=1)],
        }
    )
    return pop.sort_values("Total", ascending=False).head(ANALYSIS_TOP_COMPOSITIONS)


def _table(frame: pd.DataFrame, empty_message: str) -> str:
    """Render a populated table or its specific empty-state message."""
    if frame.empty:
        return f"_{empty_message}_"
    return tabulate(frame, headers="keys", tablefmt="github", showindex=False)


def format_report(
    behavioral_df: pd.DataFrame,
    exodia_df: pd.DataFrame,
    popularity_df: pd.DataFrame,
    versions: list[str] | None = None,
) -> str:
    """Render an analysis report with explicit sample and metric limitations.

    Args:
        behavioral_df: Composition outcome comparisons.
        exodia_df: Three-star four- and five-cost summary.
        popularity_df: Composition popularity across tracked tiers.
        versions: Exact stored game versions represented in the sample.

    Returns:
        Markdown text ready to save or display.
    """
    lines = [
        "# TFT composition analysis",
        "",
        "Observed Challenger and Grandmaster final boards. "
        "These descriptive comparisons do not establish a skill gap or explain player decisions.",
        "",
        "**Game versions:** " + (", ".join(versions) if versions else "No harvested matches"),
        "",
        f"## Composition popularity (top {ANALYSIS_TOP_COMPOSITIONS})",
        "",
        "C = Challenger; G = Grandmaster. Play rate is the share of that tier's sampled boards.",
        "",
        _table(
            popularity_df,
            "No tracked ranked matches are available. Harvest matches to populate this report.",
        ),
        "",
        "## Composition outcomes",
        "",
        "Δ = C − G. Top 4% is the top-four placement rate. Util% is final-board presence of "
        "both resistance reduction and anti-heal item keywords; it does not measure combat uptime. "
        "Cap is the number of upgraded five-cost units with no active trait overlap. "
        "BIS% reports top-four boards with at most one of the carry's three most common sampled items; "
        "item popularity does not establish an optimal build. Bail is average placement for a one-star carry.",
        "",
        _table(behavioral_df, "No compositions meet the minimum sample size in both tiers."),
        "",
        "## Three-star four- and five-cost boards",
        "",
        "Lobby copies count copies on other stored boards in the same match. "
        "Incomplete lobby storage can undercount copies. "
        "Other 1★% is the share of boards whose other champions are all one-star; "
        "final-board data cannot establish whether a player sold units to reach three stars.",
        "",
        _table(
            exodia_df, "No three-star four- or five-cost units were found in the sampled boards."
        ),
        "",
    ]
    if versions and len(versions) > 1:
        lines[6:6] = [
            "Multiple game versions are combined. Use --game-version to compare one exact patch.",
            "",
        ]
    return "\n".join(lines)
