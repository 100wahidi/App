"""Service de reporting data quality basé uniquement sur scripts.py."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import pandas as pd

from ..models.api_models import KpiResult, ReportingResponse
from ..core.quality_checks import (
    accuracy_check_kpi,
    consistency_check,
    dead_kri_alert,
    kpis_calculation,
    kri_distribution_evolution,
    load_data,
    patterns,
)


class ReportingService:
    """Service principal de génération de reporting qualité (scripts.py)."""

    def __init__(self) -> None:
        self.patterns = patterns

    def load_data(self, file_path: str) -> pd.DataFrame:
        """Charge les données via scripts.py."""
        return load_data(file_path)

    def kpis_calculation(self, df: pd.DataFrame) -> KpiResult:
        """Calcule les KPIs via scripts.py."""
        (
            global_quality_completeness,
            specific_col_quality_completeness,
            global_quality_validity,
            specific_col_quality_validity,
        ) = kpis_calculation(df)

        return KpiResult(
            global_quality_completeness=round(global_quality_completeness, 2),
            global_quality_validity=round(global_quality_validity, 2),
            specific_col_quality_completeness={k: round(v, 2) for k, v in specific_col_quality_completeness.items()},
            specific_col_quality_validity={k: round(v, 2) for k, v in specific_col_quality_validity.items()},
        )

    def consistency_check(self, df: pd.DataFrame, patterns: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """Détecte les écarts via scripts.py."""
        consistency_issues = consistency_check(df, patterns or self.patterns)
        normalized: List[Dict[str, Any]] = []
        for issue in consistency_issues:
            normalized.append(
                {
                    "column": issue.get("column"),
                    "index": int(issue.get("index", -1)),
                    "value": None if pd.isna(issue.get("value")) else str(issue.get("value")),
                    "consistency_pct": round(float(issue.get("consistency_pct", 0.0)), 2),
                }
            )
        return normalized

    def accuracy_check_kpi(
        self,
        df: pd.DataFrame,
        reference_df: Optional[pd.DataFrame],
        key_columns: List[str],
    ) -> Dict[str, Any]:
        """Compare certaines colonnes via scripts.py."""
        if reference_df is None or not key_columns:
            return {}
        result = accuracy_check_kpi(df, reference_df, key_columns)
        normalized: Dict[str, Any] = {}
        for key, value in result.items():
            normalized[key] = {
                "missing_in_reference": [str(v) for v in value.get("missing_in_reference", [])],
                "accuracy_pct": round(float(value.get("accuracy_pct", 0.0)), 2),
            }
        return normalized

    def dead_kri_alert(self, df: pd.DataFrame, kri_column: str, date_column: str) -> List[Dict[str, Any]]:
        """Détecte les KRI inactifs via scripts.py."""
        alerts = dead_kri_alert(df.copy(), kri_column, date_column)
        normalized: List[Dict[str, Any]] = []
        for alert in alerts:
            date_value = alert.get("last_calculated_date")
            normalized.append(
                {
                    "kri_value": None if pd.isna(alert.get("kri_value")) else str(alert.get("kri_value")),
                    "last_calculated_date": None
                    if pd.isna(date_value)
                    else pd.to_datetime(date_value, errors="coerce").isoformat(),
                    "alert_type": str(alert.get("alert_type", "dead_kri_alert")),
                }
            )
        return normalized

    def kri_distribution_evolution(self, df: pd.DataFrame, kri_column: str, date_column: str) -> List[Dict[str, Any]]:
        """Retourne la distribution des KRI via scripts.py au format JSON."""
        distribution = kri_distribution_evolution(df.copy(), kri_column, date_column)
        if distribution is None:
            return []
        out_df = distribution.reset_index()
        first_col = out_df.columns[0]
        out_df[first_col] = out_df[first_col].astype(str)
        return out_df.to_dict(orient="records")

    def _build_column_analysis(
        self,
        consistency_issues: List[Dict[str, Any]],
        total_rows: int,
    ) -> List[Dict[str, Any]]:
        by_column: Dict[str, int] = {}
        for issue in consistency_issues:
            column = str(issue.get("column", "unknown"))
            by_column[column] = by_column.get(column, 0) + 1

        rows: List[Dict[str, Any]] = []
        for column, error_count in by_column.items():
            ratio = (error_count / total_rows) * 100 if total_rows > 0 else 0.0
            if ratio <= 1:
                status = "OK"
            elif ratio <= 5:
                status = "Warning"
            else:
                status = "Critical"
            rows.append({"column": column, "error_count": error_count, "status": status})

        rows.sort(key=lambda x: x["error_count"], reverse=True)
        return rows

    def generate_report(
        self,
        file_path: str,
        reference_file_path: Optional[str] = None,
        key_columns: Optional[List[str]] = None,
    ) -> ReportingResponse:
        """Génère un rapport complet de data quality à partir de chemins de fichiers."""
        df = self.load_data(file_path)
        reference_df = self.load_data(reference_file_path) if reference_file_path else None
        return self.generate_report_from_df(
            df=df,
            file_name=os.path.basename(file_path),
            reference_df=reference_df,
            key_columns=key_columns,
        )

    def generate_report_from_df(
        self,
        df: pd.DataFrame,
        file_name: str,
        reference_df: Optional[pd.DataFrame] = None,
        key_columns: Optional[List[str]] = None,
    ) -> ReportingResponse:
        """Génère un rapport complet de data quality directement depuis des DataFrames."""

        kpis = self.kpis_calculation(df)
        consistency_issues = self.consistency_check(df)
        accuracy_issues = self.accuracy_check_kpi(df, reference_df, key_columns or [])
        dead_kri_alerts = self.dead_kri_alert(df, "kri", "snapshot_date")
        evolution = self.kri_distribution_evolution(df, "kri", "snapshot_date")
        column_analysis = self._build_column_analysis(consistency_issues, len(df))
        global_score = round(
            (kpis.global_quality_completeness + kpis.global_quality_validity) / 2,
            2,
        )

        return ReportingResponse(
            file_name=file_name,
            total_rows=len(df),
            total_columns=len(df.columns),
            global_score=global_score,
            kpis=kpis,
            consistency_issues=consistency_issues,
            column_analysis=column_analysis,
            failure_cases=consistency_issues,
            accuracy_issues=accuracy_issues,
            dead_kri_alerts=dead_kri_alerts,
            kri_distribution_evolution=evolution,
        )