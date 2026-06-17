"""
Client minimale Fatture in Cloud per la creazione di autofatture (self_supplier_invoice).

Espone:
    - FicClient.find_or_create_supplier(name, country, vat_number, ...)
    - FicClient.create_self_supplier_invoice(...) -> dict con id e numero documento
    - FicClient.refresh_if_needed() -> rinnova access_token usando il refresh_token

Riferimenti API: https://developers.fattureincloud.it/api-reference/
Tipologie documento autofattura coperte: TD17, TD18, TD19 (reverse charge UE / extra-UE).
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import certifi
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = Path.home() / ".secrets" / "mailift" / ".env"
if not ENV_PATH.exists():
    ENV_PATH = ROOT / ".env"  # Fallback per compatibilità

API_BASE = "https://api-v2.fattureincloud.it"
TOKEN_URL = f"{API_BASE}/oauth/token"

# Codici paese UE (per stabilire se applicare il fix CAP/Provincia/PIVA extra-UE)
_EU_COUNTRIES = {
    "IT", "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR",
    "HU", "IE", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE",
}

# Mappa codice ISO -> nome italiano del paese (FiC vuole il nome italiano in entity.country)
_COUNTRY_NAMES_IT: dict[str, str] = {
    "IT": "Italia", "AT": "Austria", "BE": "Belgio", "BG": "Bulgaria", "HR": "Croazia",
    "CY": "Cipro", "CZ": "Repubblica Ceca", "DK": "Danimarca", "EE": "Estonia", "FI": "Finlandia",
    "FR": "Francia", "DE": "Germania", "GR": "Grecia", "HU": "Ungheria", "IE": "Irlanda",
    "LV": "Lettonia", "LT": "Lituania", "LU": "Lussemburgo", "MT": "Malta",
    "NL": "Paesi Bassi", "PL": "Polonia", "PT": "Portogallo", "RO": "Romania",
    "SK": "Slovacchia", "SI": "Slovenia", "ES": "Spagna", "SE": "Svezia",
    "GB": "Regno Unito", "UK": "Regno Unito", "CH": "Svizzera", "NO": "Norvegia",
    "IS": "Islanda", "LI": "Liechtenstein",
    "US": "Stati Uniti", "CA": "Canada", "MX": "Messico", "BR": "Brasile",
    "AU": "Australia", "NZ": "Nuova Zelanda", "JP": "Giappone", "CN": "Cina",
    "IN": "India", "SG": "Singapore", "HK": "Hong Kong", "AE": "Emirati Arabi Uniti",
    "IL": "Israele", "TR": "Turchia", "RU": "Russia", "UA": "Ucraina",
    "ZA": "Sudafrica", "EG": "Egitto", "AR": "Argentina", "CL": "Cile",
    "KR": "Corea del Sud", "ID": "Indonesia", "TH": "Thailandia", "VN": "Vietnam",
    "SM": "San Marino", "VA": "Città del Vaticano",
}


def _country_it_name(iso: str) -> str:
    """Ritorna il nome italiano del paese da codice ISO. Fallback al codice stesso."""
    if not iso:
        return ""
    return _COUNTRY_NAMES_IT.get(iso.upper(), iso.upper())


def _regime_fiscale_for_country(country_iso: str) -> str:
    """Ritorna il codice RegimeFiscale del fornitore in base al paese.

    - Fornitori UE → RF01 (Ordinario)
    - Fornitori extra-UE → RF18 (Altro)
    """
    iso = (country_iso or "").upper()
    if iso in _EU_COUNTRIES:
        return "RF01"
    return "RF18"


def _update_env(updates: dict[str, str]) -> None:
    if not ENV_PATH.exists():
        return
    lines = ENV_PATH.read_text().splitlines()
    seen: set[str] = set()
    for i, line in enumerate(lines):
        if "=" in line and not line.strip().startswith("#"):
            key = line.split("=", 1)[0].strip()
            if key in updates:
                lines[i] = f"{key}={updates[key]}"
                seen.add(key)
    for k, v in updates.items():
        if k not in seen:
            lines.append(f"{k}={v}")
    ENV_PATH.write_text("\n".join(lines) + "\n")


# Suffissi societari da rimuovere quando si normalizza un nome per il matching
_COMPANY_SUFFIX_TOKENS = {
    "inc", "incorporated", "ltd", "limited", "llc", "lcc", "pbc", "co",
    "srl", "spa", "sas", "snc", "sa", "sl", "sarl",
    "gmbh", "ug", "ag", "kg",
    "ab", "oy", "oyj", "oü", "uab", "as", "bv", "nv",
    "se", "se.", "se,", "société", "société anonyme",
    "s.r.l.", "s.r.l", "s.p.a.", "s.p.a", "s.a.s.", "s.r.o.", "sro", "s.r.o",
    "ltda", "lda", "plc",
}

_PUNCT_RE = re.compile(r"[.,()&/]+")
_WS_RE = re.compile(r"\s+")


def _normalize_name(name: str) -> str:
    """Normalizza un nome aziendale per matching: lowercase, senza punteggiatura, senza suffissi societari."""
    if not name:
        return ""
    n = name.lower().strip()
    n = _PUNCT_RE.sub(" ", n)
    n = _WS_RE.sub(" ", n).strip()
    tokens = [t for t in n.split(" ") if t and t not in _COMPANY_SUFFIX_TOKENS]
    return " ".join(tokens)


@dataclass
class AutofatturaLine:
    description: str
    amount_net: float
    vat_rate: float = 22.0


@dataclass
class AutofatturaInput:
    """Dati per emettere un'autofattura reverse charge.

    type_doc: codice TD17 / TD18 / TD19 (Agenzia Entrate)
    supplier_name: ragione sociale fornitore
    supplier_country: codice ISO 2 (es. IE, US, NL)
    supplier_vat_number: P.IVA o tax id (vuoto se sconosciuto)
    invoice_date: data documento autofattura — di norma data di emissione (oggi)
    period_label: descrizione del periodo coperto (es. "gennaio-marzo 2026")
    lines: 1 o più righe accorpate
    ref_invoice_number: riferimento numero fattura del fornitore (campo SDI 2.1.6.2)
    ref_invoice_date: riferimento data fattura del fornitore (campo SDI 2.1.6.3)
    currency: codice valuta (default EUR)
    """

    type_doc: str
    supplier_name: str
    supplier_country: str
    supplier_vat_number: str
    invoice_date: date
    period_label: str
    lines: list[AutofatturaLine]
    ref_invoice_number: str = ""
    ref_invoice_date: date | None = None
    currency: str = "EUR"

    @property
    def total_net(self) -> float:
        return sum(l.amount_net for l in self.lines)


class FicClient:
    def __init__(self) -> None:
        load_dotenv(ENV_PATH)
        self.client_id = os.environ["FIC_CLIENT_ID"]
        self.client_secret = os.environ["FIC_CLIENT_SECRET"]
        self.access_token = os.environ.get("FIC_ACCESS_TOKEN", "")
        self.refresh_token = os.environ.get("FIC_REFRESH_TOKEN", "")
        self.company_id = os.environ["FIC_COMPANY_ID"]
        if not self.access_token:
            raise RuntimeError("FIC_ACCESS_TOKEN mancante. Esegui prima tools/fic_device_setup.py")
        self._vat_types_cache: list[dict] | None = None
        self._reverse_charge_vat_id: int | None = None
        self._payment_accounts_cache: list[dict] | None = None
        self._payment_account_id: int | None = None
        self._suppliers_cache: list[dict] | None = None

    # ------------------------------------------------------------------ HTTP
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        url = f"{API_BASE}{path}"
        resp = requests.request(method, url, headers=self._headers(), timeout=30, **kwargs)
        if resp.status_code == 401 and self.refresh_token:
            self.refresh_if_needed(force=True)
            resp = requests.request(method, url, headers=self._headers(), timeout=30, **kwargs)
        if resp.status_code >= 400:
            raise RuntimeError(f"FiC API {method} {path} -> {resp.status_code}: {resp.text}")
        if resp.content:
            return resp.json()
        return {}

    def refresh_if_needed(self, force: bool = False) -> None:
        if not force or not self.refresh_token:
            return
        resp = requests.post(
            TOKEN_URL,
            json={
                "grant_type": "refresh_token",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
            },
            timeout=30,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Refresh token fallito: {resp.status_code} {resp.text}")
        tok = resp.json()
        self.access_token = tok["access_token"]
        if "refresh_token" in tok:
            self.refresh_token = tok["refresh_token"]
        _update_env(
            {
                "FIC_ACCESS_TOKEN": self.access_token,
                "FIC_REFRESH_TOKEN": self.refresh_token,
            }
        )

    # ------------------------------------------------------------- VAT types
    def get_vat_id_for_autofattura(self, country_iso: str | None = None) -> int:
        """Risolve l'id dell'aliquota IVA da usare per le autofatture passive.

        Scelta country-aware (verificata leggendo fatture reali + pattern del
        commercialista, sessione 2026-04-08):

            - Fornitore UE                → id=0  (IVA 22% standard, reverse charge)
            - Fornitore extra-UE          → id=10 ("Oper. non soggetta, art.7 ter", 0%)

        Motivazione fiscale: sia le fatture dei fornitori UE che extra-UE arrivano
        con 0% VAT + dicitura reverse charge. Lato autofattura italiana, però, i
        servizi generici B2B intra-UE si riportano con IVA 22% neutralizzata
        (art. 7-ter DPR 633/72, standard), mentre i servizi da fornitori extra-UE
        vanno come "operazioni non soggette" a 0% (fuori sistema IVA UE).

        Override manuale: se `FIC_VAT_ID` è settato nel `.env`, ha la precedenza
        su tutto (utile per debug/test).
        """
        # 1) Override manuale via env (forte, per test)
        env_id = os.getenv("FIC_VAT_ID")
        if env_id is not None and env_id.strip():
            try:
                return int(env_id)
            except ValueError:
                pass
        # 2) Country-aware: extra-UE -> id=10, UE (o ignoto) -> id=0
        if country_iso:
            iso = country_iso.upper()
            if iso and iso not in _EU_COUNTRIES:
                return 10
        return 0

    # Alias retrocompatibile (vecchio nome usato in altre parti del codice)
    def get_reverse_charge_vat_id(self, country_iso: str | None = None) -> int:
        return self.get_vat_id_for_autofattura(country_iso)

    def get_vat_value(self, vat_id: int) -> float:
        """Restituisce il valore percentuale dell'aliquota IVA dato il suo id.

        Es. id=0 -> 22.0, id=10 -> 0.0, id=11 -> 0.0.
        """
        if self._vat_types_cache is None:
            data = self._request("GET", f"/c/{self.company_id}/info/vat_types")
            self._vat_types_cache = data.get("data") or []
        for v in self._vat_types_cache:
            if v.get("id") == vat_id:
                return float(v.get("value") or 0)
        # Fallback: id=0 in FiC è di solito 22%
        return 22.0 if vat_id == 0 else 0.0

    def get_payment_account_id(self, prefer_name: str | None = None) -> int:
        if self._payment_account_id is not None:
            return self._payment_account_id
        if self._payment_accounts_cache is None:
            data = self._request("GET", f"/c/{self.company_id}/info/payment_accounts")
            self._payment_accounts_cache = data.get("data") or []
        if not self._payment_accounts_cache:
            raise RuntimeError(
                "Nessun conto di saldo trovato sull'account FiC. "
                "Configurane uno da Impostazioni > Conti di saldo prima di rieseguire."
            )
        target = (prefer_name or os.getenv("FIC_PAYMENT_ACCOUNT_NAME") or "revolut").lower()
        for p in self._payment_accounts_cache:
            if target in (p.get("name") or "").lower():
                self._payment_account_id = p["id"]
                return p["id"]
        self._payment_account_id = self._payment_accounts_cache[0]["id"]
        return self._payment_account_id

    # ------------------------------------------------------------- Suppliers
    def _load_suppliers(self) -> list[dict]:
        if self._suppliers_cache is None:
            data = self._request(
                "GET",
                f"/c/{self.company_id}/entities/suppliers",
                params={"per_page": 100, "sort": "-id"},
            )
            self._suppliers_cache = data.get("data") or []
        return self._suppliers_cache

    def find_or_create_supplier(
        self,
        name: str,
        country: str,
        vat_number: str = "",
    ) -> dict[str, Any]:
        """Trova un fornitore esistente con matching robusto, altrimenti lo crea.

        Priorita di matching:
            1. vat_number esatto (se fornito)
            2. nome normalizzato (lowercase, senza suffissi societari, senza punteggiatura)
            3. substring "kernel" del nome normalizzato
        """
        suppliers = self._load_suppliers()

        # 1) Match per vat_number
        vat_clean = (vat_number or "").strip().upper()
        if vat_clean:
            for s in suppliers:
                sv = (s.get("vat_number") or "").strip().upper()
                if sv and sv == vat_clean:
                    return s

        # 2) Match per nome normalizzato esatto
        target_norm = _normalize_name(name)
        if target_norm:
            for s in suppliers:
                if _normalize_name(s.get("name") or "") == target_norm:
                    return s

            # 3) Match per substring "kernel" (es. "google" matcha "Google Ireland Limited")
            kernel = target_norm.split(" ")[0] if target_norm else ""
            if len(kernel) >= 4:
                candidates = [
                    s for s in suppliers
                    if kernel in _normalize_name(s.get("name") or "")
                ]
                if len(candidates) == 1:
                    return candidates[0]

        # Nessun match -> crea nuovo.
        # Pattern osservato nelle autofatture del commercialista che sono state
        # inviate e accettate dal SDI:
        #   - address_province: "ee" LOWERCASE (non "EE")
        #   - address_postal_code: sempre "00000" per fornitori esteri
        #   - vat_number: VUOTO per fornitori esteri (anche extra-UE), NON "OO99999999999"
        #   - address_city: nome del paese in lowercase se la citta' non e' nota
        #   - address_street: obbligatorio, placeholder "Estero" se non noto
        country_iso = (country or "").upper()
        is_extra_ue = country_iso and country_iso not in _EU_COUNTRIES
        destinatario_code = os.getenv("FIC_DESTINATARIO_CODE", "M5UXCR1")
        country_it = _country_it_name(country_iso)

        payload_data: dict[str, Any] = {
            "name": name,
            "type": "company",
            "country": country_it or None,
            "country_iso": country_iso or None,
            "vat_number": vat_number or "",  # vuoto se sconosciuto (non placeholder)
            "ei_code": destinatario_code,
        }
        # Fornitori esteri: pattern SDI-valido come usato dal commercialista
        if country_iso and country_iso != "IT":
            payload_data["address_street"] = "Estero"
            payload_data["address_city"] = (country_it or country_iso).lower()
            payload_data["address_postal_code"] = "00000"
            payload_data["address_province"] = "ee"

        payload_data = {k: v for k, v in payload_data.items() if v is not None}

        created = self._request(
            "POST", f"/c/{self.company_id}/entities/suppliers", json={"data": payload_data}
        )
        new_supplier = created.get("data", {}) or {}
        # Aggiorna la cache con il nuovo fornitore
        if self._suppliers_cache is not None:
            self._suppliers_cache.append(new_supplier)
        return new_supplier

    # ------------------------------------------------------ Self invoices
    def create_self_supplier_invoice(self, af: AutofatturaInput) -> dict[str, Any]:
        """Crea un'autofattura passiva (TD17/TD18/TD19) come issued_document.

        Imposta:
            - type=self_supplier_invoice + e_invoice=true (per attivare i campi ei_data)
            - ei_data.invoice_number/invoice_date come riferimento alla fattura originale
              del fornitore (campo SDI 2.1.6 DatiFattureCollegate)
            - vat_id risolto dinamicamente (Inversione contabile art.7 ter)
            - sezionale configurabile via FIC_NUMERATION (default "a")
            - payments_list[0].status="reversed" (Stornato), come prevede la guida FiC
              per le autofatture
            - items_list di lunghezza 1: descrizione aggregata + importo totale

        Il documento risulta NON inviato al SDI finche' l'utente non clicca
        "Verifica formale" e "Firma e invia" sulla UI di Fatture in Cloud.
        """
        supplier = self.find_or_create_supplier(
            name=af.supplier_name,
            country=af.supplier_country,
            vat_number=af.supplier_vat_number,
        )

        country_iso = (af.supplier_country or "").upper() or None
        vat_id = self.get_vat_id_for_autofattura(country_iso)
        vat_value = self.get_vat_value(vat_id)
        # Una sola riga, descrizione NEUTRA del servizio (no date, no conteggi addebiti)
        total_net = round(af.total_net, 2)
        # Per vat_id=10 (non soggetta, 0%) il lordo coincide col netto.
        # Per vat_id=0 (22% reverse charge UE) il lordo = netto * 1.22.
        total_gross = round(total_net * (1 + vat_value / 100.0), 2)
        line_name = (af.lines[0].description if af.lines else f"Servizi {af.supplier_name}")[:200]
        items_list = [
            {
                "name": line_name,
                "qty": 1,
                "net_price": total_net,
                "gross_price": total_gross,
                "vat": {"id": vat_id},
            }
        ]

        subject = f"Autofattura {af.type_doc} - {af.supplier_name}"[:200]
        numeration = os.getenv("FIC_NUMERATION", "a")
        destinatario_code = os.getenv("FIC_DESTINATARIO_CODE", "M5UXCR1")
        regime_fiscale = _regime_fiscale_for_country(country_iso or "")

        payment: dict[str, Any] = {
            "amount": total_gross,  # importo LORDO (netto + IVA), deve coincidere con amount_due
            "due_date": af.invoice_date.isoformat(),
            "status": "reversed",  # = "Stornato" sulla UI FiC, default per autofatture
            "payment_account": {"id": self.get_payment_account_id()},
        }

        # ei_data: campi gestionali. I DatiFattureCollegate (od_number/od_date) li
        # compila l'utente sulla UI prima dell'invio SDI, oppure verranno popolati
        # in futuro dall'enrichment via email scraping.
        ei_data: dict[str, Any] = {
            "payment_method": os.getenv("FIC_PAYMENT_METHOD", "MP05"),  # MP05 = bonifico
        }

        # ei_raw: contiene i campi della fattura elettronica XML SDI veri,
        # in particolare TipoDocumento (TD17/18/19) e RegimeFiscale del fornitore.
        # Senza questi due, FiC non riesce a generare l'XML valido per il SDI.
        ei_raw: dict[str, Any] = {
            "FatturaElettronicaBody": {
                "DatiGenerali": {
                    "DatiGeneraliDocumento": {
                        "TipoDocumento": af.type_doc,  # TD17/TD18/TD19
                    }
                }
            },
            "FatturaElettronicaHeader": {
                "CedentePrestatore": {
                    "DatiAnagrafici": {
                        "RegimeFiscale": regime_fiscale,  # RF01 UE, RF18 extra-UE
                    }
                }
            },
        }

        # entity: riprendi tutti i campi dal supplier esistente e fai override dei
        # campi critici per il SDI. country va in italiano (es. "Stati Uniti"),
        # ei_code = M5UXCR1 (codice destinatario di Mailift / committente).
        # Per fornitori esteri, applica i default SDI-validi anche se il supplier
        # già esiste in FiC ma ha i campi indirizzo vuoti (fix bug giugno 2026).
        is_foreign = country_iso and country_iso != "IT"
        country_it_name = _country_it_name(country_iso or "")
        entity: dict[str, Any] = {
            "id": supplier.get("id"),
            "name": supplier.get("name") or af.supplier_name,
            "country": country_it_name or supplier.get("country") or None,
            "country_iso": country_iso,
            "vat_number": af.supplier_vat_number or supplier.get("vat_number") or "",
            "ei_code": destinatario_code,
            "address_street": supplier.get("address_street") or ("Estero" if is_foreign else None),
            "address_postal_code": supplier.get("address_postal_code") or ("00000" if is_foreign else None),
            "address_city": supplier.get("address_city") or ((country_it_name or country_iso or "").lower() if is_foreign else None),
            "address_province": supplier.get("address_province") or ("ee" if is_foreign else None),
        }
        entity = {k: v for k, v in entity.items() if v is not None}

        payload = {
            "data": {
                "type": "self_supplier_invoice",
                "numeration": numeration,
                "entity": entity,
                "date": af.invoice_date.isoformat(),
                "currency": {"id": af.currency},
                "subject": subject,
                "visible_subject": subject,
                "items_list": items_list,
                "payments_list": [payment],
                "e_invoice": True,
                "ei_data": ei_data,
                "ei_raw": ei_raw,
                "notes": (
                    "Operazione soggetta a reverse charge ai sensi dell'art. 17 c.2 / "
                    "art. 7-ter DPR 633/72. Come destinatario del documento si intende il "
                    "cessionario/committente."
                ),
            }
        }

        result = self._request(
            "POST", f"/c/{self.company_id}/issued_documents", json=payload
        )
        return result.get("data", {})
