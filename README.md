# Likert Survey Analysis Pipeline

A minimal, prereg-safe Python pipeline for same-day analysis of a Likert-scale survey ("Budget priorities and security"). Produces presentation-ready outputs in Polish.

## Quick Start

```bash
# Install dependencies
uv sync

# Run the pipeline
uv run python scripts/run_pipeline.py

# Run with different persona
uv run python scripts/run_pipeline.py --persona minfin

# Validate schema
uv run python -c "from src.schema import validate; validate()"

# Run tests
uv run pytest -q
```

## Outputs

All outputs are written to `outputs/`:

| File | Description |
|------|-------------|
| `descriptives_table.csv` | Descriptive statistics for all items |
| `qa_log.md` | QA filter counts and missingness flags |
| `correlations.csv` | Spearman correlation matrix |
| `figures/corr_heatmap.png` | Correlation heatmap |
| `confirmatory_results.csv` | Confirmatory test results with FDR |
| `report.md` | Full report (Polish) |
| `methods_appendix.md` | Methodology documentation |
| `slide_snippets.md` | Presentation-ready content |
| `figures/A_*.png` | Chart A: Mandate vs financing |
| `figures/B_*.png` | Chart B: Acceptable cuts |
| `figures/C_*.png` | Chart C: Inflation drivers |
| `aggregates.json` | Aggregate statistics (no PII) |
| `manifest.json` | Reproducibility metadata |

## Configuration

All analysis decisions are pre-specified in `config/analysis_plan.yml`:

- `items_universe`: Exact CSV column headers for Likert items
- `qa_filters`: Age and attention check filters
- `charts`: Chart definitions (A/B/C)
- `persona_texts`: Campaign vs MinFin narratives

## Personas

The pipeline supports two personas that change only the narrative text:

- `campaign`: Campaign-focused messaging
- `minfin`: Ministry of Finance messaging

**Important**: `aggregates.json` is byte-identical across personas (tested).

## Research Integrity

- **Locked config**: Changing `analysis_plan.yml` changes the manifest hash
- **Fail-fast**: Missing columns cause immediate pipeline failure
- **Exhaustive outputs**: All items analyzed, no cherry-picking
- **Conf/Expl split**: Clear separation in report.md

## Requirements

- Python 3.11+
- uv (package manager)
