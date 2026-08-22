#!/usr/bin/env python3
"""
optimize_landing_seo.py — fix SEO tecnici per la landing Mailift.

Pensato per girare DOPO optimize_landing_speed.py (o da solo): ogni patch e'
verificata e lo script fallisce invece di produrre un output parziale.

    python tools/optimize_landing_speed.py in.html step1.html
    python tools/optimize_landing_seo.py   step1.html finale.html --report

Cosa applica:

  ALTA
   1. <link rel="canonical"> — la stessa pagina e' raggiungibile su piu' URL
      (mailift.com, www.mailift.com/email-lp215490-page): senza canonical Google
      deve indovinare quale indicizzare.
   2. Twitter Card — gli Open Graph c'erano, i twitter:* no: su X l'anteprima
      non veniva generata.
   3. <meta name="robots" content="index, follow"> esplicito.
   4. JSON-LD FAQPage generato dalle 8 <details> REALI della pagina (estratte
      dall'HTML, non riscritte a mano: se cambi il testo delle FAQ e rilanci lo
      script, lo schema resta allineato). Candidato a rich snippet in SERP.
   5. JSON-LD WebPage collegato al ProfessionalService esistente.

  MEDIA
   6. <title> con la keyword in apertura invece del brand.
   7. Meta description con call to action esplicita.
   8. Alt text delle dashboard risultati con contesto di servizio, non solo i
      numeri (vale per Google Images e per la coerenza semantica).
   9. <meta name="author"> per i segnali E-E-A-T.

NON applicato di proposito:
  - `sameAs` nello schema ProfessionalService: servono gli URL REALI dei profili
    social Mailift e nella pagina non c'e' nessun link social. Inventarli
    darebbe a Google entita' sbagliate. Lo script lascia un commento HTML con
    il punto esatto in cui inserirli.
  - BreadcrumbList: ha senso su un sito con gerarchia di pagine, non su una
    landing singola. Aggiungerlo sarebbe markup decorativo.
  - Font non bloccante (punto 9 dell'analisi): gia' risolto, e in modo piu'
    aggressivo, da optimize_landing_speed.py (@font-face inline + preload del
    solo file variabile, invece del trucco preload/onload sul CSS di Google).
"""

from __future__ import annotations

import argparse
import html as htmllib
import json
import re
import sys
from pathlib import Path

CANONICAL = "https://mailift.com/"
OG_IMAGE = ("https://images.leadconnectorhq.com/image/f_webp/q_80/r_1200/"
            "u_https://assets.cdn.filesafe.space/us5X0gC74A4Hjpwvd83e/media/"
            "67d4419f84fb3460f370af5e.png")

TITLE_NEW = "Revenue Retention per ecommerce DTC | Mailift"
DESC_NEW = ("Mailift trasforma il database che hai gia' pagato in fatturato "
            "ricorrente: automazioni, segmentazione e campagne per ecommerce "
            "DTC da 400.000 euro l'anno. Richiedi il Revenue Audit gratuito.")


class PatchError(RuntimeError):
    pass


class Patcher:
    def __init__(self, html: str):
        self.html = html
        self.log: list[str] = []

    def sub(self, label: str, old: str, new: str, *, count: int = 1) -> None:
        found = self.html.count(old)
        if found != count:
            raise PatchError(f"[{label}] attese {count} occorrenze, trovate {found}.\n"
                             f"  pattern: {old[:110]!r}")
        self.html = self.html.replace(old, new)
        self.log.append(f"{label}: {count} sostituzione(i)")

    def re_sub(self, label: str, pattern: str, repl, *, expect: int) -> None:
        new_html, n = re.subn(pattern, repl, self.html)
        if n != expect:
            raise PatchError(f"[{label}] attese {expect} occorrenze, trovate {n}.\n"
                             f"  pattern: {pattern[:110]!r}")
        self.html = new_html
        self.log.append(f"{label}: {n} sostituzione(i)")


# ═══ ESTRAZIONE FAQ DALLA PAGINA ═════════════════════════════════════════════

def estrai_faq(html_doc: str) -> list[tuple[str, str]]:
    """Legge le FAQ dai <details>/<summary> reali invece di riscriverle.

    Cosi' se il testo delle FAQ cambia basta rilanciare lo script e lo schema
    resta allineato. Uno schema che dichiara risposte diverse da quelle visibili
    in pagina e' una violazione delle linee guida structured data di Google.
    """
    coppie = []
    for q_raw, a_raw in re.findall(
        r"<details[^>]*>\s*<summary[^>]*>(.*?)</summary>(.*?)</details>",
        html_doc, re.S,
    ):
        def pulisci(frammento: str) -> str:
            testo = re.sub(r"<[^>]+>", " ", frammento)
            testo = htmllib.unescape(testo)
            return re.sub(r"\s+", " ", testo).strip()

        domanda, risposta = pulisci(q_raw), pulisci(a_raw)
        if domanda and risposta:
            coppie.append((domanda, risposta))
    return coppie


def blocco_faq_jsonld(coppie: list[tuple[str, str]]) -> str:
    schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": a},
            }
            for q, a in coppie
        ],
    }
    return ('<script type="application/ld+json">'
            + json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
            + "</script>")


# ═══ PATCH ═══════════════════════════════════════════════════════════════════

def patch_head_meta(p: Patcher) -> None:
    """canonical, robots, author, twitter card. Inseriti dopo l'og:image."""
    ancora = f'<meta content="{OG_IMAGE}" property="og:image"/>'
    if ancora not in p.html:
        raise PatchError("[head] tag og:image non trovato: e' l'ancora di inserimento")

    nuovi = (
        ancora + "\n"
        # La pagina risponde su piu' URL (mailift.com e www.mailift.com/email-lp215490-page):
        # il canonical dice a Google quale delle due indicizzare e consolida i segnali.
        f'<link rel="canonical" href="{CANONICAL}"/>\n'
        '<meta content="index, follow" name="robots"/>\n'
        '<meta content="Lorenzo Baretta — Mailift" name="author"/>\n'
        # Gli Open Graph coprono Facebook/LinkedIn/WhatsApp; X richiede i propri tag.
        '<meta content="summary_large_image" name="twitter:card"/>\n'
        f'<meta content="{TITLE_NEW}" name="twitter:title"/>\n'
        '<meta content="Scopri quanto fatturato stai lasciando nel database con un '
        'Revenue Audit gratuito riservato a ecommerce qualificati." name="twitter:description"/>\n'
        f'<meta content="{OG_IMAGE}" name="twitter:image"/>'
    )
    p.sub("head: canonical + robots + author + twitter card", ancora, nuovi)


def patch_title_description(p: Patcher) -> None:
    """Keyword in apertura invece del brand, e description con CTA."""
    p.sub(
        "title: keyword in apertura",
        "<title>Mailift | Revenue Retention per ecommerce strutturati</title>",
        f"<title>{TITLE_NEW}</title>",
    )

    vecchia_desc = ('<meta content="Hai già pagato per acquisire i tuoi clienti. '
                    'Mailift trasforma database, automazioni e campagne in acquisti '
                    'ripetuti, maggiore marginalità e fatturato più prevedibile." '
                    'name="description"/>')
    p.sub(
        "description: aggiunta call to action",
        vecchia_desc,
        f'<meta content="{DESC_NEW}" name="description"/>',
    )


def patch_alt_risultati(p: Patcher) -> None:
    """Alt delle dashboard: i numeri da soli non dicono di che servizio si tratta.

    Il testo aggiunto resta vero (sono i risultati mostrati nella sezione
    Risultati): non nomina piattaforme che non ho verificato negli screenshot.
    """
    p.re_sub(
        "alt: contesto di servizio sulle dashboard risultati",
        r'alt="Dashboard: ([^"]+)"',
        lambda m: f'alt="Email marketing per ecommerce, risultati Mailift — {m.group(1)}"',
        expect=7,
    )


def patch_jsonld(p: Patcher) -> None:
    """FAQPage dalle FAQ reali + WebPage collegata al ProfessionalService."""
    coppie = estrai_faq(p.html)
    if len(coppie) < 4:
        raise PatchError(f"[jsonld] trovate solo {len(coppie)} FAQ nella pagina: "
                         "il markup <details>/<summary> e' cambiato")

    vecchio = ('<script type="application/ld+json">{"@context":"https://schema.org",'
               '"@type":"ProfessionalService"')
    if vecchio not in p.html:
        raise PatchError("[jsonld] blocco ProfessionalService non trovato")

    inizio = p.html.index(vecchio)
    fine = p.html.index("</script>", inizio) + len("</script>")
    blocco_service = p.html[inizio:fine]

    webpage = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "url": CANONICAL,
        "name": TITLE_NEW,
        "description": DESC_NEW,
        "inLanguage": "it-IT",
        "about": {"@type": "ProfessionalService", "name": "Mailift"},
    }

    nuovo = (
        "<!-- Per rafforzare l'entita' Mailift agli occhi di Google, aggiungi qui\n"
        '     dentro il ProfessionalService un campo "sameAs" con gli URL REALI dei\n'
        "     profili social ufficiali, es:\n"
        '       "sameAs":["https://www.linkedin.com/company/...","https://www.instagram.com/..."]\n'
        "     Non li ho inseriti io perche' nella pagina non c'e' nessun link social\n"
        "     da cui ricavarli, e URL sbagliati collegherebbero l'entita' a profili\n"
        "     di qualcun altro. -->\n"
        + blocco_service + "\n"
        + '<script type="application/ld+json">'
        + json.dumps(webpage, ensure_ascii=False, separators=(",", ":"))
        + "</script>\n"
        + "<!-- FAQPage generato dalle 8 FAQ realmente presenti in pagina.\n"
          "     Se modifichi il testo delle FAQ rilancia optimize_landing_seo.py:\n"
          "     uno schema che dichiara risposte diverse da quelle visibili viola\n"
          "     le linee guida structured data e puo' far perdere il rich snippet. -->\n"
        + blocco_faq_jsonld(coppie)
    )
    p.sub("jsonld: WebPage + FAQPage da 8 FAQ reali", blocco_service, nuovo)
    p.log.append(f"jsonld: {len(coppie)} FAQ estratte dalla pagina")


PATCHES = [
    ("head: canonical / robots / twitter", patch_head_meta),
    ("title e description", patch_title_description),
    ("alt immagini risultati", patch_alt_risultati),
    ("json-ld WebPage + FAQPage", patch_jsonld),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    p = Patcher(args.input.read_text(encoding="utf-8"))

    for nome, fn in PATCHES:
        try:
            fn(p)
        except PatchError as exc:
            print(f"FALLITO — {nome}\n  {exc}", file=sys.stderr)
            print("\nNessun file scritto.", file=sys.stderr)
            return 1
        print(f"OK   {nome}")

    args.output.write_text(p.html, encoding="utf-8")
    if args.report:
        print("\nDettaglio:")
        for riga in p.log:
            print(f"  - {riga}")
    print(f"\nScritto {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
