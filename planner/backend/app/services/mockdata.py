"""Generazione demo deterministica quando manca la chiave Anthropic (mock_mode).

Permette di provare l'app end-to-end (generazione, edit, approvazione,
pubblicazione simulata) senza costi API.
"""

from __future__ import annotations

from datetime import date, timedelta

DAY_NAMES = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]

# Cadenza consigliata per numero email/settimana → offset giorni dal lunedì
DAY_PATTERNS = {
    1: [1],
    2: [1, 4],
    3: [0, 2, 4],
    4: [0, 2, 4, 6],
    5: [0, 1, 3, 4, 6],
}

MOCK_TEMPLATES = [
    ("Promo Bold 04", "promo", ["sconto", "urgenza"]),
    ("Promo Minimal 11", "promo", ["flash sale"]),
    ("Newsletter Classic 02", "newsletter", ["editoriale"]),
    ("Newsletter Magazine 07", "newsletter", ["curation"]),
    ("Storytelling Vigna 02", "storytelling", ["brand story"]),
    ("Storytelling Founder 05", "storytelling", ["dietro le quinte"]),
    ("Lancio Prodotto Hero 01", "lancio prodotto", ["novità"]),
    ("Lancio Countdown 03", "lancio prodotto", ["countdown"]),
    ("Abbandono Carrello Soft 01", "abbandono", ["recupero"]),
    ("Re-engagement Winback 02", "re-engagement", ["winback"]),
    ("Benvenuto Warm 01", "benvenuto", ["welcome"]),
    ("Stagionale Estate 04", "stagionale", ["estate"]),
    ("Stagionale Natale 09", "stagionale", ["natale"]),
    ("Promo Bundle 06", "promo", ["bundle"]),
    ("Newsletter Tips 05", "newsletter", ["educational"]),
    ("Storytelling Cliente 03", "storytelling", ["testimonianza"]),
]


def mock_template_rows() -> list[dict]:
    rows = []
    for i, (name, category, tags) in enumerate(MOCK_TEMPLATES, start=1):
        rows.append(
            {
                "notion_page_id": f"mock-{i:03d}",
                "name": name,
                "category": category,
                "tags": tags,
                "canva_url": f"https://www.canva.com/design/DEMO{i:03d}/edit",
                "notion_url": f"https://www.notion.so/mock-template-{i:03d}",
            }
        )
    return rows


_OBJECTIVE_CYCLE = ["nurturing", "storytelling", "promo", "nurturing", "vendita"]

_THEMES = {
    "nurturing": (
        "Consigli pratici legati ai prodotti",
        "Guida rapida: come scegliere il prodotto giusto per te",
    ),
    "storytelling": (
        "Dietro le quinte del brand",
        "La storia che ci ha portato fin qui (e cosa c'entra con te)",
    ),
    "promo": (
        "Offerta della settimana",
        "Solo per pochi giorni: un'occasione da non perdere",
    ),
    "vendita": (
        "Focus sul best seller",
        "Perché tutti continuano a riordinare questo prodotto",
    ),
}

_TEMPLATE_BY_OBJECTIVE = {
    "nurturing": "newsletter",
    "storytelling": "storytelling",
    "promo": "promo",
    "vendita": "promo",
}


def mock_plan(context: dict) -> dict:
    """Piano demo coerente con i dati reali del brand (prodotti, offerte, segmenti)."""
    brand = context["brand"]
    week_start = date.fromisoformat(context["week_start"])
    num_emails = context["num_emails"]
    products = context.get("products", [])
    offers = [o for o in context.get("offers", []) if o.get("active")]
    segments = (context.get("klaviyo") or {}).get("segments") or []
    templates = context.get("templates", [])

    engaged = next(
        (s for s in segments if "engaged" in s["name"].lower() and "un" not in s["name"].lower()),
        None,
    )
    default_segment = {
        "name": engaged["name"] if engaged else "Lista principale (engaged 60 giorni)",
        "klaviyo_segment_id": engaged["klaviyo_id"] if engaged else None,
        "rationale": (
            "Segmento engaged: massimizza open rate mantenendo bassa la pressione "
            "sul resto della lista."
        ),
    }

    offsets = DAY_PATTERNS.get(num_emails) or list(range(min(num_emails, 7)))
    emails = []
    for i in range(num_emails):
        objective = _OBJECTIVE_CYCLE[i % len(_OBJECTIVE_CYCLE)]
        theme, angle = _THEMES[objective]
        d = week_start + timedelta(days=offsets[i % len(offsets)])
        best = next((p for p in products if p.get("is_best_seller")), None)
        prod = best or (products[i % len(products)] if products else None)
        offer = offers[0] if (offers and objective in ("promo", "vendita")) else None

        wanted_cat = _TEMPLATE_BY_OBJECTIVE[objective]
        tpl = next((t for t in templates if t.get("category") == wanted_cat), None)

        first_line = f"Ciao {{{{ first_name|default:'' }}}},"
        product_name = prod["name"] if prod else "il nostro prodotto di punta"
        body_lines = [
            first_line,
            "",
            f"[DEMO — generazione senza API Claude] {angle}.",
            "",
            f"Questa settimana parliamo di {product_name}: perché è rilevante per te, "
            f"come usarlo al meglio e cosa lo rende diverso.",
            "",
        ]
        if offer:
            body_lines += [
                f"In più, con il codice {offer.get('code') or offer['name']} hai "
                f"{offer.get('discount') or 'uno sconto dedicato'} fino al "
                f"{offer.get('valid_to') or 'fine settimana'}.",
                "",
            ]
        body_lines += ["👉 Scopri di più sul sito.", "", f"A presto,\nIl team {brand['name']}"]

        emails.append(
            {
                "position": i + 1,
                "send_date": d.isoformat(),
                "send_day": DAY_NAMES[d.weekday()],
                "send_time": "09:30" if d.weekday() >= 5 else "08:30",
                "objective": objective,
                "theme": theme,
                "angle": angle,
                "segment": dict(default_segment),
                "subject_variants": [
                    f"{theme} ✉️",
                    f"{brand['name']}: {theme.lower()}",
                    "Questa la devi leggere",
                ],
                "preview_text": angle[:80],
                "body": "\n".join(body_lines),
                "products": (
                    [{"name": prod["name"], "reason": "prodotto centrale dell'email"}]
                    if prod
                    else []
                ),
                "offer": (
                    {
                        "name": offer["name"],
                        "code": offer.get("code", ""),
                        "discount": offer.get("discount", ""),
                    }
                    if offer
                    else None
                ),
                "template_notion_page_id": tpl["notion_page_id"] if tpl else None,
            }
        )
    return {"emails": emails}


def mock_regenerated_email(email: dict, instructions: str) -> dict:
    out = dict(email)
    note = f" (rigenerata{': ' + instructions if instructions else ''})"
    out["subject_variants"] = [s + " ✨" for s in email.get("subject_variants", [])][:3] or [
        "Nuovo oggetto A",
        "Nuovo oggetto B",
    ]
    out["body"] = (email.get("body") or "") + f"\n\n[DEMO{note}]"
    return out


def mock_klaviyo_snapshot() -> dict:
    from datetime import datetime, timezone

    return {
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "account_name": "Account demo",
        "total_profiles": 12400,
        "segments": [
            {"klaviyo_id": "demo-eng-30", "name": "Engaged 30 days", "profile_count": 3200},
            {"klaviyo_id": "demo-eng-90", "name": "Engaged 90 days", "profile_count": 6100},
            {"klaviyo_id": "demo-vip", "name": "VIP - 2+ ordini", "profile_count": 840},
            {"klaviyo_id": "demo-uneng", "name": "Unengaged 90 days", "profile_count": 4100},
        ],
        "campaigns": [
            {
                "klaviyo_id": "demo-c1",
                "name": "Newsletter settimanale",
                "sent_at": None,
                "recipients": 3100,
                "open_rate": 0.41,
                "click_rate": 0.021,
                "revenue": 830.0,
            },
            {
                "klaviyo_id": "demo-c2",
                "name": "Flash sale fine mese",
                "sent_at": None,
                "recipients": 6000,
                "open_rate": 0.33,
                "click_rate": 0.030,
                "revenue": 2400.0,
            },
        ],
        "metrics_summary": {
            "avg_open_rate": 0.37,
            "avg_click_rate": 0.025,
            "total_revenue_30d": 3230.0,
            "campaigns_last_30d": 6,
            "engagement_health": "good",
        },
        "recommendations": [
            "Open rate medio 37%: lista sana, ok la frequenza attuale.",
            "Segmento 'Unengaged 90 days' con 4.1k profili: pianificare re-engagement.",
        ],
    }
