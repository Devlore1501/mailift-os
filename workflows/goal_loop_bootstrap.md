# Goal → Loop Bootstrap — dal prompt grezzo al piano esecutivo

## Obiettivo

Trasformare **qualsiasi prompt grezzo di Lorenzo** in un piano di lavoro
eseguibile, senza fargli scrivere brief lunghi. Prendo il suo input così com'è,
lo classifico, compilo una **Goal Card** standard, chiedo **una sola**
conferma-lampo (o parto diretto se il rischio è basso) ed eseguo iterando.

Questo workflow è il **primo passo mentale** di ogni task ambizioso o vago.
Non sostituisce gli altri workflow: se il goal ricade in un workflow esistente
(inbox, autofatture, klaviyo, lead, calendario…), la Goal Card punta a quello.

## Quando usarlo

- Lorenzo dà un obiettivo largo o poco definito: "voglio X", "sistemami Y",
  "porta avanti Z", "trovami…", "fai partire…".
- Frasi trigger: **"goal:"**, **"loop:"**, "obiettivo", "portami a", "voglio
  arrivare a", "ogni giorno/settimana fai", "monitora", "tieni sotto controllo".
- In dubbio all'inizio di un task non banale → applica comunque questo protocollo
  in testa (anche solo mentalmente) prima di agire.

Se il task è micro e ovvio (1 tool call, reversibile) **salta il protocollo** e
fallo: non serve una Goal Card per "che task ho oggi".

---

## Passo 0 — Classifica il prompt: Modo A o Modo B

| | **Modo A — Goal singolo** | **Modo B — Loop ricorrente** |
|---|---|---|
| Segnale | end-state che finisce ("arriva a", "fai", "crea", "trova") | ricorrenza ("ogni", "monitora", "tieni d'occhio", "quando succede X") |
| Esecuzione | scompongo → eseguo → riporto, **in questa sessione** | imposto un ciclo che si **ri-esegue da solo** nel tempo |
| Meccanismo | il loop è *interno* (do → check → adjust finché DoD) | il loop è *esterno* (ScheduleWakeup / cron / scheduled-tasks) |
| Fine | Definition of Done raggiunta | condizione di stop esplicita, o "finché non lo fermo" |

Se il prompt è ambiguo tra i due, **default a Modo A** e segnalo che posso
promuoverlo a ricorrente dopo.

---

## Passo 1 — Compila la Goal Card (sempre, entrambi i modi)

Riempi questi campi. Se un campo è vuoto e **non** è deducibile con giudizio
ragionevole, è l'unica cosa su cui chiedere.

```
🎯 GOAL CARD
─────────────────────────────────────────────
Goal        : <l'obiettivo riformulato in 1 frase, misurabile>
Modo        : A (singolo)  |  B (ricorrente)
Done quando : <criterio osservabile di "fatto". Numeri, non aggettivi>
Perché      : <cosa sblocca per Mailift / il cliente — 1 riga>
Input ho    : <dati/accessi già disponibili>
Input manca : <cosa serve e da dove lo prendo, o "niente">
Tool/WF     : <workflow o tool esistenti da usare — cerca prima in workflows/ e tools/>
Guardrail   : <azioni irreversibili o esterne che richiedono OK — vedi CLAUDE.md MAI FARE>
[solo Modo B]
Cadenza     : <ogni quanto: es. ogni giorno 8:30 / ogni ora / lun 9:00>
Trigger     : <cosa controlla a ogni giro>
Stop        : <quando smette: condizione o "finché Lorenzo non ferma">
```

**Regole di compilazione:**
1. **Cerca prima l'esistente.** Prima di inventare, controlla `workflows/` e
   `tools/`. Il campo Tool/WF deve puntare a ciò che c'è già.
2. **Done misurabile.** Mai "migliora le ads" → sì "3 campagne 322 in draft con
   copy Loss Aversion, pronte da review". Se non riesci a rendere il Done
   misurabile, quello è il vero blocco: chiedilo.
3. **Guardrail dalla CLAUDE.md.** Invio email/messaggi, modifiche live Klaviyo,
   pagamenti, delete → sempre in Guardrail, mai in autopilot.

---

## Passo 2 — Conferma-lampo (non un brief)

Mostra la Goal Card compilata e chiudi con **una** riga:

> "Parto così, o correggo qualcosa?"

**Salta la conferma e parti diretto** se *tutte* vere:
- Modo A, e
- nessun Guardrail (niente azioni irreversibili/esterne), e
- Input manca = niente.

**Chiedi sempre** se: Modo B (stai creando qualcosa di persistente), c'è un
Guardrail, o manca un input che non sai dedurre.

Coerente con CLAUDE.md: non fare domande inutili, ma fermati sul rischio alto.

---

## Passo 3 — Esegui

### Modo A — Loop interno (do → check → adjust)

```
1. Spezza il Goal in step ordinati (max ~5-7, ognuno = 1 risultato concreto).
2. Per ogni step:
   a. esegui (tool/workflow giusto)
   b. verifica il risultato REALE (rileggi lo stato, non fidarti a memoria)
   c. se fallisce → leggi l'errore, aggiusta, ritenta
      (se usa API a pagamento/crediti → chiedi prima di ri-lanciare)
3. Ripeti finché "Done quando" è vero.
4. Se scopri che il Goal era mal posto → fermati e ridefinisci con Lorenzo,
   non forzare un piano sbagliato.
```

Per goal grossi/paralleli valuta un **subagent** o, se Lorenzo lo chiede
esplicitamente ("usa un workflow" / "ultracode"), un **Workflow** multi-agente.
Di default resta in-sessione.

### Modo B — Loop esterno (si ri-esegue da solo)

Scegli il meccanismo per cadenza:

| Serve | Usa |
|---|---|
| Ciclo dentro questa sessione, cadenza flessibile, tu-lo-guidi | skill **`/loop`** (o `ScheduleWakeup` per ripianificare il risveglio) |
| Task cloud schedulato a cron (gira anche a Claude spento) | skill **`schedule`** / `scheduled-tasks` MCP / `CronCreate` |

Per Modo B definisci **sempre** nero su bianco: cadenza, cosa controlla, quale
azione fa a ogni giro, e la **condizione di stop**. Un loop senza stop è un bug,
non una feature. E se ogni giro può fare azioni esterne (email, post), il loro
invio resta **Guardrail** → prepara la bozza, non spedire in autonomo.

---

## Passo 4 — Riporta (formato fisso CLAUDE.md)

Chiudi sempre con:

- **Fatto** : cosa ho completato (con prova verificata alle spalle)
- **Resta** : cosa manca / prossimo step
- **Flag** : blocchi, rischi, decisioni che aspettano te

Per Modo B aggiungi: *"Loop attivo: <cadenza>. Prossimo giro: <quando>. Stop con: <come>."*

---

## Principio guida

Il tuo valore è **restringere l'incertezza prima di agire**, non produrre piani
lunghi. Una Goal Card di 8 righe ben fatta > un brief di 2 pagine. Se dopo la
Goal Card Lorenzo dice "sì", hai già eliminato il 90% dei modi di sbagliare.

Regola d'oro: **niente Done misurabile = niente esecuzione.** Prima lo rendi
misurabile, poi parti.
