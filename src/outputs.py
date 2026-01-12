"""Output generation: reports, charts, manifest."""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from src.analysis import ConfirmatoryResult, DescriptiveRow
from src.loader import LoadResult
from src.schema import AnalysisPlan


def get_item_label(item: str, config: AnalysisPlan) -> str:
    """Get display label for an item."""
    if item in config.item_labels:
        return config.item_labels[item]
    # Extract short label from item text
    if item.startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.")):
        # Numbered items - take first part
        parts = item.split(".", 1)
        if len(parts) > 1:
            return parts[1][:40].strip() + "..."
    if "[" in item and "]" in item:
        # Extract bracket content for budget tradeoff items
        start = item.rfind("[")
        end = item.rfind("]")
        return item[start + 1:end]
    return item[:40] + "..."


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
            content += f"| {r.test_id} | {r.dv[:30]} | {stat_str} | {p_str} | {padj_str} | {eff_str} | {r.n} |\n"
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
        content += f"\n*... i {len(descriptives) - 10} pozostałych pozycji (pełne dane w descriptives_table.csv)*\n"

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

**Ograniczenie**: Dane pochodzą z jednorazowego badania; mogą nie odzwierciedlać stabilnych preferencji.

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

    fig, ax = plt.subplots(figsize=(10, 6))

    y = np.arange(len(labels))
    height = 0.6

    # Plot disagree (negative side)
    ax.barh(y, disagree, height, label="Nie zgadzam się", color="#d73027")
    # Plot neutral (centered around 0)
    ax.barh(y, neutral, height, left=[d for d in disagree], label="Neutralnie", color="#fee08b")
    # Plot agree (positive side)
    ax.barh(y, agree, height, label="Zgadzam się", color="#1a9850")

    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel("% respondentów")
    ax.set_title("Postawy wobec wydatków na obronność i ich finansowania")
    ax.legend(loc="lower right")
    ax.axvline(0, color="black", linewidth=0.5)
    ax.set_xlim(-100, 100)

    plt.tight_layout()
    plt.savefig(output_dir / "figures" / "A_mandate_vs_financing.png", dpi=150)
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

    fig, ax = plt.subplots(figsize=(10, 5))

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
    ax.set_yticklabels(labels)
    ax.set_xlabel("% respondentów")
    ax.set_title("Akceptowalność ograniczenia wydatków w różnych obszarach")
    ax.legend(title="Poziom", loc="lower right", ncol=5)
    ax.set_xlim(0, 100)

    plt.tight_layout()
    plt.savefig(output_dir / "figures" / "B_acceptable_cuts.png", dpi=150)
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

    fig, ax = plt.subplots(figsize=(10, 5))

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
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.set_ylabel("% respondentów")
    ax.set_title("Postrzegane przyczyny wzrostu cen")
    ax.legend(title="Stopień", loc="upper right")

    plt.tight_layout()
    plt.savefig(output_dir / "figures" / "C_inflation_drivers.png", dpi=150)
    plt.close()


def generate_correlation_heatmap(
    corr_matrix: pd.DataFrame,
    config: AnalysisPlan,
    output_dir: Path,
) -> None:
    """Generate correlation heatmap."""
    if corr_matrix.empty:
        # Create placeholder
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.text(0.5, 0.5, "Brak danych do korelacji", ha="center", va="center")
        ax.set_title("Macierz korelacji Spearmana")
        plt.savefig(output_dir / "figures" / "corr_heatmap.png", dpi=150)
        plt.close()
        return

    # Shorten labels
    short_labels = [get_item_label(col, config)[:20] for col in corr_matrix.columns]

    fig, ax = plt.subplots(figsize=(14, 12))
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
    )
    ax.set_title("Macierz korelacji Spearmana")
    plt.xticks(rotation=45, ha="right")
    plt.yticks(rotation=0)
    plt.tight_layout()
    plt.savefig(output_dir / "figures" / "corr_heatmap.png", dpi=150)
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
    import pandas
    import scipy
    import matplotlib
    import numpy

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
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "persona": persona,
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
