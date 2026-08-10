# PRD — Content Engine Dashboard Mailift

*v1.0 · 2026-08-06 · Owner: Lorenzo Baretta · Stato: bozza da validare*

> Dashboard interna per sviluppare idee video, generare hook e didascalie, e gestire la pipeline di produzione contenuti — costruita sopra la knowledge base della skill `mailift-social-strategy`.

---

## 1. Problema

Oggi il processo contenuti vive in tre posti scollegati:
- **Le idee** nascono in chat con l'AI e si perdono nella cronologia.
- **Gli script e le didascalie** stanno in file markdown nel repo, difficili da consultare da telefono.
- **Lo stato di produzione** (girato / da girare / pubblicato / performance) non è tracciato da nessuna parte.

Risultato: ogni sessione di lavoro riparte da zero, i contenuti già scritti si dimenticano, e non c'è un punto unico dove vedere "cosa pubblico questa settimana e cosa devo ancora girare".

## 2. Obiettivo

Un'unica dashboard dove Lorenzo:
1. **Genera e archivia idee** classificate secondo il sistema (pilastro, tipo, livello di consapevolezza).
2. **Sviluppa un'idea in contenuto completo** (hook → script → didascalia → titolo a schermo) applicando le regole della knowledge base, con l'AI come motore.
3. **Gestisce la pipeline** dall'idea alla pubblicazione, con lo stato di ogni contenuto.
4. **Traccia i segnali che contano** (parole chiave commentate, salvataggi, DM) per decidere il mese successivo.

**Metrica di successo della dashboard:** tempo da idea a contenuto pronto < 15 minuti; zero contenuti scritti e mai usati per dimenticanza.

## 3. Utente

Uno solo: Lorenzo (founder-operator). Uso da desktop per le sessioni di scrittura, da telefono durante le riprese (leggere script/teleprompter) e la pubblicazione (copiare didascalie). Niente multi-utente, niente permessi.

## 4. Knowledge base integrata (il cuore)

La dashboard incorpora le regole della skill `mailift-social-strategy` come **vincoli attivi nei form e nei prompt**, non come documentazione da leggere:

| Regola | Come vive nella dashboard |
|---|---|
| Due assi: obiettivo (attrazione/consapevolezza/vendita) × pubblico (broad/MOF/BOF) | Campi obbligatori di classificazione su ogni idea; il broad blocca la parola "email" nell'hook con un warning |
| Tre famiglie di struttura (8 beat, raffica, yap 5 blocchi + variante 2° hook) | Selettore di template che genera lo scheletro giusto |
| Regole hook (≤12 parole, non nominare il meccanismo, accusare/contraddire, prime 3 parole cancellabili?) | Validatore automatico sull'hook: conteggio parole + checklist + warning sui pattern vietati |
| Pattern vietati (hook da guru: "cheat code", "il top 0,1%", "tattiche non etiche") | Blacklist con warning |
| Didascalia = riparte da dove finisce il video, prime 2 righe autonome, domanda finale qualificante, testo semplice senza markdown | Template di generazione + checklist |
| Titolo a schermo (4 sec, leggibile senza audio, contiene il numero) | Campo dedicato per contenuto |
| Guardrail (niente case study inventati, claim numerici flaggati "da verificare") | Flag `claim_da_verificare` su ogni contenuto, bloccante per lo stato "pronto per ads" |
| Voice of customer (citazioni verbatim dalle call) | Pannello laterale consultabile + iniettato nei prompt di generazione |
| Banca variabili ([pain], [risultato], [errore], [mito]) e banca hook per leva | Suggeritore nel form di creazione |
| Esercizio macro→micro compilato (5 pilastri → micro-argomenti) | Albero navigabile da cui si creano idee con un click |

**Fonte dati:** i file in `.claude/skills/mailift-social-strategy/` restano la single source of truth. La dashboard li legge (import/sync), non li duplica a mano.

## 5. Funzionalità

### 5.1 Idea Bank (MVP)
- Lista idee con classificazione: **pilastro** (Revenue Leak Audit · Flows · Campaign Engine · Segmentation · List Growth) · **tipo** (attrazione/consapevolezza/vendita) · **pubblico** (broad/MOF/BOF) · **formato** (yap, raffica, schema, screen-recording, metafora, lista muta 10s…) · priorità · note.
- Generazione idee via AI: input = pilastro + tipo + pubblico → output = 5-10 idee con angolo, pescate da macro→micro e VOC. Le già usate vengono escluse.
- Import del backlog esistente (le 50 idee sui 5 pilastri, i 21 broad, i 15 "ce l'hai ma non rende").
- Dedup: warning se un'idea nuova è troppo simile a una esistente.

### 5.2 Content Builder (MVP)
Flusso guidato in 4 passi partendo da un'idea:
1. **Nucleo** — una frase obbligatoria ("cosa si portano a casa"). Senza nucleo non si procede.
2. **Hook** — l'AI ne propone 3-5 varianti dalla banca hook per leva; il validatore controlla le regole; Lorenzo sceglie o riscrive. *L'hook si sceglie qui ma si può rivedere dopo lo script (regola: hook per ultimo).*
3. **Script** — generato sulla struttura scelta (8 beat / raffica / yap), con blocchi etichettati e stima parole/durata (60s ≈ 190, 30s ≈ 90). Regola di taglio integrata: "accorcia Body 2".
4. **Didascalia + titolo a schermo + CTA** — didascalia che continua il video (non riassume), keyword CTA scelta da un registro centrale (vedi 5.4), hashtag a 3 livelli.

Output: scheda contenuto completa, copiabile a blocchi (script per teleprompter, caption in testo semplice).

### 5.3 Pipeline / Calendario (MVP)
- Stati: **Idea → Scritto → Da girare → Girato → Montato → Programmato → Pubblicato**.
- Vista kanban + vista calendario settimanale (Lun/Mer/Ven/Dom, mercoledì = consapevolezza).
- Contatore del mix: % attrazione vs consapevolezza del mese vs target (75/25 in fase movimento; 40/40/20 in fase richieste) con alert se sbilanciato.
- Batch mode: selezioni N contenuti "da girare" → esporta un unico documento teleprompter per la sessione di ripresa.

### 5.4 Registro CTA & Risorse (MVP — è il guardrail più importante)
- Tabella keyword → risorsa promessa → stato risorsa (esiste / da creare / bozza).
- **Blocco pubblicazione**: un contenuto con CTA a keyword non passa a "Programmato" se la risorsa è "da creare". (Motivo: con un buyer già bruciato dalle agenzie, una risorsa promessa e non consegnata costa più del lead.)
- Keyword attive: CARRELLO, WELCOME, INBOX, POPUP, SEGMENTI, RIACQUISTO, WINBACK, OGGETTO, RIORDINO, VIP, BROWSE, PULIZIA, LISTA, LEAK.

### 5.5 Performance & Segnali (v2)
- Inserimento manuale (o import) per contenuto pubblicato: salvataggi, condivisioni, commenti con keyword, DM generati, compilazioni questionario.
- Classifica per **buyer signal**, non per views: "un video da 400 views con 2 DM di titolari batte 40.000 views con zero".
- Report mensile: keyword più richiesta → dolore più vivo → suggerimento temi mese successivo.

### 5.6 Reference Vault (v2)
- Archivio reference: link + trascrizione + scheletro estratto (via AI) + verdetto (usare/scartare) + motivo.
- Collegabile alla pipeline dell'agente analista (Apify → filtro anomalia ≥2× media profilo → Whisper → analisi), quando esisterà.

## 6. Requisiti non funzionali

- **Mobile-first per lettura/copia** (teleprompter e caption da telefono), desktop per scrittura.
- Didascalie sempre esportate in **testo semplice** (niente markdown — Instagram non lo renderizza).
- Copia one-tap per ogni blocco.
- Dati versionati o esportabili in markdown (compatibilità col repo, niente lock-in).
- Italiano.

## 7. Stack proposto

Due opzioni, in ordine di preferenza:

**Opzione A — dentro l'ecosistema esistente (consigliata per partire):**
- **Notion database** (idee, pipeline, registro CTA) + **n8n** (già nello stack per il sales setter) per le automazioni + chiamate API Claude per la generazione con i file skill come system prompt. Zero sviluppo frontend, live in giorni.

**Opzione B — webapp dedicata (quando l'opzione A sta stretta):**
- Next.js + Supabase (o la cartella `webapp/` già presente nel repo come base), API Claude (`claude-sonnet-5` per generazione bulk, `claude-fable-5` o `claude-opus-5` per la scrittura finale), sync della knowledge base dal repo GitHub.

## 8. Fuori scope (v1)

- Pubblicazione automatica sui social (si copia/incolla).
- Scraping automatico di TikTok/Instagram (pipeline separata, vedi PRD agente analista se/quando si farà).
- Editing video.
- Multi-utente / clienti dell'agenzia.

## 9. Fasi

| Fase | Contenuto | Criterio di uscita |
|---|---|---|
| **F1 — Fondamenta** | Idea Bank + import backlog esistente + Registro CTA | Tutte le idee della sessione vivono nella dashboard; nessuna CTA orfana |
| **F2 — Builder** | Content Builder con validatore hook e template 3 strutture | Un contenuto completo prodotto in <15 min |
| **F3 — Pipeline** | Kanban + calendario + mix-alert + batch teleprompter | Il piano mese 1 gestito interamente dalla dashboard |
| **F4 — Segnali** | Performance manuale + report keyword | Primo report mensile che orienta il mese 2 |

## 10. Rischi

- **La dashboard diventa un giocattolo**: il rischio più alto è passare più tempo a sistemare la dashboard che a girare video. Mitigazione: F1 in Notion (zero sviluppo), passare a F2+ solo se il flusso in Notion è usato davvero per 2+ settimane.
- **Drift dalla knowledge base**: se le regole vengono copiate a mano nella dashboard, divergono dalla skill. Mitigazione: la skill resta la fonte, la dashboard la importa.
- **Claim non verificati che finiscono in ads**: mitigato dal flag bloccante (5.4 / guardrail).
