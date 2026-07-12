"""Enum centralizzati (NFR-11): pillar, format, surface, stati pipeline, ruoli.

Estendere qui e solo qui. I valori sono stringhe snake_case salvate a DB;
le label sono per la UI.
"""

PILLARS = {
    "revenue_leak": "Revenue Leak",
    "proof": "Proof",
    "educational": "Educational",
    "contrarian": "Contrarian",
    "backstage": "Backstage",
}

# Mix pillar target di default (§6.2 PRD) — configurabile da Impostazioni.
DEFAULT_PILLAR_TARGETS = {
    "revenue_leak": 30,
    "proof": 25,
    "educational": 25,
    "contrarian": 10,
    "backstage": 10,
}

# Tassonomia provvisoria dei 12 format (Domanda aperta #4 del PRD).
# Da confermare con Lorenzo; sostituire le voci qui quando la lista è definitiva.
FORMATS = {
    "talking_head": "Talking head",
    "pov_screen": "POV / screen recording",
    "tutorial": "Tutorial / how-to",
    "caso_studio": "Caso studio",
    "prima_dopo": "Prima / dopo",
    "mito_sfatato": "Mito da sfatare",
    "lista_errori": "Lista errori",
    "reaction": "Reaction / duet",
    "dietro_le_quinte": "Dietro le quinte",
    "storytelling": "Storytelling",
    "dati_grafici": "Dati & grafici",
    "qna": "Q&A",
}

SURFACES = {
    "reel": "Reel",
    "carousel": "Carosello",
    "story": "Story",
    "other": "Altro",
}

# Pipeline M1 (FR-M1-04). L'ordine conta per la board Kanban.
CONTENT_STATUSES = [
    "idea",
    "script",
    "production",
    "critic",
    "scheduled",
    "published",
    "archived",
]

CONTENT_STATUS_LABELS = {
    "idea": "Idea",
    "script": "Script",
    "production": "In produzione",
    "critic": "Critico",
    "scheduled": "Programmato",
    "published": "Pubblicato",
    "archived": "Archiviato",
}

PLATFORMS = {"instagram": "Instagram", "tiktok": "TikTok"}

IDEA_STATUSES = ["proposed", "approved", "discarded"]
IDEA_ORIGINS = ["ai", "manual"]

SOURCE_TYPES = ["rss", "reddit", "trend", "competitor"]

ROLES = ["admin", "editor", "contributor"]

# Soglie di default (§10 PRD) — editabili da Impostazioni (FR-X-03).
DEFAULT_SETTINGS = {
    "critic_gate_min": "38",           # gate qualità: sotto questa soglia niente "Programmato"
    "winner_retention_pct": "65",      # winner: retention media > soglia ...
    "winner_save_rate_decile": "90",   # ... oppure save rate >= percentile
    "kill_retention_pct": "40",        # kill: format con retention media < soglia ...
    "kill_min_posts": "5",             # ... dopo almeno N post
    "format_min_posts": "3",           # sotto N post il giudizio per format è "campione insufficiente"
    "pillar_mix_alert_pp": "7",        # alert scostamento mix pillar (punti percentuali)
    "idea_job_enabled": "true",        # job giornaliero Idea Engine
    "idea_job_interval_hours": "24",
    "metrics_reminder_hours": "48",    # metriche attese entro 48h dalla pubblicazione
}
