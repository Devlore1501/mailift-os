import json
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session as OrmSession

from ..auth import any_user, editor_or_admin
from ..db import get_db
from ..models import Content, Metric, User
from ..schemas import MetricIn, MetricOut
from ..services.activity import log_activity
from ..services.csv_import import METRIC_FIELDS, import_csv
from ..util import naive_utc

router = APIRouter(prefix="/api", tags=["metrics"])


def _metric_out(m: Metric) -> dict:
    data = MetricOut.model_validate(m).model_dump()
    data.update(save_rate=m.save_rate, share_rate=m.share_rate,
                icp_ratio=m.icp_ratio, dm_fhs_rate=m.dm_fhs_rate)
    return data


@router.get("/contents/{content_id}/metrics")
def list_metrics(content_id: int, user: User = Depends(any_user), db: OrmSession = Depends(get_db)):
    if not db.get(Content, content_id):
        raise HTTPException(status_code=404, detail="Contenuto non trovato")
    rows = (db.query(Metric).filter(Metric.content_id == content_id)
            .order_by(Metric.captured_at.asc()).all())
    return [_metric_out(m) for m in rows]


@router.post("/contents/{content_id}/metrics", status_code=201)
def add_metric(content_id: int, body: MetricIn, user: User = Depends(editor_or_admin),
               db: OrmSession = Depends(get_db)):
    """FR-M2-01: inserimento manuale metriche (snapshot)."""
    if not db.get(Content, content_id):
        raise HTTPException(status_code=404, detail="Contenuto non trovato")
    values = body.model_dump(exclude_unset=True)
    if values.get("captured_at"):
        values["captured_at"] = naive_utc(values["captured_at"])
    metric = Metric(content_id=content_id, **values)
    db.add(metric)
    log_activity(db, user, "content", content_id, "aggiunto snapshot metriche")
    db.commit()
    db.refresh(metric)
    return _metric_out(metric)


@router.delete("/metrics/{metric_id}", status_code=204)
def delete_metric(metric_id: int, user: User = Depends(editor_or_admin),
                  db: OrmSession = Depends(get_db)):
    metric = db.get(Metric, metric_id)
    if not metric:
        raise HTTPException(status_code=404, detail="Metrica non trovata")
    db.delete(metric)
    db.commit()


@router.get("/metrics/fields")
def metric_fields(user: User = Depends(any_user)):
    """Campi disponibili per il mapping colonne dell'import CSV."""
    return {"fields": sorted(METRIC_FIELDS), "match_fields": ["external_url", "content_id", "title"]}


@router.post("/metrics/import")
def import_metrics_csv(
    file: UploadFile = File(...),
    mapping: str = Form(...),          # JSON {colonna_csv: campo_metric}
    match_field: str = Form(...),      # external_url | content_id | title
    match_column: str = Form(...),     # nome colonna CSV con la chiave
    captured_at: str | None = Form(default=None),  # ISO opzionale
    user: User = Depends(editor_or_admin),
    db: OrmSession = Depends(get_db),
):
    """FR-M2-02: import CSV con mapping colonne."""
    try:
        mapping_dict = json.loads(mapping)
        assert isinstance(mapping_dict, dict) and mapping_dict
    except (ValueError, AssertionError):
        raise HTTPException(status_code=422, detail="mapping deve essere un JSON object non vuoto")
    captured_dt = None
    if captured_at:
        try:
            captured_dt = naive_utc(datetime.fromisoformat(captured_at))
        except ValueError:
            raise HTTPException(status_code=422, detail="captured_at non è una data ISO valida")
    try:
        result = import_csv(db, file.file.read(), mapping_dict, match_field, match_column, captured_dt)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    log_activity(db, user, "content", None, f"import CSV metriche: {result['imported']} righe")
    db.commit()
    return result
