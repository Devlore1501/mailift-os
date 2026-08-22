# tools/ — indice ragionato

88 script deterministici (Layer 3 del framework WAT). La cartella è **volutamente
piatta**: spostare i file in sottocartelle romperebbe gli import Python e i path
citati nei workflow e in `Claude.md`. Questo indice sostituisce le sottocartelle.

Convenzione: `*_client.py` = wrapper API riutilizzabile, `*_oauth_setup.py` = da
lanciare **una volta sola** per generare il token in `tokens/`.

## Meta / Facebook Ads
| Script | Cosa fa |
|---|---|
| `fb_ads_client.py` | Wrapper API Meta Ads (base per gli altri) |
| `fb_campaign_launcher.py` | Crea e lancia campagne |
| `fb_relaunch_campaign.py` | Rilancia una campagna esistente |
| `fb_restore_archived.py` | Ripristina ad archiviati |
| `fb_rules_setup.py` | Configura regole automatiche |
| `fb_fetch_ad_copy.py` | Scarica il copy degli ad attivi |
| `fb_mcp_inject.py` | Ponte verso l'MCP Meta Ads |
| `ads_advisor.py` | Raccomandazioni scala/uccidi sulle creative |
| `ads_report.py` | Report performance campagne |
| `ads_dashboard_sync.py` | Sincronizza i dati sulla dashboard |
| `ads_creative_tracker.py` | Tracking creative nel tempo |
| `ab_test.py` | Setup e lettura test A/B |
| `create_322_*.py` | Script one-off campagna "322" (bank, cbo, cbo3, draft, single) |
| `create_ads2_drafts.py` | Genera bozze ad in blocco |
| `simula_creative.py` / `simula_visitatori.py` | Simulazioni per stimare performance |

## Pipeline creative e database asset
| Script | Cosa fa |
|---|---|
| `pipeline.py` | Entry point: `python tools/pipeline.py run all` |
| `pipeline_config.py` | Configurazione della pipeline |
| `creative_db.py` | Accesso a `data/creative_db.sqlite` |
| `creative_assets.py` | Download e gestione asset in `data/creative_assets/` |
| `creative_classifier.py` | Classificazione automatica delle creative |
| `creative_fatigue_detector.py` | Rileva l'affaticamento creativo |
| `creative_dashboard.py` + `.html.tpl` | Dashboard HTML delle creative |
| `variant_images.py` | Genera varianti immagine |
| `swap_images_and_live.py` | Sostituisce immagini e pubblica |
| `watch_unblock_swap.py` | Watcher per lo swap |

## Email marketing
| Script | Cosa fa |
|---|---|
| `klaviyo_client.py` | Client Klaviyo multi-account (serve `KLAVIYO_API_KEY_*`) |

## CRM — GoHighLevel
| Script | Cosa fa |
|---|---|
| `ghl_client.py` | Client GHL principale (contatti, note, tag) |
| `ghl_calendar_client.py` | Calendari e appuntamenti GHL |
| `ghl_orders_client.py` | Ordini GHL |
| `ghl_sync.py` | Sincronizzazione dati |
| `ghl_probe.py` | Diagnostica connessione/permessi |
| `embed_ghl_form.py` / `embed_survey.py` | Embed di form e survey nelle landing |

## Google Workspace
| Script | Cosa fa |
|---|---|
| `gmail_client.py` | Lettura/scrittura Gmail (`gmail_oauth_setup.py` una volta) |
| `gcal_client.py` | Google Calendar (`gcal_oauth_setup.py` una volta) |
| `gsheets_oauth_setup.py` / `gsheets_script_setup.py` | Setup Sheets e Apps Script |
| `mailift_sync.gs` | Apps Script lato Google |

## Inbox e triage email
| Script | Cosa fa |
|---|---|
| `inbox_triage.py` | Triage inbox → priorità e categorie |
| `classify_emails.py` | Classificatore email |
| `process_inbox.sh` | Wrapper shell del triage |

## Amministrazione, fatture, banca
| Script | Cosa fa |
|---|---|
| `fic_client.py` | Client Fatture in Cloud (`fic_device_setup.py` una volta) |
| `run_autofatture.py` | Esecuzione autofatture TD17/18/19 |
| `monthly_autofatture.py` | Ciclo mensile autofatture |
| `fix_autofatture_vat.py` | Correzione IVA su autofatture |
| `parse_bank_statement.py` | Parsing estratti conto da `inbox/` |
| `classify_transactions.py` | Classificazione movimenti bancari |
| `revolut_client.py` | Client Revolut (`revolut_oauth_setup.py` una volta) |
| `cleanup_suppliers.py` / `verify_suppliers_from_email.py` | Pulizia e verifica fornitori |

## Notion e task
| Script | Cosa fa |
|---|---|
| `notion_tasks.py` | list / create / update / batch close su Tasks_Mailift |
| `cleanup_notion_categories.py` | Normalizza le categorie |

## Call e contesto clienti
| Script | Cosa fa |
|---|---|
| `process_call.py` | `python tools/process_call.py <cliente> <trascrizione.txt>` |
| `create_call_from_summary.py` | Crea la nota call da un summary |
| `fathom_batch_import.py` | Import in blocco da Fathom |
| `gather_reactivation_context.py` | Contesto per riattivare un cliente |
| `reengagement_radar.py` | Individua clienti da ricontattare |

## Lead research
| Script | Cosa fa |
|---|---|
| `find_owners.py` | Trova i titolari di un'attività |
| `clean_places.py` | Pulizia dati da Google Places |

## Landing page e performance web
| Script | Cosa fa |
|---|---|
| `restructure_landing.py` / `restyle_landing.py` | Ristruttura e riveste una landing |
| `optimize_landing_seo.py` / `optimize_landing_speed.py` | Ottimizzazione SEO e velocità |
| `speedtest_page.py` | Misura la velocità di una pagina |
| `serve_static_gzip.py` | Server statico locale con gzip |
| `clarity_client.py` | Dati Microsoft Clarity |

## Voce, Telegram, bot
| Script | Cosa fa |
|---|---|
| `vapi_client.py` / `vapi_webhook_server.py` / `voice_handler.py` | Appointment setter vocale |
| `telegram_bot.py` | Bot Telegram della segretaria |

## Orchestrazione e infrastruttura
| Script | Cosa fa |
|---|---|
| `agent_runner.py` | Esecuzione agenti |
| `scheduler.py` | Scheduling dei job |
| `control_server.py` + `control_dashboard.html.tpl` | Dashboard di controllo |
| `manus_bridge.py` / `manus_session.py` | Integrazione Manus |
| `make_blueprints/` | Blueprint Make.com |
