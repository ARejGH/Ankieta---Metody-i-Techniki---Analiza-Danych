"""Tests for schema validation."""


import pytest
from pydantic import ValidationError

from src.schema import AnalysisPlan, load_config


def test_config_loads_successfully():
    """Test that the default config loads and validates."""
    config = load_config()
    assert len(config.items_universe) == 25
    assert config.version == "1.0"


def test_invalid_correlations_scope_fails():
    """Test that invalid correlations scope raises error."""
    # Create a minimal invalid config
    raw = {
        "version": "1.0",
        "items_universe": ["test_item"],
        "qa_filters": {
            "age_column": "age",
            "age_keep_value": "Yes",
            "attention_check_column": "attention",
            "attention_check_expected": "correct",
        },
        "indices": [],
        "correlations": {
            "scope": "invalid_scope",  # Invalid!
            "items_explicit": [],
        },
        "confirmatory_tests": [],
        "gating_thresholds": {"min_group_n": 10},
        "missingness_rules": {"flag_threshold": 0.20, "index_na_rule": "min_valid_items"},
        "fdr_settings": {"q": 0.05, "method": "bh"},
        "charts": [{"id": "A_test", "type": "diverging_bar", "items": ["test_item"]}],
        "persona_texts": {
            "campaign": {"report_intro": "test", "slide_cta": "test"},
            "minfin": {"report_intro": "test", "slide_cta": "test"},
        },
    }

    with pytest.raises(ValidationError) as exc_info:
        AnalysisPlan.model_validate(raw)

    assert "correlations" in str(exc_info.value).lower() or "scope" in str(exc_info.value).lower()


def test_chart_items_must_be_in_universe():
    """Test that chart items must be in items_universe."""
    raw = {
        "version": "1.0",
        "items_universe": ["test_item"],
        "qa_filters": {
            "age_column": "age",
            "age_keep_value": "Yes",
            "attention_check_column": "attention",
            "attention_check_expected": "correct",
        },
        "indices": [],
        "correlations": {"scope": "all_items", "items_explicit": []},
        "confirmatory_tests": [],
        "gating_thresholds": {"min_group_n": 10},
        "missingness_rules": {"flag_threshold": 0.20, "index_na_rule": "min_valid_items"},
        "fdr_settings": {"q": 0.05, "method": "bh"},
        "charts": [
            {
                "id": "A_test",
                "type": "diverging_bar",
                "items": ["not_in_universe"],  # Invalid!
            }
        ],
        "persona_texts": {
            "campaign": {"report_intro": "test", "slide_cta": "test"},
            "minfin": {"report_intro": "test", "slide_cta": "test"},
        },
    }

    with pytest.raises(ValidationError) as exc_info:
        AnalysisPlan.model_validate(raw)

    assert "not in items_universe" in str(exc_info.value)
