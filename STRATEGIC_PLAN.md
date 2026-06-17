# Piano Strategico: Mailift → €100k/mese con IA

**Versione**: 1.0  
**Data**: 2026-04-09  
**Owner**: Lorenzo Baretta  
**Framework**: WAT (Workflows, Agents, Tools)

---

## Visione Finale

**Stato Attuale** (Marzo 2026):
- **MRR**: €9.000/mese (7 clienti attivi)
- **Ore operative**: 60–80 ore/mese (email, triage, report, follow-up, admin)
- **Automatizzazione**: ~10%

**Obiettivo** (Fine 2026):
- **MRR**: €100.000/mese (scaling 11x)
- **Ore operative**: 20–25 ore/mese (solo decision-making strategico + sales + copywriting)
- **Automatizzazione**: 90%+

**Strategia**: Non aggiungere persone, solo intelligenza (IA + automazione).

---

## Il Problema Oggi

| Fase | Task | Tempo/settimana | Automazione |
|---|---|---|---|
| **Lead Gen** | Incoming leads (landing, email, form) | 4h | ❌ Nessuna |
| **Discovery** | Qualification HOT/WARM/COLD | 5h | ⚠️ Manuale (workflow esiste, non automatizzato) |
| **Call** | Analizzare trascrizione Fathom, note GHL | 3h | ❌ Paste manuale |
| **Onboarding** | Sequenza email nurture + checklist task (7 clienti) | 6h | ❌ No—cada cliente è manuale |
| **Delivery** | Report Klaviyo settimanali (7 account) | 4h | ⚠️ Workflow esiste, run manuale |
| **Retention** | Follow-up cliente non risposte, upsell signal | 5h | ❌ Nessuno |
| **Admin** | Gmail triage, Notion, calendari | 3h | ✅ Parziale (email classif in place) |
| **Totale** | | **30h/settimana** | ~10% automatizzato |

**Context**: 7 clienti attivi (€9k MRR). Per scalare a €100k MRR (11x), aggiungere 70+ nuovi clienti senza aumentare ore = automazione must-have.

**Bottleneck top 3:**
1. **Onboarding non scalabile** — ogni nuovo cliente = 6-8 ore di setup manuale
2. **Reporting manuale** — Klaviyo è letto ogni lunedì a mano, nessun insight proattivo
3. **Lead qual esterna al CRM** — trascrizioni Fathom → Note GHL → tag = 3 step manuali

---

## Architettura di Soluzione

### Layer 1: Workflows (SOPs nel git)
- `lead_qualification.md` — Criteri HOT/WARM/COLD, flusso Fathom → briefing → GHL
- `onboarding_sequence.md` — Task sequence da account creato → prima campagna live
- `weekly_reporting.md` — Klaviyo → Google Sheets → email report
- `retention_monitoring.md` — SLA tracking, anomaly detection, upsell opportunities
- `call_analysis.md` — Trascrizione → action items + GHL sync
- `inbox_orchestration.md` — Email → categoria → task/reply/archive

### Layer 2: Agents (Questa è te — automazione intelligente)
- **Lead Classifier Agent**: legge trascrizione Fathom, applica criteri ICP, genera briefing
- **Onboarding Coordinator**: crea task Notion, schedula email, popola calendario
- **Reporting Agent**: pull Klaviyo, costruisce tabelle, genera insight
- **Anomaly Detector**: monitora SLA Klaviyo, deliverability, engagement calo
- **Call Analyzer**: Fathom → JSON strutturato → GHL sync + follow-up proposal

### Layer 3: Tools (Python determinisitici)
**Nuovi da creare:**
- `tools/lead_classifier.py` — Claude API per classificazione + briefing
- `tools/onboarding_sequencer.py` — Crea task Notion, schedula Gmail, gestisce timeline
- `tools/klaviyo_auto_report.py` — Estrae Klaviyo, calcola delta, genera tabelle
- `tools/anomaly_detector.py` — Monitora metriche Klaviyo vs soglie, segnala
- `tools/call_analyzer.py` — Ingesta trascrizione, struttura JSON, sync GHL

**Già in place** (potenziare):
- `tools/gmail_client.py` ✅
- `tools/notion_tasks.py` ✅
- `tools/ghl_client.py` ✅
- `tools/klaviyo_client.py` ✅
- `tools/gcal_client.py` ✅

---

## Piano Implementazione (6 Fasi, 8 settimane)

### 🔴 **FASE 1: Qualification + Lead Triage (Week 1–2)**

**Cosa fa:** Automatizza discovery call processing + incoming lead triage  
**Tempo Lorenzo salvato:** ~10h/settimana

#### 1.1 Lead Classifier Agent
**Deliverable:** `tools/lead_classifier.py` + `workflows/lead_qualification_auto.md`

```python
# Pseudocode
def classify_lead(transcription: str, lead_email: str = None) -> dict:
    """
    Input: trascrizione Fathom di discovery call
    Output: {
        'classificazione': 'HOT' | 'WARM' | 'COLD',
        'motivazione': str,
        'briefing_gamma_id': str,  # generato durante la funzione
        'ghl_tags': list[str],
        'red_flags': list[str],
        'follow_up_slot': Optional[datetime],  # se HOT
    }
    """
    # Step 1: Claude Opus estrae schema JSON dalla trascrizione
    extracted = claude_extract_structure(transcription)
    
    # Step 2: Applica criteri ICP (determinisitco)
    classificazione = apply_icp_rules(extracted)
    
    # Step 3: Genera briefing Gamma (se non presente, crea)
    if not briefing_id:
        briefing_id = gamma_create_briefing(extracted, classificazione)
    
    # Step 4: Ritorna dict completo per GHL sync + follow-up
    return {...}
```

**Azione concreta:**
1. Crea tool con Claude API (Opus per extraction, Haiku per classificazione se troppo banale)
2. Integra Gamma MCP per auto-generare briefing slide
3. Testa con 3 trascrizioni reali (EV8, HCF, precedenti warm/cold)
4. Aggiungi a `.env`: `LEAD_CLASSIFIER_MODEL = claude-opus-4-6`

**Workflow associato:**
```markdown
# Workflow: Lead Qualification Auto

**Trigger:** Lorenzo incolla trascrizione Fathom in chat, o aggiunge file locale

**Execution:**
1. Chiama `tools/lead_classifier.py classify_lead(transcription)`
2. Ricevi dict con classificazione + briefing Gamma ID
3. Mostra a Lorenzo: classificazione + motivazione + briefing preview
4. Se Lorenzo approva: sync su GHL (find_or_create + note + tags)
5. Se HOT: proponi 3 slot follow-up (gcal_find_my_free_time + email template)
6. Se WARM/COLD: archivia in GHL, segnala action (nurture o archive)
```

#### 1.2 Incoming Email Lead Classifier
**Deliverable:** Tool per classificare email in arrivo (form submissions, website form, booking)

Estendi `tools/inbox_triage.py`:
- Categoria aggiuntiva: `LEAD_HOT` / `LEAD_WARM` / `LEAD_COLD`
- Estrae: email, nome, azienda, sito web, pain point
- Crea contatto in GHL automaticamente con tag `form-submission`
- Non invia nulla, solo classifica e avvisa Lorenzo

**Timeline:** 5 giorni

---

### 🟡 **FASE 2: Klaviyo Reporting Automation (Week 3)**

**Cosa fa:** Genera report settimanale Klaviyo senza toccare Klaviyo UI  
**Tempo Lorenzo salvato:** ~4h/settimana

#### 2.1 Weekly Reporting Agent
**Deliverable:** `tools/klaviyo_auto_report.py` + `workflows/weekly_reporting_auto.md`

```python
def generate_weekly_report(client_name: str, start_date: date, end_date: date) -> dict:
    """
    Input: cliente (EV8, HCF, Bergamo), data range (default: ultimi 7 giorni)
    Output: {
        'summary': str,
        'metrics_table': dict,  # open_rate, CTR, bounce, ecc.
        'top_campaigns': list[dict],
        'active_flows': list[dict],
        'anomalies': list[str],  # bounce alto, flusso morto, ecc.
        'insights': list[str],  # esattamente 3
        'pdf_export': bytes,  # PDF scaricabile
    }
    """
    # Step 1: Estrai account Klaviyo per cliente via MCP
    client_account = ghl_find_client_account(client_name)
    
    # Step 2: Pull campagne + flussi ultimi 7gg + 7gg precedenti
    campaigns = klaviyo_get_campaigns(account, date_range=14d)
    flows = klaviyo_get_flows(account, date_range=14d)
    
    # Step 3: Calcola metriche comparative
    metrics = {
        'email_sent': {
            'week_current': ...,
            'week_previous': ...,
            'delta_pct': ...,
        },
        ...
    }
    
    # Step 4: Estrai top 3 campagne per revenue/recipient
    top_campaigns = sorted(
        campaigns, 
        key=lambda c: c['revenue'] / c['recipients'],
        reverse=True
    )[:3]
    
    # Step 5: Identifica anomalie (bounce >2%, flusso morto, ecc.)
    anomalies = detect_anomalies(metrics, flows)
    
    # Step 6: Claude Opus genera 3 insight specifici + actionabili
    insights = claude_generate_insights(
        metrics=metrics,
        anomalies=anomalies,
        campaigns=top_campaigns,
        prompt=INSIGHTS_PROMPT,
        count=3,
    )
    
    # Step 7: Popola Google Sheet (optional) + export PDF
    sheet_id = gsheet_populate_row(client_name, metrics)
    pdf = generate_pdf_report(metrics, campaigns, flows, insights)
    
    return {
        'summary': f"{client_name} report — settiamana {start_date}",
        'metrics_table': metrics,
        'top_campaigns': top_campaigns,
        'active_flows': flows,
        'anomalies': anomalies,
        'insights': insights,
        'pdf_export': pdf,
        'sheet_id': sheet_id,
    }
```

**Azione concreta:**
1. Integra Klaviyo API (già in place via MCP)
2. Crea logica comparative metriche
3. Aggiungi Claude Opus per insight generation (cost ~$0.50 per report)
4. Testa con EV8 Style (3 run per verificare vs interfaccia manuale)
5. Schedula via `tools/scheduler.py` ogni lunedì 6:00 AM

**Workflow associato:**
```markdown
# Workflow: Weekly Klaviyo Report

**Trigger:** Lunedì 6:00 AM (schedulato) oppure manuale da Lorenzo

**Execution:**
1. Per ogni cliente attivo (EV8, HCF, Bergamo):
   a. Chiama `tools/klaviyo_auto_report.py generate_weekly_report(client_name)`
   b. Ricevi dict con metriche + insights + PDF
2. Manda email a Lorenzo con:
   - Summary per cliente
   - Tabella metriche comparative
   - Top 3 campagne
   - 3 insight specifici
   - Allegati: PDF report
3. Se anomalies > 0: evidenzia in rosso e segnala urgenza
4. Salva PDF in Drive folder cliente
```

**Timeline:** 5 giorni

---

### 🟡 **FASE 3: Client Onboarding Automation (Week 4–5)**

**Cosa fa:** Da account creato su Klaviyo → prima campagna live senza tocar mano  
**Tempo Lorenzo salvato:** ~8h/cliente nuovo

#### 3.1 Onboarding Sequencer
**Deliverable:** `tools/onboarding_sequencer.py` + `workflows/onboarding_automation.md`

```python
def create_onboarding_sequence(client: dict) -> dict:
    """
    Input: {
        'name': str,
        'email': str,
        'company': str,
        'shopify_url': str,
        'klaviyo_account_id': str,
        'start_date': date,  # quando inizia onboarding
    }
    
    Output: {
        'onboarding_task_id': str,  # pagina Notion creata
        'email_drafts': list[dict],  # 5 email di nurture
        'calendar_events': list[dict],
        'checklist_status': dict,
    }
    """
    
    # Step 1: Crea pagina Notion sub-task di onboarding
    notion_onboarding = notion_create_task(
        title=f"Onboarding — {client['name']}",
        description="...",
        assignee="segretaria",
        due_date=client['start_date'] + 30days,
        category="Onboarding",
        properties={
            'Cliente': client['name'],
            'Account Klaviyo': client['klaviyo_account_id'],
            'Shopify': client['shopify_url'],
        },
    )
    
    # Step 2: Crea sub-checklist Notion
    checklist_items = [
        "Day 0: Accesso Klaviyo confermato",
        "Day 1: Primo flusso (Welcome Series) setup",
        "Day 3: Segmentazione iniziale importata",
        "Day 5: Template email customizzate",
        "Day 7: Flusso di acquisto configurato",
        "Day 10: Campagna di lancio OK",
        "Day 15: Report primo settimanale",
        "Day 30: Review + prossimi passi",
    ]
    notion_update_task(task_id, checklist=checklist_items)
    
    # Step 3: Genera email draft di nurture (5 email su 30 giorni)
    email_templates = [
        {
            'day': 0,
            'subject': f'Benvenuto in Mailift, {client["name"]}!',
            'body': TEMPLATE_WELCOME,
            'status': 'draft',
        },
        {
            'day': 3,
            'subject': 'Accesso Klaviyo — prossimi step',
            'body': TEMPLATE_SETUP,
            'status': 'draft',
        },
        # ecc.
    ]
    
    # Step 4: Schedula email su Gmail (draft, non inviata)
    for email in email_templates:
        gmail_draft = gmail_create_draft(
            to=client['email'],
            subject=email['subject'],
            body=email['body'],
        )
        email['draft_id'] = gmail_draft['id']
    
    # Step 5: Schedula task reminder su Google Calendar
    for checklist_item in checklist_items:
        gcal_create_event(
            title=f"[Onboarding {client['name']}] {checklist_item}",
            start=client['start_date'] + timedelta(days=day),
            duration=15,
            description=f"Task: {checklist_item}\nURL Notion: {notion_task_url}",
            reminders=['email'],
        )
    
    # Step 6: Ritorna dict con status
    return {
        'onboarding_task_id': notion_onboarding['id'],
        'email_drafts': email_templates,
        'calendar_events': [event['id'] for event in events],
        'checklist_status': {item: 'pending' for item in checklist_items},
    }
```

**Azione concreta:**
1. Crea tool che orchestri Notion + Gmail + GCal
2. Scrivi 5 email template di default (welcome, setup, launch, report, review)
3. Testa con HCF (cliente in setup) — verifica timeline vs realtà
4. Consenti customizzazione: `--template=bergamo_vini` per seguire flow diverso

**Workflow associato:**
```markdown
# Workflow: Onboarding Automation

**Trigger:** Lorenzo crea nuovo cliente in GHL con tag "onboarding-start"

**Execution:**
1. Chiama `tools/onboarding_sequencer.py create_onboarding_sequence(client)`
2. Ricevi:
   - Notion task creato con checklist
   - 5 email draft su Gmail
   - 8 calendar event schedulati
3. Notifica Lorenzo: "Onboarding automatico creato. Rivedi email draft, approva + invia quando pronto."
4. Man mano che Lorenzo completa step Klaviyo/Shopify, marca checklist Notion
5. Calendar reminder notifica quando prossimo step è dovuto
```

**Timeline:** 8 giorni

---

### 🟠 **FASE 4: Call Analysis Automation (Week 5–6)**

**Cosa fa:** Fathom trascrizione → azioni concrete (GHL note, follow-up, task)  
**Tempo Lorenzo salvato:** ~2-3h/settimana se 3+ call/settimana

#### 4.1 Call Analyzer + GHL Sync
**Deliverable:** `tools/call_analyzer.py` + estensione `discovery_call_processing.md`

```python
def analyze_call(transcription: str, call_date: date, lead_email: str = None) -> dict:
    """
    Input: trascrizione Fathom
    Output: struttura completa per GHL + follow-up
    """
    
    # Step 1: Claude Opus estrae structured data
    call_analysis = claude_extract_call_data(
        transcription=transcription,
        schema=CALL_ANALYSIS_SCHEMA,
    )
    
    # Step 2: Classifica lead HOT/WARM/COLD (vedi Fase 1)
    classification = apply_icp_rules(call_analysis)
    
    # Step 3: Genera brief GHL da incollare (markdown + JSON alternativo)
    ghl_note = f"""## Call Analysis — {call_date}

**Classificazione:** {classification['level']} ({classification['emoji']})
**Motivazione:** {classification['reason']}

### Dati Estrazione
- **Settore:** {call_analysis['sector']}
- **Fatturato:** {call_analysis['revenue_range']}
- **ESP Attuale:** {call_analysis['current_esp']}
- **Decision Maker:** {call_analysis['decision_maker_present']}

### Pain Points (citazioni)
{to_bullet_list(call_analysis['pain_points'])}

### Obiezioni Emerse
{to_bullet_list(call_analysis['objections'])}

### Next Steps Proposti
{call_analysis['next_steps']}

### Follow-up Suggerito
- **Timeline:** {call_analysis['follow_up_timeline']}
- **Tipo:** {call_analysis['follow_up_type']}  (call, email, demo, proposal)
- **Responsabile:** Lorenzo
"""
    
    # Step 4: Crea/aggiorna contatto GHL
    contact = ghl_find_or_create_contact(
        email=lead_email or call_analysis['email'],
        company=call_analysis['company'],
        first_name=call_analysis['first_name'],
        phone=call_analysis['phone'],
    )
    
    # Step 5: Aggiungi nota GHL
    ghl_add_note(
        contact_id=contact['id'],
        body=ghl_note,
    )
    
    # Step 6: Applica tag
    ghl_add_tags(
        contact_id=contact['id'],
        tags=[
            f"call-{classification['level'].lower()}",
            f"sector-{call_analysis['sector_slug']}",
            f"call-{call_date.year}-{call_date.month:02d}",
        ],
    )
    
    # Step 7: Se HOT, proponi follow-up automatico
    if classification['level'] == 'HOT':
        follow_up_slots = gcal_find_meeting_times(
            attendees=[lorenzo_email],
            duration=30,
            timeMin=datetime.now(),
            timeMax=datetime.now() + timedelta(days=7),
        )
        
        return {
            'classification': classification,
            'ghl_contact_id': contact['id'],
            'ghl_note_id': note['id'],
            'follow_up_options': follow_up_slots,
            'action': 'PROPOSE_SLOTS',  # Lorenzo sceglie
        }
    
    return {
        'classification': classification,
        'ghl_contact_id': contact['id'],
        'ghl_note_id': note['id'],
        'action': 'ARCHIVE' if classification['level'] == 'COLD' else 'NURTURE',
    }
```

**Azione concreta:**
1. Estendi tool già esistente in Fase 1 (lead_classifier → call_analyzer)
2. Integra `ghl_client.py` per aggiunta note + tag
3. Testa con 2-3 trascrizioni reali (verificar vs Lorenzo review manuale)
4. Affina prompt Claude per estrattore dati (iterazione)

**Timeline:** 6 giorni

---

### 🟠 **FASE 5: Anomaly Detection + Performance Monitoring (Week 6–7)**

**Cosa fa:** Monitora SLA Klaviyo, identifica anomalie, propone azioni correttive  
**Tempo Lorenzo salvato:** ~3-4h/settimana (previene crisi)

#### 5.1 Anomaly Detector Agent
**Deliverable:** `tools/anomaly_detector.py` + `workflows/sla_monitoring.md`

```python
def detect_anomalies(client_name: str) -> dict:
    """
    Input: cliente
    Output: lista anomalie rilevate con severity + azione suggerita
    """
    
    # Step 1: Pull metriche attuali Klaviyo
    current = klaviyo_get_current_metrics(client_name)
    historical = klaviyo_get_metrics_last_30_days(client_name)
    
    # Step 2: Calcola baseline (media 30 giorni precedenti)
    baseline = {
        'open_rate': mean([week['open_rate'] for week in historical]),
        'ctr': mean([week['ctr'] for week in historical]),
        'bounce_rate': mean([week['bounce_rate'] for week in historical]),
        'engagement_rate': mean([week['engagement'] for week in historical]),
    }
    
    # Step 3: Identifica deviazioni vs soglie
    anomalies = []
    
    if current['bounce_rate'] > 0.02:  # > 2%
        anomalies.append({
            'severity': 'critical',
            'type': 'high_bounce',
            'metric': current['bounce_rate'],
            'threshold': 0.02,
            'action': 'Pulire segmento inattivi 90gg prima prossimo invio',
            'estimated_impact': f"-{(current['bounce_rate'] - 0.02) * current['total_recipients']} contatti persi",
        })
    
    if current['open_rate'] < baseline['open_rate'] * 0.8:  # calo > 20%
        anomalies.append({
            'severity': 'high',
            'type': 'engagement_drop',
            'metric': current['open_rate'],
            'baseline': baseline['open_rate'],
            'delta_pct': (current['open_rate'] / baseline['open_rate'] - 1) * 100,
            'action': 'Controllare: subject line? Sending time? Segmentazione?',
        })
    
    if current['flows_triggered'] == 0 and historical[-1]['flows_triggered'] > 100:
        anomalies.append({
            'severity': 'critical',
            'type': 'flow_stopped',
            'action': 'Flusso ha smesso di triggherare. Verificare logica trigger + Shopify integration.',
        })
    
    # Step 4: Prioritizza anomalie
    anomalies = sorted(anomalies, key=lambda a: severity_to_int(a['severity']), reverse=True)
    
    return {
        'client': client_name,
        'check_timestamp': now(),
        'baseline': baseline,
        'current': current,
        'anomalies_count': len(anomalies),
        'anomalies': anomalies,
        'summary': claude_summarize_anomalies(anomalies),  # riassunto 2 righe
    }
```

**Azione concreta:**
1. Crea tool che monitora Klaviyo secondo SLA (bounce <2%, open rate >15% media, flussi attivi)
2. Schedula `tools/scheduler.py` per run giornaliero 8:00 AM
3. Se anomalie > 0: manda email alert a Lorenzo con azione suggerita
4. Testa su EV8 (cliente maturo con buon storico)

**Timeline:** 5 giorni

---

### 🟢 **FASE 6: Integration & Optimization (Week 7–8)**

**Cosa fa:** Connette tutti i pezzi, elimina doppioni, affina timing  
**Outcome:** Sistema coeso pronto per operazioni 100% automatiche

#### 6.1 Orchestrazione Make.com / n8n
**Azione:**
1. Rivedi Make.com setup esistente (controllare cosa è wired)
2. Configura webhook per trigger:
   - Nuovo lead in GHL → runbook discovery call processing
   - Nuovo cliente onboarding-start → trigger onboarding sequencer
   - Lunedì 6:00 AM → trigger weekly reporting
   - Ogni giorno 8:00 AM → trigger anomaly detector
3. Testa tutti i flussi end-to-end con dati reali

#### 6.2 Polish + Edge cases
- Gestione errori: se Klaviyo API down, bufferizzo e retry
- Validazione input: se trascrizione è troppo corta, chiedo conferma
- Logging: salva tutti i run in DB per audit trail
- Testing: 2-3 run reali per fase prima di "production"

#### 6.3 Documentazione + Handoff
- Aggiorna CLAUDE.md con nuovi tool + workflow
- Crea runbook per Lorenzo: "cosa fare se tool fallisce"
- Training: mostra a Lorenzo i dashboard Make.com / task monitoring

**Timeline:** 8 giorni

---

## Deliverable Finali (fine Week 8)

### Per Lorenzo
- ✅ Dashboard Notion: task automatici, loro status in tempo reale
- ✅ Email settimanale: report Klaviyo, anomalie, insight
- ✅ Gmail: email draft nurture (approva + invia quando pronto)
- ✅ GCal: reminder onboarding + follow-up automatico schedulati
- ✅ GHL: contatti con note/tag auto-populate su discovery call

### Per la Segretaria (IA)
- ✅ Lead Classifier: trascrizione → HOT/WARM/COLD + briefing Gamma
- ✅ Onboarding Sequencer: cliente nuovo → checklist + email + reminder
- ✅ Weekly Reporter: Klaviyo pull → tabelle + insight
- ✅ Call Analyzer: call → GHL note + follow-up proposal
- ✅ Anomaly Detector: monitora 24/7, segnala anomalie critiche

### Infrastructure
- ✅ Make.com / n8n wired: webhook orchestration completo
- ✅ `.env` completato: API key per tutti i servizi
- ✅ Logging + audit trail: tutti i run tracciati in DB
- ✅ Error handling: fallback graceful se API down

---

## Metriche di Successo

| Metrica | Prima | Target (Week 8) | Impatto |
|---|---|---|---|
| **Ore/settimana task operativi** | 30h | 12h | -60% |
| **Lead qualification time** | 15 min | 2 min | Automazione totale |
| **Report Klaviyo generation** | 4h manuale | 15 min | Automazione totale |
| **Onboarding per cliente** | 6-8h manuale | 1h review | -85% |
| **Follow-up proposal time** | 5 min/call | Automatico | Istantaneo |
| **Anomaly detection response** | 7 giorni medi | 24h | Proattivo |

---

## Timeline Visiva

```
Week 1-2    Week 3      Week 4-5          Week 5-6        Week 6-7        Week 7-8
┌─────┐   ┌──────┐   ┌───────────┐   ┌────────────┐   ┌──────────┐   ┌────────────┐
│ FASE1   │ FASE2 │   │   FASE3   │   │   FASE4    │   │  FASE5   │   │   FASE6    │
│ Lead    │Report │   │Onboarding │   │Call        │   │Anomaly   │   │Integration │
│Qual+    │Autom  │   │Automation │   │Analysis    │   │Detector  │   │& Polish    │
│Triage   │      │   │           │   │            │   │          │   │            │
└─────┘   └──────┘   └───────────┘   └────────────┘   └──────────┘   └────────────┘
  ✅       ✅          ✅               ✅              ✅              ✅ READY
```

---

## FAQ & Mitigazione Rischi

### Q: "È troppo? Non posso fare tutto in 8 settimane."
**A**: Vero. Priorità:
1. **Priorità assoluta (Week 1-3)**: Fase 1 + 2 (lead qual + reporting). Questo riduce il 60% del lavoro manuale.
2. **Fase 3**: Se Week 3 va bene e HCF è in onboarding, fai onboarding automation (gain massimo per nuovo cliente).
3. **Fase 4-5**: Se vuoi, ma sono "nice to have" per scalare in Fase 2. Puoi farlo dopo.
4. **Fase 6**: Integration quando tutto è stabile.

### Q: "E se Claude API fallisce?"
**A**: Fallback:
- Logging di ogni error nella DB locale
- Retry automatio su API 503/429
- Se fallisce > 3 volte, manda alert a Lorenzo con messaggio grezzo (es. "trascrizione grezza di 50 righe" da leggere a mano)
- Mai dare risposta sbagliata confidently

### Q: "GHL API non è wired nel .env. Che faccio?"
**A**: Il tool `ghl_client.py` esiste già. Solo aggiungi:
```
GHL_API_KEY=pit-xxxxx  # Personal Integration Token (chiedi da GHL UI)
GHL_LOCATION_ID=xxxxx  # Mailift location ID
```
Test su un contatto di prova, poi scale.

### Q: "Cosa succede se Klaviyo API limita rate?"
**A**: Implementa queue + backoff:
- Se 429 (rate limit): attendi 60 secondi + retry
- Se quota giornaliera full: buffer il report per domani
- Comunica a Lorenzo: "Report posticipato per limite API — probabilmente carico alto"

---

## Prossimi Step Immediati

1. **Domanda a Lorenzo**: Ok il piano? Vuoi modificare ordine fasi?
2. **Setup Week 0** (questo weekend):
   - Crea branch `feature/automation-phase1` nel git
   - Configura `.env` con API key mancanti (Anthropic, Notion, GMail token check)
   - Test tools già in place: `tools/ghl_client.py`, `tools/notion_tasks.py`
3. **Kick-off Fase 1** (lunedì 2026-04-13):
   - Crea `tools/lead_classifier.py`
   - Implementa primissima versione schema extraction
   - Test con 1 trascrizione reale

---

**Versione documento:** 1.0  
**Next review:** 2026-04-13 (fine Fase 1)  
**Owner:** Lorenzo + Segretaria IA
