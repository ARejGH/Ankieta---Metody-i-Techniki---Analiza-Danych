"""CSV loader with QA filters."""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.schema import AnalysisPlan


@dataclass
class LoadResult:
    """Result of loading and filtering the data."""

    df: pd.DataFrame
    n_total: int
    n_after_age: int
    n_after_attention: int
    ignored_columns: list[str]


def load_and_filter(
    config: AnalysisPlan,
    csv_path: Path | None = None,
) -> LoadResult:
    """Load CSV and apply QA filters.

    Args:
        config: Validated analysis plan
        csv_path: Path to CSV file. Defaults to data/raw/survey_latest.csv

    Returns:
        LoadResult with filtered DataFrame and QA stats

    Raises:
        FileNotFoundError: If CSV file doesn't exist
        ValueError: If any items_universe column is missing from CSV
    """
    if csv_path is None:
        csv_path = Path("data/raw/survey_latest.csv")

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    # Load CSV
    df = pd.read_csv(csv_path)
    n_total = len(df)

    # Validate items_universe columns exist
    csv_columns = set(df.columns)
    for item in config.items_universe:
        if item not in csv_columns:
            raise ValueError(f"items_universe column missing from CSV: {item}")

    # Validate QA filter columns exist
    qa = config.qa_filters
    if qa.age_column not in csv_columns:
        raise ValueError(f"age_column missing from CSV: {qa.age_column}")
    if qa.attention_check_column not in csv_columns:
        raise ValueError(f"attention_check_column missing from CSV: {qa.attention_check_column}")

    # Apply age filter
    df = df[df[qa.age_column] == qa.age_keep_value].copy()
    n_after_age = len(df)

    # Apply attention check filter
    df = df[df[qa.attention_check_column] == qa.attention_check_expected].copy()
    n_after_attention = len(df)

    # Identify ignored columns (not in items_universe and not QA/metadata)
    items_set = set(config.items_universe)
    qa_columns = {qa.age_column, qa.attention_check_column}
    ignored_columns = [
        col for col in df.columns
        if col not in items_set and col not in qa_columns
    ]

    return LoadResult(
        df=df,
        n_total=n_total,
        n_after_age=n_after_age,
        n_after_attention=n_after_attention,
        ignored_columns=ignored_columns,
    )


# Likert scale mappings for encoding
LIKERT_AGREE_MAP = {
    "Zdecydowanie się nie zgadzam": 1,
    "Raczej się nie zgadzam": 2,
    "Ani tak, ani nie": 3,
    "Raczej się zgadzam": 4,
    "Zdecydowanie się zgadzam": 5,
}

LIKERT_DEGREE_MAP = {
    "Wcale": 1,
    "W małym stopniu": 2,
    "W umiarkowanym stopniu": 3,
    "W dużym stopniu": 4,
    "W bardzo dużym stopniu": 5,
}


def encode_likert(df: pd.DataFrame, items: list[str]) -> pd.DataFrame:
    """Encode Likert responses to numeric values.

    Handles both agree/disagree scale and degree scale.
    Numeric strings (1-5) are converted directly.

    Args:
        df: DataFrame with Likert responses
        items: List of column names to encode

    Returns:
        DataFrame with numeric encoded values
    """
    df = df.copy()

    for col in items:
        if col not in df.columns:
            continue

        series = df[col]

        # Check if already numeric
        if pd.api.types.is_numeric_dtype(series):
            continue

        # Try to convert string numbers first
        try:
            numeric = pd.to_numeric(series, errors="coerce")
            if numeric.notna().any():
                df[col] = numeric
                continue
        except (ValueError, TypeError):
            pass

        # Map Likert text to numbers
        mapped = series.map(LIKERT_AGREE_MAP)
        if mapped.notna().sum() < series.notna().sum() * 0.5:
            # Try degree scale if agree scale didn't work well
            mapped = series.map(LIKERT_DEGREE_MAP)

        df[col] = mapped

    return df
