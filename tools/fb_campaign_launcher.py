#!/usr/bin/env python3
"""
fb_campaign_launcher.py — Lancia campagna Meta Ads per Flow Health Score
(mailift.com/landing)

Struttura:
  Campagna  : Flow Health Score — Conversioni [Jun26]  |  OUTCOME_SALES
  TOF €15/g : Advantage+ Italia           | fhs_v2, gap_v5, fhs_v4, gap_v1, fhs_v3
  MOF €10/g : Retargeting visitatori 30gg | gap_v4, fhs_v1, gap_v2, processo_v1
  BOF  €5/g : Retargeting visitatori 7gg  | processo_v2, processo_v3, fhs_v5, gap_v3

Usage:
  python3 tools/fb_campaign_launcher.py              # dry-run (default — nessuna modifica)
  python3 tools/fb_campaign_launcher.py --go         # lancia live
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

# ── Env ────────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = Path.home() / ".secrets" / "mailift" / ".env"
load_dotenv(ENV_PATH if ENV_PATH.exists() else PROJECT_ROOT / ".env")

TOKEN = os.environ.get("FB_ACCESS_TOKEN", "")
RAW_ID = os.environ.get("FB_AD_ACCOUNT_ID", "").strip()
ACCOUNT_ID = f"act_{RAW_ID}" if RAW_ID and not RAW_ID.startswith("act_") else RAW_ID
API_VER = "v21.0"
BASE = f"https://graph.facebook.com/{API_VER}"
LANDING = "https://mailift.com/landing"

DRY = "--go" not in sys.argv

# Permette di riusare una campagna già creata: --campaign-id=XXXX
EXISTING_CAMPAIGN_ID: str | None = next(
    (a.split("=", 1)[1] for a in sys.argv if a.startswith("--campaign-id=")), None
)
EXISTING_MOF_AUDIENCE: str | None = next(
    (a.split("=", 1)[1] for a in sys.argv if a.startswith("--mof-audience=")), None
)
EXISTING_BOF_AUDIENCE: str | None = next(
    (a.split("=", 1)[1] for a in sys.argv if a.startswith("--bof-audience=")), None
)

# ── Creative assignment ────────────────────────────────────────────────────────
PHASES: dict[str, dict] = {
    "TOF": {
        "stems": [
            "fhs_v2_stat_shock",
            "gap_v5_flow_rotto",
            "fhs_v4_doodle",
            "gap_v1_contrario",
            "fhs_v3_founder_pointing",
        ],
        "budget": 1500,  # EUR cents → €15/g
        "label": "Broad Italia",
    },
    "MOF": {
        "stems": [
            "gap_v4_benchmark",
            "fhs_v1_cine_laptop",
            "gap_v2_riacquisto",
            "processo_v1_steps",
        ],
        "budget": 1000,  # €10/g
        "label": "Retargeting 30gg",
    },
    "BOF": {
        "stems": [
            "processo_v2_cine_steps",
            "processo_v3_doodle_steps",
            "fhs_v5_screenshot",
            "gap_v3_agenzia_founder",
        ],
        "budget": 500,  # €5/g
        "label": "Retargeting 7gg",
    },
}

COPY: dict[str, dict] = {
    "TOF": {
        "message": (
            "La maggior parte degli eCommerce italiani su Klaviyo ha flussi attivi da mesi "
            "e non li ha mai toccati. In media: €8.500 di revenue persa ogni mese. "
            "Il Flow Health Score ti dice esattamente cosa si rompe nel tuo Klaviyo "
            "— in 5 minuti, con Claude AI."
        ),
        "headline": "I flussi Klaviyo perdono €8.500/mese",
    },
    "MOF": {
        "message": (
            "I top store italiani generano il 35% del fatturato dall'email. "
            "Il gap non è nella frequenza — sono i flussi rotti. "
            "In 5 minuti Claude analizza ogni tuo flow e ti dice esattamente dove perdi "
            "revenue, con il numero esatto in euro."
        ),
        "headline": "Il tuo Klaviyo perde migliaia ogni mese",
    },
    "BOF": {
        "message": (
            "Il sistema che le agenzie vendono a €2.000/mese. Tuo per €37. "
            "Connetti Klaviyo → Claude analizza ogni flow → "
            "ricevi score + gap in euro + piano 30 giorni."
        ),
        "headline": "€37 adesso. Migliaia recuperati dopo.",
    },
}

IMAGE_DIRS = [
    Path.home() / "Downloads" / "images (5)",
    Path.home() / "Downloads" / "images (6)",
    Path.home() / "Downloads" / "images (7)",
]


# ── HTTP helpers ───────────────────────────────────────────────────────────────
def _get(path: str, **params) -> dict:
    r = requests.get(
        f"{BASE}/{path}",
        params={"access_token": TOKEN, **params},
        timeout=20,
    )
    if not r.ok:
        raise RuntimeError(f"GET /{path} → {r.status_code}: {r.text[:300]}")
    return r.json()


def _post(path: str, files=None, **data) -> dict:
    if DRY:
        preview = {k: str(v)[:80] for k, v in data.items()}
        print(f"      [DRY] POST /{path}: {json.dumps(preview, ensure_ascii=False)[:140]}")
        return {"id": f"DRY_{int(time.time() * 1000) % 999999}"}
    payload = {"access_token": TOKEN, **data}
    r = requests.post(f"{BASE}/{path}", data=payload, files=files, timeout=60)
    if not r.ok:
        raise RuntimeError(f"POST /{path} → {r.status_code}: {r.text[:300]}")
    return r.json()


# ── Discovery ──────────────────────────────────────────────────────────────────
def find_page(hint: str) -> tuple[str, str]:
    """Cerca la pagina per nome tra le pagine gestite dall'utente."""
    hint_l = hint.lower()
    data = _get("me/accounts", fields="id,name", limit=100)
    for pg in data.get("data", []):
        if hint_l in pg.get("name", "").lower():
            return pg["id"], pg["name"]
    all_pages = [pg["name"] for pg in data.get("data", [])]
    raise ValueError(f"Pagina '{hint}' non trovata.\nDisponibili: {all_pages}")


def find_pixel() -> str | None:
    """Recupera primo pixel attivo collegato all'account."""
    data = _get(f"{ACCOUNT_ID}/adspixels", fields="id,name")
    pixels = data.get("data", [])
    if not pixels:
        return None
    px = pixels[0]
    print(f"    Pixel trovato: {px['name']} (id: {px['id']})")
    return px["id"]


# ── Images ─────────────────────────────────────────────────────────────────────
def upload_images() -> dict[str, str]:
    """Carica tutte le PNG dalle directory, ritorna {stem: hash}."""
    hashes: dict[str, str] = {}
    for img_dir in IMAGE_DIRS:
        if not img_dir.exists():
            print(f"    ⚠️  Directory non trovata: {img_dir}")
            continue
        for img_path in sorted(img_dir.glob("*.png")):
            stem = img_path.stem
            print(f"    Upload {stem}...", end=" ", flush=True)
            if DRY:
                hashes[stem] = f"dry_{stem[:10]}"
                print("[DRY]")
                continue
            with open(img_path, "rb") as f:
                r = requests.post(
                    f"{BASE}/{ACCOUNT_ID}/adimages",
                    data={"access_token": TOKEN},
                    files={img_path.name: f},
                    timeout=60,
                )
            r.raise_for_status()
            img_hash = list(r.json()["images"].values())[0]["hash"]
            hashes[stem] = img_hash
            print(f"✓ {img_hash[:12]}...")
    return hashes


# ── Custom Audiences ───────────────────────────────────────────────────────────
def create_website_audience(pixel_id: str, days: int, name: str) -> str:
    rule = json.dumps({
        "inclusions": {"operator": "or", "rules": [{
            "event_sources": [{"id": pixel_id, "type": "pixel"}],
            "retention_seconds": days * 86400,
            "filter": {"operator": "and", "filters": [{
                "field": "event", "operator": "=", "value": "PageView",
            }]},
        }]},
    })
    result = _post(
        f"{ACCOUNT_ID}/customaudiences",
        name=name,
        rule=rule,
        retention_days=days,
        pixel_id=pixel_id,
        description=f"Visitatori mailift.com/landing — ultimi {days}gg",
    )
    return result["id"]


# ── Campaign objects ───────────────────────────────────────────────────────────
def create_campaign() -> str:
    result = _post(
        f"{ACCOUNT_ID}/campaigns",
        name="Flow Health Score — Conversioni [Jun26]",
        objective="OUTCOME_SALES",
        status="ACTIVE",
        special_ad_categories=json.dumps([]),
        is_adset_budget_sharing_enabled="false",
    )
    return result["id"]


def create_adset(
    name: str,
    campaign_id: str,
    budget_cents: int,
    targeting: dict,
    pixel_id: str | None,
    advantage_plus: bool = False,
) -> str:
    # targeting_automation must live INSIDE targeting spec
    targeting["targeting_automation"] = {"advantage_audience": 1 if advantage_plus else 0}
    targeting_str = json.dumps(targeting)
    params: dict = dict(
        name=name,
        campaign_id=campaign_id,
        daily_budget=budget_cents,
        billing_event="IMPRESSIONS",
        optimization_goal="OFFSITE_CONVERSIONS",
        bid_strategy="LOWEST_COST_WITHOUT_CAP",
        destination_type="WEBSITE",
        status="ACTIVE",
        targeting=targeting_str,
    )
    if pixel_id:
        params["promoted_object"] = json.dumps({
            "pixel_id": pixel_id,
            "custom_event_type": "PURCHASE",
        })
    result = _post(f"{ACCOUNT_ID}/adsets", **params)
    return result["id"]


def create_creative(
    name: str,
    page_id: str,
    img_hash: str,
    message: str,
    headline: str,
) -> str:
    story_spec = json.dumps({
        "page_id": page_id,
        "link_data": {
            "image_hash": img_hash,
            "link": LANDING,
            "message": message,
            "name": headline,
            "call_to_action": {
                "type": "SHOP_NOW",
                "value": {"link": LANDING},
            },
        },
    })
    result = _post(
        f"{ACCOUNT_ID}/adcreatives",
        name=name,
        object_story_spec=story_spec,
    )
    return result["id"]


def create_ad(name: str, adset_id: str, creative_id: str) -> str:
    result = _post(
        f"{ACCOUNT_ID}/ads",
        name=name,
        adset_id=adset_id,
        creative=json.dumps({"creative_id": creative_id}),
        status="ACTIVE",
    )
    return result["id"]


# ── Main ───────────────────────────────────────────────────────────────────────
def main() -> None:
    if not TOKEN or not ACCOUNT_ID:
        sys.exit("❌ FB_ACCESS_TOKEN o FB_AD_ACCOUNT_ID non trovati in .env")

    print(f"\n{'='*62}")
    if DRY:
        print("  DRY RUN — nessuna modifica reale (aggiungi --go per lanciare)")
    else:
        print("  🚀 LIVE — lancio campagna Meta Ads")
    print(f"  Account : {ACCOUNT_ID}")
    print(f"  Budget  : TOF €15/g | MOF €10/g | BOF €5/g = €30/g totali")
    print(f"{'='*62}")

    # 1. Pagina
    print("\n[1] Ricerca pagina 'daily business ads'...")
    page_id, page_name = find_page("daily business")
    print(f"    ✓ {page_name}  (id: {page_id})")

    # 2. Pixel
    print("\n[2] Ricerca pixel...")
    pixel_id = find_pixel()
    if not pixel_id:
        print("    ⚠️  Nessun pixel — MOF/BOF creati senza custom audience. Installa il pixel su mailift.com/landing.")

    # 3. Upload immagini
    print("\n[3] Upload immagini...")
    img_hashes = upload_images()
    print(f"    ✓ {len(img_hashes)} immagini caricate")

    # 4. Campagna
    audience_ids: dict[str, str | None] = {"MOF": None, "BOF": None}
    if EXISTING_CAMPAIGN_ID:
        campaign_id = EXISTING_CAMPAIGN_ID
        print(f"\n[4] Riuso campagna esistente: {campaign_id}")
    else:
        print("\n[4] Creazione campagna...")
        campaign_id = create_campaign()
        print(f"    ✓ campaign_id: {campaign_id}")

    # 5. Custom audiences per retargeting
    if EXISTING_MOF_AUDIENCE and EXISTING_BOF_AUDIENCE:
        audience_ids["MOF"] = EXISTING_MOF_AUDIENCE
        audience_ids["BOF"] = EXISTING_BOF_AUDIENCE
        print(f"\n[5] Riuso audience esistenti — MOF: {EXISTING_MOF_AUDIENCE} | BOF: {EXISTING_BOF_AUDIENCE}")
    elif pixel_id:
        print("\n[5] Creazione custom audience retargeting...")
        try:
            audience_ids["MOF"] = create_website_audience(
                pixel_id, 30, "Mailift — Landing 30gg"
            )
            print(f"    ✓ MOF (30gg): {audience_ids['MOF']}")
        except Exception as e:
            print(f"    ⚠️  MOF audience fallita: {e}")
        try:
            audience_ids["BOF"] = create_website_audience(
                pixel_id, 7, "Mailift — Landing 7gg"
            )
            print(f"    ✓ BOF  (7gg): {audience_ids['BOF']}")
        except Exception as e:
            print(f"    ⚠️  BOF audience fallita: {e}")
    else:
        print("\n[5] Skip custom audience (nessun pixel)")

    # 6. Ad set + creatives + ads per ogni fase
    print("\n[6] Creazione ad set, creative e annunci...")
    adset_ids: dict[str, str] = {}

    for phase, cfg in PHASES.items():
        print(f"\n  ── {phase} | {cfg['label']} | €{cfg['budget']//100}/g ──")

        if phase == "TOF":
            # Advantage+: age_max not allowed below 65, so omit it
            targeting: dict = {
                "geo_locations": {"countries": ["IT"]},
                "age_min": 25,
            }
            adv_plus = True
        else:
            aud_id = audience_ids.get(phase)
            targeting = {
                "geo_locations": {"countries": ["IT"]},
                "age_min": 25,
                "age_max": 55,
                **({"custom_audiences": [{"id": aud_id}]} if aud_id else {}),
            }
            adv_plus = False

        adset_id = create_adset(
            name=f"FHS — {phase} | {cfg['label']}",
            campaign_id=campaign_id,
            budget_cents=cfg["budget"],
            targeting=targeting,
            pixel_id=pixel_id,
            advantage_plus=adv_plus,
        )
        adset_ids[phase] = adset_id
        print(f"    Ad set: {adset_id}")

        copy = COPY[phase]
        for stem in cfg["stems"]:
            h = img_hashes.get(stem)
            if not h:
                print(f"    ⚠️  {stem}: hash non trovato, skip")
                continue
            creative_id = create_creative(
                name=f"FHS|{phase}|{stem}",
                page_id=page_id,
                img_hash=h,
                message=copy["message"],
                headline=copy["headline"],
            )
            ad_id = create_ad(
                name=f"FHS|{phase}|{stem}",
                adset_id=adset_id,
                creative_id=creative_id,
            )
            print(f"    ✓ {stem} → ad {ad_id}")

    # 7. Summary
    print(f"\n{'='*62}")
    if DRY:
        print("  ✅ Dry run completato — tutto OK")
        print("  Lancia con:  python3 tools/fb_campaign_launcher.py --go")
    else:
        print("  🚀 Campagna attiva!")
        print(f"\n  campaign_id : {campaign_id}")
        for ph, aid in adset_ids.items():
            print(f"  {ph}          : {aid}  (€{PHASES[ph]['budget']//100}/g)")
        print(f"\n  Landing     : {LANDING}")
        print("  Controlla su: business.facebook.com → Ads Manager")
    print(f"{'='*62}\n")


if __name__ == "__main__":
    main()
