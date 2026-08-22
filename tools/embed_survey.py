#!/usr/bin/env python3
"""Sostituisce il form GHL della landing con il questionario a piu' step.

Sesto anello della catena: speed -> seo -> form -> restructure -> restyle -> survey.

Cosa cambia rispetto a v4:
  1. l'iframe punta al survey W8hTZ3pjIZ33wvU03raf invece che al form
     BWP9SIDtgeOQVmbAbmfA;
  2. la sezione audit torna a fondo scuro, perche' il questionario adesso
     e' scuro anche lui (vedi landing/ghl-survey-mailift.css) e la scatola
     bianca non serve piu';
  3. l'altezza riservata scende da 910px a 210px, misurata sul PRIMO step.

Sull'altezza riservata: l'iframe e' loading="lazy", quindi si carica quando
l'utente ci arriva scrollando, e lo scroll non e' un input che esclude uno
shift dal calcolo del CLS. Percio' il valore riservato deve corrispondere
allo step che si vede al caricamento (il primo, ~198px con il CSS di
ghl-survey-mailift.css applicato), non allo step piu' alto: riservare i
545px del quinto step lascerebbe un buco scuro di 340px sotto il primo
campo. La crescita agli step successivi avviene invece dopo un clic su
"Avanti", quindi e' input-adiacente e non pesa sul CLS.

Corollario: il CSS del questionario va incollato su GoHighLevel PRIMA di
pubblicare questa pagina. Senza, GHL rende il primo step a 328px e in
cima alla sezione si vede un salto di ~130px (oltre al widget bianco).

Come ogni patcher di questa catena: se una sostituzione non trova il suo
bersaglio si ferma con un errore invece di scrivere un file a meta'.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

SURVEY_ID = "W8hTZ3pjIZ33wvU03raf"
SURVEY_URL = f"https://go.mailift.com/widget/survey/{SURVEY_ID}"

# Misurato sul questionario reale con il CSS di ghl-survey-mailift.css
# applicato: primo step ~198px (campo + footer + margini). 210 tiene un
# margine di sicurezza senza aprire un buco visibile.
ALTEZZA_RISERVATA = 210


class PatchError(RuntimeError):
    """Una sostituzione non ha trovato il suo bersaglio."""


def sostituisci_unico(html: str, pattern: str, nuovo: str, cosa: str, *, flags=0) -> str:
    """Sostituisce l'unica occorrenza di `pattern`, o solleva PatchError."""
    trovati = list(re.finditer(pattern, html, flags))
    if len(trovati) != 1:
        raise PatchError(
            f"{cosa}: attese 1 occorrenza, trovate {len(trovati)}. "
            f"Il file di partenza non e' quello che questo tool si aspetta."
        )
    m = trovati[0]
    return html[: m.start()] + nuovo + html[m.end() :]


def nodi_testo(html: str) -> list[str]:
    """Testo visibile spezzato per nodo, usato come invariante di non-perdita."""
    senza_commenti = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    senza_script = re.sub(r"<(script|style)\b.*?</\1>", "", senza_commenti, flags=re.S | re.I)
    pezzi = re.split(r"<[^>]+>", senza_script)
    return [t for t in (re.sub(r"\s+", " ", p).strip() for p in pezzi) if t]


# ── 1. CSS del contenitore ────────────────────────────────────────────────
CSS_VECCHIO = re.compile(
    r"/\* ─── FORM GHL \(embed\) ─+ \*/.*?\.ghl-form iframe\{[^}]*\}",
    re.S,
)

CSS_NUOVO = f"""/* ─── QUESTIONARIO GHL (embed) ──────────────────────────────── */
/* Il widget e' un survey a 5 step, non un form unico: ogni step ha
   un'altezza diversa e form_embed.js ridimensiona l'iframe via postMessage
   a ogni passaggio.

   Qui si riserva l'altezza del PRIMO step ({ALTEZZA_RISERVATA}px), non del piu' alto.
   L'iframe e' lazy: si carica scrollando, e lo scroll non esclude uno shift
   dal CLS, quindi il valore riservato deve combaciare con cio' che appare al
   caricamento. Gli step successivi sono piu' alti (fino a ~545px per i sei
   scaglioni di fatturato) ma crescono dopo un clic su "Avanti", quindi il
   loro shift e' input-adiacente e non pesa sul punteggio.

   Niente sfondo bianco, a differenza del form precedente: il questionario
   e' vestito di scuro dal CSS in landing/ghl-survey-mailift.css, incollato
   nel modulo CSS avanzato del survey su GoHighLevel. Se quel CSS non e'
   attivo, il widget torna chiaro e qui si vedra' un rettangolo bianco. */
.ghl-form{{
  min-height:{ALTEZZA_RISERVATA}px;
  border-radius:16px;
}}
.ghl-form iframe{{
  display:block;width:100%;min-height:{ALTEZZA_RISERVATA}px;
  border:0;background:transparent;
}}"""

# ── 2. markup dell'iframe ─────────────────────────────────────────────────
IFRAME_VECCHIO = re.compile(r"<iframe\s+src=\"https://go\.mailift\.com/widget/form/.*?</iframe>", re.S)

IFRAME_NUOVO = f"""<iframe
          src="{SURVEY_URL}"
          id="{SURVEY_ID}"
          title="Questionario per richiedere il Revenue Audit gratuito"
          loading="lazy"
          scrolling="no"
          style="border:none;width:100%;"
          data-layout="{{'id':'INLINE'}}"
          data-trigger-type="alwaysShow"
          data-trigger-value=""
          data-activation-type="alwaysActivated"
          data-activation-value=""
          data-deactivation-type="neverDeactivate"
          data-deactivation-value=""
          data-form-name="Survey 4"
          data-height="{ALTEZZA_RISERVATA}"
          data-layout-iframe-id="inline-{SURVEY_ID}"
          data-form-id="{SURVEY_ID}"></iframe>"""


def applica(html: str) -> tuple[str, list[str]]:
    fatto: list[str] = []

    html = sostituisci_unico(html, CSS_VECCHIO.pattern, CSS_NUOVO, "blocco CSS del form", flags=re.S)
    fatto.append(f"CSS del contenitore riscritto (altezza riservata {ALTEZZA_RISERVATA}px, sfondo trasparente)")

    html = sostituisci_unico(html, IFRAME_VECCHIO.pattern, IFRAME_NUOVO, "iframe del form", flags=re.S)
    fatto.append(f"iframe puntato al survey {SURVEY_ID}")

    # La sezione audit torna scura: il widget non e' piu' bianco, quindi non
    # serve piu' il fondo chiaro che gli era stato messo attorno.
    html = sostituisci_unico(
        html,
        r'<section class="section light" id="audit">',
        '<section class="section" id="audit">',
        "sezione audit",
    )
    fatto.append("sezione audit riportata a fondo scuro (restano chiare risultati e deliverable)")

    # "Pochi campi" descriveva il form a schermata unica: adesso sono 5 step.
    html = sostituisci_unico(
        html,
        r'<p class="sub">Pochi campi, nessun questionario infinito\.</p>',
        '<p class="sub">5 domande brevi, una alla volta. Meno di un minuto.</p>',
        "sottotitolo del form",
    )
    fatto.append("sottotitolo aggiornato: descriveva un form a schermata unica")

    return html, fatto


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("sorgente", type=Path)
    ap.add_argument("destinazione", type=Path)
    args = ap.parse_args()

    html = args.sorgente.read_text(encoding="utf-8")
    prima = Counter(nodi_testo(html))

    try:
        nuovo, fatto = applica(html)
    except PatchError as e:
        print(f"KO   {e}", file=sys.stderr)
        return 1

    # Invariante: l'unico testo che puo' cambiare e' il sottotitolo.
    dopo = Counter(nodi_testo(nuovo))
    attesi_persi = {"Pochi campi, nessun questionario infinito."}
    persi = {n for n, c in prima.items() if dopo[n] < c} - attesi_persi
    if persi:
        print(f"KO   persi {len(persi)} nodi di testo non previsti: {list(persi)[:3]}", file=sys.stderr)
        return 1

    args.destinazione.write_text(nuovo, encoding="utf-8")

    # Verifiche sul risultato, non sulle intenzioni.
    controlli = [
        (f"/widget/survey/{SURVEY_ID}" in nuovo, "URL del survey presente"),
        ("/widget/form/BWP9SIDtgeOQVmbAbmfA" not in nuovo, "vecchio form rimosso"),
        (nuovo.count('class="section light"') == 2, "restano 2 sezioni chiare"),
        ('id="audit"' in nuovo and 'class="section" id="audit"' in nuovo, "audit scura"),
        ("go.mailift.com/js/form_embed.js" in nuovo, "script di embed ancora presente"),
        (f"min-height:{ALTEZZA_RISERVATA}px" in nuovo, "altezza riservata applicata"),
    ]
    ko = [nome for ok, nome in controlli if not ok]

    print("OK   questionario incorporato")
    for riga in fatto:
        print(f"  - {riga}")
    for ok, nome in controlli:
        print(f"  {'✓' if ok else '✗'} {nome}")
    print(f"  → {args.destinazione}  ({args.destinazione.stat().st_size / 1024:.1f} KB)")
    return 1 if ko else 0


if __name__ == "__main__":
    raise SystemExit(main())
