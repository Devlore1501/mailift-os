#!/usr/bin/env python3
"""
Simulatore di reazione alle creative (scroll-stop test).

Fratello di simula_visitatori.py, che testa la LANDING. Qui si testa il
momento prima: l'immagine dentro il feed, quando l'utente sta scorrendo e
decide in mezzo secondo se fermarsi.

⚠ Non predice CTR. Nessun modello sa quanti su cento si fermeranno. E' ricerca
qualitativa: serve a capire COSA comunica una creative e A CHI parla, non
quanto performera'.

La domanda giusta per Mailift non e' "quale ferma piu' gente" ma "quale ferma
la gente GIUSTA". Il 27/07/2026 la creative col CTR migliore (roas ltv, 4,29%)
aveva ZERO conversioni: fermava tutti tranne chi poteva comprare. Per questo
le persone sono meta' dentro e meta' fuori target, e il punteggio finale
premia lo scarto fra i due gruppi, non il totale.

Le persone sono le stesse di simula_visitatori.py: importate, non duplicate.
Se cambia l'avatar, cambia in un posto solo.

CLI:
  python tools/simula_creative.py "/percorso/cartella"
  python tools/simula_creative.py img1.png img2.png
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(Path.home() / ".secrets" / "mailift" / ".env")
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT / "tools"))

from simula_visitatori import PERSONE  # unica definizione degli avatar

MODELLO = os.environ.get("ANTHROPIC_MODEL") or "claude-sonnet-4-5"

SCHEMA = """Rispondi SOLO con JSON valido, nient'altro:
{"fermo_scroll": true|false,
 "cliccherei": true|false,
 "cosa_promette": "cosa offre secondo te, in una frase",
 "per_chi_e": "che tipo di persona pensi sia il destinatario",
 "reazione": "il tuo pensiero istintivo, con le tue parole",
 "cosa_non_va": "cosa ti frena o ti insospettisce, o null"}"""

MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".webp": "image/webp", ".gif": "image/gif"}


def tipo_reale(dati: bytes, suffisso: str) -> str:
    """Formato dai byte, non dall'estensione.

    Gli export dei tool di design finiscono spesso .png ma dentro sono WebP:
    l'API rifiuta il media_type sbagliato e l'intera esecuzione si ferma.
    """
    if dati.startswith(b"\x89PNG"):
        return "image/png"
    if dati.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if dati[:4] == b"RIFF" and dati[8:12] == b"WEBP":
        return "image/webp"
    if dati.startswith(b"GIF8"):
        return "image/gif"
    return MIME.get(suffisso.lower(), "image/png")


def chiedi(client, persona, img_b64, mime):
    sistema = (
        f"Sei {persona['nome']}, {persona['eta']} anni. {persona['profilo']}\n"
        "Stai scorrendo il feed di Instagram sul telefono, senza particolare "
        "attenzione. Questa immagine e' una sponsorizzata che ti passa davanti. "
        "Rispondi come faresti davvero: la maggior parte delle sponsorizzate si "
        "scorre via senza pensarci. Fermati solo se ti fermeresti sul serio."
    )
    r = client.messages.create(
        model=MODELLO, max_tokens=600, system=sistema,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": mime, "data": img_b64}},
            {"type": "text", "text": SCHEMA},
        ]}],
    )
    testo = r.content[0].text.strip()
    m = re.search(r"\{.*\}", testo, flags=re.S)
    if not m:
        return {"errore": testo[:160]}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError as e:
        return {"errore": str(e)}


SCHEMA_COPY = """Rispondi SOLO con JSON valido, nient'altro:
{"fermo_scroll": true|false,
 "cliccherei": true|false,
 "cosa_promette": "cosa offre secondo te, in una frase",
 "per_chi_e": "che tipo di persona pensi sia il destinatario",
 "reazione": "il tuo pensiero istintivo, con le tue parole",
 "cosa_non_va": "cosa ti frena o ti insospettisce, o null"}"""


def leggi_varianti(percorso: Path) -> list[dict]:
    """Estrae le varianti da un markdown con sezioni '### Variante N'."""
    testo = percorso.read_text(encoding="utf-8")
    fuori = []
    for blocco in re.split(r"^###\s+", testo, flags=re.M)[1:]:
        campo = lambda k: (re.search(rf"\*\*{k}:\*\*\s*(.+?)(?=\n\*\*|\Z)",
                                     blocco, flags=re.S) or [None, ""])[1].strip()
        fuori.append({
            "nome": blocco.splitlines()[0].strip(),
            "angle": campo("ANGLE"), "titolo": campo("TITOLO"),
            "prima_riga": campo("PRIMA RIGA"), "corpo": campo("CORPO"),
        })
    return [v for v in fuori if v["corpo"]]


def chiedi_copy(client, persona, v):
    sistema = (
        f"Sei {persona['nome']}, {persona['eta']} anni. {persona['profilo']}\n"
        "Stai scorrendo il feed di Instagram. Ti passa davanti una sponsorizzata: "
        "vedi il titolo e le prime righe, il resto e' nascosto dietro 'altro...'. "
        "Rispondi come faresti davvero: quasi tutte le sponsorizzate si scorrono via."
    )
    testo = (f"TITOLO: {v['titolo']}\n\n{v['corpo']}\n\n"
             "[link: calcolatore gratuito, 2 minuti]\n\n" + SCHEMA_COPY)
    r = client.messages.create(model=MODELLO, max_tokens=600, system=sistema,
                               messages=[{"role": "user", "content": testo}])
    m = re.search(r"\{.*\}", r.content[0].text.strip(), flags=re.S)
    if not m:
        return {"errore": "no json"}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError as e:
        return {"errore": str(e)}


def main() -> None:
    ap = argparse.ArgumentParser(description="Scroll-stop test su creative o copy")
    ap.add_argument("percorsi", nargs="+", help="immagini, cartella, o .md di copy")
    args = ap.parse_args()

    # modalita' testo: un markdown di varianti invece che immagini
    md = [Path(p) for p in args.percorsi if Path(p).suffix.lower() == ".md"]
    if md:
        return main_copy(md[0])

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY mancante")
    import anthropic

    files: list[Path] = []
    for p in args.percorsi:
        pp = Path(p)
        if pp.is_dir():
            files += sorted(x for x in pp.iterdir() if x.suffix.lower() in MIME)
        elif pp.suffix.lower() in MIME:
            files.append(pp)
    if not files:
        raise SystemExit("Nessuna immagine trovata.")

    client = anthropic.Anthropic()
    dentro = [p for p in PERSONE if p["in_target"]]
    fuori = [p for p in PERSONE if not p["in_target"]]

    print(f"\nSCROLL-STOP TEST · {len(files)} creative × {len(PERSONE)} persone · {MODELLO}")
    print("Non e' una previsione di CTR: sono reazioni ragionate, non statistica.")
    print("=" * 94)

    risultati = []
    for f in files:
        dati = f.read_bytes()
        b64 = base64.b64encode(dati).decode()
        mime = tipo_reale(dati, f.suffix)

        # Una persona che fallisce non deve far cadere l'intera esecuzione.
        def valuta(p):
            try:
                return (p, chiedi(client, p, b64, mime))
            except Exception as e:
                return (p, {"errore": str(e)[:160]})

        with ThreadPoolExecutor(max_workers=6) as ex:
            esiti = list(ex.map(valuta, PERSONE))

        d_stop = sum(1 for p, e in esiti if p["in_target"] and e.get("fermo_scroll"))
        f_stop = sum(1 for p, e in esiti if not p["in_target"] and e.get("fermo_scroll"))
        d_click = sum(1 for p, e in esiti if p["in_target"] and e.get("cliccherei"))
        f_click = sum(1 for p, e in esiti if not p["in_target"] and e.get("cliccherei"))
        # Il punteggio premia lo SCARTO: una creative che ferma tutti non seleziona.
        punteggio = d_click - f_click

        risultati.append(dict(file=f.name, d_stop=d_stop, f_stop=f_stop,
                              d_click=d_click, f_click=f_click, punteggio=punteggio,
                              esiti=esiti))

        print(f"\n┌─ {f.name}")
        print(f"│  IN TARGET    si ferma {d_stop}/{len(dentro)}   cliccherebbe {d_click}/{len(dentro)}")
        print(f"│  fuori target si ferma {f_stop}/{len(fuori)}   cliccherebbe {f_click}/{len(fuori)}")
        for p, e in esiti:
            if e.get("errore"):
                print(f"│   {p['nome']}: errore {e['errore'][:70]}")
                continue
            tag = "IN TGT" if p["in_target"] else "fuori "
            azione = "CLICCA" if e.get("cliccherei") else ("si ferma" if e.get("fermo_scroll") else "scorre via")
            print(f"│   [{tag}] {p['nome']:8s} {azione:10s} \"{(e.get('reazione') or '')[:88]}\"")
            if e.get("per_chi_e"):
                print(f"│            → pensa sia per: {e['per_chi_e'][:76]}")
            if e.get("cosa_non_va"):
                print(f"│            → lo frena:      {str(e['cosa_non_va'])[:76]}")
        print("└" + "─" * 92)

    print("\n" + "=" * 94)
    print("CLASSIFICA — per capacita' di SELEZIONARE, non di piacere")
    print("-" * 94)
    print(f"{'creative':38s} {'click in target':>16s} {'click fuori':>12s} {'scarto':>8s}")
    for r in sorted(risultati, key=lambda x: -x["punteggio"]):
        print(f"{r['file'][:38]:38s} {r['d_click']:>16d} {r['f_click']:>12d} {r['punteggio']:>+8d}")

    migliore = max(risultati, key=lambda x: x["punteggio"])
    print(f"\n  Miglior selezione: {migliore['file']}")
    if migliore["punteggio"] <= 0:
        print("  ⚠ Nessuna creative seleziona: attirano quanto o piu' il pubblico sbagliato.")
        print("    E' il problema misurato sui lead reali — nessun opt-in in ICP.")
    peggiore = min(risultati, key=lambda x: x["punteggio"])
    if peggiore["f_click"] > peggiore["d_click"]:
        print(f"  ⚠ {peggiore['file']}: attira piu' fuori target che in target.")
    print()


def main_copy(percorso: Path) -> None:
    """Stessa logica, ma sul TESTO dell'annuncio invece che sull'immagine."""
    import anthropic
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY mancante")
    varianti = leggi_varianti(percorso)
    if not varianti:
        raise SystemExit(f"Nessuna variante in {percorso} (attese sezioni '### Variante N')")

    client = anthropic.Anthropic()
    dentro = [p for p in PERSONE if p["in_target"]]
    fuori = [p for p in PERSONE if not p["in_target"]]

    print(f"\nTEST COPY · {len(varianti)} varianti × {len(PERSONE)} persone · {MODELLO}")
    print("Non e' una previsione di CTR: sono reazioni ragionate, non statistica.")
    print("=" * 94)

    risultati = []
    for v in varianti:
        def valuta(p):
            try:
                return (p, chiedi_copy(client, p, v))
            except Exception as e:
                return (p, {"errore": str(e)[:150]})

        with ThreadPoolExecutor(max_workers=6) as ex:
            esiti = list(ex.map(valuta, PERSONE))

        d_click = sum(1 for p, e in esiti if p["in_target"] and e.get("cliccherei"))
        f_click = sum(1 for p, e in esiti if not p["in_target"] and e.get("cliccherei"))
        d_stop = sum(1 for p, e in esiti if p["in_target"] and e.get("fermo_scroll"))
        risultati.append(dict(v=v, d_click=d_click, f_click=f_click, d_stop=d_stop,
                              punteggio=d_click - f_click, esiti=esiti))

        print(f"\n┌─ {v['nome']} · {v['angle']}")
        print(f"│  \"{v['titolo']}\"")
        print(f"│  IN TARGET    si ferma {d_stop}/{len(dentro)}   cliccherebbe {d_click}/{len(dentro)}")
        print(f"│  fuori target                cliccherebbe {f_click}/{len(fuori)}")
        for p, e in esiti:
            if e.get("errore"):
                print(f"│   {p['nome']}: errore {e['errore'][:60]}")
                continue
            tag = "IN TGT" if p["in_target"] else "fuori "
            az = "CLICCA" if e.get("cliccherei") else ("si ferma" if e.get("fermo_scroll") else "scorre via")
            print(f"│   [{tag}] {p['nome']:8s} {az:10s} \"{(e.get('reazione') or '')[:84]}\"")
            if e.get("cosa_non_va"):
                print(f"│            → lo frena: {str(e['cosa_non_va'])[:74]}")
        print("└" + "─" * 92)

    print("\n" + "=" * 94)
    print("CLASSIFICA — per capacita' di SELEZIONARE")
    print("-" * 94)
    print(f"{'variante':44s} {'in target':>10s} {'fuori':>7s} {'scarto':>8s}")
    for r in sorted(risultati, key=lambda x: -x["punteggio"]):
        et = f"{r['v']['nome']} · {r['v']['angle']}"
        print(f"{et[:44]:44s} {r['d_click']:>10d} {r['f_click']:>7d} {r['punteggio']:>+8d}")
    top = max(risultati, key=lambda x: x["punteggio"])
    print(f"\n  Migliore: {top['v']['nome']} — \"{top['v']['titolo']}\"")
    if top["punteggio"] <= 0:
        print("  ⚠ Nessuna variante seleziona: rivedere l'angle, non il copy.")
    print()


if __name__ == "__main__":
    main()
