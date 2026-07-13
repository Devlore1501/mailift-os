"""Mailift Email Planner — piano editoriale email dei clienti retainer.

App interna single-user (come Autofatture): niente auth, gira in locale.
Backend compatto in un file: modelli, schemi e API insieme.

Pipeline campagna: idea → copy → review_cliente → programmata → inviata.
Le metriche post-invio (open rate, CTR, revenue) si inseriscono a mano
dalla card — alimentano il report settimanale Klaviyo.
"""
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker

TMP_DIR = Path(__file__).resolve().parent.parent / ".tmp"
TMP_DIR.mkdir(exist_ok=True)
engine = create_engine(f"sqlite:///{TMP_DIR / 'email_planner.db'}",
                       connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False)
Base = declarative_base()

CAMPAIGN_STATUSES = ["idea", "copy", "review_cliente", "programmata", "inviata"]
STATUS_LABELS = {
    "idea": "Idea", "copy": "Copy", "review_cliente": "Review cliente",
    "programmata": "Programmata", "inviata": "Inviata",
}
CAMPAIGN_TYPES = {"campagna": "Campagna", "flash_sale": "Flash sale", "flow": "Flow"}


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is not None and dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    active = Column(Boolean, nullable=False, default=True)
    program_notes = Column(Text, nullable=True)   # es. "2 email/settimana, sabato 9:30"
    tone_notes = Column(Text, nullable=True)      # es. "1ª persona, confidenziale (Paolo)"
    campaigns = relationship("Campaign", back_populates="client")


class Campaign(Base):
    __tablename__ = "campaigns"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    type = Column(String, nullable=False, default="campagna")  # campagna|flash_sale|flow
    status = Column(String, nullable=False, default="idea", index=True)
    subject = Column(String, nullable=True)
    preview_text = Column(String, nullable=True)
    brief = Column(Text, nullable=True)
    scheduled_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    klaviyo_url = Column(String, nullable=True)
    # metriche post-invio (manuali, per il report settimanale)
    open_rate_pct = Column(Float, nullable=True)
    ctr_pct = Column(Float, nullable=True)
    revenue = Column(Float, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    client = relationship("Client", back_populates="campaigns")


# ---- Schemi ----

class ClientIn(BaseModel):
    name: str
    active: bool = True
    program_notes: Optional[str] = None
    tone_notes: Optional[str] = None


class ClientOut(ClientIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class CampaignIn(BaseModel):
    client_id: Optional[int] = None
    title: Optional[str] = None
    type: Optional[str] = None
    subject: Optional[str] = None
    preview_text: Optional[str] = None
    brief: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    klaviyo_url: Optional[str] = None
    open_rate_pct: Optional[float] = None
    ctr_pct: Optional[float] = None
    revenue: Optional[float] = None


class CampaignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    client_id: int
    title: str
    type: str
    status: str
    subject: Optional[str] = None
    preview_text: Optional[str] = None
    brief: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    klaviyo_url: Optional[str] = None
    open_rate_pct: Optional[float] = None
    ctr_pct: Optional[float] = None
    revenue: Optional[float] = None
    client_name: Optional[str] = None


class StatusIn(BaseModel):
    status: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


SEED_CLIENTS = [
    ("Bergamo Vini", "2 email/settimana, sabato ore 9:30 · flash sale ultimi 3 giorni del mese · 80% contenuto / 20% promo",
     "1ª persona confidenziale, come se scrivesse Paolo (enologo)"),
    ("Le Rive", None, None),
    ("Riccardo Coach", "Coaching (non eCommerce)", None),
]


app = FastAPI(title="Mailift Email Planner API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5175", "http://127.0.0.1:5175"],
                   allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if not db.query(Client).first():
            for name, program, tone in SEED_CLIENTS:
                db.add(Client(name=name, program_notes=program, tone_notes=tone))
            db.commit()
    finally:
        db.close()


@app.get("/api/health")
def health():
    return {"db_ok": True}


@app.get("/api/config")
def config():
    return {"statuses": CAMPAIGN_STATUSES, "status_labels": STATUS_LABELS, "types": CAMPAIGN_TYPES}


@app.get("/api/clients", response_model=list[ClientOut])
def list_clients(db: Session = Depends(get_db)):
    return db.query(Client).order_by(Client.name).all()


@app.post("/api/clients", response_model=ClientOut, status_code=201)
def create_client(body: ClientIn, db: Session = Depends(get_db)):
    if db.query(Client).filter(Client.name == body.name).first():
        raise HTTPException(status_code=409, detail="Cliente già esistente")
    client = Client(**body.model_dump())
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


@app.patch("/api/clients/{client_id}", response_model=ClientOut)
def update_client(client_id: int, body: ClientIn, db: Session = Depends(get_db)):
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    for field, value in body.model_dump().items():
        setattr(client, field, value)
    db.commit()
    db.refresh(client)
    return client


def _campaign_out(c: Campaign) -> dict:
    out = CampaignOut.model_validate(c).model_dump()
    out["client_name"] = c.client.name if c.client else None
    return out


@app.get("/api/campaigns")
def list_campaigns(
    client_id: Optional[int] = None,
    status: Optional[str] = None,
    scheduled_from: Optional[datetime] = Query(default=None),
    scheduled_to: Optional[datetime] = Query(default=None),
    db: Session = Depends(get_db),
):
    q = db.query(Campaign)
    if client_id:
        q = q.filter(Campaign.client_id == client_id)
    if status:
        q = q.filter(Campaign.status.in_(status.split(",")))
    if scheduled_from:
        q = q.filter(Campaign.scheduled_at >= naive_utc(scheduled_from))
    if scheduled_to:
        q = q.filter(Campaign.scheduled_at <= naive_utc(scheduled_to))
    return [_campaign_out(c) for c in q.order_by(Campaign.scheduled_at.asc().nullslast(), Campaign.id.desc()).all()]


@app.post("/api/campaigns", status_code=201)
def create_campaign(body: CampaignIn, db: Session = Depends(get_db)):
    if not body.client_id or not body.title:
        raise HTTPException(status_code=422, detail="client_id e title sono obbligatori")
    if not db.get(Client, body.client_id):
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    if body.type and body.type not in CAMPAIGN_TYPES:
        raise HTTPException(status_code=422, detail=f"Tipo non valido, usa uno di {list(CAMPAIGN_TYPES)}")
    values = body.model_dump(exclude_unset=True)
    for f in ("scheduled_at", "sent_at"):
        if values.get(f):
            values[f] = naive_utc(values[f])
    campaign = Campaign(**values)
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return _campaign_out(campaign)


@app.patch("/api/campaigns/{campaign_id}")
def update_campaign(campaign_id: int, body: CampaignIn, db: Session = Depends(get_db)):
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campagna non trovata")
    changed = body.model_dump(exclude_unset=True)
    if "type" in changed and changed["type"] not in CAMPAIGN_TYPES:
        raise HTTPException(status_code=422, detail=f"Tipo non valido, usa uno di {list(CAMPAIGN_TYPES)}")
    if "client_id" in changed and not db.get(Client, changed["client_id"]):
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    for field, value in changed.items():
        if field in ("scheduled_at", "sent_at"):
            value = naive_utc(value)
        setattr(campaign, field, value)
    db.commit()
    db.refresh(campaign)
    return _campaign_out(campaign)


@app.post("/api/campaigns/{campaign_id}/status")
def change_status(campaign_id: int, body: StatusIn, db: Session = Depends(get_db)):
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campagna non trovata")
    if body.status not in CAMPAIGN_STATUSES:
        raise HTTPException(status_code=422, detail=f"Status non valido, usa uno di {CAMPAIGN_STATUSES}")
    # guardrail: per programmare serve la data di invio
    if body.status == "programmata" and campaign.scheduled_at is None:
        raise HTTPException(status_code=422, detail="Imposta la data di invio prima di programmare")
    campaign.status = body.status
    if body.status == "inviata" and campaign.sent_at is None:
        campaign.sent_at = campaign.scheduled_at or utcnow()
    db.commit()
    db.refresh(campaign)
    return _campaign_out(campaign)


@app.delete("/api/campaigns/{campaign_id}", status_code=204)
def delete_campaign(campaign_id: int, db: Session = Depends(get_db)):
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campagna non trovata")
    db.delete(campaign)
    db.commit()
