"""Tests for persona invariance."""

import tempfile
from pathlib import Path


def test_aggregates_byte_identical_across_personas():
    """Test that aggregates.json is byte-identical for campaign vs minfin."""
    from scripts.run_pipeline import run_pipeline

    with tempfile.TemporaryDirectory() as tmpdir:
        output_campaign = Path(tmpdir) / "campaign"
        output_minfin = Path(tmpdir) / "minfin"

        # Run pipeline with campaign persona
        run_pipeline(persona="campaign", output_dir=output_campaign)

        # Run pipeline with minfin persona
        run_pipeline(persona="minfin", output_dir=output_minfin)

        # Compare aggregates.json
        agg_campaign = (output_campaign / "aggregates.json").read_bytes()
        agg_minfin = (output_minfin / "aggregates.json").read_bytes()

        assert agg_campaign == agg_minfin, "aggregates.json differs between personas!"


def test_slide_snippets_differ_between_personas():
    """Test that slide_snippets.md differs between personas."""
    from scripts.run_pipeline import run_pipeline

    with tempfile.TemporaryDirectory() as tmpdir:
        output_campaign = Path(tmpdir) / "campaign"
        output_minfin = Path(tmpdir) / "minfin"

        # Run pipeline with both personas
        run_pipeline(persona="campaign", output_dir=output_campaign)
        run_pipeline(persona="minfin", output_dir=output_minfin)

        # Compare slide_snippets.md
        slides_campaign = (output_campaign / "slide_snippets.md").read_text()
        slides_minfin = (output_minfin / "slide_snippets.md").read_text()

        assert slides_campaign != slides_minfin, "slide_snippets.md should differ between personas!"
