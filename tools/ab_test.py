#!/usr/bin/env python3
"""
A/B test onesto sulle creative del funnel calcolatore.

Il punto di questo tool NON è dichiarare un vincitore: è dire quando puoi
crederci. A volumi bassi la differenza fra due creative è quasi sempre rumore,
e chiamare "vincitore" il numero più alto è il modo più veloce per spegnere
la creative giusta.

Perché incrocia due fonti invece di leggere solo Meta:
  denominatore -> landing page view per annuncio, da Meta (le visite VERE:
                  i click sul link includono i tocchi accidentali che non
                  caricano mai la pagina)
  numeratore   -> contatti reali in GHL con quel nome annuncio (custom field
                  "Annuncio (nome)", scritto dal Worker)

Meta da solo conta gli eventi del pixel, non le persone: il 27/07/2026
mostrava 6 lead dove in GHL ce n'era 1 (view-through + pixel che sparava su
ogni pageview del quiz). GHL è la fonte di verità sulle persone.

CLI:
  python tools/ab_test.py                        # ultimi 14 giorni
  python tools/ab_test.py --giorni 30
  python tools/ab_test.py --dal 2026-07-01 --al 2026-07-27
  python tools/ab_test.py --lift 0.5             # lift che vuoi rilevare (50%)
"""
from __future__ import annotations

import argparse
import math
import os
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(Path.home() / ".secrets" / "mailift" / ".env")
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT / "tools"))

TOKEN = os.environ.get("FB_ACCESS_TOKEN", "")
BASE = "https://graph.facebook.com/v21.0"

# Account "ads 2" — quello del funnel calcolatore. Sovrascrivibile con --account.
ACCOUNT_DEFAULT = "act_2390793521074673"

TAG_OPTIN = "calcolatore-optin"
CAMPO_ANNUNCIO = "FFS9ENqoI2lDezkohCvt"   # "Annuncio (nome)"
CAMPO_FATTURATO = "bW87MPPTFNr51QBtNZmG"  # "Quale è il tuo attuale fatturato Mensile? 1"

# Fasce ICP Mailift. Devono restare identiche alle picklistOptions di GHL:
# un opt-in fuori ICP non è una conversione utile, e contarlo falsa il test.
ICP = {
    "25.000 – 50.000€/mese",
    "50.000 – 100.000€/mese",
    "100.000 – 300.000€/mese",
    "Oltre 300.000€/mese",
}

ALPHA = 0.05    # significatività
POWER = 0.80    # potenza statistica


# ─────────────────────────────  statistica  ─────────────────────────────

def _phi(x: float) -> float:
    """CDF della normale standard. Evita la dipendenza da scipy."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def z_due_proporzioni(succ_a: int, tot_a: int, succ_b: int, tot_b: int):
    """Test z a due code su due proporzioni. Ritorna (z, p_value) o None."""
    if tot_a <= 0 or tot_b <= 0:
        return None
    pa, pb = succ_a / tot_a, succ_b / tot_b
    pool = (succ_a + succ_b) / (tot_a + tot_b)
    if pool in (0.0, 1.0):
        return None                      # nessuna varianza: test non definito
    se = math.sqrt(pool * (1 - pool) * (1 / tot_a + 1 / tot_b))
    if se == 0:
        return None
    z = (pa - pb) / se
    return z, 2 * (1 - _phi(abs(z)))


def campione_necessario(p_base: float, lift_relativo: float) -> int | None:
    """Visite per braccio per rilevare un lift relativo su p_base.

    Serve a rispondere alla domanda vera: 'quanto devo aspettare prima che
    questo confronto voglia dire qualcosa?'
    """
    if p_base <= 0 or p_base >= 1:
        return None
    p2 = min(p_base * (1 + lift_relativo), 0.999999)
    if p2 <= p_base:
        return None
    z_a = 1.959963985                    # z per alpha .05 due code
    z_b = 0.841621234                    # z per potenza .80
    pm = (p_base + p2) / 2
    num = (z_a * math.sqrt(2 * pm * (1 - pm)) + z_b * math.sqrt(
        p_base * (1 - p_base) + p2 * (1 - p2))) ** 2
    return math.ceil(num / ((p2 - p_base) ** 2))


# ─────────────────────────────  sorgenti dati  ─────────────────────────────

def visite_per_annuncio(account: str, dal: str, al: str) -> dict[str, dict]:
    """Landing page view, click e spesa per annuncio, da Meta."""
    if not TOKEN:
        raise SystemExit("FB_ACCESS_TOKEN mancante: controlla .env")
    r = requests.get(
        f"{BASE}/{account}/insights",
        params={
            "level": "ad",
            "time_range": f"{{'since':'{dal}','until':'{al}'}}",
            "fields": "ad_name,spend,impressions,inline_link_clicks,actions",
            "limit": 500,
            "access_token": TOKEN,
        },
        timeout=60,
    )
    dati = r.json()
    if "error" in dati:
        raise SystemExit(f"Meta: {dati['error'].get('message')}")

    out: dict[str, dict] = {}
    for riga in dati.get("data", []):
        lpv = 0
        for a in riga.get("actions") or []:
            if a["action_type"] == "landing_page_view":
                lpv = int(float(a["value"]))
        nome = riga.get("ad_name", "?")
        acc = out.setdefault(nome, {"lpv": 0, "click": 0, "spesa": 0.0, "impr": 0})
        acc["lpv"] += lpv
        acc["click"] += int(riga.get("inline_link_clicks") or 0)
        acc["spesa"] += float(riga.get("spend") or 0)
        acc["impr"] += int(riga.get("impressions") or 0)
    return out


def optin_per_annuncio(dal: str, al: str) -> dict[str, dict]:
    """Opt-in REALI da GHL, raggruppati per nome annuncio."""
    import ghl_client as g

    contatti = g.search_contacts_by_tags([TAG_OPTIN], limit=1000)
    out: dict[str, dict] = defaultdict(lambda: {"optin": 0, "icp": 0})
    for c in contatti:
        quando = (c.get("dateAdded") or "")[:10]
        if not (dal <= quando <= al):
            continue
        annuncio, fatturato = "(senza annuncio)", ""
        for f in c.get("customFields") or []:
            if f.get("id") == CAMPO_ANNUNCIO:
                annuncio = (f.get("value") or f.get("fieldValue") or annuncio)
            elif f.get("id") == CAMPO_FATTURATO:
                fatturato = (f.get("value") or f.get("fieldValue") or "")
        out[annuncio]["optin"] += 1
        if fatturato in ICP:
            out[annuncio]["icp"] += 1
    return dict(out)


# ─────────────────────────────  report  ─────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="A/B test onesto sulle creative")
    ap.add_argument("--giorni", type=int, default=14)
    ap.add_argument("--dal")
    ap.add_argument("--al")
    ap.add_argument("--account", default=ACCOUNT_DEFAULT)
    ap.add_argument("--lift", type=float, default=0.5,
                    help="lift relativo che vuoi poter rilevare (0.5 = +50%%)")
    args = ap.parse_args()

    al = args.al or date.today().isoformat()
    dal = args.dal or (date.fromisoformat(al) - timedelta(days=args.giorni)).isoformat()

    meta = visite_per_annuncio(args.account, dal, al)
    ghl = optin_per_annuncio(dal, al)

    righe = []
    for nome, m in meta.items():
        g_ = ghl.get(nome, {"optin": 0, "icp": 0})
        lpv = m["lpv"]
        righe.append({
            "nome": nome, "lpv": lpv, "click": m["click"], "spesa": m["spesa"],
            "optin": g_["optin"], "icp": g_["icp"],
            "tasso": (g_["optin"] / lpv) if lpv else 0.0,
            "cpl": (m["spesa"] / g_["optin"]) if g_["optin"] else None,
        })
    righe.sort(key=lambda r: -r["lpv"])
    righe = [r for r in righe if r["lpv"] or r["optin"]]

    print(f"\nA/B CREATIVE · {dal} → {al} · {args.account}")
    print("=" * 86)
    if not righe:
        print("Nessun dato nel periodo.\n")
        return

    print(f"{'creative':26s} {'visite':>7s} {'optin':>6s} {'tasso':>7s} "
          f"{'in ICP':>7s} {'spesa':>8s} {'CPL reale':>10s}")
    print("-" * 86)
    for r in righe:
        cpl = f"€{r['cpl']:.2f}" if r["cpl"] else "—"
        print(f"{r['nome'][:26]:26s} {r['lpv']:7d} {r['optin']:6d} "
              f"{r['tasso']*100:6.1f}% {r['icp']:7d} €{r['spesa']:7.2f} {cpl:>10s}")

    tot_lpv = sum(r["lpv"] for r in righe)
    tot_opt = sum(r["optin"] for r in righe)
    tot_icp = sum(r["icp"] for r in righe)
    tot_spesa = sum(r["spesa"] for r in righe)
    print("-" * 86)
    cpl_tot = f"€{tot_spesa/tot_opt:.2f}" if tot_opt else "—"
    print(f"{'TOTALE':26s} {tot_lpv:7d} {tot_opt:6d} "
          f"{(tot_opt/tot_lpv*100) if tot_lpv else 0:6.1f}% {tot_icp:7d} "
          f"€{tot_spesa:7.2f} {cpl_tot:>10s}")

    # ── il confronto, con l'onestà davanti ──
    print("\nCONFRONTO")
    print("=" * 86)
    candidate = [r for r in righe if r["lpv"] >= 1]
    if len(candidate) < 2:
        print("Serve almeno due creative con traffico per confrontare.\n")
        return

    a, b = candidate[0], candidate[1]
    test = z_due_proporzioni(a["optin"], a["lpv"], b["optin"], b["lpv"])
    print(f"  A = {a['nome'][:30]}  {a['optin']}/{a['lpv']} = {a['tasso']*100:.1f}%")
    print(f"  B = {b['nome'][:30]}  {b['optin']}/{b['lpv']} = {b['tasso']*100:.1f}%")

    if test is None:
        print("\n  Non calcolabile: serve almeno una conversione per lato.")
    else:
        z, p = test
        print(f"\n  p-value = {p:.3f}", end="   ")
        print("SIGNIFICATIVO" if p < ALPHA else "NON significativo — la differenza è compatibile col caso")

    # quanto manca per poter concludere davvero
    p_base = (tot_opt / tot_lpv) if tot_lpv else 0.0
    n = campione_necessario(p_base, args.lift) if p_base > 0 else None
    print("\nQUANTO SERVE PER DECIDERE")
    print("-" * 86)
    if not n:
        print("  Zero conversioni nel periodo: nessun tasso da confrontare.")
        print("  Prima di testare le varianti serve almeno una conversione ricorrente.")
    else:
        giorni = max((date.fromisoformat(al) - date.fromisoformat(dal)).days, 1)
        # La proiezione va fatta sulla più debole delle DUE confrontate, non
        # sulla più debole in assoluto: una creative da 1 visita non c'entra
        # col confronto e sballerebbe la stima di mesi.
        peggiore = a if a["lpv"] <= b["lpv"] else b
        al_giorno = peggiore["lpv"] / giorni
        print(f"  Tasso base osservato:        {p_base*100:.2f}%")
        print(f"  Per rilevare un +{args.lift*100:.0f}% servono:  "
              f"{n:,} visite PER CREATIVE".replace(",", "."))
        print(f"  Ne ha la più debole del test ({peggiore['nome'][:22]}): {peggiore['lpv']}")
        if peggiore["lpv"] >= n:
            print("  → hai abbastanza dati: il test sopra è affidabile.")
        elif al_giorno > 0:
            attesa = math.ceil((n - peggiore["lpv"]) / al_giorno)
            print(f"  → mancano {n - peggiore['lpv']:,}".replace(",", ".")
                  + f" visite: ~{attesa} giorni a questo ritmo "
                    f"({al_giorno:.1f} visite/creative/giorno)")
            if attesa > 60:
                print("\n  ⚠ Oltre due mesi per un solo confronto. A questo volume l'A/B")
                print("    test non è lo strumento giusto: qualunque 'vincitore' letto")
                print("    prima è rumore. Meglio cambiare una cosa grossa alla volta")
                print("    e guardare la qualità dei lead (colonna 'in ICP'), non il tasso.")

    if tot_opt and not tot_icp:
        print("\n  ⚠ Nessun opt-in in ICP: il tasso di conversione è irrilevante finché")
        print("    converte il pubblico sbagliato. Guarda 'in ICP', non 'tasso'.")
    print()


if __name__ == "__main__":
    main()
