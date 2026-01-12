---
name: Prereg-safe PRD revision
overview: "Revise the existing PRD/scaffold plan to eliminate researcher degrees of freedom: introduce a locked `analysis_plan.yml`, hard-split Confirmatory vs Exploratory sections, require multiple-comparisons correction (BH-FDR), generate exhaustive \"full outputs\" to prevent cherry-picking, add reproducibility manifest, and enforce persona-invariant numerics with machine-verifiable acceptance criteria."
todos:
  - id: patch-prd-sections
    content: "Patch existing PRD with new sections: Research Integrity, Locked Config, updated Acceptance Criteria."
    status: pending
  - id: create-analysis-plan-yml
    content: Create config/analysis_plan.yml template with full schema (indices, tests, charts, thresholds, FDR, persona texts).
    status: pending
    dependencies:
      - patch-prd-sections
  - id: implement-schema-validation
    content: Implement src/schema.py with Pydantic models and CLI validation entrypoint.
    status: pending
    dependencies:
      - create-analysis-plan-yml
  - id: update-pipeline-config-load
    content: Update run_pipeline.py to load and validate analysis_plan.yml first; fail fast on errors.
    status: pending
    dependencies:
      - implement-schema-validation
  - id: add-exhaustive-outputs
    content: Generate outputs/descriptives_table.csv, outputs/qa_log.md, outputs/correlations.md, outputs/figures/corr_heatmap.png.
    status: pending
    dependencies:
      - update-pipeline-config-load
  - id: implement-fdr-wrapper
    content: Implement BH-FDR correction using statsmodels.stats.multitest.multipletests for confirmatory tests.
    status: pending
    dependencies:
      - update-pipeline-config-load
  - id: split-report-confirmatory-exploratory
    content: Split outputs/report.md into 'Wyniki konfirmacyjne' and 'Wyniki eksploracyjne' sections.
    status: pending
    dependencies:
      - add-exhaustive-outputs
      - implement-fdr-wrapper
  - id: add-manifest-json
    content: Generate outputs/manifest.json with input_hash, analysis_plan_hash, versions, timestamp, persona.
    status: pending
    dependencies:
      - update-pipeline-config-load
  - id: add-tests-prereg
    content: "Add tests: test_schema.py, test_outputs.py, test_persona_invariance.py."
    status: pending
    dependencies:
      - split-report-confirmatory-exploratory
      - add-manifest-json
  - id: update-docs-reuse-notes
    content: Update docs/PRD.md and REUSE_NOTES.md with FDR, Spearman, ordinal references.
    status: pending
    dependencies:
      - add-tests-prereg
---

# Prereg-Safe PRD Revision Plan

This plan patches the existing PRD+scaffold ([likert_survey_prd+scaffold_1f3ad681.plan.md](.cursor/plans/likert_survey_prd+scaffold_1f3ad681.plan.md)) to lock analytical degrees of freedom, separate confirmatory from exploratory outputs, apply FDR correction, and guarantee reproducibility.

---

## 1. PRD Patch Map

| Existing Section | Change Type | What to Add / Modify |

|------------------|-------------|----------------------|

| **Context & constraints** | Append | New subsection "Research Integrity & Degrees-of-Freedom Controls" describing locked config, exhaustive exploratory outputs, FDR, Confirmatory/Exploratory split, reproducibility manifest. |

| **Repo structure to create** | Append | Add `config/analysis_plan.yml`. |

| *(new section)* | Insert before "Tooling choice" | **Locked Analysis Plan Config (`config/analysis_plan.yml`)** with full schema description (see Section 3 below). |

| **Pipeline design** | Modify diagram | Add node: `configLoad[Validate analysis_plan.yml] `feeding into `loader`; add `manifest[Write manifest.json] `after `agg`. |

| **Key implementation decisions** | Append | Paragraph on BH-FDR: "For any test family with >1 hypothesis, apply Benjamini–Hochberg FDR at q=0.05. Report both raw p and adjusted p (q-value). The number of tests per family is explicit in `analysis_plan.yml`." |

| **Showcase findings & required charts** | Modify | Move chart list into `analysis_plan.yml`; PRD references config instead of hard-coding items. |

| **Required generated artifacts** | Append | `outputs/descriptives_table.csv`, `outputs/qa_log.md`, `outputs/correlations.md`, `outputs/figures/corr_heatmap.png`, `outputs/manifest.json`. |

| **Required generated artifacts** | Modify | `outputs/report.md` must contain headings "Wyniki konfirmacyjne" and "Wyniki eksploracyjne". |

| **Acceptance criteria** | Replace/Extend | See Section 4 below (machine-verifiable checklist). |

| **Git usage plan** | Append commit | Commit 2b: "add locked analysis_plan.yml + schema validation". |

| **Execution steps** | Append step | Step 2b: "Create `config/analysis_plan.yml` template; implement schema validation with Pydantic." |

---

## 2. New / Updated Artifacts

| File | Purpose |

|------|---------|

| `config/analysis_plan.yml` | Locked analysis plan: indices, confirmatory tests, exploratory defaults, gating thresholds, FDR settings, persona templates. |

| `src/schema.py` | Pydantic models for validating `analysis_plan.yml`. |

| `outputs/descriptives_table.csv` | Per-item N, missingness %, median, mode, distribution (1–5 %). Always generated. |

| `outputs/qa_log.md` | Filtering counts (18+, attention check), mapping summary, missing data log. Always generated. |

| `outputs/correlations.md` | Spearman correlation matrix for indices and key items. Always generated. |

| `outputs/figures/corr_heatmap.png` | Heatmap of Spearman correlations. Always generated. |

| `outputs/manifest.json` | Reproducibility manifest: input_hash, analysis_plan_hash, python_version, library_versions, timestamp_utc, persona. |

| `outputs/report.md` | Now requires two main headings: "Wyniki konfirmacyjne" (confirmatory) and "Wyniki eksploracyjne" (exploratory). |

| `tests/test_persona_invariance.py` | Automated test: aggregates.json byte-identical across personas. |

---

## 3. Config Spec: `analysis_plan.yml`

```yaml
# Example skeleton (no real data)
version: "1.0"

indices:
  - id: mandate_defense
    label_pl: "Mandat dla obronności"
    items:
      - q02_increase_defense
      - q03_priority_defense
    reverse_coded: []
    score_method: mean          # mean | median
    min_valid_items: 1          # pairwise vs listwise

  - id: financing_aversion
    label_pl: "Awersja do finansowania"
    items:
      - q09_tax_increase
      - q10_public_debt
    reverse_coded:
      - q09_tax_increase        # higher = less acceptable -> reverse
    score_method: mean
    min_valid_items: 1

confirmatory_tests:
  - id: H1
    description_hidden: "Mandate vs financing aversion"
    dv: mandate_defense
    iv_grouping: null           # if null -> descriptive comparison only
    test_type: descriptive
    filter: null
    family: confirmatory

  - id: H2
    description_hidden: "Gender difference in mandate"
    dv: mandate_defense
    iv_grouping: demo_gender
    test_type: mann_whitney
    filter: null
    family: confirmatory

exploratory_outputs:
  full_descriptives: true
  correlations: true            # Spearman matrix
  qa_log: true

gating_thresholds:
  min_group_n: 10
  max_item_missingness: 0.20
  min_n_efa: 150
  efa_min_items: 10

fdr_settings:
  q: 0.05
  method: bh                    # Benjamini–Hochberg

charts:
  - id: A_mandate_vs_financing
    type: diverging_bar
    items:
      - q02_increase_defense
      - q03_priority_defense
      - q09_tax_increase
      - q10_public_debt
  - id: B_acceptable_cuts
    type: stacked_bar
    items:
      - cuts_culture
      - cuts_admin
      - cuts_invest
      - cuts_transfers
  - id: C_inflation_drivers
    type: grouped_bar
    items:
      - q15_external
      - q16_firms
      - q17_transfers

persona_texts:
  campaign:
    report_intro: "Raport dla sztabu wyborczego..."
    slide_cta: "Rekomendacja: podkreślić mandat społeczny..."
  minfin:
    report_intro: "Raport dla Ministerstwa Finansów..."
    slide_cta: "Rekomendacja: uwzględnić ostrożność fiskalną..."
```

Pipeline validation rules (fail fast):

- `indices` must be non-empty.
- Each index must have ≥1 item.
- `confirmatory_tests` may be empty (pure exploratory mode).
- `charts` must list IDs matching `A_*`, `B_*`, `C_*` patterns for showcase.
- `gating_thresholds` must have all four keys with positive ints/floats.
- `fdr_settings.method` must be one of: `bh`, `bonferroni`, `holm`.

---

## 4. Updated Acceptance Criteria (machine-verifiable)

| # | Criterion | How to Test |

|---|-----------|-------------|

| 1 | `config/analysis_plan.yml` exists and passes schema validation. | `uv run python -c "from src.schema import validate; validate()"` exits 0. |

| 2 | Pipeline exits 0 with valid config. | `uv run python scripts/run_pipeline.py --config config/analysis_plan.yml` exits 0. |

| 3 | Pipeline exits non-zero if required config keys missing. | Remove `indices` key; pipeline errors with clear message. |

| 4 | `outputs/manifest.json` contains: `input_hash`, `analysis_plan_hash`, `python_version`, `library_versions`, `timestamp_utc`, `persona`. | Parse JSON and assert keys exist. |

| 5 | `outputs/report.md` contains headings `## Wyniki konfirmacyjne` and `## Wyniki eksploracyjne`. | Grep headings. |

| 6 | For confirmatory family with >1 test, output includes columns `p` and `p_adj`. | Parse `outputs/confirmatory_results.csv`; assert both columns present. |

| 7 | `outputs/descriptives_table.csv`, `outputs/qa_log.md`, `outputs/correlations.md`, `outputs/figures/corr_heatmap.png` exist and non-empty. | File size > 0. |

| 8 | Persona invariance: `outputs/aggregates.json` byte-identical for `--persona campaign` vs `--persona minfin`. | SHA-256 match. |

| 9 | Persona switch: `outputs/slide_snippets.md` differs between personas. | Diff non-empty. |

| 10 | `uv run pytest -q` passes (≥ 3 tests: schema, outputs, persona invariance). | Exit 0. |

---

## 5. Implementation Steps (with commits)

| Step | Description | Commit Message |

|------|-------------|----------------|

| 1 | Read current plan file; document patch locations in `active_context.md`. | (no commit; planning) |

| 2 | Create `config/` folder; add `analysis_plan.yml` template with all required keys. | `chore: add locked analysis_plan.yml template` |

| 3 | Implement `src/schema.py` with Pydantic models; add validation CLI entry. | `feat: schema validation for analysis_plan` |

| 4 | Update `scripts/run_pipeline.py` to load and validate config first; fail fast on errors. | `feat: pipeline loads locked config` |

| 5 | Extend aggregation to write `descriptives_table.csv`, `qa_log.md`. | `feat: exhaustive descriptives + QA log` |

| 6 | Add Spearman correlation matrix generation + heatmap export. | `feat: correlations.md + corr_heatmap.png` |

| 7 | Implement BH-FDR wrapper using `statsmodels.stats.multitest.multipletests`. | `feat: BH-FDR correction for confirmatory tests` |

| 8 | Split report template into Confirmatory / Exploratory sections (Polish headings). | `feat: report.md with confirmatory/exploratory split` |

| 9 | Add `outputs/manifest.json` generation with hashes, versions, timestamp. | `feat: reproducibility manifest` |

| 10 | Add `tests/test_schema.py`, `tests/test_outputs.py`, `tests/test_persona_invariance.py`. | `test: schema, outputs, persona invariance` |

| 11 | Update `docs/PRD.md` with all new sections; update `REUSE_NOTES.md` with FDR/Spearman references. | `docs: PRD prereg-safe revision` |

| 12 | Final smoke test; tag release `v0.1.0-prereg`. | `chore: tag v0.1.0-prereg` |

---

## 6. Risk Register

| Risk | Impact | Mitigation |

|------|--------|------------|

| **Selective reporting (p-hacking)** | High | Locked config + exhaustive exploratory tables; confirmatory tests list is immutable. |

| **Cherry-picking charts** | Medium | Chart list in config; only those charts generated. |

| **Ad-hoc index creation** | High | Any index not in config goes to exploratory and is labelled "post-hoc". |

| **Narrative spin** | Medium | Persona only changes text; aggregates.json identical; automated invariance test. |

| **Treating ordinal as interval** | Medium | Explicit ordinal warning in `methods_appendix.md`; medians primary; means labelled as approximation. |

| **Small group sizes** | Medium | `min_group_n` threshold; tests skipped with note if not met. |

| **EFA overfitting** | Medium | N≥150 + ≥10 items gate; skipped with note if not met. |

| **LLM hallucination** | Low | Aggregates-only input; max 60 words; optional; outputs clearly labelled. |

---

## 7. Open Questions (none blocking)

All design decisions have been resolved with reasonable defaults. No blocking questions remain.

---

## References (from Brave search)

- **FDR/BH**: Benjamini & Hochberg (1995); PMC5506159 general intro; statsmodels `multipletests` docs.
- **Polychoric vs Spearman**: R-bloggers polychoric explainer; PMC11073555 on ordinal reliability; ResearchGate discussion.
- **Effect sizes for rank tests**: Cross Validated discussion; epsilon-squared formula `H / (N-1)`; `pingouin` for rank-biserial.
- **Likert best practices**: PMC3886444 (medians + nonparametric); Statistics By Jim (bootstrapping).

These references will be added to `docs/REUSE_NOTES.md` during implementation.