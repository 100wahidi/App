import pandas as pd


def load_data(file_path: str):
    file_path_str = str(file_path).lower()
    if file_path_str.endswith('.csv'):
        return pd.read_csv(file_path)
    if file_path_str.endswith('.xlsx') or file_path_str.endswith('.xls'):
        return pd.read_excel(file_path)
    raise ValueError("Unsupported file format. Use CSV or Excel.")


def kpis_calculation(df: pd.DataFrame):
    total_rows = len(df)
    valid_rows = len(df.dropna())

    global_quality_completness = (valid_rows / total_rows) * 100 if total_rows > 0 else 0
    specific_col_quality_completness = {}
    for col in df.columns:
        valid_col_rows = len(df[col].dropna())
        specific_col_quality_completness[col] = (valid_col_rows / total_rows) * 100 if total_rows > 0 else 0

    global_quality_validity = (valid_rows / total_rows) * 100 if total_rows > 0 else 0
    specific_col_quality_validity = {}
    for col in df.columns:
        valid_col_rows = len(df[col].dropna())
        specific_col_quality_validity[col] = (valid_col_rows / total_rows) * 100 if total_rows > 0 else 0

    return global_quality_completness, specific_col_quality_completness, global_quality_validity, specific_col_quality_validity


patterns = {
    "ggi_indicator": r"^\d+$",
    "snapshot_date": r"^\d{4}-\d{2}-\d{2}$",
    "exposure_days": r"^\d+(\.\d+)?$",
}


def consistency_check(df: pd.DataFrame, patterns: dict):
    consistency_issues = []

    for col, pattern in patterns.items():
        if col in df.columns:
            invalid_rows = df[~df[col].astype(str).str.match(pattern)]
            for index, row in invalid_rows.iterrows():
                consistency_issues.append({
                    "column": col,
                    "index": index,
                    "value": row[col],
                    "consistency_pct": (len(invalid_rows) / len(df)) * 100 if len(df) > 0 else 0,
                })
    return consistency_issues


def accuracy_check_kpi(df: pd.DataFrame, reference_df: pd.DataFrame, key_columns: list):
    accuracy_issues = {}
    for key in key_columns:
        if key in df.columns and key in reference_df.columns:
            missing_in_df = df[~df[key].isin(reference_df[key])]
            accuracy_issues[key] = {
                "missing_in_reference": missing_in_df[key].tolist(),
                "accuracy_pct": (len(missing_in_df) / len(df)) * 100 if len(df) > 0 else 0,
            }
    return accuracy_issues


def dead_kri_alert(df: pd.DataFrame, kri_column: str, date_column: str):
    alert = []
    if kri_column in df.columns and date_column in df.columns:
        df[date_column] = pd.to_datetime(df[date_column], errors='coerce')
        two_years_ago = df[date_column].max() - pd.DateOffset(years=2)
        dead_kri_rows = df[df[date_column] < two_years_ago]
        for _, row in dead_kri_rows.iterrows():
            alert.append({
                "kri_value": row[kri_column],
                "last_calculated_date": row[date_column],
                "alert_type": "dead_kri_alert",
            })
    return alert


def kri_distribution_evolution(df: pd.DataFrame, kri_column: str, date_column: str):
    if kri_column in df.columns and date_column in df.columns:
        df[date_column] = pd.to_datetime(df[date_column], errors='coerce')
        distribution = df.pivot_table(
            index=df[date_column].dt.to_period('M'),
            columns=kri_column,
            aggfunc='size',
            fill_value=0,
        )
        return distribution
    return None
