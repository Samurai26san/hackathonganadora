"""Strict financial contracts; Decimal serializes as a JSON string."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class BudgetFilterParams(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    years: list[int] = Field(min_length=1, max_length=5)
    region_ids: list[int] | None = None
    area_ids: list[int] | None = None
    financier_ids: list[int] | None = None
    rubro_ids: list[int] | None = None
    cuenta_ids: list[int] | None = None
    months: list[int] | None = None
    group_by: (
        Literal["financier", "area", "region", "rubro", "cuenta", "month"] | None
    ) = None
    metric: Literal["executed", "balance", "current_budget", "execution_percentage"] = (
        "executed"
    )
    date_from: date | None = None
    date_to: date | None = None
    search: str = Field(default="", max_length=200)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @field_validator("date_from", "date_to", mode="before")
    @classmethod
    def parse_iso_date(cls, value: Any) -> Any:
        if isinstance(value, str):
            if len(value) != 10 or value[4] != "-" or value[7] != "-":
                raise ValueError("La fecha debe tener formato AAAA-MM-DD")
            return date.fromisoformat(value)
        return value

    @model_validator(mode="after")
    def valid_ranges(self) -> BudgetFilterParams:
        if any(not 1900 <= year <= 2200 for year in self.years):
            raise ValueError("Gestión fuera de rango")
        if self.months is not None and any(
            not 0 <= month <= 12 for month in self.months
        ):
            raise ValueError("Mes fuera de rango; PTTO corresponde a 0")
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("El inicio del período es posterior al final")
        for ids in [
            self.region_ids,
            self.area_ids,
            self.financier_ids,
            self.rubro_ids,
            self.cuenta_ids,
        ]:
            if ids is not None and any(item < 1 for item in ids):
                raise ValueError("Identificadores fuera de rango")
        return self


class KPISummary(BaseModel):
    initial_budget: Decimal
    modifications: Decimal
    current_budget: Decimal
    executed: Decimal
    balance: Decimal
    execution_percentage: Decimal


class DataRow(BaseModel):
    labels: dict[str, str]
    values: dict[str, Decimal]
    dimensions: dict[str, int] = Field(default_factory=dict)
    details: dict[str, Any] = Field(default_factory=dict)


class FinancialReportResult(BaseModel):
    report_type: str
    title: str
    metadata: dict[str, Any]
    summary: KPISummary
    rows: list[DataRow]
    chart_spec: dict[str, Any] | None = None


class ExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    report: str
    format: Literal["excel", "pdf", "csv"]
    filters: BudgetFilterParams
