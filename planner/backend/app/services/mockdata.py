"""Generazione demo deterministica quando manca la chiave Anthropic (mock_mode).

Permette di provare l'app end-to-end (generazione, edit, approvazione,
pubblicazione simulata) senza costi API.
"""

from __future__ import annotations

from datetime import date, timedelta

DAY_NAMES = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]

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


def _month_objectives(n: int) -> list[str]:
    """Sequenza obiettivi 70/20/10: educative + prodotto a metà mese + promo in coda."""
    n_promo = max(1, round(0.1 * n)) if n >= 4 else 0
    n_prod = max(1, round(0.2 * n)) if n >= 3 else 0
    n_edu = n - n_promo - n_prod
    edu = ["nurturing" if i % 2 == 0 else "storytelling" for i in range(n_edu)]
    out = list(edu)
    # prodotto distribuito nel mese, promo verso fine mese
    step = max(1, len(out) // (n_prod + 1)) if n_prod else 1
    for i in range(n_prod):
        out.insert(min(len(out), (i + 1) * step + i), "vendita")
    out.extend(["promo"] * n_promo)
    return out[:n]


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
        "Offerta del mese",
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
    """Piano mensile demo coerente con i dati reali del brand."""
    brand = context["brand"]
    month_start = date.fromisoformat(context["month_start"])
    if month_start.month == 12:
        month_days = 31
    else:
        month_days = (month_start.replace(month=month_start.month + 1) - month_start).days
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

    objectives = _month_objectives(num_emails)
    step = month_days / max(num_emails, 1)
    emails = []
    for i in range(num_emails):
        objective = objectives[i]
        theme, angle = _THEMES[objective]
        offset = min(int(round(i * step)), month_days - 1)
        d = month_start + timedelta(days=offset)
        best = next((p for p in products if p.get("is_best_seller")), None)
        prod = best or (products[i % len(products)] if products else None)
        offer = offers[0] if (offers and objective in ("promo", "vendita")) else None

        # match per categoria; se la libreria usa categorie diverse (es. set
        # Canva con "educativa") ruota comunque sui template disponibili
        wanted_cat = _TEMPLATE_BY_OBJECTIVE[objective]
        tpl = next((t for t in templates if t.get("category") == wanted_cat), None) or (
            templates[i % len(templates)] if templates else None
        )

        product_name = prod["name"] if prod else "il nostro prodotto di punta"

        # bilanciamento formati: promo/vendita grafiche; metà delle educative testuali
        if objective in ("promo", "vendita"):
            email_format = "grafica"
        else:
            email_format = "testuale" if i % 2 == 1 else "grafica"

        body = ""
        blocks: list[dict] = []
        if email_format == "testuale":
            body_lines = [
                f"Ciao {{{{ first_name|default:'' }}}},",
                "",
                f"[DEMO — generazione senza API Claude] {angle}.",
                "",
                f"Oggi ti parlo di {product_name}: perché è rilevante per te, "
                f"come usarlo al meglio e cosa lo rende diverso.",
                "",
                "👉 Scopri di più sul sito.",
                "",
                f"A presto,\nIl team {brand['name']}",
            ]
            body = "\n".join(body_lines)
        else:
            blocks = [
                {
                    "type": "banner",
                    "headline": f"[DEMO] {theme}"[:60],
                    "subheadline": angle[:90],
                    "text": "",
                    "cta": "Scopri ora",
                    "visual": f"Foto hero di {product_name} su sfondo brand",
                },
                {
                    "type": "sezione",
                    "headline": "Perché sceglierlo",
                    "subheadline": "",
                    "text": "3 benefici concreti in una riga ciascuno.",
                    "cta": "",
                    "visual": "Infografica: 3 step numerati con icone, niente muri di testo",
                },
            ]
            if offer:
                blocks.append(
                    {
                        "type": "info",
                        "headline": "",
                        "subheadline": "",
                        "text": f"Codice {offer.get('code') or offer['name']} · "
                        f"{offer.get('discount') or 'sconto dedicato'}",
                        "cta": "",
                        "visual": "Badge sconto grande in evidenza",
                    }
                )
            blocks.append(
                {
                    "type": "cta_finale",
                    "headline": "Pronto a provarlo?",
                    "subheadline": "",
                    "text": "",
                    "cta": "Vai allo shop",
                    "visual": "Bottone pieno colore primario",
                }
            )

        emails.append(
            {
                "position": i + 1,
                "send_date": d.isoformat(),
                "send_day": DAY_NAMES[d.weekday()],
                "send_time": "09:30" if d.weekday() >= 5 else "08:30",
                "objective": objective,
                "format": email_format,
                "theme": theme,
                "angle": angle,
                "segment": dict(default_segment),
                "subject_variants": [
                    f"{theme} ✉️",
                    f"{brand['name']}: {theme.lower()}",
                    "Questa la devi leggere",
                ],
                "preview_text": angle[:80],
                "body": body,
                "blocks": blocks,
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
                "template_notion_page_id": (
                    tpl["notion_page_id"] if (tpl and email_format == "grafica") else None
                ),
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
    if email.get("format") == "testuale" or email.get("body"):
        out["body"] = (email.get("body") or "") + f"\n\n[DEMO{note}]"
    else:
        blocks = [dict(b) for b in email.get("blocks") or []]
        if blocks:
            blocks[0]["headline"] = (blocks[0].get("headline") or "") + " ✨"
        out["blocks"] = blocks
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


# Festività a data fissa per paese (demo): MM-DD → nome
_FIXED_HOLIDAYS: dict[str, dict[str, str]] = {
    "IT": {
        "01-01": "Capodanno", "01-06": "Epifania", "04-25": "Festa della Liberazione",
        "05-01": "Festa dei Lavoratori", "06-02": "Festa della Repubblica",
        "08-15": "Ferragosto", "11-01": "Ognissanti", "12-08": "Immacolata Concezione",
        "12-25": "Natale", "12-26": "Santo Stefano",
    },
    "FR": {
        "01-01": "Jour de l'an", "05-01": "Fête du Travail", "05-08": "Victoire 1945",
        "07-14": "Fête nationale", "08-15": "Assomption", "11-01": "Toussaint",
        "11-11": "Armistice", "12-25": "Noël",
    },
    "DE": {
        "01-01": "Neujahr", "05-01": "Tag der Arbeit", "10-03": "Tag der Deutschen Einheit",
        "12-25": "1. Weihnachtstag", "12-26": "2. Weihnachtstag",
    },
    "ES": {
        "01-01": "Año Nuevo", "01-06": "Reyes", "05-01": "Día del Trabajador",
        "08-15": "Asunción", "10-12": "Fiesta Nacional", "11-01": "Todos los Santos",
        "12-06": "Constitución", "12-08": "Inmaculada", "12-25": "Navidad",
    },
    "US": {
        "01-01": "New Year's Day", "07-04": "Independence Day", "11-11": "Veterans Day",
        "12-25": "Christmas",
    },
    "GB": {"01-01": "New Year's Day", "12-25": "Christmas", "12-26": "Boxing Day"},
}

_COMMERCIAL_DATES: dict[str, str] = {
    "02-14": "San Valentino", "03-08": "Festa della Donna", "03-19": "Festa del Papà",
    "10-31": "Halloween",
}


def mock_occasion_suggestions(country: str, month: str) -> list[dict]:
    """Suggerimenti demo: festività a data fissa + ponti calcolati + ricorrenze."""
    country = (country or "IT").upper()
    holidays = _FIXED_HOLIDAYS.get(country, _FIXED_HOLIDAYS["IT"])
    year, month_num = month.split("-")
    out: list[dict] = []
    for mmdd, name in sorted({**holidays, **_COMMERCIAL_DATES}.items()):
        if not mmdd.startswith(f"{month_num}-"):
            continue
        iso = f"{year}-{mmdd}"
        kind = "festività" if mmdd in holidays else "ricorrenza"
        out.append(
            {
                "name": name,
                "date": iso,
                "kind": kind,
                "idea": f"[DEMO] Email a tema {name}: contenuto o selezione prodotti dedicata.",
            }
        )
        # ponte: festività di martedì o giovedì
        d = date.fromisoformat(iso)
        if kind == "festività" and d.weekday() in (1, 3):
            bridge = d - timedelta(days=1) if d.weekday() == 1 else d + timedelta(days=1)
            out.append(
                {
                    "name": f"Ponte di {name}",
                    "date": bridge.isoformat(),
                    "kind": "ponte",
                    "idea": "[DEMO] Long weekend: email 'idee per il ponte' con i prodotti giusti.",
                }
            )
    return out
