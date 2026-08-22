#!/usr/bin/env python3
"""Trova il nome del titolare/owner per una lista di aziende.

Due fonti, entrambe gratuite (nessuna API a pagamento):
  1. la local-part dell'email  (mario.rossi@azienda.it -> Mario Rossi)
  2. le pagine "chi siamo / team / contatti" del sito aziendale, dove i piccoli
     installatori mettono quasi sempre nome + ruolo del titolare

    python tools/find_owners.py .tmp/installatori.csv -o .tmp/owners.csv
    python tools/find_owners.py .tmp/installatori.csv --limit 20

Colonne richieste nel CSV di input: Azienda, Email, Website.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from pathlib import Path

import requests

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept-Language": "it-IT,it;q=0.9"}
TIMEOUT = 20

# pagine dove tipicamente sta il nome del titolare, in ordine di resa
PAGE_HINTS = ["chi-siamo", "chi_siamo", "chisiamo", "azienda", "about", "about-us",
              "la-nostra-storia", "storia", "team", "il-team", "staff", "contatti",
              "contact", "contattaci"]

RUOLI = (r"(?<![A-Za-zÀ-ÿ])(?:titolare|amministratore\s+unico|amministratore\s+delegato|"
         r"amministratore|socio\s+fondatore|fondatore|founder|presidente|ceo|"
         r"direttore\s+tecnico|direttore\s+commerciale|responsabile\s+tecnico)(?![a-zà-ÿ])")

NOME = (r"[A-ZÀ-Ý][a-zà-ÿ']{2,}\s+(?:(?:De|Di|Da|Del|Della|Lo|La|Van|Mac)\s+)?"
        r"[A-ZÀ-Ý][a-zà-ÿ']{2,}")

# ruolo prima del nome  ("Titolare: Mario Rossi", "Amministratore unico - Mario Rossi")
# il negative lookahead scarta "titolare dell'impianto" / "titolare del conto"
RE_RUOLO_NOME = re.compile(
    rf"(?P<ruolo>{RUOLI})\s*[:\-–—,]?\s*(?!(?:dell|del|della|di|dei|delle|d')\b)(?P<nome>{NOME})", re.I)

# ditta individuale: la ragione sociale contiene il titolare
# ("B.E. IMPIANTI DI BASTIANELLI EMILIANO", "Elektrosat di Lazzeri Angelo")
RE_RAGIONE_SOCIALE = re.compile(
    rf"\b(?:di|d')\s+(?P<nome>{NOME})(?=\s*(?:&|e\s+c\.|s\.?a\.?s|s\.?n\.?c|$))|"
    rf"\b(?:di|d')\s+(?P<nome2>{NOME})\s*$", re.I)
# nome prima del ruolo  ("Mario Rossi, titolare", "Mario Rossi — Amministratore")
RE_NOME_RUOLO = re.compile(rf"(?P<nome>{NOME})\s*[,\-–—:]\s*(?P<ruolo>{RUOLI})", re.I)

# parole che non sono cognomi: scarta i falsi positivi tipo "Titolare Trattamento Dati"
STOPWORDS = {
    "trattamento", "dati", "privacy", "cookie", "policy", "impianti", "impianto",
    "energia", "energie", "solare", "solari", "fotovoltaico", "fotovoltaici", "srl",
    "snc", "sas", "spa", "azienda", "societa", "società", "gruppo", "servizi",
    "sistemi", "casa", "roma", "italia", "italiana", "clienti", "cliente", "lavori",
    "preventivo", "contatti", "chi", "siamo", "nostra", "nostro", "sede", "legale",
    "partita", "iva", "codice", "fiscale", "reg", "impresa", "imprese", "camera",
    "commercio", "condizioni", "termini", "utilizzo", "generali", "responsabile",
    "protezione", "riservati", "diritti", "tutti", "leggi", "scopri", "richiedi",
    "green", "solar", "energy", "power", "system", "group", "home", "sun",
    "founder", "ceo", "titolare", "amministratore", "unico", "direttore", "presidente",
    "fondatore", "ufficio", "facebook", "instagram", "linkedin", "whatsapp", "png",
    "jpg", "specification", "dispositivo", "prestazioni", "ottimizzate", "drop",
    "anche", "next", "solutions", "service", "point", "srl", "srls", "italy",
    "loading", "cookies", "newsletter", "download", "reserved", "copyright",
}

GENERIC_MAIL = {
    "info", "amministrazione", "commerciale", "contatti", "contact", "mail", "posta",
    "segreteria", "ufficio", "sales", "vendite", "assistenza", "supporto", "support",
    "preventivi", "preventivo", "tecnico", "ordini", "pec", "privacy", "noreply",
    "no-reply", "hello", "ciao", "admin", "office", "direzione", "staff", "azienda",
    "energia", "solare", "fotovoltaico", "impianti", "italia", "roma", "web", "sito",
}


# almeno un token deve essere un nome proprio: taglia "International Advisory",
# "Socio Maggioranza", "Sistemi Informativi" e simili
NOMI_PROPRI = set("""alessandro alessio alberto aldo alessandra alessia alfredo alfonso amedeo andrea
angelo anna annalisa antonella antonio arianna armando arturo augusto aurelio barbara
benedetta beatrice bruno camilla carla carlo carmela carmine caterina cesare chiara
christian cinzia claudia claudio corrado cristian cristina cristiano damiano daniela
daniele dario davide debora diego domenico donatella edoardo elena eleonora elisa
elisabetta emanuele emiliano emilio enrica enrico enzo eraldo ermanno ernesto erica
eugenio fabio fabiana fabrizio federica federico felice ferdinando filippo flavia
flavio francesca francesco franco gabriele gabriella gaetano genoveffa giacomo gianluca
gianluigi gianfranco gianni gino giorgia giorgio giovanna giovanni giulia giuliano
giulio giuseppe giuseppina graziano gregorio guido iliana ilaria irene isabella ivan
ivano jacopo laura lauro leonardo letizia lidia lorenzo luca lucia luciano lucio
ludovica luigi luigia manuel manuela marcello marco margherita maria mariangela marina
mario marta martina massimiliano massimo matteo maurizio mauro michela michele mirko
monica nadia natale nicola nicolo noemi olga oreste oscar osvaldo paola paolo pasquale
patrizia patrizio pierluigi pierpaolo piero pietro primo raffaele raffaella remo renato
renzo riccardo rita roberta roberto rolando romano rosa rosanna rosario ruggero salvatore
samuele sandra sandro sara sergio silvana silvia simona simone sofia sonia stefania
stefano susanna teresa tiziana tiziano tommaso ugo umberto valentina valentino valeria
valerio vanessa vincenzo virginia vito vittorio walter william yuri
edwin john michael david peter thomas robert james paul mark daniel""".split())


def norm(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def nome_plausibile(nome: str) -> bool:
    parti = [p for p in nome.split() if len(p) > 2]
    if len(parti) < 2:
        return False
    if any(norm(p) in STOPWORDS for p in parti):
        return False
    # nome o cognome-primo: basta che uno dei due token sia un nome proprio noto
    return any(norm(p) in NOMI_PROPRI for p in parti)


def titolo(s: str) -> str:
    return " ".join(w.capitalize() if len(w) > 2 else w.lower() for w in s.split())


def nome_da_email(email: str) -> str | None:
    """mario.rossi@x.it -> Mario Rossi. Ignora le caselle generiche."""
    local = email.split("@")[0].strip().lower()
    local = re.sub(r"\d+$", "", local)
    if not local or local in GENERIC_MAIL:
        return None
    parti = [p for p in re.split(r"[._\-]+", local) if p]
    parti = [p for p in parti if p not in GENERIC_MAIL]
    if len(parti) >= 2 and all(len(p) >= 3 and p.isalpha() for p in parti[:2]):
        return titolo(f"{parti[0]} {parti[1]}")
    return None


def get(url: str) -> str | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        if r.status_code == 200 and "html" in r.headers.get("content-type", "").lower():
            return r.text
    except requests.RequestException:
        return None
    return None


def to_text(html: str) -> str:
    html = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?i)<br\s*/?>|</(p|div|li|h[1-6]|td|tr)>", "\n", html)
    return re.sub(r"[ \t\xa0]+", " ", unescape(re.sub(r"<[^>]+>", " ", html)))


def candidate_urls(base: str, html: str) -> list[str]:
    """Link interni che assomigliano a una pagina 'chi siamo'."""
    found, seen = [], set()
    for href in re.findall(r'href=["\']([^"\']+)["\']', html, re.I):
        h = href.lower()
        if any(k in h for k in PAGE_HINTS):
            if href.startswith("/"):
                href = base.rstrip("/") + href
            elif not href.startswith("http"):
                continue
            if href not in seen:
                seen.add(href)
                found.append(href)
    return found[:4]


def estrai(testo: str) -> list[tuple[str, str]]:
    out = []
    for rx in (RE_RUOLO_NOME, RE_NOME_RUOLO):
        for mt in rx.finditer(testo):
            nome = " ".join(mt.group("nome").split())
            if nome_plausibile(nome):
                out.append((titolo(nome), " ".join(mt.group("ruolo").split()).lower()))
    return out


def lavora(row: dict) -> dict:
    azienda = row.get("Azienda", "").strip()
    email = row.get("Email", "").strip()
    sito = row.get("Website", "").strip()
    res = {"Azienda": azienda, "Email": email, "Website": sito,
           "Nome": "", "Ruolo": "", "Fonte": "", "Confidenza": ""}

    candidate_mail = [email] + [m for m in (row.get("EmailTutte") or "").split(";") if m]
    da_mail = next((n for n in (nome_da_email(m) for m in candidate_mail if m) if n), None)
    # "evolution.service@" per "Evolution Service Srls" non e' una persona:
    # se i token dell'email ricompaiono nella ragione sociale, e' il nome dell'azienda
    if da_mail:
        tok_az = set(norm(azienda).split())
        if any(norm(p) in tok_az for p in da_mail.split()) or not nome_plausibile(da_mail):
            da_mail = None

    # 0. l'insegna e' un nome di persona
    ins = re.sub(r"(?i)\b(ing|arch|geom|dott|dr|sig|studio tecnico|studio)\.?\s+", " ", azienda)
    mt_ins = re.search(NOME, ins)
    if mt_ins and nome_plausibile(mt_ins.group(0)) and len(azienda.split()) <= 5:
        res.update(Nome=titolo(mt_ins.group(0)), Ruolo="titolare",
                   Fonte="insegna", Confidenza="media")
        return res

    # 1. ditta individuale: il titolare e' gia' nella ragione sociale -> fonte piu' affidabile
    mt = RE_RAGIONE_SOCIALE.search(azienda)
    if mt:
        nome = mt.group("nome") or mt.group("nome2")
        if nome and nome_plausibile(nome):
            res.update(Nome=titolo(nome), Ruolo="titolare", Fonte="ragione sociale",
                       Confidenza="alta")
            return res

    html = get(sito) if sito.startswith("http") else None
    trovati: list[tuple[str, str]] = []
    if html:
        base = re.match(r"https?://[^/]+", sito)
        base = base.group(0) if base else sito
        trovati += estrai(to_text(html))
        for u in candidate_urls(base, html):
            sub = get(u)
            if sub:
                trovati += estrai(to_text(sub))
            if trovati:
                break

    if trovati:
        # il primo match e' quasi sempre quello in evidenza sulla pagina
        nome, ruolo = trovati[0]
        res.update(Nome=nome, Ruolo=ruolo, Fonte="sito")
        # se anche l'email dice lo stesso cognome, la confidenza sale
        cognome = norm(nome.split()[-1])
        res["Confidenza"] = "alta" if (da_mail and cognome in norm(da_mail)) or \
                                      cognome in norm(email) else "media"
    elif da_mail:
        res.update(Nome=da_mail, Ruolo="", Fonte="email", Confidenza="media")
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_in")
    ap.add_argument("-o", "--out", default=".tmp/owners.csv")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()

    rows = [r for r in csv.DictReader(open(args.csv_in, encoding="utf-8-sig"))
            if r.get("Email", "").strip() or r.get("Website", "").strip()]
    if args.limit:
        rows = rows[:args.limit]

    with ThreadPoolExecutor(args.workers) as ex:
        out = list(ex.map(lavora, rows))

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)

    con_nome = [r for r in out if r["Nome"]]
    print(f"{len(out)} aziende  ->  {len(con_nome)} con nome "
          f"({len(con_nome) / len(out) * 100:.0f}%)", file=sys.stderr)
    for fonte in ("sito", "email"):
        n = sum(1 for r in con_nome if r["Fonte"] == fonte)
        print(f"  da {fonte}: {n}", file=sys.stderr)
    print(f"scritto in {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
