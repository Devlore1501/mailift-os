# Creative

Sorgenti HTML delle creative, renderizzate a 1080×1080 con Chrome headless:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new --disable-gpu --hide-scrollbars \
  --window-size=1080,1080 --screenshot=creative/ordini_v6.png \
  "file://$PWD/creative/ordini_v6.html"
```

Perché in HTML e non in un tool di design: il testo si controlla al carattere,
le varianti si fanno in dieci secondi, e il file sta in git accanto ai dati che
lo hanno motivato. Poi si testa prima di spendere:

```bash
python3 tools/simula_creative.py creative/ordini_v6.png
```

## ordini_v6 — la prima che seleziona

Le cinque `ordini_v1..v5` (27/07/2026) segnavano tutte **−2**: attiravano più
fuori target che in target. Fermavano 14 su 15 in target, ma quasi nessuno
cliccava. Il motivo, ripetuto da tutti: numeri senza contesto («da dove escono
€8.500?») e un messaggio che diceva «sei indietro» — quindi parlava a chi è
indietro.

La v6 cambia tre cose e passa a **+2**:
1. il numero è ancorato a un fatturato («a €60.000/mese…»), quindi credibile
   e auto-qualificante
2. il qualificatore 25k+ è sulla creative, non solo sulla landing
3. il messaggio presuppone un business che già funziona: non «hai i flow
   spenti» ma «sei sotto il benchmark»

Estetica editoriale, niente clipart: Andrea (120k/mese) scartava la v1
scrivendo «sembra un volantino del discount».
