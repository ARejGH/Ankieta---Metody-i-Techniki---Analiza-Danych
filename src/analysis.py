"""Statistical analysis: descriptives, correlations, tests, FDR."""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

from src.schema import AnalysisPlan


@dataclass
class DescriptiveRow:
    """Descriptive statistics for a single item."""

    item_id: str
    n: int
    missing_pct: float
    median: float
    mode: float | None
    pct_1: float
    pct_2: float
    pct_3: float
    pct_4: float
    pct_5: float
    flagged_missingness: bool


def compute_descriptives(
    df: pd.DataFrame,
    items: list[str],
    flag_threshold: float = 0.20,
) -> list[DescriptiveRow]:
    """Compute descriptive statistics for all items.

    Args:
        df: DataFrame with numeric-encoded Likert items
        items: List of item column names
        flag_threshold: Threshold for flagging high missingness

    Returns:
        List of DescriptiveRow objects
    """
    results = []
    total_n = len(df)

    for item in items:
        series = df[item]
        valid = series.dropna()
        n = len(valid)
        missing_pct = (total_n - n) / total_n if total_n > 0 else 0.0

        if n > 0:
            median = float(valid.median())
            mode_result = valid.mode()
            mode = float(mode_result.iloc[0]) if len(mode_result) > 0 else None

            # Calculate percentages for each response level
            value_counts = valid.value_counts(normalize=True)
            pct_1 = float(value_counts.get(1, 0))
            pct_2 = float(value_counts.get(2, 0))
            pct_3 = float(value_counts.get(3, 0))
            pct_4 = float(value_counts.get(4, 0))
            pct_5 = float(value_counts.get(5, 0))
        else:
            median = np.nan
            mode = None
            pct_1 = pct_2 = pct_3 = pct_4 = pct_5 = 0.0

        results.append(DescriptiveRow(
            item_id=item,
            n=n,
            missing_pct=missing_pct,
            median=median,
            mode=mode,
            pct_1=pct_1,
            pct_2=pct_2,
            pct_3=pct_3,
            pct_4=pct_4,
            pct_5=pct_5,
            flagged_missingness=missing_pct > flag_threshold,
        ))

    return results


def descriptives_to_df(descriptives: list[DescriptiveRow]) -> pd.DataFrame:
    """Convert descriptive results to DataFrame."""
    return pd.DataFrame([
        {
            "item_id": d.item_id,
            "n": d.n,
            "missing_pct": round(d.missing_pct, 4),
            "median": d.median,
            "mode": d.mode,
            "pct_1": round(d.pct_1, 4),
            "pct_2": round(d.pct_2, 4),
            "pct_3": round(d.pct_3, 4),
            "pct_4": round(d.pct_4, 4),
            "pct_5": round(d.pct_5, 4),
            "flagged_missingness": d.flagged_missingness,
        }
        for d in descriptives
    ])


def compute_correlations(
    df: pd.DataFrame,
    config: AnalysisPlan,
) -> pd.DataFrame:
    """Compute Spearman correlation matrix.

    Args:
        df: DataFrame with numeric-encoded items
        config: Analysis plan configuration

    Returns:
        Correlation matrix as DataFrame
    """
    scope = config.correlations.scope

    if scope == "all_items":
        items = config.items_universe
    elif scope == "indices_only":
        # No indices defined -> empty correlation matrix
        items = [idx.id for idx in config.indices]
    elif scope == "indices_and_items":
        items = config.correlations.items_explicit
    else:
        raise ValueError(f"Invalid correlations scope: {scope}")

    if not items:
        # Return empty correlation matrix
        return pd.DataFrame()

    # Filter to available columns
    available_items = [item for item in items if item in df.columns]
    if not available_items:
        return pd.DataFrame()

    subset = df[available_items].copy()

    # Compute Spearman correlations
    corr_matrix = subset.corr(method="spearman")

    return corr_matrix


@dataclass
class ConfirmatoryResult:
    """Result of a confirmatory test."""

    test_id: str
    dv: str
    iv: str | None
    statistic: float | None
    p: float | None
    p_adj: float | None
    effect_size: float | None
    n: int
    note: str


def run_confirmatory_tests(
    df: pd.DataFrame,
    config: AnalysisPlan,
) -> list[ConfirmatoryResult]:
    """Run all confirmatory tests defined in config.

    Args:
        df: DataFrame with numeric-encoded items
        config: Analysis plan configuration

    Returns:
        List of ConfirmatoryResult objects
    """
    if not config.confirmatory_tests:
        return [ConfirmatoryResult(
            test_id="none",
            dv="N/A",
            iv=None,
            statistic=None,
            p=None,
            p_adj=None,
            effect_size=None,
            n=len(df),
            note="No confirmatory tests defined",
        )]

    results = []
    for test in config.confirmatory_tests:
        if test.test_type == "descriptive":
            # Just report descriptive stats
            if test.dv in df.columns:
                series = df[test.dv].dropna()
                results.append(ConfirmatoryResult(
                    test_id=test.id,
                    dv=test.dv,
                    iv=None,
                    statistic=float(series.median()) if len(series) > 0 else None,
                    p=None,
                    p_adj=None,
                    effect_size=None,
                    n=len(series),
                    note="Descriptive only (median)",
                ))
            else:
                results.append(ConfirmatoryResult(
                    test_id=test.id,
                    dv=test.dv,
                    iv=None,
                    statistic=None,
                    p=None,
                    p_adj=None,
                    effect_size=None,
                    n=0,
                    note=f"DV column not found: {test.dv}",
                ))
        elif test.test_type == "mann_whitney":
            # Mann-Whitney U test for two-group comparison
            if test.iv_grouping and test.iv_grouping in df.columns:
                groups = df.groupby(test.iv_grouping)[test.dv].apply(list).to_dict()
                group_names = list(groups.keys())
                if len(group_names) == 2:
                    g1 = [x for x in groups[group_names[0]] if pd.notna(x)]
                    g2 = [x for x in groups[group_names[1]] if pd.notna(x)]
                    min_n = config.gating_thresholds.min_group_n
                    if len(g1) >= min_n and len(g2) >= min_n:
                        stat, p = stats.mannwhitneyu(g1, g2, alternative="two-sided")
                        # Rank-biserial correlation as effect size
                        n1, n2 = len(g1), len(g2)
                        r = 1 - (2 * stat) / (n1 * n2)
                        results.append(ConfirmatoryResult(
                            test_id=test.id,
                            dv=test.dv,
                            iv=test.iv_grouping,
                            statistic=float(stat),
                            p=float(p),
                            p_adj=None,  # Will be adjusted later
                            effect_size=float(r),
                            n=n1 + n2,
                            note=f"Mann-Whitney U (groups: {group_names[0]} vs {group_names[1]})",
                        ))
                    else:
                        results.append(ConfirmatoryResult(
                            test_id=test.id,
                            dv=test.dv,
                            iv=test.iv_grouping,
                            statistic=None,
                            p=None,
                            p_adj=None,
                            effect_size=None,
                            n=len(g1) + len(g2),
                            note=f"Skipped: group n < {min_n}",
                        ))
                else:
                    results.append(ConfirmatoryResult(
                        test_id=test.id,
                        dv=test.dv,
                        iv=test.iv_grouping,
                        statistic=None,
                        p=None,
                        p_adj=None,
                        effect_size=None,
                        n=0,
                        note=f"Mann-Whitney requires exactly 2 groups, found {len(group_names)}",
                    ))
            else:
                results.append(ConfirmatoryResult(
                    test_id=test.id,
                    dv=test.dv,
                    iv=test.iv_grouping,
                    statistic=None,
                    p=None,
                    p_adj=None,
                    effect_size=None,
                    n=0,
                    note="IV column not found",
                ))
        elif test.test_type == "kruskal_wallis":
            # Kruskal-Wallis H test for multi-group comparison
            if test.iv_grouping and test.iv_grouping in df.columns:
                groups = df.groupby(test.iv_grouping)[test.dv].apply(list).to_dict()
                min_n = config.gating_thresholds.min_group_n
                valid_groups = [
                    [x for x in g if pd.notna(x)]
                    for g in groups.values()
                    if len([x for x in g if pd.notna(x)]) >= min_n
                ]
                if len(valid_groups) >= 2:
                    stat, p = stats.kruskal(*valid_groups)
                    # Epsilon-squared as effect size: H/(N-1)
                    total_n = sum(len(g) for g in valid_groups)
                    epsilon_sq = stat / (total_n - 1) if total_n > 1 else None
                    results.append(ConfirmatoryResult(
                        test_id=test.id,
                        dv=test.dv,
                        iv=test.iv_grouping,
                        statistic=float(stat),
                        p=float(p),
                        p_adj=None,
                        effect_size=float(epsilon_sq) if epsilon_sq else None,
                        n=total_n,
                        note=f"Kruskal-Wallis ({len(valid_groups)} groups)",
                    ))
                else:
                    results.append(ConfirmatoryResult(
                        test_id=test.id,
                        dv=test.dv,
                        iv=test.iv_grouping,
                        statistic=None,
                        p=None,
                        p_adj=None,
                        effect_size=None,
                        n=0,
                        note=f"Skipped: fewer than 2 groups with n >= {min_n}",
                    ))
            else:
                results.append(ConfirmatoryResult(
                    test_id=test.id,
                    dv=test.dv,
                    iv=test.iv_grouping,
                    statistic=None,
                    p=None,
                    p_adj=None,
                    effect_size=None,
                    n=0,
                    note="IV column not found",
                ))

    return results


def apply_fdr_correction(
    results: list[ConfirmatoryResult],
    config: AnalysisPlan,
) -> list[ConfirmatoryResult]:
    """Apply FDR correction to confirmatory test p-values.

    Args:
        results: List of confirmatory test results
        config: Analysis plan configuration

    Returns:
        Updated list with p_adj values
    """
    # Get valid p-values
    p_values = [r.p for r in results if r.p is not None]

    if len(p_values) <= 1:
        # No correction needed for single test
        for r in results:
            if r.p is not None:
                r.p_adj = r.p
        return results

    # Apply correction
    method_map = {
        "bh": "fdr_bh",
        "bonferroni": "bonferroni",
        "holm": "holm",
    }
    method = method_map[config.fdr_settings.method]
    _, p_adj, _, _ = multipletests(p_values, alpha=config.fdr_settings.q, method=method)

    # Update results
    p_idx = 0
    for r in results:
        if r.p is not None:
            r.p_adj = float(p_adj[p_idx])
            p_idx += 1

    return results


def confirmatory_to_df(results: list[ConfirmatoryResult]) -> pd.DataFrame:
    """Convert confirmatory results to DataFrame."""
    return pd.DataFrame([
        {
            "test_id": r.test_id,
            "dv": r.dv,
            "iv": r.iv or "",
            "statistic": r.statistic,
            "p": r.p,
            "p_adj": r.p_adj,
            "effect_size": r.effect_size,
            "n": r.n,
            "note": r.note,
        }
        for r in results
    ])


def build_aggregates(
    df: pd.DataFrame,
    config: AnalysisPlan,
    descriptives: list[DescriptiveRow],
) -> dict:
    """Build aggregates.json content.

    Contains only aggregate statistics (no row-level data, timestamps, or free text).

    Args:
        df: Filtered DataFrame
        config: Analysis plan configuration
        descriptives: Computed descriptive statistics

    Returns:
        Dictionary for aggregates.json
    """
    items_agg = {}
    for d in descriptives:
        items_agg[d.item_id] = {
            "n": d.n,
            "median": d.median,
            "mode": d.mode,
            "response_pcts": {
                "1": d.pct_1,
                "2": d.pct_2,
                "3": d.pct_3,
                "4": d.pct_4,
                "5": d.pct_5,
            },
        }

    return {
        "n_respondents": len(df),
        "n_items": len(config.items_universe),
        "items": items_agg,
    }
