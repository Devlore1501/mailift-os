#!/usr/bin/env python3
"""Pulisce un export Apify Google Places e arricchisce con le email dai siti.

    python tools/clean_places.py <export.csv> -o .tmp/leads.csv \
        --esclusi .tmp/installatori.csv

Cosa fa:
  1. tiene solo le colonne utili all'outreach (l'export ne ha 300+)
  2. scarta chiusi definitivamente/temporaneamente e schede senza nome
  3. deduplica per placeId, poi per telefono e per dominio del sito
  4. marca chi e' gia' presente in una lista esistente (--esclusi), per non
     ricontattare due volte
  5. visita sito + pagine contatti e ne estrae le email (mailto: e testo)

Le email con il dominio del sito battono gmail/libero; le PEC restano ultime
perche' spesso non vengono lette per la posta commerciale.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from find_owners import PAGE_HINTS, candidate_urls, get, to_text  # noqa: E402

TIENI = ["title", "categoryName", "address", "city", "postalCode", "state",
         "phone", "phoneUnformatted", "website", "totalScore", "reviewsCount",
         "url", "placeId"]

RE_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

# domini di servizi, non del cliente
DOMINI_ESCLUSI = {
    "sentry.io", "wix.com", "wixpress.com", "godaddy.com", "example.com",
    "sentry.wixpress.com", "gstatic.com", "google.com", "googlemail.com",
    "schema.org", "w3.org", "jquery.com", "cloudflare.com", "elementor.com",
    "wordpress.org", "yoast.com", "adobe.com", "facebook.com", "domain.com",
    "mysite.com", "sentry-next.wixpress.com", "email.com", "yourdomain.com",
}
ESTENSIONI = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".css", ".js")

GENERICHE = ("info", "contatti", "contact", "mail", "posta", "segreteria",
             "amministrazione", "commerciale", "preventivi", "assistenza")


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def dominio(url: str) -> str:
    try:
        h = urlparse(url if url.startswith("http") else "http://" + url).hostname or ""
    except ValueError:
        return ""
    return h.lower().removeprefix("www.")


def valida(mail: str, host: str) -> bool:
    mail = mail.lower()
    if mail.endswith(ESTENSIONI) or mail.count("@") != 1:
        return False
    dom = mail.split("@")[1]
    if dom in DOMINI_ESCLUSI or any(dom.endswith("." + d) for d in DOMINI_ESCLUSI):
        return False
    if re.match(r"^[0-9a-f]{16,}@", mail):      # id offuscati
        return False
    return True


def punteggio(mail: str, host: str) -> int:
    """Piu' alto = meglio. Dominio proprio > casella generica > free > pec."""
    dom = mail.split("@")[1].lower()
    local = mail.split("@")[0].lower()
    p = 0
    if host and (dom == host or dom.endswith("." + host) or host.endswith("." + dom)):
        p += 100
    if any(local.startswith(g) for g in GENERICHE):
        p += 20
    if dom.endswith("pec.it") or "pec." in dom or local.startswith("pec"):
        p -= 60
    if dom in ("gmail.com", "libero.it", "hotmail.it", "yahoo.it", "alice.it",
               "virgilio.it", "tiscali.it", "outlook.it"):
        p -= 15
    return p


def trova_email(sito: str) -> tuple[str, str]:
    """Ritorna (email migliore, tutte le email separate da ;)."""
    if not sito or not sito.startswith("http"):
        return "", ""
    host = dominio(sito)
    html = get(sito)
    if not html:
        return "", ""

    pagine = [html]
    base = re.match(r"https?://[^/]+", sito)
    base = base.group(0) if base else sito
    for u in candidate_urls(base, html)[:3]:
        sub = get(u)
        if sub:
            pagine.append(sub)

    trovate: set[str] = set()
    for pg in pagine:
        for m in re.findall(r'mailto:([^"\'?>&\s]+)', pg, re.I):
            trovate.add(unescape(m).strip().lower())
        for m in RE_EMAIL.findall(to_text(pg)):
            # via code tipo 'x@gmail.com\\' o 'x@dominio.it.'
            trovate.add(m.strip().lower().rstrip('.\\/-_'))

    buone = sorted({m for m in trovate if valida(m, host)},
                   key=lambda m: (-punteggio(m, host), m))
    return (buone[0] if buone else ""), ";".join(buone[:5])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_in")
    ap.add_argument("-o", "--out", default=".tmp/leads.csv")
    ap.add_argument("--esclusi", help="CSV con lista gia' contattata (colonna Website/Email)")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--no-email", action="store_true", help="solo pulizia, niente scraping")
    args = ap.parse_args()

    rows = list(csv.DictReader(open(args.csv_in, encoding="utf-8-sig")))
    tot = len(rows)

    # --- filtri ---
    scarti = {"chiuso": 0, "senza nome": 0, "duplicato": 0}
    puliti, visti_id, visti_tel, visti_dom = [], set(), set(), set()
    for r in rows:
        if r.get("permanentlyClosed") == "true" or r.get("temporarilyClosed") == "true":
            scarti["chiuso"] += 1
            continue
        if not r.get("title", "").strip():
            scarti["senza nome"] += 1
            continue
        pid = r.get("placeId", "")
        tel = re.sub(r"\D", "", r.get("phoneUnformatted") or r.get("phone") or "")
        dom = dominio(r.get("website", ""))
        if (pid and pid in visti_id) or (tel and tel in visti_tel) or (dom and dom in visti_dom):
            scarti["duplicato"] += 1
            continue
        visti_id.add(pid)
        if tel:
            visti_tel.add(tel)
        if dom:
            visti_dom.add(dom)
        puliti.append({k: (r.get(k) or "").strip() for k in TIENI})

    # --- gia' in lista ---
    gia = set()
    if args.esclusi and Path(args.esclusi).exists():
        for r in csv.DictReader(open(args.esclusi, encoding="utf-8-sig")):
            d = dominio(r.get("Website", "") or r.get("website", ""))
            if d:
                gia.add(d)
    for r in puliti:
        r["gia_in_lista"] = "si" if dominio(r["website"]) in gia and r["website"] else ""

    # --- email ---
    if args.no_email:
        for r in puliti:
            r["email"], r["email_tutte"] = "", ""
    else:
        with ThreadPoolExecutor(args.workers) as ex:
            res = list(ex.map(lambda r: trova_email(r["website"]), puliti))
        for r, (best, tutte) in zip(puliti, res):
            r["email"], r["email_tutte"] = best, tutte

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(puliti[0].keys()))
        w.writeheader()
        w.writerows(puliti)

    con_sito = sum(1 for r in puliti if r["website"])
    con_mail = sum(1 for r in puliti if r["email"])
    nuovi = sum(1 for r in puliti if not r["gia_in_lista"])
    print(f"{tot} righe in ingresso", file=sys.stderr)
    for k, v in scarti.items():
        print(f"  scartati {k:12}: {v}", file=sys.stderr)
    print(f"-> {len(puliti)} aziende uniche ({nuovi} non ancora in lista)", file=sys.stderr)
    print(f"   con sito : {con_sito}", file=sys.stderr)
    print(f"   con email: {con_mail}", file=sys.stderr)
    print(f"scritto in {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
