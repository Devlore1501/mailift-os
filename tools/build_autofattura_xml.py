"""
Genera i file XML FatturaPA (TD17) delle autofatture passive direttamente da un
estratto conto Revolut, senza passare da Fatture in Cloud.

Serve quando vuoi i .xml pronti da caricare a mano (portale SDI, o import in FiC)
invece di farli creare via API da `run_autofatture.py`.

Le convenzioni sui campi replicano quelle gia' validate dal SDI in
`tools/fic_client.py` (sessioni 2026-04-07/08):
    - CedentePrestatore = fornitore estero, CessionarioCommittente = Mailift Srl
    - CodiceDestinatario = M5UXCR1 (codice di Mailift: in autofattura sei tu il
      destinatario del documento elettronico)
    - RegimeFiscale RF01 per fornitori UE, RF18 per extra-UE
    - Sede estera: Indirizzo "Estero", CAP "00000", Comune = paese lowercase,
      Provincia omessa (in XML e' opzionale e il pattern XSD vuole [A-Z]{2},
      quindi la "ee" lowercase usata su FiC qui non e' riportabile)
    - Aliquota country-aware: UE -> 22%, extra-UE -> 0% con Natura N2.1
      ("non soggetta art. 7-ter")

Esecuzione:
    python tools/build_autofattura_xml.py inbox/estratto.csv --out .tmp/xml
    python tools/build_autofattura_xml.py inbox/estratto.csv --start-number 30
    python tools/build_autofattura_xml.py inbox/estratto.csv --data 2026-07-31

Dopo la generazione lo script stampa la riconciliazione con l'estratto conto:
ogni movimento deve finire o in un'autofattura o in una categoria di esclusione,
e la somma deve tornare al saldo netto del periodo.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.fic_client import _EU_COUNTRIES, _country_it_name, _regime_fiscale_for_country

CENT = Decimal("0.01")

# --------------------------------------------------------------------- Mailift
# Dati del committente (= noi). Vedi workflows/emit_autofatture.md.
COMMITTENTE = {
    "denominazione": "MAILIFT SRL",
    "piva": "18160081008",
    "indirizzo": "Via Casilina 1940",
    "cap": "00132",
    "comune": "Roma",
    "provincia": "RM",
    "nazione": "IT",
    "codice_destinatario": "M5UXCR1",
}

# Placeholder AdE per identificativo fiscale estero non noto. Va sostituito con
# la P.IVA/VAT reale letta dalla fattura del fornitore prima dell'invio al SDI.
VAT_PLACEHOLDER = "OO99999999999"


@dataclass
class Fornitore:
    """Regola di riconoscimento di un fornitore sull'estratto conto."""
    pattern: str                      # regex sulla Description del movimento
    denominazione: str
    paese: str                        # ISO 3166-1 alpha-2
    vat: str = ""                     # VAT reale, se nota con certezza
    verifica: str = ""                # se valorizzato -> finisce in da_verificare/
    descrizione: str = ""             # riga della fattura; default generato


# Registro fornitori. Ordine = priorita' di match.
FORNITORI: list[Fornitore] = [
    # --- UE: 22% reverse charge, RF01 ---
    Fornitore(r"^Facebk", "Meta Platforms Ireland Limited", "IE",
              descrizione="Servizi di pubblicita' online"),
    Fornitore(r"Commissione Revolut", "Revolut Bank UAB", "LT",
              descrizione="Commissioni servizi bancari - piano Grow"),
    Fornitore(r"Dropbox", "Dropbox International Unlimited Company", "IE",
              descrizione="Servizi software in abbonamento"),
    Fornitore(r"Hostinger", "Hostinger International Ltd", "CY",
              descrizione="Servizi di hosting e VPS"),
    Fornitore(r"^Apple\.com", "Apple Distribution International Ltd", "IE",
              verifica="Se e' un acquisto B2C con IVA italiana gia' applicata, "
                       "NON va autofattura: e' nota spese.",
              descrizione="Servizi e contenuti digitali"),

    # --- Extra-UE: 0% non soggetta art. 7-ter, RF18 ---
    Fornitore(r"^Anthropic", "Anthropic PBC", "US",
              descrizione="Servizi software in abbonamento"),
    Fornitore(r"^Openart", "OpenArt", "US",
              descrizione="Servizi software in abbonamento"),
    Fornitore(r"^Opus Clip", "Opus Clip", "US",
              descrizione="Servizi software in abbonamento"),
    Fornitore(r"^Paddle\.net", "Paddle.com Market Ltd", "GB",
              descrizione="Servizi software in abbonamento (merchant of record)"),
    Fornitore(r"^Myleadfox", "Myleadfox", "AE",
              descrizione="Servizi software in abbonamento"),
    Fornitore(r"^Canva", "Canva Pty Ltd", "AU",
              descrizione="Servizi software in abbonamento"),
    Fornitore(r"^Gamma\.app", "Gamma Tech Inc", "US",
              descrizione="Servizi software in abbonamento"),
    Fornitore(r"Elevenlabs", "ElevenLabs Inc", "US",
              descrizione="Servizi software in abbonamento"),

    # --- Da verificare prima di emettere ---
    Fornitore(r"^Lovable", "Lovable Labs", "US",
              verifica="Il repo si contraddice: workflows/emit_autofatture.md dice "
                       "Lovable US (extra-UE, 0%), classify_transactions.py dice "
                       "Lovable AB (SE, quindi UE 22%). Qui e' generato come US. "
                       "Controlla l'entita' sulla fattura reale.",
              descrizione="Servizi software in abbonamento"),
    Fornitore(r"skool\.com", "Skool.com", "US",
              verifica="Verifica che il billing sia intestato a Mailift e non B2C.",
              descrizione="Servizi software in abbonamento"),
    Fornitore(r"Digital Media Llc", "Digital Media LLC", "US",
              verifica="Fornitore non identificato: recupera la ricevuta prima di emettere.",
              descrizione="Servizi software in abbonamento"),
]

# Movimenti che NON generano autofattura, con la motivazione mostrata in riconciliazione.
ESCLUSIONI: list[tuple[str, str]] = [
    (r"Google Workspace",
     "Google Cloud Italy S.r.l. (P.IVA IT11256580967) - IVA 22% italiana diretta -> TD01"),
    (r"Hyundai Capital Bank",
     "emette fattura elettronica italiana -> TD01"),
    (r"^Eni\b|Fiumicino",
     "carburante, fornitore italiano"),
    (r"HR JOB SI|Marinangeli|Crivello|SAF srl|TORA",
     "bonifico a fornitore/persona italiana"),
    (r"Compenso amministratore|^A Main$|Da tasse varie",
     "compenso amministratore / giroconto interno"),
]


@dataclass
class Gruppo:
    """Una autofattura: un fornitore, tutti i suoi movimenti del periodo."""
    fornitore: Fornitore
    movimenti: list[tuple[date, Decimal, str]] = field(default_factory=list)

    @property
    def imponibile(self) -> Decimal:
        return sum((m[1] for m in self.movimenti), Decimal("0")).quantize(CENT)

    @property
    def is_ue(self) -> bool:
        return self.fornitore.paese.upper() in _EU_COUNTRIES

    @property
    def aliquota(self) -> Decimal:
        return Decimal("22.00") if self.is_ue else Decimal("0.00")

    @property
    def natura(self) -> str:
        return "" if self.is_ue else "N2.1"

    @property
    def imposta(self) -> Decimal:
        return (self.imponibile * self.aliquota / Decimal("100")).quantize(CENT)

    @property
    def totale(self) -> Decimal:
        return (self.imponibile + self.imposta).quantize(CENT)


# ------------------------------------------------------------------ Parsing CSV
def leggi_movimenti(path: Path) -> list[dict]:
    """Legge il CSV Revolut e ritorna solo le uscite completate."""
    righe = []
    with path.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("State") != "COMPLETED":
                continue
            try:
                amount = Decimal(r["Amount"])
            except Exception:
                continue
            righe.append({
                "data": datetime.strptime(r["Date started (UTC)"], "%Y-%m-%d").date(),
                "descrizione": (r.get("Description") or "").strip(),
                "riferimento": (r.get("Reference") or "").strip(),
                "importo": amount,
                "id": r.get("ID", ""),
            })
    return righe


def classifica(movimenti: list[dict]) -> tuple[list[Gruppo], list[dict], list[dict], list[dict]]:
    """Ripartisce i movimenti in: autofatture, esclusi, entrate, non classificati."""
    gruppi: dict[str, Gruppo] = {}
    esclusi, entrate, ignoti = [], [], []

    for m in movimenti:
        if m["importo"] >= 0:
            entrate.append(m)
            continue
        netto = -m["importo"]
        testo = " ".join(p for p in (m["descrizione"], m["riferimento"]) if p)

        for pattern, motivo in ESCLUSIONI:
            if re.search(pattern, testo, re.I):
                esclusi.append({**m, "motivo": motivo})
                break
        else:
            for f in FORNITORI:
                if re.search(f.pattern, m["descrizione"], re.I):
                    g = gruppi.setdefault(f.denominazione, Gruppo(fornitore=f))
                    g.movimenti.append((m["data"], netto, m["descrizione"]))
                    break
            else:
                ignoti.append(m)

    ordinati = sorted(gruppi.values(), key=lambda g: (-g.imponibile))
    return ordinati, esclusi, entrate, ignoti


# --------------------------------------------------------------- Generazione XML
def _sub(parent: ET.Element, tag: str, text: str | None = None) -> ET.Element:
    el = ET.SubElement(parent, tag)
    if text is not None:
        el.text = text
    return el


def costruisci_xml(g: Gruppo, numero: str, data_doc: date, progressivo: str) -> ET.ElementTree:
    """Costruisce l'albero FatturaPA v1.2.2 di una singola autofattura TD17."""
    ns = "http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"
    ET.register_namespace("p", ns)
    root = ET.Element(f"{{{ns}}}FatturaElettronica", {"versione": "FPR12"})

    paese = g.fornitore.paese.upper()
    paese_it = _country_it_name(paese)

    # ---------------------------------------------------------------- Header
    header = _sub(root, "FatturaElettronicaHeader")

    trasm = _sub(header, "DatiTrasmissione")
    id_trasm = _sub(trasm, "IdTrasmittente")
    _sub(id_trasm, "IdPaese", COMMITTENTE["nazione"])
    _sub(id_trasm, "IdCodice", COMMITTENTE["piva"])
    _sub(trasm, "ProgressivoInvio", progressivo)
    _sub(trasm, "FormatoTrasmissione", "FPR12")
    # In autofattura il destinatario del documento elettronico sei tu stesso.
    _sub(trasm, "CodiceDestinatario", COMMITTENTE["codice_destinatario"])

    # CedentePrestatore = il fornitore estero.
    cedente = _sub(header, "CedentePrestatore")
    anag = _sub(cedente, "DatiAnagrafici")
    id_iva = _sub(anag, "IdFiscaleIVA")
    _sub(id_iva, "IdPaese", paese)
    _sub(id_iva, "IdCodice", g.fornitore.vat or VAT_PLACEHOLDER)
    anagrafica = _sub(anag, "Anagrafica")
    _sub(anagrafica, "Denominazione", g.fornitore.denominazione)
    _sub(anag, "RegimeFiscale", _regime_fiscale_for_country(paese))
    sede = _sub(cedente, "Sede")
    _sub(sede, "Indirizzo", "Estero")
    _sub(sede, "CAP", "00000")
    _sub(sede, "Comune", (paese_it or paese).lower())
    # Provincia omessa: opzionale, e per sede estera il pattern XSD [A-Z]{2} non si applica.
    _sub(sede, "Nazione", paese)

    # CessionarioCommittente = Mailift (emittente materiale dell'autofattura).
    cess = _sub(header, "CessionarioCommittente")
    anag_c = _sub(cess, "DatiAnagrafici")
    id_iva_c = _sub(anag_c, "IdFiscaleIVA")
    _sub(id_iva_c, "IdPaese", COMMITTENTE["nazione"])
    _sub(id_iva_c, "IdCodice", COMMITTENTE["piva"])
    anagrafica_c = _sub(anag_c, "Anagrafica")
    _sub(anagrafica_c, "Denominazione", COMMITTENTE["denominazione"])
    sede_c = _sub(cess, "Sede")
    _sub(sede_c, "Indirizzo", COMMITTENTE["indirizzo"])
    _sub(sede_c, "CAP", COMMITTENTE["cap"])
    _sub(sede_c, "Comune", COMMITTENTE["comune"])
    _sub(sede_c, "Provincia", COMMITTENTE["provincia"])
    _sub(sede_c, "Nazione", COMMITTENTE["nazione"])

    # ------------------------------------------------------------------ Body
    body = _sub(root, "FatturaElettronicaBody")

    generali = _sub(body, "DatiGenerali")
    doc = _sub(generali, "DatiGeneraliDocumento")
    _sub(doc, "TipoDocumento", "TD17")
    _sub(doc, "Divisa", "EUR")
    _sub(doc, "Data", data_doc.isoformat())
    _sub(doc, "Numero", numero)
    _sub(doc, "ImportoTotaleDocumento", f"{g.totale:.2f}")
    _sub(doc, "Causale",
         "Autofattura art. 17 c.2 DPR 633/72 - reverse charge su servizi "
         "ricevuti da soggetto non residente (art. 7-ter).")

    beni = _sub(body, "DatiBeniServizi")
    linea = _sub(beni, "DettaglioLinee")
    _sub(linea, "NumeroLinea", "1")
    _sub(linea, "Descrizione", g.fornitore.descrizione or "Servizi ricevuti da soggetto non residente")
    _sub(linea, "Quantita", "1.00")
    _sub(linea, "PrezzoUnitario", f"{g.imponibile:.2f}")
    _sub(linea, "PrezzoTotale", f"{g.imponibile:.2f}")
    _sub(linea, "AliquotaIVA", f"{g.aliquota:.2f}")
    if g.natura:
        _sub(linea, "Natura", g.natura)

    riep = _sub(beni, "DatiRiepilogo")
    _sub(riep, "AliquotaIVA", f"{g.aliquota:.2f}")
    if g.natura:
        _sub(riep, "Natura", g.natura)
    _sub(riep, "ImponibileImporto", f"{g.imponibile:.2f}")
    _sub(riep, "Imposta", f"{g.imposta:.2f}")
    _sub(riep, "EsigibilitaIVA", "I")
    if g.natura:
        _sub(riep, "RiferimentoNormativo",
             "Operazione non soggetta ad IVA ai sensi dell'art. 7-ter DPR 633/72")
    else:
        _sub(riep, "RiferimentoNormativo",
             "Inversione contabile art. 17 c.2 DPR 633/72")

    pag = _sub(body, "DatiPagamento")
    _sub(pag, "CondizioniPagamento", "TP02")  # pagamento completo
    dett = _sub(pag, "DettaglioPagamento")
    _sub(dett, "ModalitaPagamento", "MP08")   # carta di pagamento
    _sub(dett, "DataScadenzaPagamento", data_doc.isoformat())
    _sub(dett, "ImportoPagamento", f"{g.totale:.2f}")

    ET.indent(root, space="  ")
    return ET.ElementTree(root)


def nome_file(g: Gruppo, progressivo: int) -> str:
    """IT<piva>_<progressivo base36 a 5 char>.xml, come da convenzione SDI."""
    alfabeto = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    n, code = progressivo, ""
    while n:
        n, r = divmod(n, 36)
        code = alfabeto[r] + code
    return f"IT{COMMITTENTE['piva']}_{code.rjust(5, '0')}.xml"


# ------------------------------------------------------------- Riconciliazione
def riconcilia(movimenti, gruppi, esclusi, entrate, ignoti, out_dir: Path) -> bool:
    """Verifica che ogni euro dell'estratto conto sia stato assegnato. True se quadra."""
    ok = True
    print("\n" + "=" * 72)
    print("RICONCILIAZIONE CON L'ESTRATTO CONTO")
    print("=" * 72)

    tot_uscite = sum((-m["importo"] for m in movimenti if m["importo"] < 0), Decimal("0"))
    tot_entrate = sum((m["importo"] for m in entrate), Decimal("0"))
    tot_af = sum((g.imponibile for g in gruppi), Decimal("0"))
    tot_esclusi = sum((-m["importo"] for m in esclusi), Decimal("0"))
    tot_ignoti = sum((-m["importo"] for m in ignoti), Decimal("0"))

    n_uscite = len([m for m in movimenti if m["importo"] < 0])
    n_af = sum(len(g.movimenti) for g in gruppi)

    print(f"\nMovimenti letti: {len(movimenti)}  "
          f"(uscite {n_uscite}, entrate {len(entrate)})")
    print(f"  in autofattura      {n_af:>3} mov.  {tot_af:>10.2f} EUR")
    print(f"  esclusi motivati    {len(esclusi):>3} mov.  {tot_esclusi:>10.2f} EUR")
    print(f"  non classificati    {len(ignoti):>3} mov.  {tot_ignoti:>10.2f} EUR")
    print(f"  {'-' * 46}")
    somma = tot_af + tot_esclusi + tot_ignoti
    print(f"  somma               {n_af + len(esclusi) + len(ignoti):>3} mov.  {somma:>10.2f} EUR")
    print(f"  totale uscite CSV   {n_uscite:>3} mov.  {tot_uscite:>10.2f} EUR")

    if somma != tot_uscite or (n_af + len(esclusi) + len(ignoti)) != n_uscite:
        print("  ✗ NON QUADRA: dei movimenti in uscita non sono stati assegnati")
        ok = False
    else:
        print("  ✓ ogni movimento in uscita e' assegnato, somme identiche")

    print(f"\nEntrate/topup (mai autofattura): {tot_entrate:>10.2f} EUR")
    print(f"Saldo netto periodo:             {tot_entrate - tot_uscite:>10.2f} EUR")

    # Ricontrollo per fornitore leggendo gli XML scritti su disco.
    print("\nControllo XML generati contro i movimenti del CSV:")
    ns = {"p": "http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"}
    per_file = {}
    for path in sorted(out_dir.rglob("*.xml")):
        tree = ET.parse(path)
        r = tree.getroot()
        per_file[path] = {
            "denominazione": r.findtext(".//CedentePrestatore/DatiAnagrafici/Anagrafica/Denominazione"),
            "imponibile": Decimal(r.findtext(".//DatiRiepilogo/ImponibileImporto")),
            "imposta": Decimal(r.findtext(".//DatiRiepilogo/Imposta")),
            "totale": Decimal(r.findtext(".//DatiGeneraliDocumento/ImportoTotaleDocumento")),
            "linea": Decimal(r.findtext(".//DettaglioLinee/PrezzoTotale")),
            "pagamento": Decimal(r.findtext(".//DettaglioPagamento/ImportoPagamento")),
            "numero": r.findtext(".//DatiGeneraliDocumento/Numero"),
        }

    by_name = {g.fornitore.denominazione: g for g in gruppi}
    if len(per_file) != len(gruppi):
        print(f"  ✗ generati {len(per_file)} XML per {len(gruppi)} fornitori")
        ok = False

    for path, d in sorted(per_file.items(), key=lambda x: x[1]["denominazione"]):
        g = by_name.get(d["denominazione"])
        problemi = []
        if g is None:
            problemi.append("fornitore non presente nel raggruppamento CSV")
        else:
            atteso = g.imponibile
            if d["imponibile"] != atteso:
                problemi.append(f"imponibile XML {d['imponibile']} != CSV {atteso}")
            if d["linea"] != d["imponibile"]:
                problemi.append("riga != riepilogo")
            if d["imposta"] != g.imposta:
                problemi.append(f"imposta {d['imposta']} != attesa {g.imposta}")
            if d["totale"] != d["imponibile"] + d["imposta"]:
                problemi.append("totale != imponibile + imposta")
            if d["pagamento"] != d["totale"]:
                problemi.append("pagamento != totale documento")
        stato = "✓" if not problemi else "✗"
        if problemi:
            ok = False
        n_mov = len(g.movimenti) if g else 0
        print(f"  {stato} {d['numero']:<7} {d['denominazione']:<42} "
              f"{d['imponibile']:>8.2f} + IVA {d['imposta']:>7.2f} = {d['totale']:>8.2f} "
              f"({n_mov} mov.)")
        for p in problemi:
            print(f"      → {p}")

    if ignoti:
        print("\n⚠ Movimenti non classificati (decidili a mano):")
        for m in ignoti:
            print(f"    {m['data']}  {-m['importo']:>8.2f}  {m['descrizione']}")

    print("\nEsclusi dettaglio:")
    for m in sorted(esclusi, key=lambda x: x["importo"]):
        print(f"    {m['data']}  {-m['importo']:>8.2f}  {m['descrizione'][:38]:<38} {m['motivo']}")

    return ok


# ------------------------------------------------------------------------ main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("statement", type=Path, help="CSV estratto conto Revolut")
    ap.add_argument("--out", type=Path, default=ROOT / ".tmp" / "xml",
                    help="cartella di output (default .tmp/xml)")
    ap.add_argument("--start-number", type=int, required=True,
                    help="primo progressivo libero del sezionale (es. 30 -> 30/a)")
    ap.add_argument("--numeration", default="a", help="sezionale (default 'a')")
    ap.add_argument("--data", type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
                    default=None, help="data documento (default: ultimo giorno del periodo)")
    args = ap.parse_args()

    movimenti = leggi_movimenti(args.statement)
    if not movimenti:
        print("Nessun movimento COMPLETED trovato.", file=sys.stderr)
        return 1

    gruppi, esclusi, entrate, ignoti = classifica(movimenti)
    data_doc = args.data or max(m["data"] for m in movimenti)

    pronte = args.out / "pronte"
    verifica = args.out / "da_verificare"
    pronte.mkdir(parents=True, exist_ok=True)
    verifica.mkdir(parents=True, exist_ok=True)

    print(f"Periodo: {min(m['data'] for m in movimenti)} → {max(m['data'] for m in movimenti)}")
    print(f"Data documento: {data_doc}   Sezionale: /{args.numeration}   "
          f"Progressivo iniziale: {args.start_number}\n")

    for i, g in enumerate(gruppi):
        numero = f"{args.start_number + i}/{args.numeration}"
        progressivo = args.start_number + i
        tree = costruisci_xml(g, numero, data_doc, f"{progressivo:05d}")
        dest = verifica if g.fornitore.verifica else pronte
        path = dest / nome_file(g, progressivo)
        tree.write(path, encoding="UTF-8", xml_declaration=True)
        tag = "DA VERIFICARE" if g.fornitore.verifica else "pronta"
        print(f"  [{tag:<13}] {numero:<7} {g.fornitore.denominazione:<42} "
              f"{g.imponibile:>8.2f}  → {path.name}")
        if g.fornitore.verifica:
            print(f"       ⚠ {g.fornitore.verifica}")

    ok = riconcilia(movimenti, gruppi, esclusi, entrate, ignoti, args.out)

    print("\n" + "=" * 72)
    print("PROMEMORIA PRIMA DELL'INVIO AL SDI")
    print("=" * 72)
    print(f"  1. Sostituisci il placeholder {VAT_PLACEHOLDER} con la VAT reale del")
    print("     fornitore in ogni XML (CedentePrestatore/DatiAnagrafici/IdFiscaleIVA).")
    print(f"  2. Verifica che {args.start_number} sia davvero il primo progressivo libero")
    print(f"     del sezionale '{args.numeration}' su Fatture in Cloud.")
    print("  3. Svuota da_verificare/ solo dopo aver letto le fatture reali.")
    print("  4. Gli XML NON vanno committati: contengono dati fiscali.")

    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
