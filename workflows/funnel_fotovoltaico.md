# Funnel fotovoltaico B2C — quiz di qualifica → lead in GHL + Sheet

## Obiettivo

Generare lead B2C fotovoltaico qualificati (proprietari di casa, tetto proprio,
bolletta alta, intenzione a breve) tramite un quiz-calcolatore statico, e
consegnarli già segmentati HOT/WARM/COLD dentro GHL + un Google Sheet.

Il modello ricalca il funnel calcolatore Mailift (`landing/optin-calcolatore.html`
+ `workers/ghl-form-proxy.js`): landing → quiz → gate contatti → risultato.
La differenza è che qui il risultato **è** la lead magnet: la stima di risparmio.

## Componenti

| Pezzo | File | Cosa fa |
|---|---|---|
| Sito | `landing/fotovoltaico/index.html` | Landing + quiz 8 domande + calcolo + risultato. Single file, zero dipendenze. |
| Worker | `workers/pv-lead-proxy.js` | Riceve il lead, upsert GHL + nota, riga su Sheet, evento Meta CAPI. |
| Config worker | `workers/wrangler-pv.toml` | Deploy config (segreti via `wrangler secret put`). |
| Sheet | `workers/sheet-webhook.gs` | Apps Script da incollare nel foglio: append riga. |

## Setup (una volta)

1. **Google Sheet** — crea il foglio "Lead Fotovoltaico", Estensioni → Apps Script,
   incolla `workers/sheet-webhook.gs`, distribuisci come App web (accesso: chiunque),
   copia l'URL `/exec`.
2. **Worker**
   ```bash
   cd workers
   wrangler secret put GHL_API_KEY --config wrangler-pv.toml       # pit-… scope contacts.write
   wrangler secret put GHL_LOCATION_ID --config wrangler-pv.toml
   wrangler secret put SHEET_WEBHOOK_URL --config wrangler-pv.toml # URL /exec del passo 1
   wrangler deploy --config wrangler-pv.toml
   ```
3. **Sito** — in `landing/fotovoltaico/index.html`, in cima allo `<script>`:
   - `CFG.ENDPOINT` = URL del Worker
   - `CFG.META_PIXEL_ID` = pixel (solo se si fa traffico a pagamento; va aggiunto
     anche lo snippet `fbq` in `<head>`)
   - sostituisci il link "Privacy policy" (oggi è un `alert` segnaposto) e il
     brand "SolarCheck" con quello definitivo.
4. **Hosting** — qualsiasi statico: Cloudflare Pages, Vercel, GHL custom page.
   Nessun build step: si carica il file e basta.

## Scoring — come nasce HOT/WARM/COLD

Punti sommati sulle risposte (definiti in `STEPS[].opts[].pt`):

| Dimensione | Peso max | Perché |
|---|---|---|
| Tipo immobile | 30 | Villetta = tetto disponibile subito |
| Proprietà | 25 | Chi non possiede non può firmare |
| Bolletta mensile | 30 | Sotto i 60 €/mese il payback è troppo lungo |
| Tempistica | 25 | Distingue il compratore dal curioso |
| Tetto + consumi + batteria | ~28 | Fattori tecnici, pesano meno |

Soglie: **HOT ≥ 75**, **WARM 50-74**, **COLD < 50**.

**Squalifica dura** (`stop:true`, non arriva al calcolo): affitto, appartamento
in condominio con tetto comune. Vengono mostrati il perché e una raccolta email
facoltativa → tag `fv-non-idoneo`. Meglio perdere il lead che bruciarlo con un
venditore che non può vendergli niente.

## Cosa arriva in GHL

- Contatto upsert con nome, email, telefono, CAP.
- Tag: `fotovoltaico-quiz`, `fv-hot|warm|cold`, `cap-<CAP>`, più
  `fv-urgente` / `fv-non-idoneo` / `fv-vuole-preventivi` quando applicabile.
- **Nota** con tutte le risposte + la stima esatta mostrata al lead + attribuzione.
  (Non usiamo custom field: la location GHL non ne ha per il fotovoltaico. Se un
  giorno si creano, vanno mappati in `CAMPI_NOTA` dentro il Worker.)

Aggancia le automation GHL al trigger **Contact Tag = `fv-hot`** per il richiamo
prioritario entro 24h — è la promessa fatta nel risultato del quiz.

## Modello di calcolo (`stima()` nell'HTML)

```
spesa annua      = bolletta media mensile × 12
consumo kWh      = spesa annua / PREZZO_KWH
kWp consigliato  = consumo / resa zona   (arrotondato a 0,5 · clamp 2-8 kWp)
produzione       = kWp × resa zona       (Nord 1150 / Centro ~1340 / Sud 1450-1480 kWh/kWp)
autoconsumo %    = profilo consumi (28-45%) + 30pp con batteria, cap 85%
risparmio annuo  = autoconsumo × PREZZO_KWH + immesso × RITIRO_KWH
costo            = kWp × COSTO_KWP + batteria × COSTO_KWH_BATT
payback          = costo × (1 − DETRAZIONE) / risparmio annuo
```

Tutti i parametri stanno nell'oggetto `CFG` in cima allo script: quando cambia il
prezzo dell'energia o il costo al kWp si tocca **solo lì**.

⚠️ **DETRAZIONE è a 0,50 (prima casa).** L'aliquota italiana cambia con le leggi
di bilancio: verificarla prima di ogni campagna, altrimenti il payback mostrato
è sbagliato in modo dimostrabile — ed è il numero su cui il lead decide.

## Guardrail

- Il quiz **non promette** rendimenti: ogni schermata di risultato porta il
  disclaimer "stima indicativa, non è un preventivo". Non rimuoverlo.
- Consenso privacy obbligatorio (checkbox separata dal consenso al ricontatto:
  sono due basi giuridiche diverse).
- Prima di mandare traffico serve una privacy policy reale linkata: oggi il link
  apre un `alert` segnaposto apposta per non partire per sbaglio.
- Il token GHL vive solo nel Worker. Mai nel file HTML.

## Da fare quando il funnel gira

1. Privacy policy + cookie banner (se si aggiunge il pixel).
2. Sequenza email di nurturing per i WARM (il report via email è già promesso).
3. Verificare la rete di installatori per CAP prima di promettere "3 preventivi
   dalla tua zona": la promessa è nel risultato del quiz.
