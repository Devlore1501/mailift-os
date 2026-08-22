#!/usr/bin/env python3
"""Scoring ICP Mailift su export MyLeadFox (eCommerce IT).

Legge il CSV MyLeadFox, calcola uno score 0-100 sull'ICP Mailift
(eCommerce DTC italiano, Shopify+Klaviyo, 25k-300k EUR/mese) e produce:
  - .tmp/leads_scored.csv       tutti i lead ordinati per score
  - outreach/top30.md           shortlist con punto d'attacco per riga

Uso:
    python tools/score_leads_myleadfox.py "<path-csv>" [--top 30] [--platform shopify]

Note sui dati MyLeadFox (verificate sul export del 05/08/2026):
  - "Est. Monthly Sales" e' in USD e stimato (min export ~$76k -> lista gia' filtrata).
  - "Est. Products Sold" e' la dimensione del catalogo, NON unita' vendute:
    non usarlo per calcolare AOV (1001hobbies: 68k "prodotti venduti" su $138k).
  - "Installed Apps" e' popolato quasi solo per Shopify; per Woo/Presta lo stack
    email si legge da "Technology Used".
"""

import argparse
import csv
import os
import re
import sys

USD_EUR = 0.92  # cambio indicativo: la stima e' comunque un ordine di grandezza

ESP_KLAVIYO = ["klaviyo"]
ESP_ALTRI = [
    "mailchimp", "sendinblue", "brevo", "omnisend", "mailerlite",
    "activecampaign", "getresponse", "mailup", "4dem", "sendgrid",
    "drip", "hubspot", "constant contact", "shopify email",
]
PIXEL_ADS = {
    "facebook pixel": 4,
    "meta pixel": 4,
    "google ads pixel": 3,
    "tiktok pixel": 3,
    "pinterest pixel": 1,
}

# Fuori ICP: non sono eCommerce DTC (editoria, servizi, marketplace, B2B puro)
ESCLUSIONI_RE = re.compile(
    r"\b(notizie|quotidiano|testata|giornale|blog di|magazine|"
    r"agenzia (web|di comunicazione|marketing)|web agency|"
    r"noleggio|autonoleggio|biglietti|ticket|"
    r"corsi di formazione|consulenza aziendale|software house|"
    r"marketplace|comparatore|portale di annunci)\b",
    re.I,
)

# Prefissi di lingua/paese: segnalano lo storefront localizzato di un brand
# internazionale (it.aukey.com, de.bamboom.it) -> decision-maker non italiano,
# nessun owner-volto-del-brand. Fuori ICP.
LOCALE_RE = re.compile(r"^(it|en|de|fr|es|nl|pt|pl|dk|se|fi|be|at|ch|uk|us)\.", re.I)

# Margine tipicamente sottile: reseller, outlet, stocchisti. Non escluso,
# ma penalizzato e segnalato (ICP Hormozi: margine 50%+).
MARGINE_RE = re.compile(r"\b(resell|reseller|outlet|stock house|stockhouse|destock|liquidazion)", re.I)


def num(s):
    """Estrae il primo numero da una cella (gestisce 'USD $148,670')."""
    s = re.sub(r"[^0-9.]", "", (s or "").replace(",", ""))
    try:
        return float(s)
    except ValueError:
        return 0.0


def stack(row):
    return (row.get("Installed Apps", "") + " " + row.get("Technology Used", "")).lower()


def esp_di(row):
    s = stack(row)
    if any(k in s for k in ESP_KLAVIYO):
        return "klaviyo"
    trovati = [e for e in ESP_ALTRI if e in s]
    if trovati:
        return trovati[0]
    return None


def radice(host):
    """Dominio radice, per deduplicare i sottodomini di lingua dello stesso brand."""
    h = (host or "").strip().lower().replace("https://", "").replace("http://", "")
    h = h.split("/")[0]
    if h.startswith("www."):
        h = h[4:]
    h = LOCALE_RE.sub("", h)
    return h


def score(row):
    """Ritorna (punteggio, dict_motivazioni, lista_stop, lista_warning)."""
    pt = {}
    stop = []

    fatt_eur = num(row["Est. Monthly Sales"]) * USD_EUR
    visite = num(row["Est Monthly Visits"])
    piatt = (row.get("Platform") or "").strip()
    esp = esp_di(row)
    s = stack(row)

    # --- Fatturato stimato (0-25) — sweet spot dichiarato 80-200k EUR/mese
    if 80_000 <= fatt_eur <= 200_000:
        pt["fatturato"] = 25
    elif 50_000 <= fatt_eur < 80_000 or 200_000 < fatt_eur <= 300_000:
        pt["fatturato"] = 20
    elif 25_000 <= fatt_eur < 50_000:
        pt["fatturato"] = 12
    elif 300_000 < fatt_eur <= 600_000:
        pt["fatturato"] = 8
    else:
        pt["fatturato"] = 0
        if fatt_eur < 25_000:
            stop.append("sotto soglia 25k")
        else:
            stop.append("oltre 600k (enterprise)")

    # --- Piattaforma (0-20) — Shopify e' la specializzazione Mailift
    pt["piattaforma"] = {"Shopify": 20, "PrestaShop": 8, "WooCommerce": 6}.get(piatt, 4)

    # --- Stack email (0-20)
    if esp == "klaviyo":
        pt["esp"] = 20  # paga gia' Klaviyo: budget provato, leak = sottoutilizzo
    elif esp:
        pt["esp"] = 14  # ESP generalista su un eCommerce: leak strutturale + angle migrazione
    else:
        pt["esp"] = 10  # nessun ESP rilevato: leak massimo ma awareness bassa

    # --- Traffico (0-15) — input diretto del Revenue Leak Calculator
    if visite >= 50_000:
        pt["traffico"] = 15
    elif visite >= 20_000:
        pt["traffico"] = 12
    elif visite >= 10_000:
        pt["traffico"] = 8
    else:
        pt["traffico"] = 3

    # --- Dipendenza da paid (0-10) — angle "traffico gia' pagato"
    pt["paid"] = min(10, sum(v for k, v in PIXEL_ADS.items() if k in s))

    # --- Contattabilita' (0-10)
    pt["contatto"] = (6 if row.get("Email", "").strip() else 0) + (
        4 if row.get("Phone Number", "").strip() else 0
    )
    if not row.get("Email", "").strip() and not row.get("Phone Number", "").strip():
        stop.append("nessun contatto")

    testo = f"{row.get('Name','')} {row.get('Description','')}"
    if ESCLUSIONI_RE.search(testo):
        stop.append("non DTC (editoria/servizi/marketplace)")

    host = (row.get("Website") or "").strip().lower()
    if LOCALE_RE.match(host):
        stop.append("storefront localizzato di brand internazionale")

    warn = []
    if MARGINE_RE.search(f"{testo} {host}"):
        pt["margine"] = -8
        warn.append("margine da verificare (reseller/outlet)")

    return sum(pt.values()), pt, stop, warn


def segmento(row):
    """Segmento di messaggistica: determina quale script usare."""
    esp = esp_di(row)
    if esp == "klaviyo":
        return "A - Klaviyo attivo"
    if esp:
        return "B - ESP generalista"
    return "C - Nessun ESP"


def punto_attacco(row):
    """Osservazione concreta e verificabile da mettere in prima riga del messaggio."""
    esp = esp_di(row)
    s = stack(row)
    visite = int(num(row["Est Monthly Visits"]))
    bits = []

    if esp == "klaviyo":
        bits.append(f"Klaviyo gia' installato su {row['Platform']}")
    elif esp:
        bits.append(f"{esp.title()} su un eCommerce {row['Platform']} (ESP non eCommerce-native)")
    else:
        bits.append(f"nessun ESP rilevato sul sito ({row['Platform']})")

    ads = [k.replace(" pixel", "").title() for k in PIXEL_ADS if k in s]
    if ads:
        bits.append(f"pixel attivi: {', '.join(ads)}")
    if visite:
        bits.append(f"~{visite:,}".replace(",", ".") + " visite/mese stimate")

    popup = any(x in s for x in ["privy", "optimonk", "sumo", "justuno", "wisepops"])
    if not popup and esp:
        bits.append("nessun tool di lead capture dedicato rilevato")

    return " · ".join(bits)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path")
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--platform", default=None, help="filtra per piattaforma, es. Shopify")
    ap.add_argument("--out-dir", default=".")
    args = ap.parse_args()

    with open(args.csv_path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    scored = []
    for r in rows:
        sc, pt, stop, warn = score(r)
        r["_score"] = sc
        r["_dettaglio"] = pt
        r["_stop"] = stop
        r["_warn"] = warn
        r["_segmento"] = segmento(r)
        r["_attacco"] = punto_attacco(r)
        scored.append(r)

    validi = [r for r in scored if not r["_stop"]]
    if args.platform:
        validi = [r for r in validi if r["Platform"].lower() == args.platform.lower()]
    validi.sort(key=lambda r: (-r["_score"], -num(r["Est Monthly Visits"])))

    # dedup: un solo record per brand (tiene il migliore)
    visti, dedup = set(), []
    for r in validi:
        k = radice(r["Website"])
        if k in visti:
            continue
        visti.add(k)
        dedup.append(r)
    duplicati = len(validi) - len(dedup)
    validi = dedup

    tmp_dir = os.path.join(args.out_dir, ".tmp")
    out_dir = os.path.join(args.out_dir, "outreach")
    os.makedirs(tmp_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)

    csv_out = os.path.join(tmp_dir, "leads_scored.csv")
    campi = [
        "Website", "Name", "Email", "Phone Number", "City", "Platform",
        "Est. Monthly Sales", "Est Monthly Visits", "Shop Category", "Instagram",
    ]
    with open(csv_out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["score", "segmento", "punto_attacco", "warning"] + campi)
        for r in validi:
            w.writerow([r["_score"], r["_segmento"], r["_attacco"], "; ".join(r["_warn"])]
                       + [r.get(c, "") for c in campi])

    top = validi[: args.top]
    md = os.path.join(out_dir, f"top{args.top}.md")
    with open(md, "w", encoding="utf-8") as f:
        f.write(f"# Top {args.top} — shortlist outreach (fonte: {os.path.basename(args.csv_path)})\n\n")
        f.write(f"Lead totali: {len(rows)} · in ICP dopo dedup: {len(validi)} · "
                f"esclusi: {len(rows)-len(validi)-duplicati} · duplicati brand rimossi: {duplicati}\n\n")
        for i, r in enumerate(top, 1):
            fatt = num(r["Est. Monthly Sales"]) * USD_EUR
            f.write(f"## {i}. {r['Name'] or r['Website']} — score {r['_score']}\n")
            f.write(f"- **Sito**: {r['Website']} · **Piattaforma**: {r['Platform']}\n")
            f.write(f"- **Segmento**: {r['_segmento']}\n")
            f.write(f"- **Fatturato stimato**: ~{fatt/1000:.0f}k EUR/mese · "
                    f"**Visite**: ~{int(num(r['Est Monthly Visits'])):,}".replace(",", ".") + "/mese\n")
            f.write(f"- **Contatti**: {r['Email'] or '—'} · {r['Phone Number'] or '—'}"
                    + (f" · IG: {r['Instagram']}" if r['Instagram'] else "") + "\n")
            f.write(f"- **Punto d'attacco**: {r['_attacco']}\n")
            if r["Shop Category"]:
                f.write(f"- **Categoria**: {r['Shop Category']}\n")
            if r["_warn"]:
                f.write(f"- **⚠ Da verificare**: {'; '.join(r['_warn'])}\n")
            f.write("\n")

        f.write("---\n\n## Appendice — migliori 10 per segmento B e C\n\n")
        f.write("Da usare per testare gli angle alternativi "
                "(migrazione ESP / nessun ESP) su un campione parallelo.\n\n")
        for seg in ["B - ESP generalista", "C - Nessun ESP"]:
            f.write(f"### {seg}\n\n")
            for r in [x for x in validi if x["_segmento"] == seg][:10]:
                f.write(f"- **{r['Name'] or r['Website']}** ({r['Website']}, {r['Platform']}, "
                        f"score {r['_score']}) — {r['Email'] or r['Phone Number'] or 'no contatto'} — "
                        f"{r['_attacco']}\n")
            f.write("\n")

    print(f"OK — {len(validi)}/{len(rows)} lead in ICP")
    for seg in ["A - Klaviyo attivo", "B - ESP generalista", "C - Nessun ESP"]:
        print(f"  {seg}: {sum(1 for r in validi if r['_segmento']==seg)}"
              f" (nei top{args.top}: {sum(1 for r in top if r['_segmento']==seg)})")
    print(f"CSV completo -> {csv_out}")
    print(f"Shortlist    -> {md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
