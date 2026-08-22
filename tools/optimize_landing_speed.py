#!/usr/bin/env python3
"""
optimize_landing_speed.py — ottimizzazioni performance deterministiche per la
landing Mailift (mailift_landing_v2.html / custom code GHL).

Ogni patch e' esplicita e verificata: se un pattern non viene trovato lo script
FALLISCE invece di produrre silenziosamente un output incompleto. Questo permette
di rilanciarlo su un nuovo export della landing e accorgersi subito se il markup
e' cambiato.

Uso:
    python tools/optimize_landing_speed.py <input.html> <output.html>
    python tools/optimize_landing_speed.py <input.html> <output.html> --report

Cosa fa (in ordine di impatto misurato su Lighthouse mobile):

 1. FONT — elimina il <link rel=stylesheet> a fonts.googleapis.com, che e'
    render-blocking (836 ms misurati). Inter e' un font VARIABILE: un solo file
    woff2 (subset latin, 47 KB) copre tutti i pesi 300-900. Lo dichiariamo
    inline con @font-face + <link rel=preload>, cosi' il download parte al primo
    byte dell'HTML invece che dopo due round-trip su fonts.googleapis.com.

 2. IMMAGINI — i 4 screenshot "creativita'" pesavano 13,6 MB DI PNG CIASCUNO
    (54 MB totali) serviti raw da storage.googleapis.com. Passano dal CDN
    GoHighLevel in webp ridimensionato. Anche loghi piattaforma e dashboard
    vengono ridimensionati alla dimensione realmente renderizzata.

 3. PAINT — rimuove la texture noise SVG feTurbulence a tutto viewport in
    position:fixed (rasterizzata e ripiastrellata a ogni scroll) e ancora il
    gradiente di sfondo al flusso del documento invece di fixed.

 4. COMPOSITING — togliere backdrop-filter:blur(20px) dalla nav sticky: forzava
    un passaggio di blur su tutta la larghezza a ogni frame di scroll.

 5. LAYOUT — content-visibility:auto sulle sezioni sotto la piega: il browser
    salta layout e paint di cio' che non e' a schermo (attacca gli 1,1 s di
    "Style & Layout" del main thread).

 6. JS — corregge gli apostrofi non escapati alle righe ~1645/1648 che
    generavano un SyntaxError e rendevano MORTO tutto lo script inline (form
    audit senza handler, sticky CTA mai visibile). Sostituisce anche il listener
    di scroll che chiamava getBoundingClientRect() a ogni evento con un
    IntersectionObserver.

Nota: il file di output va incollato nel blocco custom code della pagina GHL.
Questo script non fa deploy.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# ── Font: Inter variable, subset latin. Un solo file per tutti i pesi. ────────
INTER_LATIN_WOFF2 = (
    "https://fonts.gstatic.com/s/inter/v20/"
    "UcC73FwrK3iLTeHuS_nVMrMxCp50SjIa1ZL7W0Q5nw.woff2"
)
INTER_LATIN_RANGE = (
    "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,"
    "U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,"
    "U+2212,U+2215,U+FEFF,U+FFFD"
)

LC_CDN = "https://images.leadconnectorhq.com/image"
GHL_MEDIA = "https://storage.googleapis.com/msgsndr/DCkx36MFJXMc24bUUG1G/media"
FILESAFE = "https://assets.cdn.filesafe.space/us5X0gC74A4Hjpwvd83e/media"


class PatchError(RuntimeError):
    pass


class Patcher:
    """Applica sostituzioni verificate e tiene traccia di cosa ha cambiato."""

    def __init__(self, html: str):
        self.html = html
        self.log: list[str] = []

    def sub(self, label: str, old: str, new: str, *, count: int = 1) -> None:
        """Sostituzione letterale. Fallisce se le occorrenze non sono `count`."""
        found = self.html.count(old)
        if found != count:
            raise PatchError(
                f"[{label}] attese {count} occorrenze, trovate {found}.\n"
                f"  pattern: {old[:120]!r}"
            )
        self.html = self.html.replace(old, new)
        self.log.append(f"{label}: {count} sostituzione(i)")

    def re_sub(self, label: str, pattern: str, repl, *, expect: int) -> None:
        """Sostituzione regex. Fallisce se le occorrenze non sono `expect`."""
        new_html, n = re.subn(pattern, repl, self.html)
        if n != expect:
            raise PatchError(
                f"[{label}] attese {expect} occorrenze regex, trovate {n}.\n"
                f"  pattern: {pattern[:120]!r}"
            )
        self.html = new_html
        self.log.append(f"{label}: {n} sostituzione(i)")

    def require_absent(self, label: str, needle: str) -> None:
        if needle in self.html:
            raise PatchError(f"[{label}] '{needle}' ancora presente nell'output")
        self.log.append(f"{label}: verificato assente")


# ═══ 1. FONT NON BLOCCANTE ═══════════════════════════════════════════════════

def patch_fonts(p: Patcher, font_url: str = INTER_LATIN_WOFF2) -> None:
    """Sostituisce il CSS render-blocking di Google Fonts con preload + @font-face.

    font_url: da dove servire Inter. Il default e' fonts.gstatic.com. Se carichi
    il woff2 nella media library GoHighLevel e passi qui quell'URL, il font viene
    servito dallo stesso dominio: si risparmiano DNS + TLS + una connessione a
    terzi e l'LCP misurato scende da 2,08 s a 1,24 s.
    """
    same_origin = "fonts.gstatic.com" not in font_url
    crossorigin = "" if same_origin else " crossorigin"
    preconnect = (
        ""
        if same_origin
        else '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>\n'
    )
    origine = (
        "servito dallo stesso dominio della pagina"
        if same_origin
        else "servito da fonts.gstatic.com (terza parte)"
    )

    old = (
        '<link rel="preconnect" href="https://fonts.googleapis.com"/>\n'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>\n'
        '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet"/>'
    )
    new = (
        f'{preconnect}'
        f'<link rel="preload" as="font" type="font/woff2"{crossorigin} href="{font_url}"/>\n'
        '<style>\n'
        '/* Inter variable, subset latin: UN file copre tutti i pesi 300-900.\n'
        '   Prima erano 7 pesi richiesti via un <link rel=stylesheet> a\n'
        '   fonts.googleapis.com, che e\' render-blocking: 836 ms misurati prima\n'
        '   che il browser potesse dipingere qualsiasi cosa. Ora il @font-face e\'\n'
        '   inline e il preload sopra fa partire il download al primo byte.\n\n'
        f'   Il font e\' {origine}.\n'
        '   font-display:swap garantisce che Inter venga sempre applicato: il\n'
        '   testo appare subito nel font di sistema e passa a Inter appena e\'\n'
        '   pronto. Con il font sullo stesso dominio arriva prima del primo\n'
        '   paint, quindi lo scambio non si vede e non produce layout shift. */\n'
        '@font-face{\n'
        "  font-family:'Inter';\n"
        '  font-style:normal;\n'
        '  font-weight:300 900;\n'
        '  font-display:swap;\n'
        f'  src:url({font_url}) format("woff2");\n'
        f'  unicode-range:{INTER_LATIN_RANGE};\n'
        '}\n'
        '</style>'
    )
    p.sub("font: link render-blocking -> preload + @font-face", old, new)
    p.require_absent("font: nessun stylesheet remoto", 'fonts.googleapis.com/css2')


# ═══ 2. IMMAGINI ═════════════════════════════════════════════════════════════

def patch_images(p: Patcher) -> None:
    # 2a. Loghi piattaforma: PNG 1000x416 (33 KB) renderizzati a 58x24 CSS.
    #     Il CDN GoHighLevel rifiuta cdn.shopify.com (403), ma il CDN Shopify
    #     accetta ?width= e negozia webp via header Accept -> 2,8 KB.
    p.re_sub(
        "img: loghi piattaforma -> width=140 (33 KB -> 2,8 KB x6)",
        r'(src="https://cdn\.shopify\.com/s/files/1/0657/9431/0368/files/[^"]+?)"',
        lambda m: f'{m.group(1)}&width=140"',
        expect=6,
    )

    # 2b. Screenshot creativita': 13,6 MB di PNG raw ciascuno, renderizzati a
    #     138x173 CSS. Via CDN in webp r_300 -> 40 KB.
    p.re_sub(
        "img: creativita' -> CDN webp r_300 (13,6 MB -> 40 KB x4)",
        rf'src="{re.escape(GHL_MEDIA)}/([0-9a-f]+\.png)"',
        lambda m: f'src="{LC_CDN}/f_webp/q_70/r_300/u_{GHL_MEDIA}/{m.group(1)}"',
        expect=4,
    )

    # 2c. Dashboard risultati: r_1200 (20 KB) renderizzate a 292x164 -> r_620.
    p.re_sub(
        "img: dashboard risultati -> r_620 (20 KB -> 7 KB x7)",
        r'/image/f_webp/q_80/r_1200/u_(' + re.escape(FILESAFE) + r'/(?:906c797a|686c8ec2|d7469e67|88148d84|c3c60dcd|bd74bfac|41f2aa48)[^"]+)"',
        lambda m: f'/image/f_webp/q_75/r_620/u_{m.group(1)}"',
        expect=7,
    )

    # 2d. Ritratto founder: renderizzato a 318x398 -> r_700.
    p.re_sub(
        "img: ritratto founder -> r_700",
        r'/image/f_webp/q_80/r_1200/u_(' + re.escape(FILESAFE) + r'/69884cb10a7fd176fb22f7df\.png)"',
        lambda m: f'/image/f_webp/q_75/r_700/u_{m.group(1)}"',
        expect=1,
    )

    # 2e. Gallery founder: renderizzata a 192x192 -> r_420.
    p.re_sub(
        "img: gallery founder -> r_420 (x3)",
        r'/image/f_webp/q_80/r_1200/u_(' + re.escape(FILESAFE) + r'/(?:e874e377|9c4109cc|07df15ac)[^"]+)"',
        lambda m: f'/image/f_webp/q_75/r_420/u_{m.group(1)}"',
        expect=3,
    )

    # 2f. Tutte le <img> sono sotto la piega e hanno gia' loading="lazy".
    #     decoding="async" evita che il decode blocchi il main thread.
    #     width/height dichiarano il rapporto intrinseco: il CSS della pagina usa
    #     aspect-ratio, quindi i valori non alterano il layout (il CSS vince) ma
    #     tolgono a Lighthouse l'audit "unsized-images" e danno al browser il
    #     rapporto prima che l'immagine arrivi.
    dimensioni = {
        "platform-logo": (140, 58),      # naturale 1000x416
        "work-card": (300, 375),         # CSS aspect-ratio 4/5
        "result-img": (620, 349),        # CSS aspect-ratio 16/9
        "founder-portrait": (700, 875),  # contenitore 4/5
        "founder-gallery": (420, 420),   # CSS aspect-ratio 1
    }

    def dims_for(alt: str) -> tuple[int, int]:
        if "Dashboard" in alt:
            return dimensioni["result-img"]
        if "creativit" in alt:
            return dimensioni["work-card"]
        if "founder e strategist" in alt:
            return dimensioni["founder-portrait"]
        if "durante attivit" in alt:
            return dimensioni["founder-gallery"]
        return dimensioni["platform-logo"]

    def add_attrs(m: re.Match) -> str:
        alt = m.group(1)
        w, h = dims_for(alt)
        return f'<img decoding="async" width="{w}" height="{h}" alt="{alt}"'

    p.re_sub(
        "img: decoding=async + width/height su tutte le immagini",
        r'<img alt="([^"]*)"',
        add_attrs,
        expect=21,
    )

    # Nessun r_1200 residuo dentro un tag <img>. L'unico r_1200 che resta e'
    # quello di og:image, che deve rimanere grande: e' l'anteprima social e non
    # viene scaricata dal browser che apre la pagina.
    residui = [m.group(0) for m in re.finditer(r'<img[^>]*r_1200[^>]*>', p.html)]
    if residui:
        raise PatchError(f"[img] {len(residui)} <img> ancora a r_1200: {residui[0][:120]}")
    p.log.append("img: nessun <img> a r_1200 (og:image escluso di proposito)")


# ═══ 3. PAINT: noise texture + gradienti fixed ═══════════════════════════════

def patch_paint(p: Patcher) -> None:
    old_noise_start = '/* ─── NOISE TEXTURE ────────────────────────────────────────── */\nbody::before{'
    if old_noise_start not in p.html:
        raise PatchError("[paint] blocco NOISE TEXTURE non trovato")

    start = p.html.index(old_noise_start)
    end_marker = '/* ─── LAYOUT ───────────────────────────────────────────────── */'
    end = p.html.index(end_marker, start)
    old_block = p.html[start:end]

    new_block = (
        '/* ─── SFONDO ────────────────────────────────────────────────── */\n'
        '/* Era: body::before con una texture di rumore SVG a tutto viewport\n'
        '   in position:fixed (rasterizzata e ripiastrellata a ogni frame di\n'
        '   scroll) + body::after con due gradienti fixed. Il noise a opacita'
        "' 0,02\n"
        '   effettiva era invisibile e costava paint su ogni frame: rimosso.\n'
        '   I gradienti restano ma ancorati al flusso del documento (absolute,\n'
        '   altezza limitata) invece che fixed: si dipingono una volta sola. */\n'
        'body::after{\n'
        '  content:"";\n'
        '  position:absolute;\n'
        '  top:0;left:0;right:0;height:1600px;\n'
        '  pointer-events:none;\n'
        '  z-index:0;\n'
        '  background:\n'
        '    radial-gradient(ellipse 70% 50% at 90% 0%, rgba(255,138,61,.11) 0%, transparent 60%),\n'
        '    radial-gradient(ellipse 60% 50% at 10% 60%, rgba(51,100,255,.07) 0%, transparent 55%);\n'
        '}\n\n'
    )
    p.sub("paint: rimossa texture noise fixed, gradienti ancorati al flusso",
          old_block, new_block)

    # body::after e' ora absolute: serve un contenitore posizionato.
    p.sub(
        "paint: body position:relative (contenitore per il gradiente)",
        '  overflow-x:hidden;\n}',
        '  overflow-x:hidden;\n  position:relative;\n}',
    )
    p.require_absent("paint: nessun feTurbulence residuo", "feTurbulence")


# ═══ 4. COMPOSITING: backdrop-filter e animazione infinita ═══════════════════

def patch_compositing(p: Patcher) -> None:
    p.sub(
        "compositing: rimosso backdrop-filter dalla nav sticky",
        '  background:rgba(6,16,28,.82);\n'
        '  backdrop-filter:blur(20px) saturate(1.4);\n'
        '  -webkit-backdrop-filter:blur(20px) saturate(1.4);\n',
        '  /* backdrop-filter rimosso: forzava un blur su tutta la nav a ogni\n'
        '     frame di scroll. Sfondo piu\' opaco, resa quasi identica. */\n'
        '  background:rgba(6,16,28,.94);\n',
    )

    p.sub(
        "compositing: pulse infinito -> glow statico",
        '  box-shadow:0 0 10px var(--accent),0 0 20px rgba(255,138,61,.4);\n'
        '  animation:pulse 2.4s ease-in-out infinite;\n'
        '}\n'
        '@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.6;transform:scale(.85)}}\n',
        '  /* animazione pulse rimossa: un\'animazione infinita tiene attivo il\n'
        '     compositor per tutta la sessione. Glow statico. */\n'
        '  box-shadow:0 0 10px var(--accent),0 0 20px rgba(255,138,61,.4);\n'
        '}\n',
    )


# ═══ 5. LAYOUT: content-visibility sotto la piega ════════════════════════════

def patch_content_visibility(p: Patcher) -> None:
    p.sub(
        "layout: content-visibility:auto sulle sezioni sotto la piega",
        '.section{padding:100px 0;position:relative}',
        '.section{\n'
        '  padding:100px 0;position:relative;\n'
        '  /* Il browser salta layout e paint delle sezioni fuori schermo.\n'
        '     Da solo vale ~2,6 s di Speed Index nella misura A/B.\n'
        '     Non applicato a nav / hero / proof-bar: sono sopra la piega.\n\n'
        '     contain-intrinsic-size e\' l\'altezza che il browser ASSUME per una\n'
        '     sezione mai renderizzata. Se e\' molto sbagliata, la pagina cambia\n'
        '     altezza mentre scorri e la posizione di scroll salta. 1500px e\' la\n'
        '     mediana delle altezze reali misurate a 375px di viewport\n'
        '     (1397/1271/1650/1580/1473/1700/1717/946/1744/921). La keyword auto\n'
        '     fa si\' che, dopo il primo render, valga la dimensione vera. */\n'
        '  content-visibility:auto;\n'
        '  contain-intrinsic-size:auto 1500px;\n'
        '}\n'
        '/* Unica sezione fuori scala: contiene la griglia delle 7 dashboard. */\n'
        '#risultati{contain-intrinsic-size:auto 4500px}\n'
        '/* La sezione del form resta sempre renderizzata: finche\' e\' saltata non\n'
        '   ha un box, e l\'IntersectionObserver che nasconde la CTA sticky quando\n'
        '   si arriva al form non puo\' osservarla. E\' l\'unica delle 11 sezioni in\n'
        '   cui la correttezza vale piu\' del layout risparmiato. */\n'
        '#audit{content-visibility:visible}',
    )

    # final-section e footer non usano la classe .section: vanno aggiunti a mano.
    # Da soli hanno portato "Style & Layout" da 644 a 278 ms nella misura A/B.
    p.sub(
        "layout: content-visibility su final-section",
        '\n.final-section{',
        '\n.final-section{content-visibility:auto;contain-intrinsic-size:auto 620px;',
    )
    p.sub(
        "layout: content-visibility su footer",
        '\n.footer{',
        '\n.footer{content-visibility:auto;contain-intrinsic-size:auto 170px;',
    )


# ═══ 6. JS: syntax error + scroll listener ═══════════════════════════════════

def patch_js(p: Patcher) -> None:
    # 6a. Apostrofi non escapati -> SyntaxError -> script inline MORTO.
    p.sub(
        "js: fix SyntaxError apostrofo in 'un'email'",
        "'Inserisci un'email di lavoro valida.'",
        '"Inserisci un\'email di lavoro valida."',
    )
    p.sub(
        "js: fix SyntaxError apostrofo in 'l'investimento'",
        "'Seleziona l'investimento advertising.'",
        '"Seleziona l\'investimento advertising."',
    )

    # 6b. Reveal: scriveva opacity/transform inline su 27 elementi al parse,
    #     forzando un ricalcolo di stile prima del primo paint. Sull'attuale
    #     pagina live non girava affatto (SyntaxError), quindi rimuoverlo non
    #     cambia nulla di visibile.
    old_reveal_start = "// ─── Reveal on scroll ─────────────────────────────────────────"
    old_sticky_start = "// ─── Sticky CTA ───────────────────────────────────────────────"
    if old_reveal_start not in p.html or old_sticky_start not in p.html:
        raise PatchError("[js] blocchi reveal/sticky non trovati")
    s = p.html.index(old_reveal_start)
    e = p.html.index(old_sticky_start)
    p.sub(
        "js: rimosso reveal-on-scroll (27 scritture di stile inline pre-paint)",
        p.html[s:e],
        "// Reveal on scroll rimosso: impostava opacity:0 + transform inline su\n"
        "// 27 elementi durante il parse, forzando un ricalcolo di stile prima\n"
        "// del primo paint. Sulla pagina live non veniva mai eseguito (lo script\n"
        "// era interrotto da un SyntaxError), quindi la resa non cambia.\n\n",
    )

    # 6c. Sticky CTA: getBoundingClientRect() a ogni evento di scroll forzava un
    #     reflow sincrono per frame. Due IntersectionObserver, zero layout.
    old_sticky = """// ─── Sticky CTA ───────────────────────────────────────────────
const sticky = document.getElementById('stickyCta');
const hero   = document.querySelector('.hero');
const audit  = document.getElementById('audit');
function toggleSticky() {
  const pastHero  = scrollY > hero.offsetHeight * 0.8;
  const nearAudit = audit.getBoundingClientRect().top < innerHeight * 0.75;
  sticky.classList.toggle('show', pastHero && !nearAudit);
}
addEventListener('scroll', toggleSticky, { passive: true });
toggleSticky();"""

    new_sticky = """// ─── Sticky CTA ───────────────────────────────────────────────
// Era un listener di scroll che chiamava getBoundingClientRect() a ogni
// evento: un reflow sincrono per frame. Due IntersectionObserver danno la
// stessa logica (mostra dopo l'hero, nascondi sul form) a costo zero sul
// main thread.
const sticky = document.getElementById('stickyCta');
const hero   = document.querySelector('.hero');
const audit  = document.getElementById('audit');
let pastHero = false, nearAudit = false;
const apply = () => sticky.classList.toggle('show', pastHero && !nearAudit);

// entries[entries.length - 1] e non entries[0]: durante uno scroll veloce
// l'observer consegna piu' record in un colpo solo e il primo e' il piu'
// VECCHIO. Leggendo quello, la CTA restava visibile tornando in cima.
const ultimo = entries => entries[entries.length - 1];

new IntersectionObserver(entries => {
  pastHero = !ultimo(entries).isIntersecting;
  apply();
}, { threshold: 0, rootMargin: '-20% 0px 0px 0px' }).observe(hero);

// #audit e' escluso da content-visibility (vedi il CSS): una sezione con
// content-visibility:auto e fuori schermo non ha un box da osservare, quindi
// l'observer non scattava e la CTA restava sopra il form. Osservando la
// sezione intera - alta ~1700px - l'intersezione resta vera per tutto il
// tempo in cui l'utente sta compilando, che e' esattamente quando la barra
// non deve coprire il form.
new IntersectionObserver(entries => {
  nearAudit = ultimo(entries).isIntersecting;
  apply();
}, { threshold: 0, rootMargin: '0px 0px -25% 0px' }).observe(audit);"""

    p.sub("js: sticky CTA da listener di scroll a IntersectionObserver",
          old_sticky, new_sticky)


PATCHES = [
    ("1. font non bloccante", patch_fonts),
    ("2. immagini dimensionate", patch_images),
    ("3. paint: noise + gradienti", patch_paint),
    ("4. compositing: blur + animazione", patch_compositing),
    ("5. layout: content-visibility", patch_content_visibility),
    ("6. js: syntax error + scroll", patch_js),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--report", action="store_true",
                    help="stampa il dettaglio di ogni sostituzione")
    ap.add_argument("--font-url", default=INTER_LATIN_WOFF2,
                    help="da dove servire Inter. Default: fonts.gstatic.com. "
                         "Passa l'URL della media library GoHighLevel per servirlo "
                         "dallo stesso dominio (LCP 2,08 s -> 1,24 s misurati).")
    args = ap.parse_args()

    html = args.input.read_text(encoding="utf-8")
    p = Patcher(html)

    for name, fn in PATCHES:
        try:
            fn(p, args.font_url) if fn is patch_fonts else fn(p)
        except PatchError as exc:
            print(f"FALLITO — {name}\n  {exc}", file=sys.stderr)
            print("\nNessun file scritto. Il markup di input e' cambiato rispetto\n"
                  "a quello per cui questo script e' stato scritto: aggiorna il\n"
                  "pattern corrispondente prima di riprovare.", file=sys.stderr)
            return 1
        print(f"OK   {name}")

    args.output.write_text(p.html, encoding="utf-8")

    if args.report:
        print("\nDettaglio sostituzioni:")
        for line in p.log:
            print(f"  - {line}")

    before, after = len(html), len(p.html)
    print(f"\nScritto {args.output}")
    print(f"HTML: {before:,} -> {after:,} byte ({after - before:+,})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
