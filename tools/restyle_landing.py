#!/usr/bin/env python3
"""
restyle_landing.py — quinto passo della catena. Tre interventi visivi chiesti da
Lorenzo dopo aver rivisto la v3, piu' la pulizia della sezione founder.

    python tools/restructure_landing.py c.html d.html
    python tools/restyle_landing.py     d.html finale.html --report

── 1. MARQUEE DELLE CREATIVITA' ────────────────────────────────────────────
La griglia di 4 card viene sostituita da un nastro scorrevole, come sulla home
di mailift.com. Risolve due problemi in un colpo solo: l'effetto voluto, e le
3 immagini su 4 che erano rotte (404 all'origine). Le 8 creativita' qui sotto
sono quelle REALI gia' pubblicate su mailift.com, verificate una per una.

Differenza voluta rispetto alla home: li' l'animazione va da translateX(0) a
translateX(-100%) su una lista che contiene gia' il contenuto duplicato, quindi
nella seconda meta' del ciclo il nastro esce di scena e lascia un vuoto prima
di ripartire. Qui si ferma a -50%: a quel punto la copia 2 si trova esattamente
dove stava la copia 1 e il loop e' invisibile.

Le immagini originali pesano 1880x5728 px l'una. Passate dal resizer di GHL
(f_webp/q_72/r_360) scendono a 360x1096: a schermo sono alte 450px, cioe' larghe
~148px, quindi 360px di sorgente sono gia' oltre il doppio della densita'
necessaria su retina.

── 2. SEZIONE FOUNDER ──────────────────────────────────────────────────────
Via le 3 foto della gallery. Erano etichettate "Lorenzo Baretta durante
attivita' professionali 1/2/3" ma ritraggono persone diverse: chi legge se ne
accorge, e una prova che non regge indebolisce tutto quello che le sta intorno.
Resta il ritratto vero.

La citazione prende una firma. Una frase in prima persona senza nome sotto,
accanto a un volto, non si capisce di chi sia: e' la stessa quantita' di testo
che pero' non porta fiducia.

── 3. SFONDI ALTERNATI ─────────────────────────────────────────────────────
Tre sezioni passano a fondo chiaro. NON tutte a scacchiera: alternare a
ripetizione rende la pagina a strisce e non esalta piu' niente. Il chiaro qui
fa da riflettore su tre momenti, scelti perche' sono i tre punti in cui il
lettore deve fermarsi:

    risultati     — gli screenshot Klaviyo staccano molto meglio sul chiaro
    deliverable   — l'elenco di cosa ricevi, il punto piu' concreto
    audit (form)  — e qui c'e' un effetto collaterale utile: il form GHL e'
                    bianco per costruzione, e su fondo chiaro smette di
                    sembrare un rettangolo estraneo incollato sul buio

Il tema scuro definisce diversi colori di testo in modo fisso invece che con
le variabili (.fit-list, .founder-quote, .eyebrow, label...). Su fondo chiaro
diventerebbero illeggibili, quindi vengono riscritti uno per uno piu' sotto.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Le 8 creativita' pubblicate su mailift.com. Verificate: tutte rispondono 200
# e passano dal resizer di GHL.
BASE = "https://storage.googleapis.com/msgsndr/DCkx36MFJXMc24bUUG1G/media/"
CREATIVITA = [
    "675873233c18ec49cb02e88f.png",
    "67587323b96532b574193688.png",
    "67587323b5c0947c2151c297.png",
    "675873237a3acfa42abd1adb.png",
    "67587323b5c094090151c298.png",
    "67587323b5c094063251c299.png",
    "675873243c5cd52a27b06492.png",
    "6758732353bb950844ac15b7.png",
]
LARGHEZZA_SORGENTE = 360
ALTEZZA_SORGENTE = 1096   # 360 x (5728/1880), l'aspetto reale delle immagini

# Sezioni che passano a fondo chiaro, identificate come nel passo precedente.
SEZIONI_CHIARE = ("risultati", "@deliverable", "audit")


class PatchError(RuntimeError):
    pass


# ═══ 1. MARQUEE ══════════════════════════════════════════════════════════════

def blocco_marquee() -> str:
    def img(nome: str, copia: int) -> str:
        url = (f"https://images.leadconnectorhq.com/image/f_webp/q_72/"
               f"r_{LARGHEZZA_SORGENTE}/u_{BASE}{nome}")
        # La seconda copia esiste solo per chiudere il loop: nascosta agli
        # screen reader, che altrimenti leggerebbero due volte la stessa cosa.
        extra = ' aria-hidden="true"' if copia == 2 else ""
        alt = "" if copia == 2 else f"Creativita email realizzata da Mailift per un ecommerce"
        return (f'<img decoding="async" loading="lazy" '
                f'width="{LARGHEZZA_SORGENTE}" height="{ALTEZZA_SORGENTE}" '
                f'alt="{alt}"{extra} src="{url}"/>')

    copia1 = "\n          ".join(img(n, 1) for n in CREATIVITA)
    copia2 = "\n          ".join(img(n, 2) for n in CREATIVITA)
    return f"""<div class="marquee reveal" aria-label="Esempi di creativita email realizzate da Mailift">
        <div class="marquee-track">
          {copia1}
          {copia2}
        </div>
      </div>"""


CSS_MARQUEE = """
/* ─── MARQUEE CREATIVITÀ ────────────────────────────────────── */
.marquee{
  overflow:hidden;
  /* Sfuma ai bordi invece di tagliare di netto: senza, le immagini
     compaiono e spariscono con uno scatto sul bordo del contenitore. */
  -webkit-mask-image:linear-gradient(90deg,transparent,#000 5%,#000 95%,transparent);
          mask-image:linear-gradient(90deg,transparent,#000 5%,#000 95%,transparent);
}
.marquee-track{
  display:flex;width:max-content;
  animation:mailift-marquee 36s linear infinite;
}
/* Fermarlo al passaggio del mouse: sono screenshot di email, chi si ferma
   li sta leggendo. */
.marquee:hover .marquee-track{animation-play-state:paused}
.marquee img{
  flex:none;
  height:450px;width:auto;
  margin:0 10px;
  border-radius:14px;
  border:1px solid var(--border);
  background:var(--surface);
}
@keyframes mailift-marquee{
  from{transform:translateX(0)}
  /* -50% e non -100%: la lista contiene due copie identiche, quindi a meta'
     corsa la copia 2 e' esattamente dove stava la copia 1 e il salto non si
     vede. Con -100% il nastro esce tutto e lascia un buco. */
  to{transform:translateX(-50%)}
}
@media(max-width:760px){
  .marquee img{height:300px;margin:0 7px}
  .marquee-track{animation-duration:28s}
}
/* Chi ha chiesto meno animazioni al sistema operativo non se la merita
   addosso comunque: nastro fermo e scorrimento a dito. */
@media(prefers-reduced-motion:reduce){
  .marquee{overflow-x:auto;-webkit-mask-image:none;mask-image:none}
  .marquee-track{animation:none}
}
"""


def fine_div(html: str, inizio: int) -> int:
    """Indice subito dopo il </div> che chiude il <div> che inizia a `inizio`.

    Serve un contatore vero e non una regex: al primo tentativo avevo usato
    `.*?</div>\\s*</div>\\s*</div>` dando per scontato che le card fossero dei
    <div>, ma sono <figure>. Non trovando tre </div> di fila dentro la griglia,
    la regex tirava dritto e si mangiava anche la sezione founder che veniva
    dopo — con la gallery dentro, che il passo successivo non trovava piu'.
    """
    prof = 0
    for tag in re.finditer(r"<div\b|</div>", html[inizio:]):
        prof += 1 if tag.group(0) != "</div>" else -1
        if prof == 0:
            return inizio + tag.end()
    raise PatchError("<div> non chiuso: markup malformato")


def patch_marquee(html: str) -> tuple[str, str]:
    ancora = '<div class="work-grid reveal">'
    inizio = html.find(ancora)
    if inizio < 0:
        raise PatchError("blocco .work-grid non trovato nella sezione #lavoro")
    fine = fine_div(html, inizio)

    blocco = html[inizio:fine]
    quante = blocco.count('class="work-card"')
    if quante != 4:
        raise PatchError(f"attese 4 work-card, trovate {quante}: il markup e' cambiato")
    if "founder" in blocco:
        raise PatchError("il blocco selezionato sconfina nella sezione founder")

    html = html[:inizio] + blocco_marquee() + html[fine:]
    return html, f"4 work-card sostituite dal marquee con {len(CREATIVITA)} creativita' reali"


# ═══ 2. FOUNDER ══════════════════════════════════════════════════════════════

def patch_founder(html: str) -> tuple[str, list[str]]:
    log = []

    m = re.search(r'\s*<div class="founder-gallery".*?</div>', html, re.S)
    if not m:
        raise PatchError("blocco .founder-gallery non trovato")
    quante = m.group(0).count("<img")
    if quante != 3:
        raise PatchError(f"attese 3 foto nella gallery, trovate {quante}")
    html = html[:m.start()] + html[m.end():]
    log.append(f"rimosse le {quante} foto della gallery (ritraevano persone diverse)")

    # Firma sotto la citazione.
    fine_cit = '</blockquote>'
    if fine_cit not in html:
        raise PatchError("citazione del founder non trovata")
    html = html.replace(
        fine_cit,
        '<cite class="founder-cite">Lorenzo Baretta — founder, Mailift</cite></blockquote>',
        1,
    )
    log.append("aggiunta la firma sotto la citazione")
    return html, log


CSS_FOUNDER = """
/* ─── FIRMA DELLA CITAZIONE ─────────────────────────────────── */
.founder-cite{
  display:block;margin-top:14px;
  font-style:normal;font-size:.8rem;font-weight:600;
  letter-spacing:.02em;color:var(--muted);
}
"""


# ═══ 3. SEZIONI CHIARE ═══════════════════════════════════════════════════════

CSS_CHIARO = """
/* ─── SEZIONI A FONDO CHIARO ────────────────────────────────── */
/* Riflettore su tre momenti della pagina, non alternanza a scacchiera:
   risultati, deliverable e form. Il resto resta scuro.

   Prima le variabili: tutto quello che nel tema scuro le usa si adatta da
   solo (card, bordi, superfici). */
.section.light{
  --surface:#ffffff;
  --surface-2:#e8eff7;
  --border:rgba(11,26,44,.11);
  --border-2:rgba(11,26,44,.20);
  --text:#0b1a2c;
  --muted:#5a6c82;
  --soft:#33465e;
  --accent-glow:rgba(255,138,61,.16);
  background:#eff4fa;
  color:#0b1a2c;
  border-top:1px solid rgba(11,26,44,.08);
  border-bottom:1px solid rgba(11,26,44,.08);
}
/* Poi i colori che il tema scuro fissa a mano invece che con le variabili:
   su fondo chiaro resterebbero bianchi su bianco. */
.section.light h1,.section.light h2,.section.light h3,
.section.light h4,.section.light strong,
.section.light .stat-num,.section.light .badge-text strong{color:#0b1a2c}
.section.light p,.section.light li,.section.light .lead,
.section.light .fit-list li,.section.light label,
.section.light .result-body p,.section.light .dash-disclaimer,
.section.light .proof-disclaimer,.section.light small{color:#41566e}
.section.light .founder-quote{color:#1b2d43}
.section.light .eyebrow{
  color:#a24f0f;
  background:rgba(255,138,61,.10);
  border-color:rgba(255,138,61,.32);
}
/* Superfici semitrasparenti nate per stare sul buio: sul chiaro sparivano
   o creavano un velo grigiastro. */
.section.light .kpi,.section.light .phase-visual,
.section.light .dash-titlebar,.section.light .flow-row{
  background:rgba(11,26,44,.035);
}
.section.light .audit-step-num{background:rgba(255,138,61,.14);color:#a24f0f}
/* Due contenitori nascono neri per incorniciare contenuto chiaro sul tema
   scuro. Lasciati com'erano, sul fondo chiaro diventavano due buchi neri:
   .result-img e' la cornice degli screenshot Klaviyo (che sono bianchi, e
   con object-fit:contain lasciano vedere lo sfondo sopra e sotto), e
   .form-shell e' la scatola attorno al form. */
.section.light .result-img{
  background:#ffffff;
  border-bottom-color:rgba(11,26,44,.10);
}
.section.light .form-shell{
  background:#ffffff;
  border-color:rgba(11,26,44,.12);
}
.section.light input,.section.light select{
  background:#ffffff;color:#0b1a2c;
  border-color:rgba(11,26,44,.18);
}
/* Il pulsante primario e' arancione con testo scuro: funziona uguale sul
   chiaro, ma senza alone, che sul bianco diventa una macchia sporca. */
.section.light .btn{box-shadow:none}
.section.light .btn.ghost{
  border-color:rgba(11,26,44,.22);color:#0b1a2c;background:transparent;
}
.section.light .btn.ghost:hover{border-color:rgba(11,26,44,.4)}
"""


def patch_sezioni_chiare(html: str) -> tuple[str, list[str]]:
    """Aggiunge la classe .light alle sezioni scelte.

    Le sezioni sono riconosciute come nel passo precedente (id, oppure eyebrow
    per quelle che non ce l'hanno). Se una non si trova lo script si ferma:
    meglio nessun file che una pagina mezza ristilizzata.
    """
    log = []
    for chiave in SEZIONI_CHIARE:
        if chiave == "@deliverable":
            # La sezione nuova non ha id: la riconosco dall'eyebrow.
            m = re.search(r'<section class="section"(?=(?:(?!</section>).)*?'
                          r'Cosa ricevi, in concreto)', html, re.S)
            etichetta = "deliverable"
        else:
            m = re.search(rf'<section class="section(?: alt)?" id="{chiave}"', html)
            etichetta = chiave
        if not m:
            raise PatchError(f"sezione '{chiave}' non trovata: non posso schiarirla")

        vecchio = m.group(0)
        nuovo = vecchio.replace('class="section alt"', 'class="section light"') \
                       .replace('class="section"', 'class="section light"')
        if nuovo == vecchio:
            raise PatchError(f"non sono riuscito ad aggiungere .light a '{chiave}'")
        html = html[:m.start()] + nuovo + html[m.end():]
        log.append(f"sezione '{etichetta}' → fondo chiaro")
    return html, log


# ═══ ORCHESTRAZIONE ══════════════════════════════════════════════════════════

def inserisci_css(html: str, css: str) -> str:
    ancora = "\n/* ─── RESPONSIVE ─"
    if ancora not in html:
        raise PatchError("blocco RESPONSIVE non trovato: non so dove mettere il CSS")
    return html.replace(ancora, css + ancora, 1)


def patch(html: str) -> tuple[str, list[str]]:
    log: list[str] = []

    html, nota = patch_marquee(html)
    log.append(nota)

    html, l = patch_founder(html)
    log += l

    html, l = patch_sezioni_chiare(html)
    log += l

    html = inserisci_css(html, CSS_MARQUEE + CSS_FOUNDER + CSS_CHIARO)
    log.append("CSS di marquee, firma e sezioni chiare inserito")

    # ── Verifiche ───────────────────────────────────────────────────────────
    if html.count('class="work-card"'):
        raise PatchError("sono rimaste delle work-card: la sostituzione e' incompleta")
    # Cerco il MARKUP, non la stringa: ".founder-gallery" esiste ancora come
    # regola CSS (innocua, e la lascio nel caso la gallery torni con foto
    # vere) e faceva fallire il controllo a vuoto.
    if re.search(r'<div class="founder-gallery"', html):
        raise PatchError("la gallery del founder e' ancora presente nel markup")

    n_img = html.count('class="marquee-track"')
    if n_img != 1:
        raise PatchError(f"attesa 1 marquee-track, trovate {n_img}")
    attese = len(CREATIVITA) * 2
    trovate = len(re.findall(r'<img[^>]*storage\.googleapis\.com[^>]*>', html))
    if trovate != attese:
        raise PatchError(f"nel marquee servono {attese} immagini (8 x 2 copie), "
                         f"ne ho contate {trovate}")

    n_chiare = html.count('class="section light"')
    if n_chiare != len(SEZIONI_CHIARE):
        raise PatchError(f"attese {len(SEZIONI_CHIARE)} sezioni chiare, trovate {n_chiare}")

    aperte, chiuse = html.count("<section"), html.count("</section>")
    if aperte != chiuse:
        raise PatchError(f"sezioni sbilanciate dopo le modifiche: "
                         f"{aperte} aperture, {chiuse} chiusure")
    log.append(f"verificato: {trovate} immagini nel marquee, {n_chiare} sezioni chiare, "
               f"{aperte} sezioni bilanciate")

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
        print(f"FALLITO: {exc}\n\nNessun file scritto.", file=sys.stderr)
        return 1

    args.output.write_text(nuovo, encoding="utf-8")
    print("OK   restyle applicato")
    if args.report:
        for riga in log:
            print(f"  - {riga}")
    print(f"\nScritto {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
