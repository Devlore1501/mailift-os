#!/usr/bin/env python3
"""
Simulatore di visitatori per la landing.

⚠ COSA NON FA: non predice tassi di conversione. Nessun modello linguistico
sa quanti su cento cliccheranno. Chi lo promette vende fumo. I numeri che
stampa sono conteggi di personaggi simulati, non percentuali di mercato.

⚠ COSA FA: ricerca qualitativa automatizzata. Dà quello che a questo volume
di traffico non puoi comprare — decine di reazioni ragionate alla pagina, su
persone diverse, in due minuti invece che in 666 giorni di A/B test
(vedi tools/ab_test.py).

La domanda a cui risponde è quella giusta per Mailift: non "converte tanto?"
ma "converte CHI?". Il problema misurato il 27/07/2026 e' che il funnel
attrae store sotto i 15k invece dell'ICP 25k-300k. Le persone simulate sono
quindi metà dentro e metà fuori target: se la pagina piace a tutti, è rotta.

Due passaggi, perché li impone il comportamento reale (Clarity: tempo attivo
mediano 2s, scroll mediano 7%):
  1. COLPO D'OCCHIO — vede solo il fold, deve decidere se restare. Chi esce
     qui non vedra' mai il resto della pagina, per quanto sia buono.
  2. PAGINA INTERA — solo per chi e' rimasto: lascerebbe l'email? obiezioni?

CLI:
  python tools/simula_visitatori.py
  python tools/simula_visitatori.py --file landing/optin-calcolatore.html
  python tools/simula_visitatori.py --solo-fold        # piu' rapido/economico
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(Path.home() / ".secrets" / "mailift" / ".env")
load_dotenv(ROOT / ".env")

MODELLO = os.environ.get("ANTHROPIC_MODEL") or "claude-sonnet-4-5"
LANDING_DEFAULT = ROOT / "landing" / "optin-calcolatore.html"

# ── Le persone ──
# Fasce allineate alle picklistOptions del campo GHL e alle opzioni del quiz.
# `in_target` e' la verita' attesa: serve a misurare se la pagina SELEZIONA.
PERSONE = [
    dict(nome="Marco", eta=41, in_target=True, profilo=(
        "Founder di un eCommerce di abbigliamento, 60.000€/mese. Usa Klaviyo da due anni, "
        "ha i flow base attivi ma non li tocca da mesi. Spende 15k/mese in ads e il ROAS "
        "sta calando. Ha poco tempo, legge sul telefono tra una riunione e l'altra. "
        "Diffidente verso le agenzie: ne ha provate due e si e' trovato male.")),
    dict(nome="Silvia", eta=35, in_target=True, profilo=(
        "Titolare di un eCommerce beauty, 30.000€/mese. Sa che l'email rende poco ma non sa "
        "quantificare quanto perde. Curiosa, pragmatica, odia il linguaggio gonfiato. "
        "Ha gia' scaricato altri lead magnet e si e' pentita perche' l'hanno riempita di spam.")),
    dict(nome="Andrea", eta=48, in_target=True, profilo=(
        "CEO di un eCommerce food da 120.000€/mese, ha un marketing manager interno. "
        "Valuta fornitori con criterio, guarda le credenziali prima della promessa. "
        "Non si iscrive a nulla che sembri amatoriale: gli sembrerebbe di sprecare tempo.")),
    dict(nome="Luca", eta=29, in_target=False, profilo=(
        "Ha uno store di accessori che fattura 8.000€/mese, in difficolta'. Cerca soluzioni "
        "gratuite, e' iscritto a decine di newsletter di marketing, clicca spesso su cose "
        "che promettono di risolvere i suoi problemi. Non ha budget per un'agenzia.")),
    dict(nome="Giulia", eta=33, in_target=False, profilo=(
        "Store di gioielli artigianali, 12.000€/mese, in crescita. E' proprio nella fascia "
        "appena sotto il target. Vorrebbe crescere e valuta investimenti, ma oggi ogni spesa "
        "fissa la spaventa.")),
    dict(nome="Dario", eta=37, in_target=False, profilo=(
        "Ha una piccola agenzia di marketing con 6 clienti eCommerce. Guarda i materiali dei "
        "concorrenti per capire come si posizionano e per rubare idee di copy. "
        "Non comprerebbe mai, ma scarica volentieri.")),
]

SCHEMA_COLPO = """Rispondi SOLO con JSON valido, nient'altro:
{"resta": true|false,
 "cosa_ho_capito": "in una frase, cosa offre questa pagina secondo te",
 "e_per_me": true|false,
 "reazione": "la tua reazione istintiva in una frase, con le tue parole",
 "cosa_mi_ferma": "l'attrito principale, o null se nessuno"}"""

SCHEMA_PAGINA = """Rispondi SOLO con JSON valido, nient'altro:
{"lascia_email": true|false,
 "fiducia_1_5": 1-5,
 "obiezione_principale": "la cosa che piu' ti trattiene",
 "cosa_ha_convinto": "l'elemento piu' persuasivo, o null",
 "cosa_toglierei": "l'elemento piu' debole o fastidioso"}"""


def testo_da_html(html: str) -> tuple[str, str]:
    """Ritorna (fold, resto) come testo leggibile.

    Il fold e' la sezione .hero: e' cio' che il visitatore mediano vede nei
    suoi 2 secondi. Tutto il resto esiste solo per chi decide di scorrere.
    """
    corpo = html
    corpo = re.sub(r"<script.*?</script>", " ", corpo, flags=re.S | re.I)
    corpo = re.sub(r"<style.*?</style>", " ", corpo, flags=re.S | re.I)
    corpo = re.sub(r"<!--.*?-->", " ", corpo, flags=re.S)

    m = re.search(r'<section class="hero">(.*?)</section>', corpo, flags=re.S)
    fold_html = m.group(1) if m else ""
    resto_html = corpo.replace(fold_html, " ") if fold_html else corpo

    def pulisci(h: str) -> str:
        t = re.sub(r"<[^>]+>", "\n", h)
        t = (t.replace("&nbsp;", " ").replace("&amp;", "&")
              .replace("&egrave;", "è").replace("&#39;", "'"))
        righe = [r.strip() for r in t.splitlines()]
        return "\n".join(r for r in righe if r)

    return pulisci(fold_html), pulisci(resto_html)


def chiedi(client, sistema: str, utente: str) -> dict:
    r = client.messages.create(
        model=MODELLO, max_tokens=700, system=sistema,
        messages=[{"role": "user", "content": utente}],
    )
    testo = r.content[0].text.strip()
    m = re.search(r"\{.*\}", testo, flags=re.S)
    if not m:
        return {"errore": testo[:200]}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError as e:
        return {"errore": f"JSON non valido: {e}"}


def main() -> None:
    ap = argparse.ArgumentParser(description="Simula visitatori sulla landing")
    ap.add_argument("--file", default=str(LANDING_DEFAULT))
    ap.add_argument("--solo-fold", action="store_true",
                    help="ferma al colpo d'occhio: piu' rapido ed economico")
    args = ap.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY mancante in .env")
    try:
        import anthropic
    except ImportError:
        raise SystemExit("manca il pacchetto: pip install anthropic")

    html = Path(args.file).read_text(encoding="utf-8")
    fold, resto = testo_da_html(html)
    if not fold:
        raise SystemExit("Sezione .hero non trovata: il file ha una struttura diversa.")

    client = anthropic.Anthropic()
    print(f"\nSIMULAZIONE VISITATORI · {Path(args.file).name} · {MODELLO}")
    print("Non e' una previsione di conversione: sono reazioni ragionate, non statistica.")
    print("=" * 92)

    risultati = []
    for p in PERSONE:
        sistema = (
            f"Sei {p['nome']}, {p['eta']} anni. {p['profilo']}\n"
            "Stai scorrendo Instagram sul telefono e tocchi un'inserzione. "
            "Rispondi come rispondresti davvero tu, non come pensi si debba rispondere. "
            "Sii severo: se qualcosa non ti convince, dillo. Usa il tuo linguaggio."
        )
        colpo = chiedi(client, sistema,
                       "Questa e' la PRIMA schermata. L'hai guardata due secondi, "
                       "non hai ancora scorso nulla.\n\n"
                       f"---\n{fold}\n---\n\n" + SCHEMA_COLPO)

        pagina = None
        if colpo.get("resta") and not args.solo_fold:
            pagina = chiedi(client, sistema,
                            "Hai deciso di continuare. Ecco il resto della pagina.\n\n"
                            f"---\n{resto[:9000]}\n---\n\n" + SCHEMA_PAGINA)

        risultati.append((p, colpo, pagina))

        tag = "IN TARGET" if p["in_target"] else "fuori target"
        resta = colpo.get("resta")
        print(f"\n{p['nome']} ({tag})  →  {'RESTA' if resta else 'ESCE SUBITO'}")
        if colpo.get("errore"):
            print(f"   errore modello: {colpo['errore']}")
            continue
        print(f'   ha capito: "{colpo.get("cosa_ho_capito","?")}"')
        print(f'   reazione:  "{colpo.get("reazione","?")}"')
        print(f"   la sente sua: {'si' if colpo.get('e_per_me') else 'NO'}")
        if colpo.get("cosa_mi_ferma"):
            print(f'   attrito:   {colpo["cosa_mi_ferma"]}')
        if pagina and not pagina.get("errore"):
            print(f"   → email: {'LA LASCIA' if pagina.get('lascia_email') else 'no'}"
                  f"  · fiducia {pagina.get('fiducia_1_5','?')}/5")
            print(f'     obiezione:  {pagina.get("obiezione_principale","?")}')
            if pagina.get("cosa_ha_convinto"):
                print(f'     convince:   {pagina["cosa_ha_convinto"]}')
            if pagina.get("cosa_toglierei"):
                print(f'     toglierei:  {pagina["cosa_toglierei"]}')

    # ── il verdetto che conta: seleziona o no? ──
    print("\n" + "=" * 92)
    print("SELEZIONE — la pagina attrae chi deve?")
    print("-" * 92)
    dentro = [r for r in risultati if r[0]["in_target"]]
    fuori = [r for r in risultati if not r[0]["in_target"]]
    d_resta = sum(1 for _, c, _ in dentro if c.get("resta"))
    f_resta = sum(1 for _, c, _ in fuori if c.get("resta"))
    print(f"  In target che restano:    {d_resta}/{len(dentro)}   (piu' alto e' meglio)")
    print(f"  Fuori target che restano: {f_resta}/{len(fuori)}   (piu' BASSO e' meglio)")

    if not args.solo_fold:
        d_mail = sum(1 for _, _, p in dentro if p and p.get("lascia_email"))
        f_mail = sum(1 for _, _, p in fuori if p and p.get("lascia_email"))
        print(f"  In target che lasciano l'email:    {d_mail}/{len(dentro)}")
        print(f"  Fuori target che lasciano l'email: {f_mail}/{len(fuori)}")
        if f_mail > d_mail:
            print("\n  ⚠ Converte piu' fuori target che in target: e' esattamente il")
            print("    problema misurato sui lead reali. Il filtro non sta filtrando.")
        elif f_mail == 0 and d_mail:
            print("\n  ✓ Attrae solo chi e' in target: e' il comportamento voluto.")
    print()


if __name__ == "__main__":
    main()
