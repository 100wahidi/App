import threading
from time import time
import webbrowser
from fastapi import FastAPI, HTTPException
import pandas as pd
import pandera.pandas as pa
import numpy as np
import uvicorn
from fastapi.middleware.cors import CORSMiddleware


# API configuration: CORS

app = FastAPI(title="Data Quality API - SG ATS")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)





def sanitize_records(df: pd.DataFrame) -> list[dict]:
    return df.replace([np.inf, -np.inf], np.nan).where(pd.notnull(df), None).to_dict(orient="records")


# Data Ingestion
DATA = pd.read_csv("./reference.csv")
STAFF = pd.read_csv("./staff.csv")
KRI_DICTIONARY = pd.read_csv("./kri_dictionary.csv")
KRI_RESULT = pd.read_csv("./kri_result.csv") 
if "kri_id" in KRI_DICTIONARY.columns:
    KRI_DICTIONARY["kri_id"] = KRI_DICTIONARY["kri_id"].astype(str).str.replace("KRI", "", regex=False)

STAFF = STAFF.rename(columns={
    "employee_region": "employee_region",
    "trading_or_sales_desk": "trading_or_sales_desk",
}).copy()





# -------------------------------⚜️⚜️🐦‍🔥🐦‍🔥🌼🌼--------------------------------
# --- 🐥🐥🐥 Schema Validation: type,Patterns,Specific field roles 🐥🐥🐥 ---
# ✍️ columns types, patterns, specific field roles 


SCHEMA_REFERENCE = pa.DataFrameSchema({

    "kri": pa.Column(pa.String, pa.Check.str_matches(r"^[\w\sÀ-ÿ#'-]+$"), name="consistency"),
    "ggi": pa.Column(pa.Int, pa.Check.ge(0), coerce=True, name="valid_id"),
    "common_name": pa.Column(pa.String, nullable=True),
    "bl": pa.Column(pa.String, nullable=True),
    "subbl": pa.Column(pa.String, nullable=True),
    "pending_date": pa.Column(pa.String, pa.Check.str_matches(r"^\d{4}-\d{2}-\d{2}$"), name="format_date"),
    "snapshot_date": pa.Column(pa.String, pa.Check.str_matches(r"^\d{4}-\d{2}-\d{2}$"), name="format_date"),
    "traitement": pa.Column(pa.String, pa.Check.isin(["yes", "no"]), name="valid_status"),
    "exposure_days": pa.Column(pa.Float, pa.Check.ge(0), coerce=True, name="non_negative"),

}, strict=False)


# --- 🐥🐥🐥 Global Data Quality Features: Completness, uniqueness, Accuracy,Timeliness ---

def Global_data_dimensions(df):
    # 1. Calcul des métriques de base
    total_rows = len(df)
    total_columns = len(df.columns)

    # Doublons
    duplicate_mask = df.duplicated()
    duplicate_count = int(duplicate_mask.sum())
    unique_rows = total_rows - duplicate_count
    uniqueness_percent = round((unique_rows / total_rows * 100), 2) if total_rows > 0 else 0

    # Complétude (Valeurs non-nulles)
    total_cells = df.size
    null_count = df.isnull().sum().sum()
    completeness_percent = round(((total_cells - null_count) / total_cells * 100), 2) if total_cells > 0 else 0
    
    # Valeurs manquantes par colonne
    missing_values_map = df.isnull().sum().fillna("null value").to_dict()

    # 2. Préparation des échantillons (Samples)
    # On remplace les NaN/Inf par None pour la compatibilité JSON


    # Sample de doublons (les 5 premiers)
    duplicate_sample = df[duplicate_mask]
    
    # Sample de lignes avec au moins une valeur nulle (les 5 premières)
    null_sample = df[df.isnull().any(axis=1)].head(5)
    return total_rows, total_columns, duplicate_count, unique_rows, completeness_percent, uniqueness_percent, missing_values_map, duplicate_sample, null_sample


# anomaly detection models machine learning:
# --- 🐥🐥🐥 data quality KPIS storage ---
def data_quality_kpis(response: dict):
    global KRI_DICTIONARY, KRI_RESULT

    ggi = response["ggi"]
    kri_name = response["kri_name"]
    snapshot_date = response["snapshot_date"]
    kri_group_hint = response.get("kri_group") or response.get("kri_type") or response.get("rule")

    existing = KRI_DICTIONARY[KRI_DICTIONARY["kri_label"] == kri_name]

    if not existing.empty:
        kri_id = int(existing.iloc[0]["kri_id"])
        kri_group = str(existing.iloc[0]["kri_group"])
    else:
        numeric_ids = pd.to_numeric(KRI_DICTIONARY["kri_id"], errors="coerce")
        kri_id = int(numeric_ids.max() + 1) if numeric_ids.notna().any() else 1
        kri_group = str(kri_group_hint or kri_name)
        new_row = pd.DataFrame([
            {
                "kri_id": kri_id,
                "kri_group": kri_group,
                "kri_label": kri_name,
            }
        ])
        KRI_DICTIONARY = pd.concat([KRI_DICTIONARY, new_row], ignore_index=True)

    staff_match = STAFF[STAFF["ggi"] == ggi].head(1)
    staff_row = staff_match.iloc[0].to_dict() if not staff_match.empty else {}

    row = {
        "kri": kri_name,
        "ggi": ggi,
        "common_name": staff_row.get("common_name"),
        "employee_region": staff_row.get("employee_region"),
        "trading_or_sales_desk": staff_row.get("trading_or_sales_desk"),
        "snapshot_date": snapshot_date,
        "kri_id": kri_id,
        "kri_group": kri_group,
    }

    df = pd.DataFrame([row])
    KRI_RESULT = pd.concat([KRI_RESULT, df], ignore_index=True)

    return {
        "status": "success",
        "inserted_rows": len(df),
        "kri_id": kri_id,
        "kri_group": kri_group,
        "data": sanitize_records(df),
    }



@app.get("/bl")
def get_bl_list():
    bl_list = DATA[["kri","bl"]]
    return bl_list.to_dict(orient="records")

@app.get("/loading")
def loading_data():
    """Charge et retourne les données brutes du CSV."""
    try:
       
        # On remplace les NaN par None pour le JSON
        # the nan values kpis are already calculated
        return DATA.where(pd.notnull(DATA), "error").to_dict(orient="records")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Le fichier reference.csv est introuvable.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/overview")
# donner moi un code compatible ou overvie front :
def get_overview():
    total_rows, total_columns, duplicate_count, unique_rows, completeness_percent, uniqueness_percent, missing_values_map, duplicate_sample, null_sample = Global_data_dimensions(DATA)
    # 3. Construction de la réponse finale
    return {
        "overview": {
            "total_rows": total_rows,
            "total_columns": total_columns,
            "duplicate_rows": duplicate_count,
            "unique_rows": unique_rows,
            "completeness_percent": completeness_percent,
            "uniqueness_percent": uniqueness_percent,
            "missing_values": missing_values_map,
        },
        "details": {
            "duplicate_rows_sample": duplicate_sample,
            "null_rows_sample": null_sample,
            "columns": DATA.columns.tolist()
        }
    }



@app.get("/validation")
def validate():
    """
    Exécute la validation Pandera et retourne un rapport enrichi :
    - Les erreurs détaillées (column, check, failure_case, index)
    - Le nombre total de lignes (pour le calcul du % en React)
    """
    try:
        total_rows = len(DATA)
        
        try:
            SCHEMA_REFERENCE.validate(DATA, lazy=True)
            return {
                "status": "success", 
                "total_rows": total_rows,
                "report": []
            }
            
        except pa.errors.SchemaErrors as e:
            # Extraction du rapport d'erreurs
            report = e.failure_cases
            
            # Sélection et renommage pour correspondre à ton besoin React
            # Note: Pandera nomme la valeur erronée 'failure_case'
            output_columns = ["column", "check", "failure_case", "index"]
            filtered_report = report[output_columns].copy()
            
            # On convertit tout en string/standard pour éviter les erreurs JSON avec les types numpy
            result_list = filtered_report.fillna("null value").to_dict(orient="records")
            
            return {
                "status": "failed",
                "total_rows": total_rows,
                "report": result_list
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur interne lors de la validation : {str(e)}")



@app.get('/KriAnalytics')
def kri_analysis():
    # pivot table pour le ploting des kris en fonctions de snapshot dates 
    # avec un filtre sur les kris:
    pivoted=pd.pivot_table(DATA,index='snapshot_date',columns='kri',values='ggi',aggfunc=len,fill_value=0)
    time=pivoted.index.tolist()
    kris=pivoted.columns.tolist()
    
    return {"table":pivoted.reset_index().to_dict(orient="records"),"time":time,"kris":kris}
  


@app.get('/KriInsights')
def kri_insights():

    return {"total": len(DATA),
        "number_business": DATA[DATA['ggi']!=0].shape[0]
            ,"number_individual": DATA[DATA['ggi']==0].shape[0]}



@app.get("/kri/top-offenders")
def get_top_kris():
    top_5 = DATA['kri'].value_counts().head(5).reset_index()
    top_5.columns = ['kri', 'count']
    return top_5.to_dict(orient="records")


@app.get("/kri/dictionary")
def get_kri_dictionary():
    return sanitize_records(KRI_DICTIONARY)


@app.post("/kri/calculate")
def calculate_kri(payload: dict):
    try:
        return data_quality_kpis(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


import time
import webbrowser
import requests
URL = "https://100wahidi.github.io/kri-calculation"
def open_browser_when_ready():
    while True:
        try:
            requests.get("http://127.0.0.1:8000/validation", timeout=1)
            break
        except:
            time.sleep(0.5)

    webbrowser.open(URL)


if __name__ == "__main__":
    threading.Thread(target=open_browser_when_ready).start()

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )

