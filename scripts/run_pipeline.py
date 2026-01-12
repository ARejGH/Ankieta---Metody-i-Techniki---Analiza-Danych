#!/usr/bin/env python3
"""CLI entrypoint for the Likert Survey Analysis Pipeline."""

import argparse
import os
import sys
from pathlib import Path
from typing import Literal

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analysis import (
    apply_fdr_correction,
    build_aggregates,
    compute_correlations,
    compute_descriptives,
    confirmatory_to_df,
    descriptives_to_df,
    run_confirmatory_tests,
)
from src.loader import encode_likert, load_and_filter
from src.outputs import (
    generate_chart_a,
    generate_chart_b,
    generate_chart_c,
    generate_correlation_heatmap,
    init_labels,
    write_aggregates,
    write_manifest,
    write_methods_appendix,
    write_qa_log,
    write_report,
    write_slide_snippets,
)
from src.schema import load_config


def run_pipeline(
    persona: Literal["campaign", "minfin"] = "campaign",
    config_path: Path | None = None,
    csv_path: Path | None = None,
    output_dir: Path | None = None,
) -> None:
    """Run the full analysis pipeline.

    Args:
        persona: Persona for text outputs (campaign or minfin)
        config_path: Path to config file
        csv_path: Path to CSV file
        output_dir: Path to output directory
    """
    # Set defaults
    if config_path is None:
        config_path = Path("config/analysis_plan.yml")
    if csv_path is None:
        csv_path = Path("data/raw/survey_latest.csv")
    if output_dir is None:
        output_dir = Path("outputs")

    # Ensure output directories exist
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "figures").mkdir(exist_ok=True)

    print(f"Loading config from {config_path}...")
    config = load_config(config_path)
    print(f"✓ Config valid: {len(config.items_universe)} items in universe")

    print("Initializing label mapping...")
    labels = init_labels(config, output_dir)
    print(f"✓ Generated labels for {len(labels)} items, wrote label_map.csv")

    print(f"Loading data from {csv_path}...")
    load_result = load_and_filter(config, csv_path)
    print(f"✓ Loaded {load_result.n_total} rows, {load_result.n_after_attention} after QA filters")

    print("Encoding Likert responses...")
    df = encode_likert(load_result.df, config.items_universe)

    print("Computing descriptives...")
    descriptives = compute_descriptives(
        df, config.items_universe, config.missingness_rules.flag_threshold
    )
    desc_df = descriptives_to_df(descriptives)
    desc_df.to_csv(output_dir / "descriptives_table.csv", index=False)
    print(f"✓ Wrote descriptives_table.csv ({len(descriptives)} items)")

    print("Computing correlations...")
    corr_matrix = compute_correlations(df, config)
    corr_matrix.to_csv(output_dir / "correlations.csv")
    print(f"✓ Wrote correlations.csv ({corr_matrix.shape})")

    print("Running confirmatory tests...")
    confirmatory = run_confirmatory_tests(df, config)
    confirmatory = apply_fdr_correction(confirmatory, config)
    conf_df = confirmatory_to_df(confirmatory)
    conf_df.to_csv(output_dir / "confirmatory_results.csv", index=False)
    print(f"✓ Wrote confirmatory_results.csv ({len(confirmatory)} tests)")

    print("Building aggregates...")
    aggregates = build_aggregates(df, config, descriptives)
    write_aggregates(aggregates, output_dir)
    print("✓ Wrote aggregates.json")

    print("Generating charts...")
    generate_chart_a(df, config, descriptives, output_dir)
    print("✓ Generated A_mandate_vs_financing.png")
    generate_chart_b(df, config, descriptives, output_dir)
    print("✓ Generated B_acceptable_cuts.png")
    generate_chart_c(df, config, descriptives, output_dir)
    print("✓ Generated C_inflation_drivers.png")
    generate_correlation_heatmap(corr_matrix, config, output_dir)
    print("✓ Generated corr_heatmap.png")

    print(f"Writing reports (persona: {persona})...")
    write_qa_log(config, load_result, descriptives, output_dir)
    print("✓ Wrote qa_log.md")
    write_report(config, descriptives, confirmatory, persona, output_dir)
    print("✓ Wrote report.md")
    write_methods_appendix(config, output_dir)
    print("✓ Wrote methods_appendix.md")
    write_slide_snippets(config, descriptives, persona, output_dir)
    print("✓ Wrote slide_snippets.md")

    print("Writing manifest...")
    write_manifest(config_path, csv_path, persona, output_dir)
    print("✓ Wrote manifest.json")

    # Optional: LLM captions
    if os.environ.get("OPENAI_API_KEY"):
        print("Generating LLM captions...")
        try:
            from src.llm_captions import generate_captions

            generate_captions(aggregates, config, output_dir)
            print("✓ Wrote llm_captions.md")
        except ImportError:
            print("⚠ LLM module not available, skipping captions")
    else:
        print("ℹ OPENAI_API_KEY not set, skipping LLM captions")

    print("\n✓ Pipeline complete!")
    print(f"  Outputs written to: {output_dir.absolute()}")


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Likert Survey Analysis Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--persona",
        choices=["campaign", "minfin"],
        default="campaign",
        help="Persona for text outputs (default: campaign)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to config file (default: config/analysis_plan.yml)",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="Path to CSV file (default: data/raw/survey_latest.csv)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Path to output directory (default: outputs)",
    )

    args = parser.parse_args()

    try:
        run_pipeline(
            persona=args.persona,
            config_path=args.config,
            csv_path=args.csv,
            output_dir=args.output,
        )
    except Exception as e:
        print(f"✗ Pipeline failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
