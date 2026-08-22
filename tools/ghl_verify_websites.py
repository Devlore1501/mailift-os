#!/usr/bin/env python3
"""Verifica che i siti dichiarati dai lead siano ecommerce davvero attivi.

Il DNS non basta: un dominio inventato ma registrato (es. `stocazzo.it`) risolve
regolarmente e passa ogni controllo formale. L'unico modo di distinguerlo da un
negozio vero e' aprirlo e guardare cosa c'e' dentro.

Cerca due famiglie di segnali:
- ecommerce attivo → piattaforma nota (Shopify, WooCommerce, Prestashop, Magento)
  o elementi di acquisto (carrello, checkout, prezzi)
- non-negozio → pagina parcheggiata, dominio in vendita, "in costruzione", vuota

Read-only: fa solo GET su siti pubblici, non invia nulla.

Uso:
    python tools/ghl_verify_websites.py                 # tutti i contatti con fatturato
    python tools/ghl_verify_websites.py --incluso-fake  # anche i gia' taggati fake
"""

from __future__ import annotations

import argparse
import collections
import re
import sys
import urllib3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from ghl_fields_audit import fetch_all_contacts  # noqa: E402

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

FATTURATO = "bW87MPPTFNr51QBtNZmG"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"

ECOM = [
    "shopify", "woocommerce", "prestashop", "magento", "bigcartel", "squarespace-commerce",
    "add to cart", "aggiungi al carrello", "aggiungi al carello", "carrello", "checkout",
    "acquista ora", "spedizione gratuita", "add-to-cart", "wc-block", "cart.js",
]
PARCHEGGIO = [
    "domain is for sale", "dominio in vendita", "buy this domain", "questo dominio",
    "sedoparking", "afternic", "godaddy.com/domainsearch", "parkingcrew", "bodis.com",
    "coming soon", "prossimamente", "sito in costruzione", "under construction",
    "in allestimento", "page not found", "default web page", "apache2 ubuntu",
    "welcome to nginx", "it works!", "future home of",
]


def dominio(u: str | None) -> str:
    u = str(u or "").strip().lower().rstrip("/")
    for p in ("https://", "http://", "www."):
        while u.startswith(p):
            u = u[len(p):]
    return u.split("/")[0]


def visita(d: str) -> tuple[str, str, str]:
    """(dominio, verdetto, dettaglio).

    Prova sia il dominio nudo sia `www.`: su parecchi hosting italiani il
    dominio nudo serve la pagina di parcheggio del registrar mentre il sito
    vero sta solo su www. Provando solo il primo, un ecommerce attivo viene
    classificato "parcheggiato" — succede davvero (parquetfacile.it).
    """
    tentativi = [s + p + d for s in ("https://", "http://") for p in ("www.", "")]
    for url in tentativi:
        try:
            r = requests.get(
                url, timeout=12, verify=False, allow_redirects=True,
                headers={"User-Agent": UA, "Accept-Language": "it-IT,it;q=0.9"},
            )
        except requests.RequestException:
            continue

        if r.status_code >= 400:
            return (d, "ERRORE HTTP", f"status {r.status_code}")

        html = r.text[:200_000].lower()
        # Una pagina quasi vuota non e' un negozio, qualunque cosa dica.
        testo = re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>", " ", html, flags=re.S)
        parole = len(testo.split())

        parcheggiata = [p for p in PARCHEGGIO if p in html]
        if parcheggiata:
            return (d, "PARCHEGGIATO", parcheggiata[0])

        segnali = [s for s in ECOM if s in html]
        if segnali:
            return (d, "ecommerce", ", ".join(segnali[:3]))
        if parole < 80:
            return (d, "QUASI VUOTO", f"{parole} parole")
        return (d, "sito generico", f"{parole} parole, nessun segnale di acquisto")

    return (d, "IRRAGGIUNGIBILE", "nessuna risposta su https ne' http")


def main() -> None:
    ap = argparse.ArgumentParser(description="Verifica i siti dichiarati dai lead")
    ap.add_argument("--incluso-fake", action="store_true", help="verifica anche i gia' taggati fake")
    args = ap.parse_args()

    contacts = fetch_all_contacts()
    def cf(c, i):
        return next((x.get("value") for x in (c.get("customFields") or [])
                     if x["id"] == i and x.get("value")), None)

    pool = []
    for c in contacts:
        if not args.incluso_fake and "fake" in [t.lower() for t in (c.get("tags") or [])]:
            continue
        if not cf(c, FATTURATO):
            continue
        d = dominio(c.get("website"))
        if d and "." in d:
            pool.append((c, d))

    domini = sorted({d for _, d in pool})
    print(f"[verify] {len(pool)} contatti · {len(domini)} domini distinti da visitare...", file=sys.stderr)

    with ThreadPoolExecutor(max_workers=12) as ex:
        esiti = {d: (v, det) for d, v, det in ex.map(visita, domini)}

    per_verdetto = collections.defaultdict(list)
    for c, d in pool:
        v, det = esiti[d]
        per_verdetto[v].append((c, d, det))

    ordine = ["PARCHEGGIATO", "IRRAGGIUNGIBILE", "ERRORE HTTP", "QUASI VUOTO", "sito generico", "ecommerce"]
    for v in ordine:
        righe = per_verdetto.get(v)
        if not righe:
            continue
        print(f"\n{'═' * 78}\n{v}  ({len(righe)})")
        if v == "ecommerce":
            print("   (ok, non elencati)")
            continue
        for c, d, det in sorted(righe, key=lambda r: r[1]):
            print(f"   {d[:34]:<36} {(c.get('email') or '')[:30]:<32} {cf(c, FATTURATO)}")
            print(f"        → {det}")

    print(f"\n{'═' * 78}")
    print({v: len(r) for v, r in per_verdetto.items()})


if __name__ == "__main__":
    main()
