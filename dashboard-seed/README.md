# Seed per la Content Engine Dashboard

File pronti per l'import iniziale (F1) della dashboard.

| File | Destinazione | Contenuto |
|---|---|---|
| `idea-bank.csv` | tabella `ideas` | 69 idee classificate (pilastro, tipo, pubblico, formato, priorità, stato). Include: 50 idee sprint sui 5 pilastri, i broad della settimana yap, i formati a raffica, e i contenuti del mese 1 con stato reale (6 già girati = `usata`) |
| `cta-keywords.csv` | tabella `cta_keywords` | Le 14 keyword con risorsa promessa e stato. **4 marcate URGENTE**: promesse in video già girati ma la risorsa non esiste |

## Documenti per la sezione Knowledge

Da incollare/caricare nella sezione Knowledge dell'app (fonte: questo repo):

| Documento | Percorso | Tipo (per il routing nei prompt) |
|---|---|---|
| Regole generali + guardrail | `.claude/skills/mailift-social-strategy/SKILL.md` | regole (tutti i passi) |
| Voice of customer | `.claude/skills/mailift-social-strategy/references/voice-of-customer.md` | VOC (idee, hook, caption) |
| Banca hook per leva | `.claude/skills/mailift-social-strategy/references/banca-hook.md` | hook |
| Template script + regole caption | `.claude/skills/mailift-social-strategy/references/script-templates.md` | script, caption |
| Macro→micro + piano editoriale | `.claude/skills/mailift-social-strategy/references/piano-editoriale.md` | idee |
| Processo di scripting | `.claude/skills/mailift-social-strategy/references/processo-scripting.md` | script |

## Note per l'import

- CSV con header, virgole come separatore, campi quotati.
- Valori `stato`: `idea` / `in lavorazione` (script già scritto nel repo) / `usata` (video già girato).
- Le note segnalano dove sta lo script pronto e i claim numerici da verificare prima dell'uso in ads.
- Blacklist broad consigliata per il validatore: `email, e-mail, mail, newsletter, klaviyo, flow, flusso, deliverability, open rate, segmento`.
