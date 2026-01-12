# CLAUDE.md - Agent Working Rules

## Project Overview

This is a Likert survey analysis pipeline for a Polish research project on budget priorities and security. The pipeline produces presentation-ready outputs in Polish while maintaining strict research integrity controls.

## Key Files

- `docs/PRD.md` - Canonical requirements document
- `config/analysis_plan.yml` - Locked analysis configuration
- `scripts/run_pipeline.py` - Main entrypoint
- `src/schema.py` - Pydantic validation
- `src/loader.py` - CSV loading + QA filters
- `src/analysis.py` - Statistical computations
- `src/outputs.py` - Report/chart generation

## Commands

```bash
# Run pipeline
uv run python scripts/run_pipeline.py

# Run with minfin persona
uv run python scripts/run_pipeline.py --persona minfin

# Validate config
uv run python -c "from src.schema import validate; validate()"

# Run tests
uv run pytest -q

# Lint
uv run ruff check .
```

## Critical Rules

1. **items_universe is LOCKED** - Only columns in `items_universe` are analyzed
2. **Fail-fast** - Missing CSV columns cause immediate error
3. **Persona invariance** - `aggregates.json` must be byte-identical across personas
4. **Polish outputs** - All reports/charts use Polish text
5. **No heuristics** - All decisions pre-specified in config

## Language Policy

| Context | Language |
|---------|----------|
| Code, comments | English |
| README, CLAUDE.md | English |
| Reports, charts | Polish |

## Testing

Tests verify:
- Schema validation
- All mandatory outputs exist
- Manifest has required keys
- Report has conf/expl sections
- Persona invariance
