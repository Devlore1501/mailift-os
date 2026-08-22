#!/usr/bin/env python3
"""Genera i messaggi outreach personalizzati per i lead scorati.

Legge i template dai code block di `outreach/script-entry-offer.md` (unica fonte
di verita' della copy: si modifica li', non qui) e li compila con i dati di
`.tmp/leads_scored.csv`, scegliendo la sequenza in base al segmento del lead.

Uso:
    python tools/gen_outreach_messages.py [--top 30] [--out outreach/messaggi-top30.md]

Placeholder che restano non risolti (per scelta): {{nome}}. Il CSV MyLeadFox
espone quasi solo caselle di ruolo (info@, ordini@): il nome del titolare va
arricchito a mano o con `tools/lead_research.py` prima dell'invio. Il tool
conta e segnala quanti messaggi partono senza nome.
"""

import argparse
import csv
import os
import re
import sys

USD_EUR = 0.92
TASSO_ISCRIZIONE_BENCHMARK = 0.05  # popup a benchmark: 5% conservativo (range 6-8%)
QUOTA_EMAIL_ATTESA = 0.25  # estremo basso del benchmark 25-40%

PREFISSO_SEGMENTO = {"A - Klaviyo attivo": "A", "B - ESP generalista": "B", "C - Nessun ESP": "C"}


def leggi_template(path):
    """Estrae {codice: (oggetti, corpo)} dai blocchi ``` del documento copy."""
    testo = open(path, encoding="utf-8").read()
    blocchi = {}
    # ogni sequenza: "### A1 — Giorno 0" ... eventuali "**Oggetto...:** x" ... ```corpo```
    for m in re.finditer(
        r"^### ([ABC][1-4]) —.*?$(.*?)```\n(.*?)```",
        testo,
        re.S | re.M,
    ):
        codice, mezzo, corpo = m.group(1), m.group(2), m.group(3)
        oggetti = re.findall(r"\*\*Oggetto[^:]*:\*\*\s*(.+)", mezzo)
        blocchi[codice] = ([o.strip() for o in oggetti], corpo.rstrip())
    return blocchi


def num(s):
    s = re.sub(r"[^0-9.]", "", (s or "").replace(",", ""))
    try:
        return float(s)
    except ValueError:
        return 0.0


def eur(v):
    """Formatta arrotondando al migliaio: una stima non merita le unita'."""
    if v >= 1000:
        return f"{v/1000:.0f}k€"
    return f"{v:.0f}€"


def brand(nome, sito):
    """Normalizza i nomi urlati del CSV (ORIZZONTESHOP.IT) senza toccare gli acronimi."""
    n = (nome or "").strip() or sito
    if n.isupper() and len(n) > 4:
        n = n.title()
    return n


def mille(v):
    return f"{int(v):,}".replace(",", ".")


def valori(row):
    visite = num(row["Est Monthly Visits"])
    fatt = num(row["Est. Monthly Sales"]) * USD_EUR
    attacco = row.get("punto_attacco", "")

    esp = "il vostro ESP"
    m = re.search(r"^(\w[\w ]*?) su un eCommerce", attacco)
    if m:
        esp = m.group(1).strip()

    pixel = "pixel pubblicitari"
    m = re.search(r"pixel attivi: ([^·]+)", attacco)
    if m:
        elenco = [p.strip() for p in m.group(1).split(",")]
        pixel = (
            " e ".join(elenco) if len(elenco) <= 2
            else ", ".join(elenco[:-1]) + " e " + elenco[-1]
        )
        pixel = f"i pixel di {pixel}"

    return {
        "nome": "{{nome}}",  # da arricchire prima dell'invio
        "brand": brand(row["Name"], row["Website"]),
        "sito": row["Website"],
        "visite": mille(visite),
        "fatturato": eur(fatt),
        "revenue_email_attesa": eur(fatt * QUOTA_EMAIL_ATTESA),
        "iscritti_benchmark": mille(visite * TASSO_ISCRIZIONE_BENCHMARK),
        "esp": esp,
        "pixel": pixel,
        "osservazione_specifica": attacco.split(" · ")[0],
    }


def compila(testo, v):
    for k, val in v.items():
        testo = testo.replace("{{" + k + "}}", str(val))
    return testo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=".tmp/leads_scored.csv")
    ap.add_argument("--copy", default="outreach/script-entry-offer.md")
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    tpl = leggi_template(args.copy)
    attesi = {f"{s}{i}" for s in "ABC" for i in range(1, 5)}
    mancanti = attesi - set(tpl)
    if mancanti:
        print(f"ATTENZIONE: template mancanti nel doc copy: {sorted(mancanti)}", file=sys.stderr)

    with open(args.csv, encoding="utf-8") as f:
        leads = list(csv.DictReader(f))[: args.top]

    out = args.out or f"outreach/messaggi-top{args.top}.md"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    senza_nome = 0

    with open(out, "w", encoding="utf-8") as f:
        f.write(f"# Messaggi pronti — Top {args.top}\n\n")
        f.write("Generato da `tools/gen_outreach_messages.py`. "
                "La copy si modifica in `outreach/script-entry-offer.md`, non qui.\n\n")
        f.write("> **Prima di inviare**: sostituire `{{nome}}` col nome reale del titolare "
                "e verificare che le stime citate siano plausibili sul sito.\n\n---\n\n")

        for i, r in enumerate(leads, 1):
            v = valori(r)
            if "{{nome}}" in v["nome"]:
                senza_nome += 1
            pref = PREFISSO_SEGMENTO.get(r["segmento"])
            f.write(f"## {i}. {v['brand']} — {r['Website']}\n\n")
            f.write(f"**Segmento**: {r['segmento']} · **Score**: {r['score']} · "
                    f"**Email**: {r['Email'] or '—'} · **Tel**: {r['Phone Number'] or '—'}\n\n")
            if r.get("warning"):
                f.write(f"> ⚠ {r['warning']}\n\n")
            for step in range(1, 5):
                codice = f"{pref}{step}"
                if codice not in tpl:
                    continue
                oggetti, corpo = tpl[codice]
                giorno = {1: "Giorno 0", 2: "Giorno 3", 3: "Giorno 7", 4: "Giorno 12"}[step]
                f.write(f"### {codice} — {giorno}\n\n")
                for o in oggetti:
                    f.write(f"**Oggetto**: {compila(o, v)}\n\n")
                f.write("```\n" + compila(corpo, v) + "\n```\n\n")
            f.write("---\n\n")

    print(f"OK — {len(leads)} lead, messaggi in {out}")
    if senza_nome:
        print(f"⚠ {senza_nome}/{len(leads)} messaggi hanno ancora il placeholder "
              f"{{{{nome}}}} da compilare a mano prima dell'invio.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
