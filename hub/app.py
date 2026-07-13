"""Mailift OS Hub — punto d'ingresso unico per le webapp interne (porta 4000).

Serve la homepage con le card delle app e il loro stato live; lo stato viene
verificato server-side (nessun problema CORS). Le app restano indipendenti:
questo hub non tocca né i loro backend né i loro frontend.

Per aggiungere una nuova app alla piattaforma basta una voce in APPS.
"""
import concurrent.futures

import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="Mailift OS Hub")

APPS = [
    {
        "key": "content",
        "name": "Content Dashboard",
        "description": "Piano editoriale, KPI che contano, Idea Engine. Gate Critico e mix pillar.",
        "url": "http://localhost:5174",
        "health": "http://localhost:8010/api/health",
        "docs": "http://localhost:8010/docs",
        "accent": "#E0A93B",
    },
    {
        "key": "autofatture",
        "name": "Autofatture",
        "description": "Reverse charge TD17/18/19 su Fatture in Cloud da estratti Revolut, verifica fornitori via Gmail.",
        "url": "http://localhost:5173",
        "health": "http://localhost:8000/api/health",
        "docs": "http://localhost:8000/docs",
        "accent": "#5B9DD9",
    },
]


def _check(app_def: dict) -> dict:
    try:
        r = requests.get(app_def["health"], timeout=2)
        ok = r.status_code == 200
    except requests.RequestException:
        ok = False
    return {"key": app_def["key"], "ok": ok}


@app.get("/api/status")
def status():
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(APPS)) as pool:
        results = list(pool.map(_check, APPS))
    return {r["key"]: r["ok"] for r in results}


@app.get("/", response_class=HTMLResponse)
def home():
    cards = "\n".join(
        f"""
        <div class="card" role="link" tabindex="0" data-url="{a['url']}" style="--accent:{a['accent']}">
          <div class="card-top">
            <span class="dot" id="dot-{a['key']}" title="stato backend"></span>
            <span class="badge">app interna</span>
          </div>
          <h2>{a['name']}</h2>
          <p>{a['description']}</p>
          <div class="card-foot">
            <span class="open">Apri →</span>
            <a class="docs" href="{a['docs']}">API docs</a>
          </div>
        </div>"""
        for a in APPS
    )
    return f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mailift OS</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Plus Jakarta Sans',system-ui,sans-serif; background:#0C1420; color:#EAF0F8;
         min-height:100vh; display:flex; flex-direction:column; align-items:center; padding:8vh 24px 40px; }}
  .logo {{ font-size:34px; font-weight:800; letter-spacing:-.5px; }}
  .logo span {{ color:#E0A93B; }}
  .sub {{ color:#7D8DA3; font-size:12px; text-transform:uppercase; letter-spacing:3px; font-weight:600; margin-top:6px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,380px)); gap:20px; margin-top:48px;
           width:100%; max-width:820px; justify-content:center; }}
  .card {{ background:#15233F; border:1px solid #1D2F52; border-radius:16px; padding:24px; text-decoration:none;
           color:inherit; display:flex; flex-direction:column; gap:10px; cursor:pointer;
           transition:border-color .2s, transform .2s; }}
  .card:hover {{ border-color:var(--accent); transform:translateY(-2px); }}
  .card-top {{ display:flex; justify-content:space-between; align-items:center; }}
  .dot {{ width:10px; height:10px; border-radius:50%; background:#7D8DA3; display:inline-block; }}
  .dot.ok {{ background:#3DCB8F; box-shadow:0 0 8px #3DCB8F66; }}
  .dot.down {{ background:#E5734B; }}
  .badge {{ font-family:'JetBrains Mono',monospace; font-size:10px; color:#7D8DA3; text-transform:uppercase; letter-spacing:1px; }}
  h2 {{ font-size:20px; font-weight:800; }}
  p {{ color:#B9C6D8; font-size:14px; line-height:1.55; flex:1; }}
  .card-foot {{ display:flex; justify-content:space-between; align-items:center; margin-top:6px; }}
  .open {{ color:var(--accent); font-weight:600; font-size:14px; }}
  .docs {{ color:#7D8DA3; font-size:12px; text-decoration:none; }}
  .docs:hover {{ color:#EAF0F8; }}
  .hint {{ margin-top:40px; color:#7D8DA3; font-size:12px; font-family:'JetBrains Mono',monospace; }}
  .hint b {{ color:#B9C6D8; font-weight:500; }}
</style>
</head>
<body>
  <div class="logo">Mailift<span>.</span> OS</div>
  <div class="sub">Piattaforma interna</div>
  <div class="grid">{cards}</div>
  <div class="hint">avvio: <b>./mailift.sh</b> · pallino verde = backend attivo</div>
  <script>
    async function refresh() {{
      try {{
        const s = await (await fetch('/api/status')).json();
        for (const [key, ok] of Object.entries(s)) {{
          const dot = document.getElementById('dot-' + key);
          if (dot) dot.className = 'dot ' + (ok ? 'ok' : 'down');
        }}
      }} catch (e) {{ /* hub offline: lascia i pallini neutri */ }}
    }}
    refresh();
    setInterval(refresh, 5000);
    for (const card of document.querySelectorAll('.card')) {{
      const go = () => window.location.href = card.dataset.url;
      card.addEventListener('click', (e) => {{ if (!e.target.closest('.docs')) go(); }});
      card.addEventListener('keydown', (e) => {{ if (e.key === 'Enter') go(); }});
    }}
  </script>
</body>
</html>"""
