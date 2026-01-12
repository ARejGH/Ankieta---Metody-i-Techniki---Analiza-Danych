---
name: PRD v2 simplicity fixes
overview: Patch the prereg-safe PRD to allow empty indices, make correlations exhaustive by default, require explicit reverse-coding, define deterministic missingness rules, add `outputs/confirmatory_results.csv` as mandatory artifact, and simplify by removing EFA and optional exploratory toggles.
todos:
  - id: add-items-universe
    content: Add items_universe (locked item list) + item_labels (optional display names) to analysis_plan.yml schema.
    status: pending
  - id: update-analysis-plan-schema
    content: "Update config/analysis_plan.yml: allow empty indices, add correlations block, add missingness_rules, remove EFA thresholds."
    status: pending
    dependencies:
      - add-items-universe
  - id: update-schema-py
    content: "Update src/schema.py: empty indices valid, correlations.scope enum, missingness_rules, no EFA."
    status: pending
    dependencies:
      - update-analysis-plan-schema
  - id: item-level-mode
    content: Update pipeline to run item-level descriptives/correlations when indices is empty.
    status: pending
    dependencies:
      - update-schema-py
  - id: reverse-coding
    content: Implement explicit reverse-coding (6-x formula), log direction_label_pl in methods_appendix.
    status: pending
    dependencies:
      - update-schema-py
  - id: missingness-handling
    content: Implement missingness flagging (no drop) and index NA rule per min_valid_items.
    status: pending
    dependencies:
      - update-schema-py
  - id: confirmatory-results-csv
    content: Generate outputs/confirmatory_results.csv always (header + note row if no tests).
    status: pending
    dependencies:
      - update-schema-py
  - id: add-new-tests
    content: "Add tests: test_zero_indices, test_correlations_scope, test_missingness_flags."
    status: pending
    dependencies:
      - item-level-mode
      - missingness-handling
      - confirmatory-results-csv
  - id: update-prd-docs
    content: Update docs/PRD.md with all v2 patches; update methods_appendix template.
    status: pending
    dependencies:
      - add-new-tests
---

# PRD v2: Simplicity & Determinism Fixes

This plan patches [prereg-safe_prd_revision_cd6626c8.plan.md](.cursor/plans/prereg-safe_prd_revision_cd6626c8.plan.md) to address five MUST fixes while simplifying the overall design.

---

## 1. PRD Patch Map

| Section (line ref) | Change | Details |

|--------------------|--------|---------|

| **Config Spec / validation rules** (line 210) | Modify | Change "indices must be non-empty" to "indices may be empty (valid); pipeline runs at item-level if no indices". |

| **Config Spec / indices schema** (lines 125–142) | Modify | Rename `reverse_coded` to `reverse_items`; add `direction_label_pl` field per index (e.g., "wyższe = silniejszy mandat"). |

| **Config Spec** (after indices block) | Add | New `correlations` block with `scope` enum and optional `items_explicit` list. |

| **Config Spec / exploratory_outputs** (lines 162–165) | Remove | Delete entire block; exhaustive outputs are always generated (no toggle). |

| **Config Spec / gating_thresholds** (lines 167–171) | Simplify | Remove `min_n_efa` and `efa_min_items`; EFA is out of scope. Keep only `min_group_n` and `max_item_missingness`. |

| **Config Spec** (after gating_thresholds) | Add | New `missingness_rules` block with `flag_threshold` and `index_na_rule`. |

| **New / Updated Artifacts** (line 106) | Modify | Change "Spearman correlation matrix for indices and key items" to "Spearman correlation matrix per `correlations.scope` (default: all Likert items)". |

| **New / Updated Artifacts** (after line 115) | Add | `outputs/confirmatory_results.csv` — always generated; schema specified. |

| **Acceptance criteria #3** (line 229) | Modify | Change test to "Remove `indices` key; pipeline still runs (indices optional)". |

| **Acceptance criteria #6** (line 235) | Modify | Add "outputs/confirmatory_results.csv always exists; if no confirmatory tests, file has header + note row". |

| **Acceptance criteria** (after #10) | Add | New criterion #11: "Pipeline runs with zero indices and still generates correlations + heatmap + descriptives". |

| **Risk Register** (lines 287–288) | Remove | Delete EFA-related row; EFA is out of scope. |

---

## 2. Updated Config Spec: `analysis_plan.yml`

```yaml
version: "1.0"

# --- ITEM UNIVERSE (LOCKED) ---
# Explicit list of exact CSV column headers for all Likert items.
# Only these columns are included in descriptives/correlations/plots.
# Pipeline fails fast if any listed column is missing from CSV.
items_universe:
  - "1. Obecna sytuacja bezpieczeństwa w regionie zwiększa ryzyko zagrożenia militarnego dla Polski."
  - "2. W najbliższych latach Polska powinna zwiększyć wydatki na obronność."
  - "3. Nawet kosztem innych wydatków publicznych obronność powinna być jednym z priorytetów budżetu państwa."
  - "Załóżmy, że państwo chce zwiększyć wydatki na obronność, ale bez podnoszenia łącznych wydatków budżetu.\nOznacza to, że większe wydatki na obronność musiałyby zostać sfinansowane przez mniejsze wydatki w innych obszarach.\nNa ile akceptowalne jest dla Ciebie zmniejszenie wydatków w poniższych obszarach? [Kultura (w tym sport)]"
  - "Załóżmy, że państwo chce zwiększyć wydatki na obronność, ale bez podnoszenia łącznych wydatków budżetu.\nOznacza to, że większe wydatki na obronność musiałyby zostać sfinansowane przez mniejsze wydatki w innych obszarach.\nNa ile akceptowalne jest dla Ciebie zmniejszenie wydatków w poniższych obszarach? [Administracja publiczna]"
  - "Załóżmy, że państwo chce zwiększyć wydatki na obronność, ale bez podnoszenia łącznych wydatków budżetu.\nOznacza to, że większe wydatki na obronność musiałyby zostać sfinansowane przez mniejsze wydatki w innych obszarach.\nNa ile akceptowalne jest dla Ciebie zmniejszenie wydatków w poniższych obszarach? [Inwestycje publiczne]"
  - "Załóżmy, że państwo chce zwiększyć wydatki na obronność, ale bez podnoszenia łącznych wydatków budżetu.\nOznacza to, że większe wydatki na obronność musiałyby zostać sfinansowane przez mniejsze wydatki w innych obszarach.\nNa ile akceptowalne jest dla Ciebie zmniejszenie wydatków w poniższych obszarach? [Transfery społeczne]"
  - "8. Przy decyzjach budżetowych ważne jest znalezienie kompromisu między bezpieczeństwem a innymi potrzebami społecznymi."
  - "9. Podwyższenie podatków (czyli płacilibyśmy więcej podatków niż obecnie) w celu sfinansowania większych wydatków na obronność jest dla mnie akceptowalne."
  - "10. Zaciągnięcie dodatkowego długu publicznego (pożyczenie pieniędzy przez państwo) w celu sfinansowania większych wydatków na obronność jest dla mnie akceptowalne."
  - "11. Jeśli trzeba wybrać, wolę finansowanie zwiększonych wydatków na obronność przez…"
  - "12. Państwo powinno ograniczać wydatki, aby unikać zadłużania się."
  - "14. Wzrost cen w ostatnich latach był dla mnie dużym obciążeniem finansowym."
  - "15. W jakim stopniu wzrost cen wynika z czynników zewnętrznych (np. ceny energii, sytuacja międzynarodowa)?"
  - "16. W jakim stopniu wzrost cen wynika z polityki cenowej firm (np. podwyżki cen, marże)?"
  - "17. W jakim stopniu wypłacanie świadczeń i dodatków przyczynia się do wzrostu cen?"
  - "18. Ograniczanie wydatków publicznych może pomóc w spowolnieniu inflacji."
  - "19. Poparł(a)bym ograniczenie części transferów socjalnych, jeśli miałoby to spowolnić wzrost cen."
  - "20. Gdy łączna korzyść finansowa jest podobna, wolę jednorazowy przelew od państwa niż stopniowe korzyści wynikające z niższych podatków."
  - "21. Jednorazowe bony/przelewy są dla mnie bardziej zrozumiałe niż ogólne obniżki podatków."
  - "22. Wolę wsparcie, które odczuwam od razu, niż takie, którego efekty pojawiają się stopniowo w dłuższym czasie."
  - "23. Instytucje publiczne nie są wystarczająco przejrzyste w informowaniu o tym, na co wydawane są pieniądze z budżetu państwa."
  - "24. Informacje o wydatkach publicznych są łatwo dostępne publicznie w internecie."
  - "25. Gdybym chciał(a) sprawdzić, na co idą pieniądze z budżetu państwa, potrafił(a)bym znaleźć wiarygodne, oficjalne źródła."
  - "26. Uważam, że mam podstawową wiedzę o tym, jak działa budżet państwa."
  - "27. Gdybym znalazł(a) dane o wydatkach budżetu, potrafił(a)bym ocenić, czy źródło jest rzetelne."
  # NOTE: Item 13 (attention check) and item 7 (voting eligibility) are excluded from Likert analysis.
  # Demographics columns (Płeć, Wiek, etc.) are metadata, not in items_universe.

# --- ITEM LABELS (optional, for display only) ---
# Short labels for charts/tables. Keys must match items_universe entries exactly.
# If omitted, pipeline uses truncated original headers.
item_labels:
  "1. Obecna sytuacja bezpieczeństwa w regionie zwiększa ryzyko zagrożenia militarnego dla Polski.": "Ryzyko militarne"
  "2. W najbliższych latach Polska powinna zwiększyć wydatki na obronność.": "Zwiększyć wydatki"
  "3. Nawet kosztem innych wydatków publicznych obronność powinna być jednym z priorytetów budżetu państwa.": "Priorytet obronności"
  # ... (remaining labels defined similarly)

# --- INDICES (may be empty) ---
indices: []
# OR:
# indices:
#   - id: mandate_defense
#     label_pl: "Mandat dla obronności"
#     direction_label_pl: "wyższe = silniejszy mandat"
#     items:
#       - q02_increase_defense
#       - q03_priority_defense
#     reverse_items: []                # explicit list; empty if none
#     score_method: mean               # mean | median
#     min_valid_items: 1               # respondent needs >= this many valid items

# --- CORRELATIONS ---
correlations:
  scope: all_items                     # all_items | indices_only | indices_and_items
  items_explicit: []                   # only used if scope = indices_and_items

# --- CONFIRMATORY TESTS (may be empty) ---
confirmatory_tests: []
# OR:
# confirmatory_tests:
#   - id: H1
#     dv: mandate_defense
#     iv_grouping: null
#     test_type: descriptive
#     family: confirmatory

# --- GATING THRESHOLDS ---
gating_thresholds:
  min_group_n: 10                      # skip group comparison if any group < this
  max_item_missingness: 0.20           # flag items exceeding this (do NOT drop)

# --- MISSINGNESS RULES ---
missingness_rules:
  flag_threshold: 0.20                 # items above this are flagged in qa_log
  index_na_rule: min_valid_items       # index = NA if respondent has < min_valid_items

# --- FDR SETTINGS ---
fdr_settings:
  q: 0.05
  method: bh                           # bh | bonferroni | holm

# --- CHARTS ---
charts:
  - id: A_mandate_vs_financing
    type: diverging_bar
    items: [q02_increase_defense, q03_priority_defense, q09_tax_increase, q10_public_debt]
  - id: B_acceptable_cuts
    type: stacked_bar
    items: [cuts_culture, cuts_admin, cuts_invest, cuts_transfers]
  - id: C_inflation_drivers
    type: grouped_bar
    items: [q15_external, q16_firms, q17_transfers]

# --- PERSONA TEXTS ---
persona_texts:
  campaign:
    report_intro: "Raport dla sztabu wyborczego..."
    slide_cta: "Rekomendacja: podkreślić mandat społeczny..."
  minfin:
    report_intro: "Raport dla Ministerstwa Finansów..."
    slide_cta: "Rekomendacja: uwzględnić ostrożność fiskalną..."
```

### Validation Rules (updated)

- `items_universe` must be a non-empty list of strings; each string must exactly match a column header in the input CSV. **Fail-fast**: pipeline errors immediately if any listed column is missing.
- `item_labels` is optional; if present, keys must be a subset of `items_universe`.
- `indices` may be empty (valid).
- If `indices` is non-empty, each index must have ≥1 item, and all items must be in `items_universe`.
- `correlations.scope` must be one of: `all_items`, `indices_only`, `indices_and_items`.
- If `scope = indices_and_items`, `items_explicit` must be non-empty and all items must be in `items_universe`.
- `confirmatory_tests` may be empty.
- `gating_thresholds` must have `min_group_n` and `max_item_missingness` with positive values.
- `missingness_rules` must have `flag_threshold` (0–1) and `index_na_rule` = `min_valid_items`.
- `fdr_settings.method` must be one of: `bh`, `bonferroni`, `holm`.
- `charts` must be non-empty with IDs matching `A_*`, `B_*`, `C_*`; all items referenced must be in `items_universe`.

---

## 2b. Item Universe (Locked)

- `items_universe` is an explicit list of **exact CSV column headers** for all Likert items to be analyzed.
- The pipeline computes descriptives, correlations, and plots **only** over columns in `items_universe` (plus derived indices, if any).
- Any CSV column **not** in `items_universe` is treated as metadata and excluded from statistical outputs.
- Changing `items_universe` constitutes a new analysis plan version (the `analysis_plan_hash` in `manifest.json` will differ).
- **Fail-fast**: if any column listed in `items_universe` is missing from the CSV, the pipeline exits immediately with a clear error message.
- `item_labels` (optional) provides short display names for charts/tables; it does not affect item selection.

---

## 3. Mandatory Outputs + Schemas

| File | Always Generated | Schema / Contents |

|------|------------------|-------------------|

| `outputs/descriptives_table.csv` | Yes | Columns: `item_id`, `n`, `missing_pct`, `median`, `mode`, `pct_1`, `pct_2`, `pct_3`, `pct_4`, `pct_5`, `flagged_missingness` |

| `outputs/qa_log.md` | Yes | Sections: items_universe count + list, ignored CSV columns, filtering counts (18+, attention check), missingness flags, mapping summary |

| `outputs/correlations.csv` | Yes | Spearman correlation matrix (per `correlations.scope`) |

| `outputs/figures/corr_heatmap.png` | Yes | Heatmap of above matrix |

| `outputs/confirmatory_results.csv` | Yes | Columns: `test_id`, `dv`, `iv`, `statistic`, `p`, `p_adj`, `effect_size`, `n`, `note`. If no tests: header + row with note "No confirmatory tests specified". |

| `outputs/report.md` | Yes | Headings: `## Wyniki konfirmacyjne`, `## Wyniki eksploracyjne` (Polish) |

| `outputs/methods_appendix.md` | Yes | Sections: Item Universe definition, Scoring Rules (reverse-coding formula, direction labels), Missingness Handling, FDR Correction, Limitations (Polish) |

| `outputs/slide_snippets.md` | Yes | 3 blocks per showcase chart (Polish) |

| `outputs/aggregates.json` | Yes | Aggregates only (no row-level data) |

| `outputs/manifest.json` | Yes | Keys: `input_hash`, `analysis_plan_hash`, `python_version`, `library_versions`, `timestamp_utc`, `persona` |

---

## 4. Updated Acceptance Criteria

| # | Criterion | How to Test |

|---|-----------|-------------|

| 1 | `analysis_plan.yml` passes schema validation. | `uv run python -c "from src.schema import validate; validate('config/analysis_plan.yml')"` exits 0. |

| 2 | Pipeline exits 0 with valid config. | `uv run python scripts/run_pipeline.py` exits 0. |

| 3 | Pipeline runs with `indices: []` (zero indices). | Remove all indices from config; pipeline still exits 0 and generates all mandatory outputs. |

| 4 | `correlations.scope` validation. | Set `scope: invalid`; pipeline errors with clear message. |

| 5 | `outputs/confirmatory_results.csv` always exists. | File exists and has header row; if no tests, contains note row. |

| 6 | FDR applied when >1 confirmatory test. | Parse `confirmatory_results.csv`; assert `p_adj` column present and values ≤ 1. |

| 7 | Exhaustive outputs generated. | `descriptives_table.csv`, `qa_log.md`, `correlations.csv`, `corr_heatmap.png` all exist and non-empty. |

| 8 | Manifest completeness. | Parse `manifest.json`; assert all 6 required keys present. |

| 9 | Report has confirmatory/exploratory split. | Grep `## Wyniki konfirmacyjne` and `## Wyniki eksploracyjne` in `report.md`. |

| 10 | Persona invariance. | `aggregates.json` byte-identical across `--persona campaign` and `--persona minfin`. |

| 11 | Persona switch changes text. | `slide_snippets.md` differs between personas. |

| 12 | Missingness flagged. | Items with missing_pct > `flag_threshold` have `flagged_missingness = True` in `descriptives_table.csv`. |

| 13 | Reverse-coding logged. | `methods_appendix.md` contains reverse-coding formula and direction labels for each index. |

| 14 | `uv run pytest -q` passes. | At least 4 tests: schema, outputs, persona invariance, zero-indices. |

| 15 | `items_universe` is non-empty and all listed columns exist in CSV. | Pipeline errors with clear message if any column missing (fail-fast). |

| 16 | Extra CSV columns not in `items_universe` are ignored. | Add a dummy column to CSV; verify it does not appear in `descriptives_table.csv` or `correlations.csv`. |

| 17 | Descriptives and correlations computed exactly over `items_universe`. | Assert row/column count in `descriptives_table.csv` equals `len(items_universe)`. |

| 18 | `qa_log.md` includes items_universe summary. | Grep for "items_universe" section with count and list. |

---

## 5. Implementation Steps + Commits

| Step | Description | Commit |

|------|-------------|--------|

| 1 | Update `config/analysis_plan.yml` template per new schema (empty indices, correlations block, no EFA). | `chore: simplify analysis_plan.yml schema` |

| 2 | Update `src/schema.py`: allow empty indices, add correlations.scope enum, add missingness_rules, remove EFA thresholds. | `feat: schema allows empty indices + correlations scope` |

| 3 | Update pipeline to run at item-level if indices empty; generate correlations per scope. | `feat: item-level mode when no indices` |

| 4 | Implement reverse-coding with formula `6 - x`; log direction_label_pl in methods_appendix. | `feat: explicit reverse-coding + direction labels` |

| 5 | Implement missingness flagging (don't drop items); index = NA per min_valid_items. | `feat: deterministic missingness handling` |

| 6 | Add `outputs/confirmatory_results.csv` generation (header + note if empty). | `feat: confirmatory_results.csv always generated` |

| 7 | Update tests: add test_zero_indices, test_correlations_scope, test_missingness_flags. | `test: zero-indices + correlations + missingness` |

| 8 | Update `docs/PRD.md` with all patches; update methods_appendix template. | `docs: PRD v2 simplicity fixes` |

| 9 | Final smoke test. | `chore: smoke test v2` |

---

## 6. Simplicity Check: Removed / Avoided Complexities

| Removed | Reason |

|---------|--------|

| `exploratory_outputs` toggle block | Always generate everything; no opt-out reduces bugs and prevents hiding data. |

| `min_n_efa`, `efa_min_items` thresholds | EFA is out of scope; removing these eliminates an optional code path. |

| "key items" concept | Replaced with deterministic `correlations.scope` enum; no heuristics. |

| Implicit reverse-coding from item text | `reverse_items` must be explicit list; no inference. |

| Indices-required validation rule | Indices may be empty; pipeline runs at item-level. |

| `description_hidden` field in tests | Simplified to just `id`; description goes in PRD, not config. |

**Net result**: ~5 fewer config knobs, ~3 fewer optional code branches, clearer schema.

---

## 7. Final QA Answers

| Question | Answer |

|----------|--------|

| Did we eliminate all "key items" or data-driven selection? | Yes. `correlations.scope` with explicit enum and no "auto" mode. |

| Can pipeline run with zero indices? | Yes. Validation allows empty; pipeline generates item-level descriptives + correlations. |

| Are reverse-coding and directionality unambiguous? | Yes. `reverse_items` is explicit list; `direction_label_pl` required per index; formula documented. |

| Are missingness decisions deterministic and logged? | Yes. `flag_threshold` flags items; `index_na_rule` determines index NA; all logged in qa_log + methods_appendix. |

| Are acceptance criteria consistent with artifacts? | Yes. `confirmatory_results.csv` is now mandatory and tested. |