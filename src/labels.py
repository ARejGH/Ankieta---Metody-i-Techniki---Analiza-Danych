"""Label generation for chart display.

Provides short, readable Polish labels for survey items.
"""

import csv
import json
import re
from datetime import UTC, datetime
from pathlib import Path

from src.schema import AnalysisPlan

# Character limit for short labels (preferred max)
LABEL_MAX_CHARS = 28
LABEL_HARD_MAX = 40


def generate_fallback_label(item: str) -> str:
    """Generate a short label from item text using deterministic rules.

    Strategy:
    1. Extract bracket content for budget tradeoff items [Area]
    2. Remove leading question numbers (e.g., "15.")
    3. Remove parenthetical explanations
    4. Keep key noun phrase (first ~5 words)
    5. Truncate to max length
    """
    # Handle bracket items (budget tradeoff questions)
    if "[" in item and "]" in item:
        start = item.rfind("[")
        end = item.rfind("]")
        bracket_content = item[start + 1 : end].strip()
        return bracket_content[:LABEL_MAX_CHARS]

    # Remove leading question number (e.g., "15. " or "1. ")
    text = re.sub(r"^\d+\.\s*", "", item.strip())

    # Remove content in parentheses
    text = re.sub(r"\s*\([^)]*\)", "", text)

    # Remove trailing whitespace
    text = text.strip()

    # Truncate to reasonable length while keeping word boundaries
    if len(text) <= LABEL_MAX_CHARS:
        return text

    # Find last space before max length
    truncated = text[:LABEL_MAX_CHARS]
    last_space = truncated.rfind(" ")
    if last_space > LABEL_MAX_CHARS // 2:
        return truncated[:last_space].rstrip(".,;:") + "…"
    return truncated.rstrip(".,;:") + "…"


def generate_labels(config: AnalysisPlan) -> dict[str, str]:
    """Generate label mapping for all items in items_universe.

    Priority:
    1. Use config.item_labels if present for an item
    2. Otherwise generate fallback label

    Returns:
        Dict mapping original column name -> short label
    """
    labels: dict[str, str] = {}

    for item in config.items_universe:
        if item in config.item_labels:
            labels[item] = config.item_labels[item]
        else:
            labels[item] = generate_fallback_label(item)

    # Ensure uniqueness by adding suffix if needed
    _ensure_unique_labels(labels)

    return labels


def _ensure_unique_labels(labels: dict[str, str]) -> None:
    """Ensure all short labels are unique by adding disambiguating suffixes."""
    seen: dict[str, list[str]] = {}

    for orig, short in labels.items():
        if short not in seen:
            seen[short] = []
        seen[short].append(orig)

    # Fix duplicates
    for short, originals in seen.items():
        if len(originals) > 1:
            for i, orig in enumerate(originals, 1):
                suffix = f" ({i})"
                new_label = short[:LABEL_MAX_CHARS - len(suffix)] + suffix
                labels[orig] = new_label


def get_label(item: str, label_map: dict[str, str]) -> str:
    """Get display label for an item, with fallback."""
    if item in label_map:
        return label_map[item]
    return generate_fallback_label(item)


def write_label_map_csv(
    labels: dict[str, str],
    output_dir: Path,
    created_by: str = "config_or_fallback",
) -> Path:
    """Write label mapping to CSV file.

    Columns: original_column_name, short_label, created_by, timestamp
    """
    output_path = output_dir / "label_map.csv"
    timestamp = datetime.now(UTC).isoformat()

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["original_column_name", "short_label", "created_by", "timestamp"])
        for orig, short in labels.items():
            writer.writerow([orig, short, created_by, timestamp])

    return output_path


def write_label_map_json(
    labels: dict[str, str],
    output_dir: Path,
) -> Path:
    """Write label mapping to JSON file."""
    output_path = output_dir / "label_map.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(labels, f, ensure_ascii=False, indent=2)

    return output_path


def validate_labels(labels: dict[str, str]) -> list[str]:
    """Validate that all labels meet requirements.

    Returns list of error messages (empty if valid).
    """
    errors: list[str] = []

    # Check uniqueness
    short_labels = list(labels.values())
    if len(short_labels) != len(set(short_labels)):
        duplicates = [lbl for lbl in short_labels if short_labels.count(lbl) > 1]
        errors.append(f"Duplicate labels found: {set(duplicates)}")

    # Check length limits
    for orig, short in labels.items():
        if len(short) > LABEL_HARD_MAX:
            errors.append(f"Label too long ({len(short)} chars): {short}")

    return errors
