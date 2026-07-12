"""Import CSV metriche con mapping colonne (FR-M2-02).

Il client manda il file + un mapping {colonna_csv: campo_metric} + la colonna
usata per agganciare il contenuto (match_field: external_url | content_id | title).
Fino a ~1.000 righe senza timeout (NFR-02): parsing in memoria, un commit unico.
"""
import csv
import io
from datetime import datetime

from sqlalchemy.orm import Session

from ..models import Content, Metric

METRIC_FIELDS = {
    "views", "likes", "avg_retention_pct", "hook_retention_pct", "rewatch_rate",
    "saves", "shares", "comments", "icp_comments", "non_icp_comments",
    "dm_keyword_triggers", "fhs_clicks", "fhs_purchases",
}
INT_FIELDS = {
    "views", "likes", "saves", "shares", "comments", "icp_comments",
    "non_icp_comments", "dm_keyword_triggers", "fhs_clicks", "fhs_purchases",
}
MATCH_FIELDS = ("external_url", "content_id", "title")


def _parse_number(value: str, field: str):
    value = (value or "").strip().replace("%", "")
    if value == "":
        return None
    value = value.replace(",", ".")
    number = float(value)
    return int(round(number)) if field in INT_FIELDS else number


def import_csv(
    db: Session,
    file_bytes: bytes,
    mapping: dict[str, str],
    match_field: str,
    match_column: str,
    captured_at: datetime | None = None,
) -> dict:
    if match_field not in MATCH_FIELDS:
        raise ValueError(f"match_field deve essere uno di {MATCH_FIELDS}")
    bad_fields = set(mapping.values()) - METRIC_FIELDS
    if bad_fields:
        raise ValueError(f"Campi metrica sconosciuti: {sorted(bad_fields)}")

    text = file_bytes.decode("utf-8-sig", errors="replace")
    sample = text[:2048]
    delimiter = ";" if sample.count(";") > sample.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if not reader.fieldnames:
        raise ValueError("CSV vuoto o senza header")
    missing_cols = ({match_column} | set(mapping)) - set(reader.fieldnames)
    if missing_cols:
        raise ValueError(f"Colonne assenti nel CSV: {sorted(missing_cols)}")

    imported, unmatched, errors = 0, [], []
    for i, row in enumerate(reader, start=2):
        raw_key = (row.get(match_column) or "").strip()
        if not raw_key:
            unmatched.append({"row": i, "key": "", "reason": "chiave vuota"})
            continue

        q = db.query(Content)
        if match_field == "content_id":
            try:
                content = q.filter(Content.id == int(raw_key)).first()
            except ValueError:
                content = None
        elif match_field == "external_url":
            content = q.filter(Content.external_url == raw_key).first()
        else:
            content = q.filter(Content.title == raw_key).first()

        if not content:
            unmatched.append({"row": i, "key": raw_key, "reason": "contenuto non trovato"})
            continue

        values = {}
        try:
            for col, field in mapping.items():
                values[field] = _parse_number(row.get(col, ""), field)
        except ValueError as exc:
            errors.append({"row": i, "key": raw_key, "reason": f"valore non numerico: {exc}"})
            continue

        metric = Metric(content_id=content.id, **values)
        if captured_at:
            metric.captured_at = captured_at
        db.add(metric)
        imported += 1

    db.commit()
    return {"imported": imported, "unmatched": unmatched, "errors": errors}
