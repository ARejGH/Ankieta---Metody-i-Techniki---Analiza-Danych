"""Output generation: reports, charts, manifest."""

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from src.analysis import ConfirmatoryResult, DescriptiveRow
from src.labels import generate_labels, get_label, write_label_map_csv
from src.loader import LoadResult
from src.schema import AnalysisPlan

# Module-level label cache (populated per pipeline run)
_label_map: dict[str, str] = {}


def init_labels(config: AnalysisPlan, output_dir: Path) -> dict[str, str]:
    """Initialize label mapping and write to output directory.

    Returns the label map for use in chart generation.
    """
    global _label_map
    _label_map = generate_labels(config)
    write_label_map_csv(_label_map, output_dir)
    return _label_map


def get_item_label(item: str, config: AnalysisPlan) -> str:
    """Get display label for an item."""
    # Use cached label map if available
    if _label_map and item in _label_map:
        return _label_map[item]
    # Fallback to config-based lookup
    return get_label(item, config.item_labels)


def write_qa_log(
    config: AnalysisPlan,
    load_result: LoadResult,
    descriptives: list[DescriptiveRow],
    output_dir: Path,
) -> None:
    """Write qa_log.md with QA filter results and item info."""
    flagged = [d for d in descriptives if d.flagged_missingness]

    content = f"""# Dziennik kontroli jakości (QA Log)

## Definicja zbioru danych

### items_universe
- **Liczba pozycji**: {len(config.items_universe)}
- **Lista pozycji**:
"""
    for i, item in enumerate(config.items_universe, 1):
        label = get_item_label(item, config)
        content += f"  {i}. {label}\n"

    content += f"""
### Kolumny pominięte (metadata)
- **Liczba**: {len(load_result.ignored_columns)}
- Timestamp, dane demograficzne, pytania kontrolne

## Filtrowanie QA

| Etap | Liczba respondentów |
|------|---------------------|
| Wczytane z CSV | {load_result.n_total} |
| Po filtrze wieku (18+) | {load_result.n_after_age} |
| Po filtrze uwagi | {load_result.n_after_attention} |

- **Usunięto (wiek < 18)**: {load_result.n_total - load_result.n_after_age}
- **Usunięto (błąd uwagi)**: {load_result.n_after_age - load_result.n_after_attention}

## Flagi braków danych

Próg: {config.missingness_rules.flag_threshold * 100:.0f}%
"""
    if flagged:
        content += "\n| Pozycja | % braków |\n|---------|----------|\n"
        for d in flagged:
            content += f"| {get_item_label(d.item_id, config)} | {d.missing_pct * 100:.1f}% |\n"
    else:
        content += "\nBrak pozycji z przekroczonym progiem braków danych.\n"

    (output_dir / "qa_log.md").write_text(content, encoding="utf-8")


def write_report(
    config: AnalysisPlan,
    descriptives: list[DescriptiveRow],
    confirmatory: list[ConfirmatoryResult],
    persona: Literal["campaign", "minfin"],
    output_dir: Path,
) -> None:
    """Write report.md with confirmatory and exploratory sections."""
    persona_text = config.persona_texts[persona]

    content = f"""# Raport: Priorytety budżetowe i bezpieczeństwo

{persona_text.report_intro}

---

## Wyniki konfirmacyjne

"""
    if confirmatory and confirmatory[0].note != "No confirmatory tests defined":
        content += "| Test | Zmienna | Statystyka | p | p (skorygowane) | Wielkość efektu | n |\n"
        content += "|------|---------|------------|---|-----------------|-----------------|---|\n"
        for r in confirmatory:
            stat_str = f"{r.statistic:.2f}" if r.statistic else "—"
            p_str = f"{r.p:.4f}" if r.p else "—"
            padj_str = f"{r.p_adj:.4f}" if r.p_adj else "—"
            eff_str = f"{r.effect_size:.3f}" if r.effect_size else "—"
            dv_short = r.dv[:30]
            cols = [r.test_id, dv_short, stat_str, p_str, padj_str, eff_str, str(r.n)]
            content += "| " + " | ".join(cols) + " |\n"
    else:
        content += "*Brak zdefiniowanych testów konfirmacyjnych.*\n"

    content += """
---

## Wyniki eksploracyjne

### Statystyki opisowe

Poniżej przedstawiono statystyki opisowe dla wszystkich pozycji ankiety.

| Pozycja | n | Mediana | Moda | % odpowiedzi 4-5 |
|---------|---|---------|------|------------------|
"""
    for d in descriptives[:10]:  # Show top 10
        label = get_item_label(d.item_id, config)[:40]
        agree_pct = (d.pct_4 + d.pct_5) * 100
        mode_str = f"{d.mode:.0f}" if d.mode else "—"
        content += f"| {label} | {d.n} | {d.median:.1f} | {mode_str} | {agree_pct:.1f}% |\n"

    if len(descriptives) > 10:
        remaining = len(descriptives) - 10
        note = f"... i {remaining} pozostałych pozycji (pełne dane w descriptives_table.csv)"
        content += f"\n*{note}*\n"

    content += """
### Korelacje

Macierz korelacji Spearmana dostępna w `correlations.csv` i `figures/corr_heatmap.png`.

---

## Ograniczenia

- Dane pochodzą z jednorazowego badania ankietowego
- Skale Likerta traktowane są jako dane porządkowe (stosowano mediany i testy nieparametryczne)
- Brak możliwości wnioskowania przyczynowego
"""

    (output_dir / "report.md").write_text(content, encoding="utf-8")


def write_methods_appendix(
    config: AnalysisPlan,
    output_dir: Path,
) -> None:
    """Write methods_appendix.md with methodology details."""
    content = """# Aneks metodologiczny

## Item Universe (Zbiór pozycji)

Analiza obejmuje wyłącznie pozycje zdefiniowane w `items_universe` w konfiguracji.
Każda pozycja musi dokładnie odpowiadać nagłówkowi kolumny w pliku CSV.

## Zasady kodowania

### Skala zgadzania się
- 1 = Zdecydowanie się nie zgadzam
- 2 = Raczej się nie zgadzam
- 3 = Ani tak, ani nie
- 4 = Raczej się zgadzam
- 5 = Zdecydowanie się zgadzam

### Skala stopnia
- 1 = Wcale
- 2 = W małym stopniu
- 3 = W umiarkowanym stopniu
- 4 = W dużym stopniu
- 5 = W bardzo dużym stopniu

### Skala akceptowalności (pozycje 4-7)
- 1 = Zdecydowanie nieakceptowalne
- 5 = Zdecydowanie akceptowalne

### Odwracanie kodowania
Dla pozycji wymagających odwrócenia stosowana jest formuła: `6 - x`

Kierunek interpretacji dla każdego indeksu jest podany w konfiguracji (`direction_label_pl`).

## Braki danych

- Braki danych są flagowane, gdy przekraczają próg `flag_threshold` (domyślnie 20%)
- Pozycje z brakami danych NIE są automatycznie usuwane
- Dla indeksów: wartość = NA, jeśli respondent ma mniej ważnych pozycji niż `min_valid_items`

## Korekta wielokrotnych porównań

Dla rodzin z więcej niż jednym testem konfirmacyjnym stosowana jest korekta FDR:
- Metoda: Benjamini-Hochberg (domyślnie)
- Poziom q: 0.05

## Ograniczenia metodologiczne

1. **Dane porządkowe**: Skale Likerta są danymi porządkowymi, nie interwałowymi.
   - Stosujemy mediany jako miarę tendencji centralnej
   - Stosujemy testy nieparametryczne (Mann-Whitney U, Kruskal-Wallis)
   - Średnie są raportowane jako przybliżenie, z odpowiednim oznaczeniem

2. **Brak wnioskowania przyczynowego**: Badanie przekrojowe nie pozwala na wnioski przyczynowe.

3. **Selektywność próby**: Próba może nie być reprezentatywna dla populacji ogólnej.
"""
    (output_dir / "methods_appendix.md").write_text(content, encoding="utf-8")


def write_slide_snippets(
    config: AnalysisPlan,
    descriptives: list[DescriptiveRow],
    persona: Literal["campaign", "minfin"],
    output_dir: Path,
) -> None:
    """Write slide_snippets.md with presentation-ready content."""
    persona_text = config.persona_texts[persona]

    # Find items for each chart
    chart_a_items = next(c.items for c in config.charts if c.id.startswith("A_"))
    chart_b_items = next(c.items for c in config.charts if c.id.startswith("B_"))
    chart_c_items = next(c.items for c in config.charts if c.id.startswith("C_"))

    # Get descriptives for chart items
    desc_map = {d.item_id: d for d in descriptives}

    def get_top_agree(items: list[str]) -> tuple[str, float]:
        """Get item with highest agreement."""
        best = None
        best_pct = 0.0
        for item in items:
            if item in desc_map:
                pct = desc_map[item].pct_4 + desc_map[item].pct_5
                if pct > best_pct:
                    best_pct = pct
                    best = item
        return get_item_label(best, config) if best else "—", best_pct * 100

    def get_median_range(items: list[str]) -> tuple[float, float]:
        """Get median range for items."""
        medians = [desc_map[i].median for i in items if i in desc_map]
        return (min(medians), max(medians)) if medians else (0, 0)

    a_top, a_pct = get_top_agree(chart_a_items)
    b_top, b_pct = get_top_agree(chart_b_items)
    c_min, c_max = get_median_range(chart_c_items)

    content = f"""# Fragmenty do prezentacji

---

## Wykres A: Mandat dla obronności vs finansowanie

**Tytuł**: Postawy wobec wydatków na obronność

**Kluczowe wnioski**:
1. Najwyższe poparcie: "{a_top}" ({a_pct:.0f}% zgadza się)
2. Widoczne zróżnicowanie postaw wobec metod finansowania

**Ograniczenie**: Dane pochodzą z jednorazowego badania;
mogą nie odzwierciedlać stabilnych preferencji.

---

## Wykres B: Akceptowalne cięcia wydatków

**Tytuł**: Akceptowalność ograniczenia wydatków w różnych obszarach

**Kluczowe wnioski**:
1. Najwyższa akceptowalność cięć: "{b_top}" ({b_pct:.0f}%)
2. Respondenci różnicują akceptowalność w zależności od obszaru

**Ograniczenie**: Pytania hipotetyczne; rzeczywiste reakcje mogą się różnić.

---

## Wykres C: Przyczyny inflacji

**Tytuł**: Postrzegane przyczyny wzrostu cen

**Kluczowe wnioski**:
1. Mediany odpowiedzi wahają się od {c_min:.1f} do {c_max:.1f}
2. Respondenci przypisują wzrost cen różnym czynnikom

**Ograniczenie**: Subiektywne postrzeganie, nie obiektywna analiza przyczyn.

---

## Rekomendacja

{persona_text.slide_cta}
"""
    (output_dir / "slide_snippets.md").write_text(content, encoding="utf-8")


def generate_chart_a(
    df: pd.DataFrame,
    config: AnalysisPlan,
    descriptives: list[DescriptiveRow],
    output_dir: Path,
) -> None:
    """Generate Chart A: Diverging bar chart for mandate vs financing."""
    chart = next(c for c in config.charts if c.id.startswith("A_"))
    desc_map = {d.item_id: d for d in descriptives}

    items = chart.items
    labels = [get_item_label(item, config) for item in items]

    # Calculate diverging percentages (negative for disagree, positive for agree)
    disagree = []
    neutral = []
    agree = []

    for item in items:
        if item in desc_map:
            d = desc_map[item]
            disagree.append(-(d.pct_1 + d.pct_2) * 100)
            neutral.append(d.pct_3 * 100)
            agree.append((d.pct_4 + d.pct_5) * 100)
        else:
            disagree.append(0)
            neutral.append(0)
            agree.append(0)

    fig, ax = plt.subplots(figsize=(11, 6))

    y = np.arange(len(labels))
    height = 0.6

    # Plot disagree (negative side)
    ax.barh(y, disagree, height, label="Nie zgadzam się", color="#d73027")
    # Plot neutral (centered around 0)
    ax.barh(y, neutral, height, left=[d for d in disagree], label="Neutralnie", color="#fee08b")
    # Plot agree (positive side)
    ax.barh(y, agree, height, label="Zgadzam się", color="#1a9850")

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=10)
    ax.set_xlabel("% respondentów")
    ax.set_title("Postawy wobec wydatków na obronność i ich finansowania", fontsize=12)
    ax.legend(loc="lower right")
    ax.axvline(0, color="black", linewidth=0.5)
    ax.set_xlim(-100, 100)

    plt.tight_layout()
    plt.savefig(output_dir / "figures" / "A_mandate_vs_financing.png", dpi=150, bbox_inches="tight")
    plt.close()


def generate_chart_b(
    df: pd.DataFrame,
    config: AnalysisPlan,
    descriptives: list[DescriptiveRow],
    output_dir: Path,
) -> None:
    """Generate Chart B: Stacked bar chart for acceptable cuts."""
    chart = next(c for c in config.charts if c.id.startswith("B_"))
    desc_map = {d.item_id: d for d in descriptives}

    items = chart.items
    labels = [get_item_label(item, config) for item in items]

    fig, ax = plt.subplots(figsize=(11, 5))

    y = np.arange(len(labels))
    height = 0.6

    # Stack percentages for each response level
    colors = ["#d73027", "#fc8d59", "#fee08b", "#91cf60", "#1a9850"]
    level_labels = ["1 (nieakc.)", "2", "3", "4", "5 (akc.)"]

    left = np.zeros(len(items))
    for level, (color, level_label) in enumerate(zip(colors, level_labels), 1):
        pcts = []
        for item in items:
            if item in desc_map:
                d = desc_map[item]
                pct = getattr(d, f"pct_{level}") * 100
                pcts.append(pct)
            else:
                pcts.append(0)
        ax.barh(y, pcts, height, left=left, label=level_label, color=color)
        left += pcts

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=10)
    ax.set_xlabel("% respondentów")
    ax.set_title("Akceptowalność ograniczenia wydatków w różnych obszarach", fontsize=12)
    ax.legend(title="Poziom", loc="lower right", ncol=5)
    ax.set_xlim(0, 100)

    plt.tight_layout()
    plt.savefig(output_dir / "figures" / "B_acceptable_cuts.png", dpi=150, bbox_inches="tight")
    plt.close()


def generate_chart_c(
    df: pd.DataFrame,
    config: AnalysisPlan,
    descriptives: list[DescriptiveRow],
    output_dir: Path,
) -> None:
    """Generate Chart C: Grouped bar chart for inflation drivers."""
    chart = next(c for c in config.charts if c.id.startswith("C_"))
    desc_map = {d.item_id: d for d in descriptives}

    items = chart.items
    labels = [get_item_label(item, config) for item in items]

    fig, ax = plt.subplots(figsize=(11, 5))

    x = np.arange(len(labels))
    width = 0.15

    # Plot percentage bars for each response level
    colors = ["#d73027", "#fc8d59", "#fee08b", "#91cf60", "#1a9850"]
    level_labels = ["Wcale", "Mały", "Umiark.", "Duży", "B. duży"]

    for level, (color, level_label) in enumerate(zip(colors, level_labels), 1):
        pcts = []
        for item in items:
            if item in desc_map:
                d = desc_map[item]
                pct = getattr(d, f"pct_{level}") * 100
                pcts.append(pct)
            else:
                pcts.append(0)
        offset = width * (level - 3)
        ax.bar(x + offset, pcts, width, label=level_label, color=color)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=10)
    ax.set_ylabel("% respondentów")
    ax.set_title("Postrzegane przyczyny wzrostu cen", fontsize=12)
    ax.legend(title="Stopień", loc="upper right")

    plt.tight_layout()
    plt.savefig(output_dir / "figures" / "C_inflation_drivers.png", dpi=150, bbox_inches="tight")
    plt.close()


def generate_correlation_heatmap(
    corr_matrix: pd.DataFrame,
    config: AnalysisPlan,
    output_dir: Path,
) -> None:
    """Generate correlation heatmap with readable labels."""
    if corr_matrix.empty:
        # Create placeholder
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.text(0.5, 0.5, "Brak danych do korelacji", ha="center", va="center")
        ax.set_title("Macierz korelacji Spearmana")
        plt.savefig(output_dir / "figures" / "corr_heatmap.png", dpi=150)
        plt.close()
        return

    # Use short labels from label map
    short_labels = [get_item_label(col, config) for col in corr_matrix.columns]

    # Scale figure size based on number of items
    n_items = len(short_labels)
    fig_size = max(12, n_items * 0.5)
    fig, ax = plt.subplots(figsize=(fig_size, fig_size * 0.9))

    sns.heatmap(
        corr_matrix,
        annot=False,
        cmap="RdBu_r",
        center=0,
        vmin=-1,
        vmax=1,
        xticklabels=short_labels,
        yticklabels=short_labels,
        ax=ax,
        square=True,
    )
    ax.set_title("Macierz korelacji Spearmana", fontsize=14, pad=20)

    # Rotate x labels for readability
    plt.xticks(rotation=45, ha="right", fontsize=9)
    plt.yticks(rotation=0, fontsize=9)

    plt.tight_layout()
    plt.savefig(output_dir / "figures" / "corr_heatmap.png", dpi=150, bbox_inches="tight")
    plt.close()


def compute_file_hash(path: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def write_manifest(
    config_path: Path,
    csv_path: Path,
    persona: Literal["campaign", "minfin"],
    output_dir: Path,
) -> None:
    """Write manifest.json with reproducibility metadata."""
    import matplotlib
    import numpy
    import pandas
    import scipy

    manifest = {
        "input_hash": compute_file_hash(csv_path),
        "analysis_plan_hash": compute_file_hash(config_path),
        "python_version": sys.version,
        "library_versions": {
            "pandas": pandas.__version__,
            "scipy": scipy.__version__,
            "matplotlib": matplotlib.__version__,
            "numpy": numpy.__version__,
        },
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "persona": persona,
        "label_map": "label_map.csv",
    }

    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def write_aggregates(aggregates: dict, output_dir: Path) -> None:
    """Write aggregates.json."""
    (output_dir / "aggregates.json").write_text(
        json.dumps(aggregates, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
