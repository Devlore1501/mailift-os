# Design System — Autofatture Webapp v2

Riferimento estetico: Linear + Vercel dashboard + Raycast. Dark mode first, sobrio, denso ma leggibile, italiano.

Stack: Tailwind 3 + shadcn/ui (Radix UI primitives) + lucide-react icons + sonner toast + class-variance-authority.

---

## 1. Design tokens

Tutti i colori sono definiti come CSS variables HSL in `src/index.css` (light in `:root`, dark in `.dark`). Tailwind li espone come classi `bg-*`, `text-*`, `border-*`.

### 1.1 Colors

| Token | Ruolo | Light (HSL) | Dark (HSL) |
|---|---|---|---|
| `background` | Sfondo pagina | `0 0% 100%` | `240 10% 3.9%` |
| `foreground` | Testo base | `240 10% 3.9%` | `0 0% 98%` |
| `card` | Sfondo card | `0 0% 100%` | `240 6% 7%` |
| `popover` | Sfondo dropdown/tooltip | `0 0% 100%` | `240 6% 7%` |
| `primary` | Accent blu (CTA) | `221 83% 53%` | `217 91% 60%` |
| `secondary` | Sfondo soft | `240 4.8% 95.9%` | `240 4% 12%` |
| `muted` | Sfondo muted | `240 4.8% 95.9%` | `240 4% 12%` |
| `muted-foreground` | Testo muted | `240 3.8% 46.1%` | `240 5% 64.9%` |
| `accent` | Hover neutro | `240 4.8% 95.9%` | `240 4% 14%` |
| `border` | Bordi soft | `240 5.9% 90%` | `240 4% 16%` |
| `ring` | Focus ring | `221 83% 53%` | `217 91% 60%` |
| `destructive` | Rosso errore | `0 84% 60%` | `0 72% 51%` |
| `success` | Verde ok | `142 71% 45%` | `142 65% 45%` |
| `warning` | Ambra attenzione | `38 92% 50%` | `38 92% 50%` |

**Badge semantici** (non CSS vars, variants Tailwind diretti in `Badge`):
- `blue` — UE / 22% reverse charge
- `purple` — extra-UE / 0% non soggetta
- `amber` — warning / 0% inversione contabile
- `red` — Italia (errore fiscale) / errori
- `zinc` — sconosciuto / neutro

### 1.2 Spacing & layout
- Griglia base 4px (Tailwind default): usa `gap-2`, `gap-3`, `gap-4`, `gap-6`.
- Sidebar: 240px espansa, 56px collassata. TopBar: 56px alta.
- Main content: `px-6 py-6`, max-width lasciato libero (tabelle piene).
- Card padding: `p-6` per header/content, `p-5` per card KPI compatte.

### 1.3 Typography
- Font: Inter (fallback system sans), caricato come `font-family` CSS del `body`.
- Feature settings: `cv11`, `ss01` per zero con barra e gamba della `g`.
- Scale:
  - `text-2xl font-semibold` — page title
  - `text-lg font-semibold` — card title
  - `text-sm` — body / tabella
  - `text-xs` — badge, meta, caption
  - `text-[11px] uppercase tracking-wide` — eyebrow label (KPI, sidebar brand)
- Numeri: `tabular-nums` per colonne monetarie.

### 1.4 Radius
- `--radius: 0.5rem` → `rounded-lg` (card, dialog), `rounded-md` (input, button), `rounded-sm` (checkbox, menu item).

### 1.5 Shadows
- `shadow-sm` per card.
- `shadow-md` per popover/tooltip.
- `shadow-lg` per dialog.
- Mai box-shadow colorati (no glow); ombre sempre nere con bassa opacità.

### 1.6 Animation
- `animate-pulse-ring` — halo attorno al cerchio "current" in StepProgress.
- `animate-accordion-down/up` — Radix accordion.
- Transizioni hover: `transition-colors` (150–200ms default).

---

## 2. Componenti UI (shadcn base)

Tutti in `src/components/ui/`. Indipendenti, riusabili, tipati, con variants via `class-variance-authority`.

| File | Export | Uso |
|---|---|---|
| `button.tsx` | `Button`, `buttonVariants` | Variants: `default`, `outline`, `secondary`, `ghost`, `link`, `destructive`. Sizes: `default`, `sm`, `lg`, `icon`. |
| `card.tsx` | `Card`, `CardHeader`, `CardTitle`, `CardDescription`, `CardContent`, `CardFooter` | Contenitore base dashboard + wizard steps. |
| `input.tsx` | `Input` | Campi testo; integra focus ring. |
| `label.tsx` | `Label` | Radix Label, accessibile. |
| `badge.tsx` | `Badge` | Variants semantici + color-coded (`blue`/`purple`/`amber`/`red`/`zinc`). Usato da `SupplierBadge` e `VatBadge`. |
| `separator.tsx` | `Separator` | Horizontal / vertical. |
| `skeleton.tsx` | `Skeleton` | Loading placeholder. |
| `progress.tsx` | `Progress` | Barra progresso determinata. |
| `switch.tsx` | `Switch` | Toggle booleano (dark/light, env). |
| `checkbox.tsx` | `Checkbox` | Esclusione righe tabella. |
| `table.tsx` | `Table`, `TableHeader`, `TableBody`, `TableFooter`, `TableRow`, `TableHead`, `TableCell`, `TableCaption` | Review table + history. |
| `dialog.tsx` | `Dialog` + parts | Modali conferma / PDF preview. |
| `sheet.tsx` | `Sheet` + parts | Drawer laterale (settings, filtri). |
| `popover.tsx` | `Popover` + parts | HealthIndicator, mini form. |
| `tooltip.tsx` | `Tooltip`, `TooltipProvider` + parts | Warning + abbreviazioni. `TooltipProvider` montato in `Shell`. |
| `alert.tsx` | `Alert`, `AlertTitle`, `AlertDescription` | Variants: `default`, `info`, `success`, `warning`, `destructive`. Banner dry-run, errori inline. |
| `tabs.tsx` | `Tabs`, `TabsList`, `TabsTrigger`, `TabsContent` | Settings page (override / info sistema). |
| `accordion.tsx` | `Accordion` + parts | Dettagli collassabili. |
| `select.tsx` | `Select` + parts | Country override, filtri. |
| `dropdown-menu.tsx` | `DropdownMenu` + parts | Row actions, kebab menu. |
| `command.tsx` | `Command`, `CommandDialog` + parts | Command palette (Cmd+K, future). |
| `form.tsx` | `Form`, `FormField`, `FormItem`, `FormLabel`, `FormControl`, `FormDescription`, `FormMessage`, `useFormField` | Wrapper react-hook-form + zod. |
| `sonner.tsx` | `Toaster`, `toast` | Toast globale. `<Toaster />` montato in `main.tsx`. |

---

## 3. Componenti layout

| File | Uso |
|---|---|
| `layout/Shell.tsx` | Root app: Sidebar + TopBar + `<Outlet />` + `TooltipProvider` globale. |
| `layout/Sidebar.tsx` | Sidebar fissa 240/56px, 4 nav item, `HealthIndicator`, toggle tema, toggle collapse. |
| `layout/TopBar.tsx` | Breadcrumb dinamico + Cmd+K hint + `EnvironmentSwitch` + company badge. |

---

## 4. Componenti domain-specific

In `src/components/domain/`. Tutti presentazionali: i dati live arrivano dai React Query hooks che scrive `frontend-eng` in `src/lib/queries.ts`.

| Componente | Props principali | Quando usarlo |
|---|---|---|
| `StepProgress` | `steps: Step[]`, `currentStep` | In cima al wizard "Nuovo run" (6 step). |
| `SupplierBadge` | `countryIso` | **Ovunque si mostra un fornitore** (Review, History, Verify). |
| `VatBadge` | `vatId`, `vatRatePercent` | **Colonna IVA** della tabella Review + Results. |
| `BillToWarning` | `supplier`, `portalUrl?` | Icon warning in colonna Review per righe con `billing_data_warning=true`. |
| `PdfPreviewDialog` | `supplierKey`, `open`, `onOpenChange` | Dialog dai link PDF in Verify + Review. |
| `HealthIndicator` | `status`, `checks[]` | Sidebar (live) + Settings (dettaglio). |
| `EnvironmentSwitch` | — | TopBar: toggle Live/Dry-run, persiste in localStorage, emette evento `autofatture:env`. |
| `EmptyState` | `icon`, `title`, `description?`, `action?` | Stati vuoti (no runs, no override, no results). |
| `Stat` | `label`, `value`, `delta?`, `hint?` | Card KPI dashboard (es. "Autofatture create", "Fornitori totali"). |

---

## 5. Utilities (`src/lib/`)

- `utils.ts`
  - `cn(...classes)` — `clsx` + `tailwind-merge`.
  - `EU_COUNTRIES` — set con i 27 ISO UE (mirror di `tools/fic_client.py`).
  - `isEu(iso)`, `isExtraUe(iso)`, `isItaly(iso)` — helper classificazione.
  - `formatCurrency(amount, currency="EUR")` — locale `it-IT`, `€ 3.112,45`.
  - `formatDate(iso, style)` — `"short"` → `08/04/2026`, `"medium"` (default) → `8 apr 2026`, `"long"` con orario.
  - `truncate(str, max)` — troncamento con ellissi.
- `theme.ts`
  - `initTheme()` — applica tema salvato a `document.documentElement` prima del paint.
  - `useTheme()` — `{ theme, setTheme, toggle }`, persiste in localStorage, reagisce a `prefers-color-scheme` in modalità `system`.

---

## 6. Linee guida d'uso

- **Mostri un fornitore?** Usa sempre `SupplierBadge` per il paese (niente bandiere custom).
- **Mostri un'aliquota IVA?** Usa sempre `VatBadge` — il testo è già semantico (22% RC, 0% NS, ecc.).
- **Hai un Bill to warning dal backend?** Metti `<BillToWarning />` in una colonna dedicata, non come modifier del nome.
- **Vuoi mostrare un errore?** Preferisci `toast.error()` (sonner) per azioni utente e `<Alert variant="destructive">` per errori di pagina.
- **Loading lungo?** `<Skeleton />` per contenuti strutturati (tabelle, card). `<Progress />` per job con percentuale. Mai spinner grezzi al centro della pagina.
- **Stato vuoto?** Sempre `<EmptyState />`, mai stringa di testo nuda.
- **Numeri monetari?** Classe `tabular-nums` + `formatCurrency()`, allineamento a destra in tabella.
- **Label utente?** In **italiano**. Le variabili/props/commenti restano in inglese.
- **Icone?** Da `lucide-react`, size default `h-4 w-4` in linea col testo body.
- **Focus?** Nessun elemento cliccabile senza focus ring. Radix già ce lo dà, non sovrascrivere `outline-none` senza `focus-visible:ring-*`.
