# Interactions — Autofatture Webapp v2

Linee guida per micro-interazioni, shortcut, loading state, toast, errori.

---

## 1. Keyboard shortcuts

| Shortcut | Azione | Scope |
|---|---|---|
| `Cmd/Ctrl + K` | Apre command palette (`CommandDialog`) | Globale (priorità lower, da implementare in fase 2) |
| `Cmd/Ctrl + U` | Trigger upload (apre file picker su step Upload) | Wizard Upload |
| `Cmd/Ctrl + Enter` | Conferma step corrente (equivale a "Avanti →") | Wizard |
| `Esc` | Torna indietro di uno step / chiude dialog / chiude popover | Globale |
| `Cmd/Ctrl + D` | Toggle dark/light (mirror del bottone sidebar) | Globale |
| `/` | Focus nella search bar in History | History |
| `J` / `K` | Naviga su/giù nelle righe di una tabella focused | Tabelle review/history (futuro) |

Tutti i bottoni d'azione devono avere focus ring visibile (`focus-visible:ring-2 focus-visible:ring-ring`). Radix UI ci dà focus trap gratis dentro dialog/sheet/popover.

---

## 2. Toast patterns (sonner)

Mount `<Toaster />` una sola volta in `main.tsx`. Tutti i toast sono richiamati via `import { toast } from "@/components/ui/sonner"`.

| Situazione | Variant | Esempio |
|---|---|---|
| Azione utente riuscita | `toast.success(...)` | `toast.success("Override salvato")` |
| Errore di rete / API | `toast.error(...)` | `toast.error("Creazione fallita", { description: err.message })` |
| Warning non bloccante | `toast.warning(...)` | `toast.warning("3 fornitori senza PDF")` |
| Info/neutro | `toast.info(...)` | `toast.info("Job avviato", { description: "Classificazione in corso" })` |
| Loading con promessa | `toast.promise(p, { loading, success, error })` | upload file, creazione batch |

**Regole**:
- Toast per **azioni esplicite** dell'utente (click, submit, upload).
- **NO toast** per risposte polling di background (usa badge/indicator in place).
- **NO toast** per validazione form inline (usa `FormMessage`).
- Descrizione opzionale sotto il titolo: usa per ID job, riferimenti, link breve.
- Max durata: 5s success/info, 8s warning, 10s error.
- `richColors` attivato: success/error hanno già colori semantici.

---

## 3. Loading states

Tre pattern distinti — scegli in base alla **forma** del contenuto che sta caricando.

### 3.1 Skeleton (preferito)
Per contenuti **strutturati** dove conosci la forma finale.
- Tabelle: una `Skeleton` per riga (3–5 righe), stessa altezza della row reale.
- Card KPI: `Skeleton` rettangolare per il valore, piccolo per la label.
- PDF preview: `Skeleton` grande al posto dell'iframe + skeleton per il selector.

```tsx
{loading ? <Skeleton className="h-5 w-24" /> : <span>{value}</span>}
```

### 3.2 Progress bar
Per operazioni **con percentuale nota** (job con totale/current).
- Upload file (bytes).
- Classificazione (transazioni totali).
- Verifica fornitori (fornitori totali).
- Creazione autofatture (righe totali).

Mostra sempre anche la label `N/M` accanto alla barra.

### 3.3 Spinner
Evitare. Usa solo per **micro-azioni inline** (bottone con azione async): icona `Loader2` in animazione `animate-spin` dentro il bottone. Mai uno spinner al centro della pagina.

```tsx
<Button disabled={isPending}>
  {isPending && <Loader2 className="h-4 w-4 animate-spin" />}
  Salva
</Button>
```

---

## 4. Error states

| Tipo errore | Presentazione |
|---|---|
| Errore di rete temporaneo | `toast.error()` + retry button nel toast action |
| Errore validazione form | `<FormMessage />` inline sotto il campo, rosso |
| Errore di pagina (query fallita) | `<Alert variant="destructive">` al top della pagina, con bottone "Riprova" |
| Backend down totale | Banner full-width in TopBar + `HealthIndicator` rosso |
| 404 dati | `<EmptyState>` con icona `FileQuestion` |
| Job fallito | Toast + `StepProgress` step in stato `error` + Alert con dettagli |

**Messaggio errore**: sempre in italiano, orientato all'azione. Non "Internal server error" ma "Creazione fallita. Riprova tra qualche secondo.". Mostra dettaglio tecnico solo in `description` collassabile o sotto una <details> per debug.

---

## 5. Dry-run mode

Quando `EnvironmentSwitch` è su Dry-run:
- Banner full-width fucsia sotto il TopBar: "🧪 Modalità simulazione — nessuna autofattura verrà creata".
- Tutti i bottoni "Crea" mantengono label normale ma il job invia flag `dry_run=true`.
- Nei Results, badge "Simulazione" visibile su ogni card.
- Lo stato è persistito in `localStorage` e re-idratato al reload (vedi `EnvironmentSwitch.getStoredEnvironment`).
- L'evento `window.dispatchEvent(new CustomEvent("autofatture:env"))` permette ai React Query hooks di invalidare i param quando l'utente cambia ambiente mid-flusso.

---

## 6. Table interactions (Review page)

- **Checkbox sul singolo row**: esclude la riga senza rimuoverla (visual: `opacity-50` + `line-through` sul nome).
- **Checkbox header**: select/deselect all.
- **Override inline country**: click sul `SupplierBadge` apre `Popover` con `Select` dei paesi → conferma con Enter.
- **Warning icon**: hover mostra `Tooltip` con messaggio + link portale.
- **Row action kebab (⋯)**: `DropdownMenu` con "Apri PDF", "Escludi", "Override persistente…".
- **Footer sticky**: totali aggiornati in tempo reale quando cambiano gli exclude.

---

## 7. Transitions & motion

- Default hover/focus: `transition-colors 150ms`.
- Dialog open/close: Radix animation CSS (fade + zoom 95→100).
- Sheet: slide da destra, 300ms ease-out.
- Sidebar collapse: `transition-[width] 200ms`.
- Stepper "current" dot: `animate-pulse-ring` (pulse 1.8s infinite).
- Mai usare `animation-duration > 400ms` per elementi UI — l'app deve percepirsi reattiva.
- `prefers-reduced-motion` rispettato: Tailwind `motion-safe:`/`motion-reduce:` quando pertinente (da aggiungere su animazioni opzionali).

---

## 8. Focus management

- Dopo azione riuscita, riporta focus al primo elemento utile: bottone "Avanti" dopo upload, primo input dopo aver aperto dialog.
- `Dialog` e `Sheet` implementano focus trap di default (Radix).
- Mai `outline: none` senza un sostituto visibile.
- Skip link opzionale "Vai al contenuto" (futuro, non blocca v2).

---

## 9. Copy / tono di voce

- Italiano, informale ma professionale. "Carica", "Verifica", "Rivedi", non "Upload"/"Review".
- Verbi all'imperativo nei CTA: "Crea autofatture", "Salva override".
- Mai "click here". Link autodescrittivi: "Apri su Fatture in Cloud".
- Errori: soggetto + cosa fare. "Token scaduto. Rigenera dalla pagina Impostazioni."
- Numeri: sempre formattati con `formatCurrency()` / `formatDate()`.
