"""Modèles Pydantic minimaux pour le reporting data quality."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ReportingRequest(BaseModel):
    """Requête de génération de reporting."""

    file_path: str = Field(..., description="Chemin absolu vers le fichier CSV/Excel à analyser")
    reference_file_path: Optional[str] = Field(
        None,
        description="Chemin d'un référentiel pour les contrôles d'accuracy",
    )
    key_columns: List[str] = Field(
        default_factory=list,
        description="Colonnes utilisées pour comparer avec le référentiel",
    )


class KpiResult(BaseModel):
    """Indicateurs qualité agrégés."""

    global_quality_completeness: float
    global_quality_validity: float
    specific_col_quality_completeness: Dict[str, float]
    specific_col_quality_validity: Dict[str, float]


class ReportingResponse(BaseModel):
    """Réponse complète de reporting."""

    file_name: str
    total_rows: int
    total_columns: int
    generated_at: datetime = Field(default_factory=datetime.now)
    global_score: float
    kpis: KpiResult
    consistency_issues: List[Dict[str, Any]]
    column_analysis: List[Dict[str, Any]]
    failure_cases: List[Dict[str, Any]]
    accuracy_issues: Dict[str, Any]
    dead_kri_alerts: List[Dict[str, Any]]
    kri_distribution_evolution: List[Dict[str, Any]]
