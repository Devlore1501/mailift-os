# Wireframes — Autofatture Webapp v2

ASCII wireframes per le pagine principali. Layout shell comune: sidebar 240px a sinistra, topbar 56px, main content scrollabile. Dark mode di default.

---

## Dashboard (`/`)

```
+----------+------------------------------------------------------------+
| Sidebar  | TopBar  Dashboard                 [Cmd+K] [Dry-run|Live] |
|          +------------------------------------------------------------+
| ◉ Dash   |                                                            |
| + Nuovo  |  Benvenuto, Lorenzo                    [+ Nuovo run]       |
| ⟲ Stor.  |                                                            |
| ⚙ Imp.   |  +--------------+ +--------------+ +--------------+        |
|          |  | Run questo   | | Autofatture  | | Fornitori    |        |
|          |  | mese         | | create       | | monitorati   |        |
|          |  |   3          | |  42          | |   16         |        |
|          |  | ultimo: 8apr | | +12 vs mese  | |              |        |
|          |  +--------------+ +--------------+ +--------------+        |
|          |                                                            |
|          |  Stato sistema                                             |
|          |  +------------------------------------------------+        |
|          |  | ✓ Fatture in Cloud    token valido              |        |
|          |  | ✓ Database            .tmp/webapp.db            |        |
|          |  | ✓ Gmail personal      token ok                  |        |
|          |  | ✓ Gmail business      token ok                  |        |
|          |  | ⚠ Anthropic           quota bassa              |        |
|          |  +------------------------------------------------+        |
|          |                                                            |
|          |  Ultimi run                                                |
|          |  +------------------------------------------------+        |
|          |  | 8 apr 2026  revolut-mar.csv   16 create  ✓     |        |
|          |  | 7 mar 2026  revolut-feb.csv   14 create  ✓     |        |
|          |  | 6 feb 2026  revolut-gen.csv   12 create  ⚠     |        |
|          |  +------------------------------------------------+        |
|          |                                                            |
| ● ok     |                                                            |
| ☀ ↔      |                                                            |
+----------+------------------------------------------------------------+
```

---

## Nuovo Run — Wizard (`/new/*`)

Header con `StepProgress` sempre visibile. Navigazione Avanti/Indietro in footer.

### Step 1 — Upload

```
StepProgress:  ① Carica  ─ ② Elabora ─ ③ Verifica ─ ④ Rivedi ─ ⑤ Crea ─ ⑥ Esito
                 ^current

+------------------------------------------------------------+
|                                                            |
|            +----------------------------------+            |
|            |                                  |            |
|            |           ⬆ Carica CSV           |            |
|            |     Trascina o clicca per        |            |
|            |      selezionare il file         |            |
|            |                                  |            |
|            |   Formati: Revolut CSV / xlsx    |            |
|            +----------------------------------+            |
|                                                            |
|  File recenti                                              |
|  • revolut-mar.csv          8 apr 2026    [Riusa]          |
|  • revolut-feb.csv          7 mar 2026    [Riusa]          |
|                                                            |
|                                            [Annulla] [→]   |
+------------------------------------------------------------+
```

### Step 2 — Elabora (parse + classify)

```
StepProgress:  ✓ Carica  ─ ② Elabora ─ ③ Verifica ─ ④ Rivedi ─ ⑤ Crea ─ ⑥ Esito

+------------------------------------------------------------+
|  Elaborazione estratto conto                               |
|                                                            |
|  ✓ Parsing CSV                       112 righe             |
|  ◉ Classificazione transazioni       ████████░░ 64%        |
|  ⋯ Raggruppamento fornitori                                |
|                                                            |
|  Log live:                                                 |
|  [10:14] Trovato Lovable (US)                              |
|  [10:14] Trovato Apify (CZ)                                |
|  [10:14] Google Cloud Italy → escluso (IT 22%)             |
|                                                            |
+------------------------------------------------------------+
```

### Step 3 — Verifica fornitori

```
+------------------------------------------------------------+
|  Verifica fornitori via email          6/16 verificati     |
|  ████████████░░░░░░░░░░░░░░░░░░░░░░░░                      |
|                                                            |
|  +------------+--------+---------+-----------+---------+  |
|  | Fornitore  | Paese  | Stato   | PDF       | Bill to |  |
|  +------------+--------+---------+-----------+---------+  |
|  | Lovable    | 🌍 US  | ✓       | [1 PDF]   | Mailift |  |
|  | Apify      | 🇪🇺 CZ | ✓       | [2 PDF]   | Mailift |  |
|  | Gamma      | 🌍 US  | ⚠ mism. | [1 PDF]   | ⚠ other|  |
|  | DKV        | 🇪🇺 DE | ✓       | [1 PDF]   | Mailift |  |
|  | Klaviyo    | 🌍 US  | ⋯       | —         | —       |  |
|  | Higgsfield | ?      | ✗ 404   | —         | —       |  |
|  +------------+--------+---------+-----------+---------+  |
|                                                            |
|                                    [← Indietro] [Avanti →]|
+------------------------------------------------------------+
```

### Step 4 — Rivedi

```
+------------------------------------------------------------+
|  Rivedi autofatture                        16 righe        |
|                                                            |
|  ⓘ 2 transazioni italiane escluse (Google Cloud Italy)    |
|                                                            |
|  +---+-----------+--------+------+-------+---------+-----+|
|  | ☐ | Fornitore | Paese  | IVA  |  Netto| Warning |   … ||
|  +---+-----------+--------+------+-------+---------+-----+|
|  | ☑ | Lovable   | 🌍 US  |[0%NS]| € 45  |         | ⋯  ||
|  | ☑ | Apify     | 🇪🇺 CZ|[22%RC]| € 89  |         | ⋯  ||
|  | ☑ | Gamma     | 🌍 US  |[0%NS]| € 20  | ⚠      | ⋯  ||
|  | ☑ | DKV       | 🇪🇺 DE|[22%RC]|€ 112  |         | ⋯  ||
|  +---+-----------+--------+------+-------+---------+-----+|
|                                                            |
|  +------------------+                                      |
|  | Totale netto     |  € 3.112,45                          |
|  | Autofatture      |     16                               |
|  | Con warning      |      3                               |
|  +------------------+                                      |
|                                                            |
|                          [← Indietro]  [Crea autofatture →]|
+------------------------------------------------------------+
```

### Step 5 — Crea

```
+------------------------------------------------------------+
|  Creazione autofatture                   ████░░░ 5/16      |
|                                                            |
|  ✓ Lovable           nr. 37                                |
|  ✓ Apify             nr. 38                                |
|  ✓ DKV               nr. 39                                |
|  ✓ ElevenLabs        nr. 40                                |
|  ◉ Gamma             creazione...                          |
|  ⋯ Higgsfield        in coda                               |
|  ⋯ Anthropic         in coda                               |
|  ...                                                       |
|                                                            |
+------------------------------------------------------------+
```

### Step 6 — Esito

```
+------------------------------------------------------------+
|  ✓ 16 autofatture create                                   |
|                                                            |
|  +-------------+  +-------------+  +-------------+         |
|  | Lovable     |  | Apify       |  | DKV         |         |
|  | € 45,00     |  | € 89,00     |  | € 112,50    |         |
|  | TD17 nr.37  |  | TD17 nr.38  |  | TD17 nr.39  |         |
|  | [Apri FiC→] |  | [Apri FiC→] |  | [Apri FiC→] |         |
|  +-------------+  +-------------+  +-------------+         |
|                                                            |
|  ⚠ Ricorda di firmarle dalla tua area FiC.                 |
|                                                            |
|                     [Dashboard] [Nuovo run] [Esporta CSV] |
+------------------------------------------------------------+
```

---

## Storico (`/history`)

```
+------------------------------------------------------------+
|  Storico run                                               |
|                                                            |
|  Filtri:  [Data da] [Data a] [Stato ▾]   🔍 cerca...       |
|                                                            |
|  +---------+----------------+--------+-------+-------+----+|
|  | Data    | Estratto conto | Create | Error | Skip  |    ||
|  +---------+----------------+--------+-------+-------+----+|
|  | 8 apr   | revolut-mar.csv|   16   |   0   |   2   | ⋯ ||
|  | 7 mar   | revolut-feb.csv|   14   |   0   |   1   | ⋯ ||
|  | 6 feb   | revolut-gen.csv|   12   |   1   |   2   | ⋯ ||
|  +---------+----------------+--------+-------+-------+----+|
|                                                            |
+------------------------------------------------------------+
```

---

## Impostazioni (`/settings`)

```
+------------------------------------------------------------+
|  Impostazioni                                              |
|                                                            |
|  [ Override fornitori ] [ Info sistema ]                   |
|                                                            |
|  Override persistenti                     [+ Nuovo]        |
|  +-------------+--------+-------+-------+----------------+|
|  | Fornitore   | Paese  | vat_id| P.IVA | Nota           ||
|  +-------------+--------+-------+-------+----------------+|
|  | Higgsfield  | 🌍 US  |  10   |  —    | extra-UE force ||
|  | Klaviyo     | 🌍 US  |  10   |  —    | no autofattura ||
|  +-------------+--------+-------+-------+----------------+|
|                                                            |
+------------------------------------------------------------+
```
