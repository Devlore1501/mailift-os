#!/usr/bin/env python3
"""
restructure_landing.py — riordina la landing Mailift secondo la sequenza che
funziona sulle landing dei competitor piu' avanzati (rif. wellcopy.net), e
aggiunge le due sezioni che oggi mancano.

Quarto passo della catena:
    python tools/optimize_landing_speed.py in.html a.html
    python tools/optimize_landing_seo.py   a.html  b.html
    python tools/embed_ghl_form.py         b.html  c.html
    python tools/restructure_landing.py    c.html  finale.html --report

── PERCHE' ─────────────────────────────────────────────────────────────────
La pagina attuale mette TRE sezioni di problema di fila (problema, costo
dell'inazione, perche' non funziona) prima di mostrare un singolo dato. I
risultati arrivano in nona posizione: chi scrolla veloce vede solo diagnosi.

La sequenza dei competitor che convertono e' l'opposto: prova PRIMA del
processo. Ti convinco che funziona, poi ti spiego come.

Questo script fa quattro cose, tutte reversibili:

  1. SPOSTA #risultati dalla 9a alla 5a posizione (subito dopo il problema).
  2. SPOSTA "perche' spesso non funziona" accanto a "le obiezioni corrette":
     sono entrambe gestione obiezioni, stavano separate da quattro sezioni.
  3. INSERISCE "Cosa ricevi, in concreto" dopo il sistema a 5 fasi. Deliverable
     CONTABILI invece che benefici: e' la sezione che chiude piu' contratti e
     oggi non esiste. I contenuti sono derivati da quello che la pagina gia'
     dichiara (i 9 flussi sono elencati uno per uno nella fase 03), non
     inventati.
  4. AGGIUNGE una fascia temporale a ciascuna delle 5 fasi. Un processo con
     delle date sembra un sistema; senza date sembra una lista di buoni
     propositi.

── COSA NON FA, DI PROPOSITO ───────────────────────────────────────────────
La riga di loghi clienti resta COMMENTATA nell'HTML. Serve la conferma di
Lorenzo che i loghi dei one-shot (Kalishoes, Partylandia, Treemme, Symposium)
siano usabili in pagina: pubblicare il marchio di un cliente senza il suo ok
e' un problema legale, non estetico. Il markup e' pronto, va solo scommentato.

Allo stesso modo NON inventa numeri che non conosco (quante campagne al mese,
ogni quanto arriva il report): dove manca il dato c'e' un commento HTML che
dice cosa aggiungere. Se la pagina viene pubblicata cosi' com'e' resta vera,
solo meno specifica di quanto potrebbe essere.
"""

from __future__ import annotations

import argparse
import re
from collections import Counter
import sys
from pathlib import Path

# ── Spacchettamento dei 90 giorni sulle 5 fasi ──────────────────────────────
# La pagina dichiara gia' "90 gg — orizzonte medio di costruzione e
# ottimizzazione iniziale" nella proof-bar. Come si distribuiscono sulle
# singole fasi e' una MIA proposta, non un dato che ho letto da qualche parte:
# se il tuo processo reale ha tempi diversi, correggi qui e rilancia.
#
# Abbreviate in "gg" per due motivi: la colonna del numero di fase e' stretta
# (56px) e "giorni 1-10" ci andava a capo, e soprattutto la proof-bar in cima
# alla pagina dice gia' "90 gg" — usare la stessa abbreviazione tiene la
# pagina coerente con se stessa.
TIMELINE = {
    "01": "gg 1-10",
    "02": "gg 10-25",
    "03": "gg 20-60",
    "04": "gg 30-90",
    "05": "in continuo",
}

# Ordine nuovo. Le chiavi sono derivate da id/classe/eyebrow di ogni sezione
# (vedi chiave_sezione). Se manca o avanza una chiave lo script si ferma.
ORDINE_NUOVO = [
    "hero",
    "proof-bar",
    "platform-strip",
    "problema",
    "costo-dell-inazione",
    "risultati",            # ← risaliva dalla 9a posizione
    "sistema",
    "@deliverable",         # ← nuova
    "lavoro",
    "baretta-founder",
    "perche-spesso-non-funziona",   # ← scendeva dalla 6a posizione
    "obiezioni-corrette",
    "qualificazione-trasparente",
    "audit",
    "faq",
    "final",
]

NUOVE = {"@deliverable"}


class PatchError(RuntimeError):
    pass


# ═══ SPLIT E CHIAVI ══════════════════════════════════════════════════════════

def chiave_sezione(markup: str) -> str:
    """Identificatore stabile per una sezione.

    Preferisce l'id (non cambia se ritocchi il copy), poi la classe
    strutturale, e solo come ultima risorsa uno slug dell'eyebrow.
    """
    m = re.search(r'\bid="([^"]+)"', markup[:400])
    if m:
        return m.group(1)

    for cls in ("hero", "proof-bar", "platform-strip", "final-section"):
        if re.search(rf'class="[^"]*\b{re.escape(cls)}\b', markup[:400]):
            return "final" if cls == "final-section" else cls

    m = re.search(r'class="eyebrow"[^>]*>(.*?)<', markup, re.S)
    if not m:
        raise PatchError(f"sezione senza id, classe nota o eyebrow: {markup[:150]!r}")

    testo = re.sub(r"\s+", " ", m.group(1)).strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", testo.replace("é", "e").replace("è", "e")
                  .replace("à", "a").replace("ò", "o").replace("ù", "u")).strip("-")
    # accorcia: "il-costo-dell-inazione" → "costo-dell-inazione"
    slug = re.sub(r"^(il|la|le|i|gli|lorenzo)-", "", slug)
    return "-".join(slug.split("-")[:4])


def estrai_sezioni(html: str) -> tuple[str, list[tuple[str, str]], str]:
    """Spezza <main> nelle sue sezioni di primo livello.

    Ho verificato che le <section> della pagina sono tutte piatte (profondita'
    massima 1), quindi uno split lineare e' sicuro. Se un giorno qualcuno
    annidasse una section dentro un'altra, il controllo qui sotto se ne
    accorge invece di produrre markup rotto.
    """
    prof = 0
    for tag in re.finditer(r"</?section\b", html):
        prof += 1 if tag.group(0) == "<section" else -1
        if prof > 1:
            raise PatchError("trovate <section> annidate: lo split non e' piu' sicuro")
        if prof < 0:
            raise PatchError("</section> senza apertura corrispondente")
    if prof != 0:
        raise PatchError("una <section> non e' stata chiusa")

    sezioni: list[tuple[str, str]] = []
    pos = 0
    prima = None
    while True:
        a = html.find("<section", pos)
        if a < 0:
            break
        b = html.find("</section>", a) + len("</section>")
        if prima is None:
            prima = a
        sezioni.append((chiave_sezione(html[a:b]), html[a:b]))
        pos = b

    if not sezioni:
        raise PatchError("nessuna <section> trovata")

    ultima_fine = html.rfind("</section>") + len("</section>")
    return html[:prima], sezioni, html[ultima_fine:]


# ═══ NUOVE SEZIONI ═══════════════════════════════════════════════════════════

def sezione_deliverable() -> str:
    """Deliverable contabili.

    Regola che mi sono dato: ogni voce qui sotto deve essere gia' affermata
    altrove nella pagina, oppure essere una conta di cose gia' elencate.
    I 9 flussi non sono un numero scelto a caso: sono esattamente i nove
    nominati nella fase 03 (welcome, browse, cart, checkout, post-purchase,
    cross-sell, replenishment, winback, VIP).
    """
    # NOTA sul markup delle voci: ogni <li> ha il contenuto avvolto in un
    # <span>. Non e' decorativo. La regola esistente e' `.fit-list li{display:
    # flex;gap:10px}` con la spunta come ::before, quindi ogni figlio diretto
    # del <li> diventa una colonna: mettendo <strong> nudo accanto al testo,
    # il grassetto finiva in una colonna e il resto della frase in un'altra,
    # spezzate da 10px di gap ("9 flussi automatici" | ": welcome, browse...").
    # Il <span> tiene tutto in un unico item flex e la frase torna continua.
    return """<section class="section">
  <div class="container">
    <div class="section-head reveal">
      <span class="eyebrow">Cosa ricevi, in concreto</span>
      <h2>Non &quot;ci occupiamo del tuo email marketing&quot;. Ecco l'elenco di quello che viene costruito e consegnato.</h2>
      <p class="lead">Le voci qui sotto sono deliverable, non obiettivi: o esistono nel tuo account o non esistono. Puoi verificarle una per una in qualsiasi momento del rapporto.</p>
    </div>

    <div class="fit-grid reveal">
      <div class="fit-card yes">
        <h3>Costruito una volta, resta tuo</h3>
        <ul class="fit-list">
          <li><span><strong>Revenue Audit iniziale</strong> su dati, tracking, segmenti, deliverability, flussi e campagne esistenti.</span></li>
          <li><span><strong>9 flussi automatici</strong>: welcome, browse abandonment, cart, checkout, post-purchase, cross-sell, replenishment, winback e VIP.</span></li>
          <li><span><strong>Segmentazione del database</strong> per comportamento, valore e ciclo di acquisto.</span></li>
          <li><span><strong>Setup della deliverability</strong>: autenticazione del dominio, pulizia della lista, gestione dei contatti inattivi.</span></li>
          <li><span><strong>Roadmap dei primi 90 giorni</strong> con priorità ordinate per impatto economico.</span></li>
        </ul>
      </div>
      <div class="fit-card yes">
        <h3>Ricorrente, ogni mese</h3>
        <ul class="fit-list">
          <li><span><strong>Calendario campagne</strong> costruito sul comportamento del database, non sul calendario delle festività.</span></li>
          <li><span><strong>Scrittura, design e invio</strong> di ogni campagna: non ricevi un piano da eseguire, ricevi le email già online.</span></li>
          <li><span><strong>Test continui</strong> su oggetto, offerta, timing e segmento, uno alla volta per capire cosa ha spostato il dato.</span></li>
          <li><span><strong>Report con i numeri di Klaviyo</strong>, non con screenshot scelti: revenue attribuita, tasso di riacquisto, salute della lista.</span></li>
          <li><span><strong>Un interlocutore solo</strong>, che risponde del risultato e non solo dell'esecuzione.</span></li>
        </ul>
      </div>
    </div>

    <!-- ══ DA COMPLETARE, LORENZO ═══════════════════════════════════════════
         Le voci qui sopra sono tutte derivate da cose che la pagina gia'
         dichiara altrove, quindi sono vere cosi' come sono. Ma le tre piu'
         convincenti sono quelle che diventano un NUMERO, e quei numeri non li
         so. Sostituisci il testo dove serve:

           - "Calendario campagne"  →  quante campagne al mese garantisci?
             (es. "minimo 8 campagne al mese, in media 12")
           - "Report con i numeri"  →  con che frequenza arriva?
             (es. "report ogni lunedi'" / "revisione mensile in call")
           - manca del tutto un tempo di risposta: se rispondi entro 24h
             lavorative, e' un deliverable e va scritto.

         Il confronto e' impietoso: un competitor scrive "minimo 8 flow con
         40-60 email dentro, 3-4 campagne a settimana". Chi legge sa esattamente
         cosa compra. Finche' non metti i numeri, questa sezione vale meta'.
    ══════════════════════════════════════════════════════════════════════ -->
  </div>
</section>"""


def sezione_loghi_clienti() -> str:
    """Riga loghi clienti — CONSEGNATA COMMENTATA, di proposito.

    La pagina oggi mostra solo loghi di PIATTAFORME (Shopify, Klaviyo,
    Attentive...). Dicono su cosa sai lavorare, non chi si e' gia' fidato:
    sono due prove diverse e la seconda pesa molto di piu'.

    Resta commentata perche' non ho la conferma che i marchi dei clienti
    one-shot siano usabili in pagina. Va scommentata solo dopo il loro ok.
    """
    return """
    <!-- ══ RIGA LOGHI CLIENTI — SCOMMENTARE DOPO AVER CHIESTO IL PERMESSO ══
         Questa e' la prova che manca di piu' in tutta la pagina: oggi mostri
         solo i tool su cui lavori, non chi ti ha gia' scelto.

         PRIMA DI SCOMMENTARE:
           1. chiedi ai clienti l'ok a usare il marchio (basta una mail, ma
              serve: pubblicare un logo senza consenso e' un problema legale)
           2. carica i loghi nella media library di GHL, in PNG su fondo
              trasparente, altezza uniforme ~58px
           3. sostituisci gli URL qui sotto e i nomi negli alt

         Se qualcuno dice di no, togli solo la sua riga: bastano quattro loghi
         veri, non serve riempire.

    <p class="platform-label" style="margin-top:34px">Brand che hanno gia' scelto Mailift</p>
    <div class="platform-logos">
      <div class="platform-logo"><img decoding="async" width="140" height="58" alt="Bergamo Vini" loading="lazy" src="URL_LOGO_BERGAMO_VINI"/></div>
      <div class="platform-logo"><img decoding="async" width="140" height="58" alt="Le Rive" loading="lazy" src="URL_LOGO_LE_RIVE"/></div>
      <div class="platform-logo"><img decoding="async" width="140" height="58" alt="Kalishoes" loading="lazy" src="URL_LOGO_KALISHOES"/></div>
      <div class="platform-logo"><img decoding="async" width="140" height="58" alt="Partylandia" loading="lazy" src="URL_LOGO_PARTYLANDIA"/></div>
      <div class="platform-logo"><img decoding="async" width="140" height="58" alt="Treemme" loading="lazy" src="URL_LOGO_TREEMME"/></div>
      <div class="platform-logo"><img decoding="async" width="140" height="58" alt="Symposium" loading="lazy" src="URL_LOGO_SYMPOSIUM"/></div>
    </div>
    ══════════════════════════════════════════════════════════════════════ -->
"""


# ═══ MODIFICHE PUNTUALI ══════════════════════════════════════════════════════

CSS_TIMELINE = """
/* ─── TIMELINE SULLE FASI ───────────────────────────────────── */
/* Una fascia temporale accanto al numero della fase: un processo con delle
   date si legge come un sistema, senza date si legge come una lista di
   intenzioni. Il valore e' dichiarativo, non un impegno contrattuale: il
   testo della sezione lo inquadra gia' come orizzonte medio. */
.phase-when{
  display:block;margin-top:7px;
  font-size:.64rem;font-weight:600;letter-spacing:.03em;
  text-transform:uppercase;color:var(--muted);
  text-align:center;line-height:1.2;
  white-space:nowrap;   /* mai a capo: "gg 1-" / "10" era illeggibile */
}
.phase-card>.phase-slot{display:flex;flex-direction:column;align-items:center}
/* La prima colonna della griglia era 56px, tarata sul solo cerchio del numero.
   Con la fascia temporale sotto serve qualche pixel in piu', altrimenti il
   testo sborda o manda a capo. */
.phase-card{grid-template-columns:76px 1fr 1fr}
@media(max-width:760px){.phase-when{font-size:.58rem}}
"""


def aggiungi_timeline(html: str) -> tuple[str, int]:
    """Avvolge ogni .phase-num in un contenitore con sotto la fascia temporale."""
    fatte = 0

    def sostituisci(m: re.Match) -> str:
        nonlocal fatte
        numero = m.group(1)
        quando = TIMELINE.get(numero)
        if quando is None:
            return m.group(0)
        fatte += 1
        return (f'<div class="phase-slot">'
                f'<div class="phase-num">{numero}</div>'
                f'<span class="phase-when">{quando}</span>'
                f"</div>")

    html = re.sub(r'<div class="phase-num">(\d{2})</div>', sostituisci, html)
    return html, fatte


def inserisci_css(html: str) -> str:
    ancora = "\n/* ─── RESPONSIVE ─"
    if ancora not in html:
        raise PatchError("blocco RESPONSIVE non trovato: non so dove mettere il CSS")
    return html.replace(ancora, CSS_TIMELINE + ancora, 1)


# ═══ ORCHESTRAZIONE ══════════════════════════════════════════════════════════

def nodi_testo(html: str) -> list[str]:
    """I singoli nodi di testo, normalizzati, nell'ordine in cui compaiono.

    Serve per il controllo di non-perdita: riordinare sezioni e avvolgere
    elementi lascia i nodi intatti, cancellarne una no.
    """
    senza_commenti = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    senza_script = re.sub(r"<(script|style)\b.*?</\1>", "", senza_commenti, flags=re.S | re.I)
    pezzi = re.split(r"<[^>]+>", senza_script)
    return [t for t in (re.sub(r"\s+", " ", p).strip() for p in pezzi) if t]


def solo_testo(html: str) -> str:
    """Testo visibile al lettore: via i commenti PRIMA dei tag.

    L'ordine conta. I commenti che questo script aggiunge contengono markup di
    esempio, quindi togliendo prima i tag resterebbero dentro dei frammenti di
    testo che gonfierebbero il conteggio e farebbero passare per buono un
    riordino che ha invece perso del contenuto vero.
    """
    senza_commenti = re.sub(r"<!--.*?-->", " ", html, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", senza_commenti)).strip()


def patch(html: str) -> tuple[str, list[str]]:
    log: list[str] = []
    testo_prima = len(solo_testo(html))

    testa, sezioni, coda = estrai_sezioni(html)
    trovate = [k for k, _ in sezioni]
    log.append(f"sezioni trovate: {len(sezioni)} → {', '.join(trovate)}")

    attese = [k for k in ORDINE_NUOVO if k not in NUOVE]
    mancanti = set(attese) - set(trovate)
    avanzate = set(trovate) - set(attese)
    if mancanti:
        raise PatchError(f"sezioni attese ma non trovate: {sorted(mancanti)}\n"
                         f"  trovate invece: {trovate}")
    if avanzate:
        raise PatchError(f"sezioni in pagina che l'ordine nuovo non prevede: {sorted(avanzate)}.\n"
                         "  Aggiungile a ORDINE_NUOVO, altrimenti sparirebbero dalla pagina.")
    if len(trovate) != len(set(trovate)):
        raise PatchError("due sezioni hanno la stessa chiave: il riordino sarebbe ambiguo")

    mappa = dict(sezioni)
    posizione_prima = {k: i for i, k in enumerate(trovate)}

    pezzi = []
    for i, chiave in enumerate(ORDINE_NUOVO):
        if chiave == "@deliverable":
            pezzi.append(sezione_deliverable())
            log.append(f"NUOVA sezione 'Cosa ricevi, in concreto' inserita in posizione {i + 1}")
        else:
            pezzi.append(mappa[chiave])
            vecchia = posizione_prima[chiave]
            if vecchia != i:
                log.append(f"spostata '{chiave}': posizione {vecchia + 1} → {i + 1}")

    nuovo = testa + "\n\n".join(pezzi) + coda

    # loghi clienti, commentati, in coda alla platform-strip
    ancora_loghi = "</div>\n  </div>\n</section>"
    idx = nuovo.find('class="platform-logos"')
    if idx < 0:
        raise PatchError("platform-logos non trovata: non so dove agganciare i loghi clienti")
    fine_strip = nuovo.find("</section>", idx)
    chiusura = nuovo.rfind("</div>", idx, fine_strip)
    nuovo = nuovo[:chiusura] + sezione_loghi_clienti() + nuovo[chiusura:]
    log.append("riga loghi clienti aggiunta COMMENTATA (serve il permesso dei clienti)")

    nuovo = inserisci_css(nuovo)
    nuovo, n_fasi = aggiungi_timeline(nuovo)
    if n_fasi != len(TIMELINE):
        raise PatchError(f"timeline applicata a {n_fasi} fasi invece di {len(TIMELINE)}: "
                         "il markup delle fasi e' cambiato")
    log.append(f"timeline aggiunta a tutte e {n_fasi} le fasi")

    # ── Verifiche ───────────────────────────────────────────────────────────
    testo_dopo = len(solo_testo(nuovo))
    if testo_dopo < testo_prima:
        raise PatchError(f"il testo visibile e' DIMINUITO ({testo_prima} → {testo_dopo} caratteri): "
                         "il riordino ha perso del contenuto")

    # Controllo di non-perdita, a livello di NODI DI TESTO.
    #
    # Non basta cercare il markup di ogni sezione dentro il nuovo file: due
    # sezioni vengono modificate di proposito (platform-strip riceve il blocco
    # loghi commentato, sistema riceve le fasce temporali infilate tra il
    # numero della fase e il titolo). E non basta nemmeno cercare il testo
    # come stringa contigua, per lo stesso motivo: inserire un elemento in
    # mezzo spezza la contiguita' senza perdere niente.
    #
    # L'invariante giusto e' che ogni nodo di testo presente prima sia ancora
    # presente dopo, almeno lo stesso numero di volte. Riordinare e avvolgere
    # elementi non tocca i nodi; cancellare per sbaglio una sezione si', e
    # verrebbe intercettato qui.
    prima_nodi = Counter(nodi_testo(html))
    dopo_nodi = Counter(nodi_testo(nuovo))
    persi = [(n, c - dopo_nodi[n]) for n, c in prima_nodi.items() if dopo_nodi[n] < c]
    if persi:
        n, quante = persi[0]
        raise PatchError(f"persi {len(persi)} nodi di testo nel riordino "
                         f"(es. {quante}× {n[:80]!r}). Nessuna sezione deve sparire.")
    log.append(f"verificato: {len(prima_nodi)} nodi di testo distinti, nessuno perso")
    if nuovo.count("<section") != len(ORDINE_NUOVO):
        raise PatchError(f"attese {len(ORDINE_NUOVO)} sezioni, nel file ce ne sono "
                         f"{nuovo.count('<section')}")
    log.append(f"verificato: tutte le {len(attese)} sezioni originali intatte, "
               f"testo {testo_prima} → {testo_dopo} caratteri")

    return nuovo, log


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
    print("OK   landing ristrutturata")
    if args.report:
        for riga in log:
            print(f"  - {riga}")
    print(f"\nScritto {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
