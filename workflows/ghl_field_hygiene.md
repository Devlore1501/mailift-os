# Igiene dei custom field GHL

## Obiettivo

Mantenere i custom field GHL segmentabili: ogni campo a scelta multipla deve avere
**≥95% dei valori dentro le proprie opzioni**. Sotto quella soglia i segmenti e le
automazioni costruiti su quel campo smettono silenziosamente di funzionare — non
danno errore, danno risultati sbagliati.

## Perché esiste questo workflow

Il 21/07/2026 la picklist del fatturato è passata da 5 fasce (15k–80k) a 6 (10k–300k).
La modifica **non è retroattiva**: i 211 valori già scritti sono rimasti com'erano, e
da un giorno all'altro il 99% di essi si è trovato fuori dalle opzioni valide. Il campo
su cui si qualifica l'ICP è diventato inutilizzabile senza che nulla segnalasse niente.

Lo stesso è successo, in piccolo, a `Budget ads mensile`: la fascia `0 - 5000€` è stata
spezzata in `0 - 3000€` + `3000€ - 5000€`, lasciando orfani 77 contatti.

**La regola che ne deriva: non si tocca una picklist senza migrare i valori esistenti
e senza aggiornare il form a monte.** Le tre cose vanno insieme o non si fanno.

## Regola d'oro

> Modificare le opzioni di un campo **non** aggiorna né i valori già scritti sui
> contatti, né il form/survey che alimenta quel campo. Sono tre sistemi separati che
> vanno allineati a mano, nello stesso intervento.

## Tool

| Tool | Cosa fa | Sicurezza |
|---|---|---|
| `tools/ghl_fields_audit.py` | inventario, fill-rate, valori orfani, dizionario campi | **read-only** |
| `tools/ghl_normalize_values.py` | applica le mappature di unificazione | **dry-run per default** |
| `tools/ghl_value_mappings.json` | le regole di mappatura (dati, non codice) | — |
| `tools/ghl_reorganize_folders.py` | rinomina cartelle e sposta i campi | **dry-run per default**, con `--revert` |
| `tools/ghl_folder_layout.json` | quale campo in quale cartella, e in che ordine | — |

```bash
python tools/ghl_fields_audit.py              # stato di salute di tutti i campi
python tools/ghl_fields_audit.py --orphans    # solo i campi con problemi
python tools/ghl_fields_audit.py --field <id> # tutti i valori di un campo
python tools/ghl_fields_audit.py --dictionary # dizionario nome ↔ chiave ↔ id
python tools/ghl_fields_audit.py --dump       # backup in .tmp/ (SEMPRE prima di scrivere)
```

## Procedura: modificare le opzioni di un campo

L'ordine non è negoziabile. Invertirlo apre una finestra in cui i valori non ancora
migrati risultano orfani.

1. **Backup** — `python tools/ghl_fields_audit.py --dump`
   GHL non ha undo sulle scritture dei custom field. Il file `.tmp/ghl_backup_<data>.json`
   è l'unico modo di tornare indietro. **Non è committato**: contiene email e dati di
   528 contatti, e il repo non è il posto giusto per la PII. Non cancellarlo finché la
   migrazione non è verificata.
2. **Regola** — aggiungi la mappatura in `tools/ghl_value_mappings.json`
3. **Dry-run** — `python tools/ghl_normalize_values.py` e **leggi il diff**
4. **Applica** — `python tools/ghl_normalize_values.py --apply`
   (aggiunge le opzioni nuove → migra i valori → rimuove le vecchie)
5. **Allinea il form a monte** — da UI GHL, altrimenti i nuovi invii ricreano orfani
6. **Verifica** — `python tools/ghl_fields_audit.py --orphans`

## Trappole verificate

**I valori devono combaciare carattere per carattere.** En-dash (`–`, U+2013) contro
trattino normale, spazi doppi, spazi in coda: sono tutti significativi. L'opzione
`50k –  80k €/mese` ha davvero un doppio spazio. Nota già presente in
[workers/ghl-form-proxy.js:31](../workers/ghl-form-proxy.js).

**`fieldKey` e `dataType` non sono modificabili dopo la creazione.** Il nome sì. Per
cambiare chiave o tipo serve creare un campo nuovo e migrare i valori — cambiando l'id,
quindi aggiornando anche blueprint Make e worker che lo referenziano. Scegli bene il
nome alla creazione.

**L'API `POST`/`PUT` vuole `options`, la lettura restituisce `picklistOptions`.**
Verificato il 01/08/2026 su un campo usa-e-getta.

**Le cartelle si gestiscono via API, con un'eccezione.** Verificato il 01/08/2026:

| Operazione | Via API |
|---|---|
| rinominare una cartella custom | ✅ `PUT` con `name` |
| spostare un campo tra cartelle | ✅ `PUT` con `parentId` |
| ordinare i campi dentro la cartella | ✅ `PUT` con `position` |
| **creare** una cartella nuova | ❌ `dataType` non accetta `FOLDER` |
| toccare le cartelle standard | ❌ `Cannot update standard folder or field` |

Le cartelle standard (`Contact`, `General Info`, `Additional Info`) non si rinominano né
si cancellano: si possono solo svuotare spostandone i campi altrove. Non potendo creare
cartelle nuove, la riorganizzazione ha riusato le 7 cartelle custom già esistenti
rinominandole — vedi `tools/ghl_folder_layout.json`.

**`position` parte da 10, mai da 0.** GHL ignora `position=0` e lascia il campo dov'era:
il primo campo di ogni cartella finirebbe in fondo. Costa un giro di scritture inutile
per accorgersene.

**Un campo a zero valori non è necessariamente morto.** I 6 campi camerali (PEC, Sede
legale, Soci e quote, Fatturato camerale, Dati camerali, Dossier pre-call) sono a zero
ma cablati ai blueprint Make di [lead_research.md](lead_research.md). Prima di cancellare
qualsiasi campo, cercare il suo id nel repo:

```bash
grep -rn "<field_id>" --include=*.py --include=*.json --include=*.js --exclude-dir=node_modules .
```

## Campi con chiave non allineata

Cinque campi hanno il `fieldKey` ereditato da uno snapshot GHL americano di un altro
settore (call center). La chiave non è modificabile: l'unica difesa è conoscerla.
`python tools/ghl_fields_audit.py --dictionary` li marca con ⚠️.

| Campo | Chiave reale |
|---|---|
| In quale settore operi? | `contact.do_you_currently_have_the_ability_to_listen_to_recordings_of_conversations_between_new_leads_and_your_staff` |
| Quanto sei soddisfatto del tuo EMAIL MARKETING? | `contact.can_your_staff_send_text_message_to_leads_from_a_business_number_without_using_a_personal_phone` |
| Fatturato ecommerce 1 | `contact.do_you_have_a_way_of_knowing_your_staff_is_calling_new_leads_within_five_minutes` |
| Budget ads mensile | `contact.radio_2877z` |
| Dimensione lista email | `contact.grandezza_lista` |

Chi costruisce un merge tag o un filtro su questi campi deve usare la chiave della
colonna di destra, non quella che il nome lascerebbe supporre.

## I due campi fatturato

Ce ne sono due, ed è voluto che restino separati:

- **`bW87MPPTFNr51QBtNZmG`** — `Quale è il tuo attuale fatturato Mensile? 1`, in
  `02 · Qualifica ICP`. È il campo vivo, scritto da landing e worker.
- **`beYFGQ1sbcsop9KtxPko`** — `Fatturato ecommerce 1`, in `99 · Legacy`. Duplicato
  storico, non più alimentato.

Il legacy aveva una scala tutta sua (`0 a 25k€ mese`, `tra 50k€ e 100k€ mese`) e 63
valori su 66 erano orfani della propria picklist. Dal 01/08/2026 usa **le stesse 6
fasce** del canonico: sta in Legacy ma resta visibile negli elenchi contatti, e con
due scale diverse sembrava che il dato fosse sporco anche dove non lo era.

I 27 contatti che avevano il fatturato **solo** sul legacy sono stati consolidati sul
canonico, che passa da 211 a **238 valori**.

Dove entrambi sono valorizzati (66 contatti) **61 concordano e 5 no**: sono lead che
hanno risposto due volte, a distanza di tempo, dichiarando cifre diverse. Non è un
errore di migrazione — è una contraddizione del lead. Due dei cinque sono già taggati
`fake`, e contraddirsi sul fatturato è di per sé un segnale.

## Qualifica fatturato

Il campo grezzo del fatturato (`bW87MPPTFNr51QBtNZmG`) resta storicamente sporco: 36
formati diversi, mensile e annuo mescolati. **Non usarlo per segmentare.**

Usare il campo derivato **`Qualifica fatturato`**, popolato da
`ghl_normalize_values.py --only qualifica`: legge il campo principale e, se vuoto,
ricade su `Fatturato ecommerce 1`. Copre 238 contatti, risolti al 96%.

Valori: `Sotto soglia (<25k/mese)` · `ICP (≥25k/mese)` · `Da riconfermare`.

Non esiste una fascia "Enterprise": nessuno dei 528 contatti dichiara oltre 300k/mese,
e tenerla spingerebbe in `Da riconfermare` i lead il cui valore è aperto verso l'alto
(`oltre 80k €/mese`, `200K€+`).

La classificazione avviene **solo se l'intervallo dichiarato ricade interamente dentro
una fascia**. Se scavalca la soglia → `Da riconfermare`. Da questo campo dipende chi
viene chiamato: meglio un dato dichiarato incerto che una qualifica inventata.

## ⏳ In sospeso: rimozione opzioni fatturato vecchie

Il 01/08/2026 la soglia di qualifica è passata da 10k a 15k/mese. GHL ha
**temporaneamente 8 opzioni** sul campo `bW87MPPTFNr51QBtNZmG`: le 6 nuove più
`Meno di 10.000€/mese` e `10.000 – 25.000€/mese`.

Le vecchie **devono restare finché landing e worker non sono deployati**: fino a
quel momento la landing in produzione manda ancora le etichette vecchie, e
rimuoverle farebbe nascere orfano ogni opt-in della finestra intermedia.

Lo storico è già stato migrato: **210 valori su 211** sono sulle etichette nuove,
l'unico residuo è `3000€ - 5000€` (un valore di budget ads finito nel campo
sbagliato). Le due opzioni vecchie hanno **zero contatti** — restano solo per
coprire la finestra fino al deploy.

I lead che entrano in quella finestra scrivono ancora le etichette vecchie: il
`value_map` contiene già `Meno di 10.000€/mese` e `10.000 – 25.000€/mese` proprio
per riassorbirli. Dopo il deploy va quindi rilanciata la migrazione **prima** di
togliere le opzioni, altrimenti quei lead restano orfani.

Sequenza post-deploy:

```bash
python tools/ghl_normalize_values.py --only picklist --apply
```

poi in `ghl_value_mappings.json` sostituire `picklist_finale` con il contenuto di
`picklist_dopo_deploy`, rilanciare lo stesso comando, e ricalcolare la qualifica:

```bash
python tools/ghl_normalize_values.py --only qualifica --apply
```

Verifica finale — non devono comparire etichette vecchie:

```bash
python tools/ghl_fields_audit.py --field bW87MPPTFNr51QBtNZmG
```

**La soglia è cablata in 10 punti**, non nei 4 ovvi. Oltre a landing, worker,
`EmailMarketingSurvey.tsx` e `reportCalculations.ts`, va aggiornata anche la
riga di squalifica `EmailMarketingSurvey.tsx` (`value === 'under-15k'`), la
edge function `supabase/functions/send-partial-webhooks`, e le label di display
in `RecoverableLeads.tsx`, `InsightCard.tsx`, `DropoffAnalytics.tsx`. La riga di
squalifica è la più insidiosa: se resta indietro il quiz **smette di squalificare
senza dare errore**.

Nota: `inTarget` in `DropoffAnalytics.tsx` è l'**ICP** (25k), non la soglia di
qualifica (15k). Sono due concetti diversi, non allinearli per errore.

## ⏳ In sospeso: cancellare il custom "Il tuo sito Web?"

Il sito viveva in due posti: il campo standard `website` e il custom
`Il tuo sito Web?` (`gXkqSQ3G2cnXRsNjs8RC`). Il 01/08/2026 i valori sono stati
unificati sullo standard: **279 contatti** (erano 249), e **zero** contatti hanno
il custom valorizzato senza lo standard. Il custom è quindi ridondante.

Il campo è stato spostato in `99 · Legacy — non usare`, **non cancellato**: finché
esiste, il workflow che lo referenzia continua a funzionare. La cancellazione
resta possibile in futuro, ma solo dopo questo passo:

> Nel workflow GHL che alimenta la ricerca pre-call, la chiave webhook `sito` è
> mappata su `{{contact.il_tuo_sito_web}}`. Va ripuntata su `{{contact.website}}`
> **da UI**. Cancellare il campo prima significa spegnere in silenzio la ricerca
> pre-call, che dal sito ricava P.IVA e dati camerali.

Fatto quello, la cancellazione è sicura:

```bash
python -c "import sys; sys.path.insert(0,'tools'); import ghl_client as g; print(g.delete_custom_field('gXkqSQ3G2cnXRsNjs8RC'))"
```

Effetto collaterale positivo del ripuntamento: la copertura della chiave `sito`
passa dal 29% al 53%.

Backup del campo standard: `.tmp/ghl_website_backup_2026-08-01.json` — il backup
dei custom field **non copre i campi standard**, per quelli serve il suo.

Un conflitto resta aperto: `p.fragment580@passinbox.com` ha `pfragment.com` sullo
standard e `pfragment.eu` sul custom, e nessuno dei due combacia col dominio
dell'email. Da decidere a mano prima di cancellare, altrimenti si perde `.eu`.

## Struttura cartelle

Le cartelle seguono le **fasi del processo di vendita**, non la fonte del dato. Prima
erano nominate per origine (`Survey | Survey 0`, `GPT SETTER`) e 28 campi su 64 stavano
in `Additional Info`: aprendo una scheda non si capiva quale campo servisse quando.

| Cartella | Campi | Cosa contiene |
|---|---|---|
| `01 · Attribuzione & Sorgente` | 8 | UTM, landing, perché ha scaricato |
| `02 · Qualifica ICP` | 14 | fatturato, settore, lista, budget — **`Qualifica fatturato` è il primo** |
| `03 · Dati azienda` | 8 | P.IVA, ragione sociale, dati camerali |
| `04 · Pre-call & Dossier` | 5 | dossier, spunti di apertura, icebreak |
| `05 · Setting & Follow-up` | 5 | classificazione, azione consigliata, link report |
| `06 · Contratto & Onboarding` | 1 | logo cliente |
| `99 · Legacy — non usare` | 23 | duplicati e campi morti |

`99 · Legacy` **non significa "da cancellare"**: contiene campi che hanno ancora dati
(`Nome` 118 usi, `Cognome` 47, `Fatturato ecommerce 1` 66). Restano leggibili, ma non
vanno più usati per cose nuove. La cancellazione è una decisione separata, da prendere
solo dopo aver verificato che il campo non sia referenziato in form, workflow o Make.

Per modificare il layout: si edita `tools/ghl_folder_layout.json` e si rilancia il tool.
L'ordine delle liste nel JSON è l'ordine dei campi nella scheda contatto.

## Manutenzione

Lanciare `python tools/ghl_fields_audit.py --orphans` dopo ogni modifica a un form o a
una picklist, e comunque a ogni revisione trimestrale del CRM. Se un campo scende sotto
il 95%, qualcuno ha cambiato qualcosa a monte senza migrare.
