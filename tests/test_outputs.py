"""Tests for output generation."""

import json
from pathlib import Path

import pytest

from src.labels import LABEL_HARD_MAX, generate_labels, validate_labels
from src.schema import load_config


@pytest.fixture(scope="module")
def outputs_dir():
    """Path to outputs directory."""
    return Path("outputs")


# --- Label Tests ---


def test_labels_generated_for_all_items():
    """Ensure labels are generated for every items_universe column."""
    config = load_config()
    labels = generate_labels(config)

    for item in config.items_universe:
        assert item in labels, f"Missing label for: {item[:50]}..."


def test_all_labels_unique():
    """Ensure all short labels are unique."""
    config = load_config()
    labels = generate_labels(config)

    short_labels = list(labels.values())
    assert len(short_labels) == len(set(short_labels)), "Duplicate labels found"


def test_labels_within_length_limit():
    """Ensure no short label exceeds hard limit."""
    config = load_config()
    labels = generate_labels(config)

    for orig, short in labels.items():
        assert len(short) <= LABEL_HARD_MAX, (
            f"Label too long ({len(short)} chars): {short}"
        )


def test_validate_labels_returns_no_errors():
    """Ensure validate_labels passes for generated labels."""
    config = load_config()
    labels = generate_labels(config)
    errors = validate_labels(labels)

    assert errors == [], f"Label validation errors: {errors}"


def test_all_mandatory_outputs_exist(outputs_dir):
    """Test that all mandatory output files exist and are non-empty."""
    mandatory_files = [
        "descriptives_table.csv",
        "qa_log.md",
        "correlations.csv",
        "figures/corr_heatmap.png",
        "confirmatory_results.csv",
        "report.md",
        "methods_appendix.md",
        "slide_snippets.md",
        "figures/A_mandate_vs_financing.png",
        "figures/B_acceptable_cuts.png",
        "figures/C_inflation_drivers.png",
        "aggregates.json",
        "manifest.json",
    ]

    for filename in mandatory_files:
        filepath = outputs_dir / filename
        assert filepath.exists(), f"Missing mandatory output: {filename}"
        assert filepath.stat().st_size > 0, f"Empty mandatory output: {filename}"


def test_manifest_has_required_keys(outputs_dir):
    """Test that manifest.json has all 6 required keys."""
    manifest_path = outputs_dir / "manifest.json"
    assert manifest_path.exists()

    with open(manifest_path) as f:
        manifest = json.load(f)

    required_keys = [
        "input_hash",
        "analysis_plan_hash",
        "python_version",
        "library_versions",
        "timestamp_utc",
        "persona",
    ]

    for key in required_keys:
        assert key in manifest, f"Missing required manifest key: {key}"


def test_report_has_conf_expl_sections(outputs_dir):
    """Test that report.md has confirmatory and exploratory sections."""
    report_path = outputs_dir / "report.md"
    assert report_path.exists()

    content = report_path.read_text()
    assert "## Wyniki konfirmacyjne" in content, "Missing confirmatory section"
    assert "## Wyniki eksploracyjne" in content, "Missing exploratory section"


def test_descriptives_row_count_matches_items_universe(outputs_dir):
    """Test that descriptives_table.csv has correct row count."""
    import pandas as pd

    from src.schema import load_config

    config = load_config()
    desc_df = pd.read_csv(outputs_dir / "descriptives_table.csv")

    assert len(desc_df) == len(config.items_universe), (
        f"Row count mismatch: {len(desc_df)} vs {len(config.items_universe)}"
    )


def test_confirmatory_results_always_exists(outputs_dir):
    """Test that confirmatory_results.csv exists even with no tests."""
    import pandas as pd

    conf_path = outputs_dir / "confirmatory_results.csv"
    assert conf_path.exists()

    df = pd.read_csv(conf_path)
    # Should have header row and at least one data row (even if just a note)
    assert len(df) >= 1
    assert "test_id" in df.columns
    assert "note" in df.columns
