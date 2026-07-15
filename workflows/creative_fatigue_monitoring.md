# Creative Fatigue Monitoring (Meta Ads)

## Obiettivo
Rilevare in anticipo quando un annuncio Meta (account ads Mailift) sta
esaurendo il pubblico indirizzabile, così da sostituire il concept prima
che il ROAS crolli.

## Perché serve (contesto Andromeda)
Con l'update **Andromeda** di Meta (2025), l'algoritmo scala aggressivamente
i creative vincenti e si affida sempre più alla creatività come segnale
principale (meno targeting dettagliato disponibile per privacy). Risultato:
un concept creativo ora esaurisce il pubblico indirizzabile in **2-3
settimane**, contro le 6+ settimane pre-Andromeda. Anche i top performer
possono calare dopo 2-4 settimane.

Regola pratica consigliata: **8-12 concept distinti per campagna**, 2-3
varianti per concept, refresh dei sottoperformanti **settimanale**, nuovi
concept ogni **2 settimane**.

Fonte: [next2ad.com — Creative fatigue: gestire le ads su Meta dopo Andromeda](https://next2ad.com/creative-fatigue-meta-ads-andromeda/)

## Quando usarlo
- **Manuale**: Lorenzo dice "controlla la creative fatigue" o "quali
  annunci stanno calando".
- **Consigliato**: insieme alla review settimanale ads (stesso giorno del
  weekly Klaviyo report), per intercettare il calo prima che il weekend
  bruci budget su un concept già esausto.

## Tool
```
python tools/creative_fatigue_detector.py            # ultimi 28gg, solo annunci ACTIVE
python tools/creative_fatigue_detector.py --days 35   # finestra più ampia
python tools/creative_fatigue_detector.py --all       # include anche PAUSED

# Senza token FB_ACCESS_TOKEN (es. sessione cloud senza .env): export manuale
python tools/creative_fatigue_detector.py --csv percorso/export.csv
```

Richiede `FB_ACCESS_TOKEN` e `FB_AD_ACCOUNT_ID` nel `.env` (stessi usati da
`tools/fb_ads_client.py`).

### Modalità `--csv` (nessun token richiesto)
Se non hai accesso al `.env` (es. Claude Code on the web, o vuoi un check
rapido senza esporre credenziali), esporta da Ads Manager un breakdown
**giornaliero per annuncio** (colonne minime: `Reporting starts`, `Ad name`,
`Ad delivery`, `Reach`, `Frequency`, `Impressions`, `CTR (all)`) e passa il
file con `--csv`. Limiti rispetto alla modalità API:
- **Età non disponibile** (l'export non include `created_time`): la
  severità si basa solo su trend CTR/frequency, confrontando la prima metà
  vs la seconda metà dei giorni con delivery reale nel file.
- Con pochi giorni di dati reali nel file (es. campagna appena (ri)lanciata),
  i delta % sono rumorosi — leggi i risultati come indicativi, non come
  fatica creativa confermata, finché non ci sono almeno 2 settimane di
  storico continuo.

## Come legge i segnali
Per ogni annuncio con almeno 500 impressioni nel periodo, il tool calcola:
- **Età** (giorni da `created_time`)
- **CTR** dell'ultima settimana vs quella precedente (Δ%)
- **Frequency** dell'ultima settimana vs quella precedente (Δ%)

**Soglie:**
| Segnale | WATCH 🟡 | URGENTE 🔴 |
|---|---|---|
| Età annuncio | ≥ 14gg | ≥ 21gg |
| Calo CTR sett/sett | ≥ -10% | ≥ -20% |
| Aumento frequency sett/sett | ≥ +15% | — |

Un annuncio URGENTE ha probabilmente esaurito il pubblico: il concept va
sostituito, non solo la variante (nuovo hook/angle, non solo un nuovo
colore o headline). Un annuncio WATCH va monitorato la settimana
successiva e serve preparare una variante di ricambio.

## Esecuzione
1. Esegui `python tools/creative_fatigue_detector.py`.
2. Leggi il riepilogo finale (N urgenti / N da monitorare / N OK).
3. Per ogni 🔴 URGENTE: proponi a Lorenzo la pausa o il refresh del
   concept (nuovo angle, non variante cosmetica).
4. Per ogni 🟡 WATCH: segnala che va tenuto d'occhio, nessuna azione
   immediata richiesta.
5. **Mai** pausare/modificare annunci live senza OK esplicito di Lorenzo
   (vedi CLAUDE.md — "MAI FARE").

## Edge case noti
- **Meno di 2 settimane di storico**: il tool non calcola `ctr_change`/
  `freq_change` (mostra solo l'ultima settimana) — normale per campagne
  appena lanciate.
- **Account con pochi annunci sopra soglia impressioni**: se il report è
  vuoto, il traffico è troppo basso per un segnale affidabile; aumenta
  `--days` o aspetta un ciclo di spesa più lungo.
- **Meta non espone "audience saturation" via API**: il tool usa CTR +
  frequency + età come proxy, non una metrica nativa di fatica.

## Apprendimenti
(Vuoto. Popolare man mano che emergono pattern specifici sull'account
Mailift — es. soglie da tarare per il funnel Flow Health Score vs
info-prodotti.)
