"""Pydantic schema validation for analysis_plan.yml."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator


class QAFilters(BaseModel):
    """QA filter configuration."""

    age_column: str
    age_keep_value: str
    attention_check_column: str
    attention_check_expected: str


class IndexConfig(BaseModel):
    """Index configuration."""

    id: str
    label_pl: str
    direction_label_pl: str
    items: list[str]
    reverse_items: list[str] = Field(default_factory=list)
    score_method: Literal["mean", "median"] = "mean"
    min_valid_items: int = 1


class CorrelationsConfig(BaseModel):
    """Correlations configuration."""

    scope: Literal["all_items", "indices_only", "indices_and_items"]
    items_explicit: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_items_explicit(self) -> "CorrelationsConfig":
        if self.scope == "indices_and_items" and not self.items_explicit:
            raise ValueError("items_explicit required when scope='indices_and_items'")
        return self


class ConfirmatoryTest(BaseModel):
    """Confirmatory test configuration."""

    id: str
    dv: str
    iv_grouping: str | None = None
    test_type: Literal["descriptive", "mann_whitney", "kruskal_wallis"] = "descriptive"
    family: str = "confirmatory"


class GatingThresholds(BaseModel):
    """Gating thresholds configuration."""

    min_group_n: int = Field(gt=0)


class MissingnessRules(BaseModel):
    """Missingness rules configuration."""

    flag_threshold: float = Field(ge=0, le=1)
    index_na_rule: Literal["min_valid_items"] = "min_valid_items"


class FDRSettings(BaseModel):
    """FDR settings configuration."""

    q: float = Field(gt=0, le=1)
    method: Literal["bh", "bonferroni", "holm"]


class ChartConfig(BaseModel):
    """Chart configuration."""

    id: str
    type: Literal["diverging_bar", "stacked_bar", "grouped_bar"]
    items: list[str]

    @model_validator(mode="after")
    def validate_chart_id(self) -> "ChartConfig":
        valid_prefixes = ("A_", "B_", "C_")
        if not self.id.startswith(valid_prefixes):
            raise ValueError(f"Chart id must start with A_, B_, or C_: {self.id}")
        return self


class PersonaText(BaseModel):
    """Persona text configuration."""

    report_intro: str
    slide_cta: str


class AnalysisPlan(BaseModel):
    """Full analysis plan schema."""

    version: str
    items_universe: list[str] = Field(min_length=1)
    item_labels: dict[str, str] = Field(default_factory=dict)
    qa_filters: QAFilters
    indices: list[IndexConfig] = Field(default_factory=list)
    correlations: CorrelationsConfig
    confirmatory_tests: list[ConfirmatoryTest] = Field(default_factory=list)
    gating_thresholds: GatingThresholds
    missingness_rules: MissingnessRules
    fdr_settings: FDRSettings
    charts: list[ChartConfig] = Field(min_length=1)
    persona_texts: dict[Literal["campaign", "minfin"], PersonaText]

    @model_validator(mode="after")
    def validate_item_labels_subset(self) -> "AnalysisPlan":
        universe_set = set(self.items_universe)
        for key in self.item_labels:
            if key not in universe_set:
                raise ValueError(f"item_labels key not in items_universe: {key}")
        return self

    @model_validator(mode="after")
    def validate_chart_items(self) -> "AnalysisPlan":
        universe_set = set(self.items_universe)
        for chart in self.charts:
            for item in chart.items:
                if item not in universe_set:
                    raise ValueError(f"Chart {chart.id} item not in items_universe: {item}")
        return self

    @model_validator(mode="after")
    def validate_index_items(self) -> "AnalysisPlan":
        universe_set = set(self.items_universe)
        for index in self.indices:
            if not index.items:
                raise ValueError(f"Index {index.id} must have at least one item")
            for item in index.items:
                if item not in universe_set:
                    raise ValueError(f"Index {index.id} item not in items_universe: {item}")
            for item in index.reverse_items:
                if item not in universe_set:
                    raise ValueError(
                        f"Index {index.id} reverse_item not in items_universe: {item}"
                    )
        return self


def load_config(config_path: Path | None = None) -> AnalysisPlan:
    """Load and validate the analysis plan configuration.

    Args:
        config_path: Path to config file. Defaults to config/analysis_plan.yml

    Returns:
        Validated AnalysisPlan model

    Raises:
        FileNotFoundError: If config file doesn't exist
        pydantic.ValidationError: If config fails validation
    """
    if config_path is None:
        config_path = Path("config/analysis_plan.yml")

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path) as f:
        raw = yaml.safe_load(f)

    return AnalysisPlan.model_validate(raw)


def validate() -> None:
    """Validate the default config file. For CLI usage."""
    config = load_config()
    print(f"✓ Config valid: {len(config.items_universe)} items in universe")


if __name__ == "__main__":
    validate()
