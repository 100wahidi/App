"""Routes FastAPI pour le reporting data quality."""

import os
import tempfile
import uuid
from pathlib import Path

import aiofiles
import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile

from ..models.api_models import ReportingRequest, ReportingResponse
from ..services.reporting_service import ReportingService

# Absolute paths to the local data files (project_root/data/)
_DATA_DIR = Path(__file__).resolve().parents[3] / "data"
_LOCAL_CSV = _DATA_DIR / "kri_quality_report.csv"
_REFERENCE_CSV = _DATA_DIR / "reference.csv"

router = APIRouter(prefix="/api/reporting", tags=["Reporting"])
reporting_service = ReportingService()


@router.get("/info")
async def reporting_info():
    """Expose les capacités du module de reporting."""
    return {
        "name": "Reporting Data Quality API",
        "description": "Reporting qualité sur fichiers CSV/Excel basé sur scripts.py (KPIs, consistency, accuracy, alertes KRI).",
        "engine": "scripts.py",
        "available_outputs": [
            "global_score",
            "kpis",
            "column_analysis",
            "failure_cases",
            "consistency_issues",
            "accuracy_issues",
            "dead_kri_alerts",
            "kri_distribution_evolution",
        ],
    }


@router.get("/local", response_model=ReportingResponse)
async def analyze_local_dataset():
    """Lit data/kri_quality_report.csv et data/reference.csv via pd.read_csv et retourne le rapport."""
    if not _LOCAL_CSV.exists():
        raise HTTPException(status_code=404, detail=f"Dataset not found: {_LOCAL_CSV}")
    try:
        # Read both CSVs directly with pandas — no upload, no temp files
        df = pd.read_csv(_LOCAL_CSV)
        ref_df = pd.read_csv(_REFERENCE_CSV) if _REFERENCE_CSV.exists() else None
        return reporting_service.generate_report_from_df(
            df=df,
            file_name=_LOCAL_CSV.name,
            reference_df=ref_df,
            key_columns=["ggi_indicator", "kri"],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur analyse locale: {exc}") from exc


@router.post("/analyze", response_model=ReportingResponse)
async def analyze_report(request: ReportingRequest):
    """Analyse un fichier existant sur disque et retourne un reporting complet."""
    if not os.path.exists(request.file_path):
        raise HTTPException(status_code=404, detail="Le fichier d'analyse est introuvable")

    if request.reference_file_path and not os.path.exists(request.reference_file_path):
        raise HTTPException(status_code=404, detail="Le fichier de référence est introuvable")

    try:
        return reporting_service.generate_report(
            file_path=request.file_path,
            reference_file_path=request.reference_file_path,
            key_columns=request.key_columns,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur de génération du reporting: {exc}") from exc


@router.post("/upload-analyze", response_model=ReportingResponse)
async def upload_and_analyze_report(
    file: UploadFile = File(...),
    reference_file: UploadFile | None = File(None),
):
    """Upload un fichier puis retourne immédiatement le reporting complet."""
    allowed_extensions = {".csv", ".xlsx", ".xls"}
    file_extension = os.path.splitext(file.filename or "")[1].lower()
    if file_extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Type de fichier non supporté")

    temp_dir = tempfile.gettempdir()
    file_id = str(uuid.uuid4())
    temp_path = os.path.join(temp_dir, f"{file_id}_{file.filename}")
    reference_temp_path = None

    try:
        async with aiofiles.open(temp_path, "wb") as temp_file:
            await temp_file.write(await file.read())

        if reference_file is not None:
            ref_ext = os.path.splitext(reference_file.filename or "")[1].lower()
            if ref_ext not in allowed_extensions:
                raise HTTPException(status_code=400, detail="Type de fichier de référence non supporté")

            reference_temp_path = os.path.join(temp_dir, f"ref_{file_id}_{reference_file.filename}")
            async with aiofiles.open(reference_temp_path, "wb") as temp_ref_file:
                await temp_ref_file.write(await reference_file.read())

        return reporting_service.generate_report(
            file_path=temp_path,
            reference_file_path=reference_temp_path,
            key_columns=["ggi_indicator", "kri"],
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur d'upload/analyse: {exc}") from exc
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if reference_temp_path and os.path.exists(reference_temp_path):
            os.remove(reference_temp_path)