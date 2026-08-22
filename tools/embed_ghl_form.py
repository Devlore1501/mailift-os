#!/usr/bin/env python3
"""
embed_ghl_form.py — sostituisce il form HTML della landing con l'embed del form
GoHighLevel, che e' l'unico che cattura davvero i lead.

Terzo passo della catena:
    python tools/optimize_landing_speed.py in.html a.html
    python tools/optimize_landing_seo.py   a.html  b.html
    python tools/embed_ghl_form.py         b.html  finale.html

Perche' serve: il form custom della landing aveva `data-endpoint=""` e nessun
handler funzionante (lo script inline era interrotto da un SyntaxError), quindi
chi lo compilava non mandava nulla a nessuno. Il form GHL e' ospitato da
GoHighLevel e scrive direttamente nel CRM.

Scelte di implementazione, tutte per non pagare in performance il form:

  - loading="lazy" sull'iframe. Il form sta in fondo alla pagina: senza lazy il
    browser scaricherebbe un intero documento da go.mailift.com durante il
    caricamento iniziale, dopo che abbiamo appena portato l'LCP sotto 1,3 s.
  - defer sullo script form_embed.js, per lo stesso motivo.
  - altezza riservata a data-height nel CSS. L'embed originale ha
    `style="height:100%"`, che in un contenitore senza altezza fa collassare
    l'iframe; e quando form_embed.js poi lo ridimensiona via postMessage, tutto
    cio' che sta sotto scivola. Riservando l'altezza in anticipo il layout shift
    e' zero.
  - niente preconnect a go.mailift.com: l'iframe e' lazy e sotto la piega,
    aprire la connessione al caricamento sarebbe sprecarla.

Rimuove anche il JS di validazione del vecchio form, che diventerebbe codice
morto con riferimenti a elementi non piu' esistenti.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

FORM_ID = "BWP9SIDtgeOQVmbAbmfA"
FORM_NAME = "LMF Consulenza 60 minuti funnel - Copy"
FORM_HEIGHT = 910
GHL_HOST = "https://go.mailift.com"


class PatchError(RuntimeError):
    pass


def blocco_iframe() -> str:
    return f"""      <div class="ghl-form">
        <iframe
          src="{GHL_HOST}/widget/form/{FORM_ID}"
          id="inline-{FORM_ID}"
          title="Richiedi il Revenue Audit gratuito"
          loading="lazy"
          data-layout="{{'id':'INLINE'}}"
          data-trigger-type="alwaysShow"
          data-trigger-value=""
          data-activation-type="alwaysActivated"
          data-activation-value=""
          data-deactivation-type="neverDeactivate"
          data-deactivation-value=""
          data-form-name="{FORM_NAME}"
          data-height="{FORM_HEIGHT}"
          data-layout-iframe-id="inline-{FORM_ID}"
          data-form-id="{FORM_ID}"></iframe>
      </div>"""


CSS_FORM = f"""
/* ─── FORM GHL (embed) ──────────────────────────────────────── */
/* L'altezza e' riservata in anticipo: form_embed.js ridimensiona l'iframe via
   postMessage dopo il caricamento, e senza altezza riservata tutto cio' che sta
   sotto slitterebbe. {FORM_HEIGHT}px e' il data-height dichiarato dall'embed.

   Lo sfondo chiaro NON e' una scelta estetica: il form su GoHighLevel dichiara
   background-color #FFFFFF e testo delle label nero, cioe' e' disegnato per
   stare su bianco. Incollato cosi' com'e' su questa pagina scura le label
   ("Nome completo", "La tua email", ...) risultavano nero su nero, illeggibili,
   e il contenuto dell'iframe non e' modificabile da qui perche' e' su un altro
   dominio.

   COME TORNARE AL FORM COMPLETAMENTE DARK: nel form builder di GoHighLevel
   metti il colore del testo delle label su bianco (#EEF2F8), poi qui sotto
   sostituisci le tre righe dello sfondo chiaro con  background:transparent;
   e togli il padding. */
.ghl-form{{
  min-height:{FORM_HEIGHT}px;
  background:#fff;
  border-radius:16px;
  padding:6px 10px;
}}
.ghl-form iframe{{
  display:block;width:100%;height:{FORM_HEIGHT}px;
  border:0;background:transparent;
}}
"""


def patch(html: str) -> tuple[str, list[str]]:
    log: list[str] = []

    # ── 1. Sostituzione del form ────────────────────────────────────────────
    inizio = html.find('<form id="auditForm"')
    if inizio < 0:
        raise PatchError("form #auditForm non trovato: e' gia' stato sostituito?")
    fine = html.find("</form>", inizio)
    if fine < 0:
        raise PatchError("chiusura </form> non trovata")
    fine += len("</form>")

    html = html[:inizio] + blocco_iframe().strip() + html[fine:]
    log.append("form custom sostituito con l'iframe GHL")

    # Il sottotitolo prometteva "Cinque campi": il form GHL ne ha sei piu' due
    # consensi. Lasciare il vecchio testo sarebbe una promessa non mantenuta
    # nel punto esatto in cui l'utente decide se compilare.
    vecchio_sub = '<p class="sub">Cinque campi. Nessun questionario infinito.</p>'
    if vecchio_sub in html:
        html = html.replace(
            vecchio_sub,
            '<p class="sub">Pochi campi, nessun questionario infinito.</p>',
        )
        log.append("sottotitolo: rimosso il conteggio dei campi, ora non corrisponde")

    # ── 2. CSS dell'embed, subito prima della chiusura dello style ──────────
    ancora_css = "\n/* ─── RESPONSIVE ─"
    if ancora_css not in html:
        raise PatchError("blocco RESPONSIVE non trovato: non so dove mettere il CSS")
    html = html.replace(ancora_css, CSS_FORM + ancora_css, 1)
    log.append("CSS dell'embed con altezza riservata (layout shift zero)")

    # ── 3. Script di GHL, defer, a fine body ───────────────────────────────
    if "<script src=" in html and "form_embed.js" in html.split("<style>")[-1].split("</style>")[-1]:
        raise PatchError("lo script form_embed.js risulta gia' presente")
    html = html.replace(
        "</body>",
        f'<script src="{GHL_HOST}/js/form_embed.js" defer></script>\n</body>',
        1,
    )
    log.append("form_embed.js aggiunto con defer a fine body")

    # ── 4. Rimozione del JS di validazione, ora codice morto ───────────────
    marcatore = "// ─── Form validation ──────────────────────────────────────────"
    if marcatore in html:
        inizio_js = html.index(marcatore)
        fine_js = html.index("</script>", inizio_js)
        html = (
            html[:inizio_js]
            + "// La validazione del vecchio form e' stata rimossa: il form ora e'\n"
              "// ospitato da GoHighLevel, che valida e salva i dati lato suo.\n"
            + html[fine_js:]
        )
        log.append("rimossa la validazione JS del vecchio form (codice morto)")

    # ── 5. Verifiche ────────────────────────────────────────────────────────
    for residuo in ("auditForm", "formStatus", "adspendError"):
        if residuo in html:
            raise PatchError(f"riferimento residuo al vecchio form: {residuo}")
    if html.count(f"inline-{FORM_ID}") != 2:
        raise PatchError("l'id dell'iframe deve comparire due volte (id + data-layout-iframe-id)")
    if 'loading="lazy"' not in blocco_iframe():
        raise PatchError("iframe senza loading=lazy")
    log.append("verificato: nessun riferimento residuo al vecchio form")

    return html, log


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    try:
        nuovo, log = patch(args.input.read_text(encoding="utf-8"))
    except PatchError as exc:
        print(f"FALLITO: {exc}\nNessun file scritto.", file=sys.stderr)
        return 1

    args.output.write_text(nuovo, encoding="utf-8")
    print("OK   form GHL integrato")
    if args.report:
        for riga in log:
            print(f"  - {riga}")
    print(f"\nScritto {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
