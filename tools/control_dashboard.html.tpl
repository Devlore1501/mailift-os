<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Controllo pipeline — Mailift</title>
<style>
  *, *::before, *::after { box-sizing: border-box; }
  /* .running/.empty impostano display: senza questo, [hidden] non nasconde nulla. */
  [hidden] { display: none !important; }
  body, h1, h2, h3, p, figure, ul { margin: 0; }
  ul { padding: 0; list-style: none; }
  button, input, select, textarea { font: inherit; color: inherit; }

  :root {
    --ground:#F2F5F5; --panel:#FFFFFF; --line:#D8E0E0; --line-soft:#E8EDED;
    --ink:#0E1A1C; --ink-2:#46585A; --ink-3:#7A8C8D;
    --accent:#0F5257; --accent-sr:#0F525714; --accent-ink:#FFFFFF;
    --ok:#2E6F52; --warn:#A25E14; --crit:#9C3227; --noise:#94A4A5; --radius:4px;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --ground:#0B1315; --panel:#111E20; --line:#24393B; --line-soft:#1A2B2D;
      --ink:#E3EDEC; --ink-2:#9DB2B2; --ink-3:#6D8283;
      --accent:#4FB3AE; --accent-sr:#4FB3AE1F; --accent-ink:#06181A;
      --ok:#5FBF8E; --warn:#D99A4E; --crit:#E0705F; --noise:#5A6E6F;
    }
  }
  :root[data-theme="dark"] {
    --ground:#0B1315; --panel:#111E20; --line:#24393B; --line-soft:#1A2B2D;
    --ink:#E3EDEC; --ink-2:#9DB2B2; --ink-3:#6D8283;
    --accent:#4FB3AE; --accent-sr:#4FB3AE1F; --accent-ink:#06181A;
    --ok:#5FBF8E; --warn:#D99A4E; --crit:#E0705F; --noise:#5A6E6F;
  }
  :root[data-theme="light"] {
    --ground:#F2F5F5; --panel:#FFFFFF; --line:#D8E0E0; --line-soft:#E8EDED;
    --ink:#0E1A1C; --ink-2:#46585A; --ink-3:#7A8C8D;
    --accent:#0F5257; --accent-sr:#0F525714; --accent-ink:#FFFFFF;
    --ok:#2E6F52; --warn:#A25E14; --crit:#9C3227; --noise:#94A4A5;
  }

  body {
    background: var(--ground); color: var(--ink);
    font: 15px/1.55 system-ui, -apple-system, "Segoe UI", sans-serif;
    padding: 36px 24px 80px;
  }
  .wrap { max-width: 1080px; margin: 0 auto; display: flex; flex-direction: column; gap: 26px; }
  h1, h2 { font-family: Georgia, "Iowan Old Style", serif; font-weight: 600; text-wrap: balance; }
  h1 { font-size: 28px; letter-spacing: -0.01em; }
  h2 { font-size: 18px; }
  .eyebrow { font-size: 11px; letter-spacing: .11em; text-transform: uppercase; color: var(--ink-3); font-weight: 600; }
  .sub { color: var(--ink-2); font-size: 13.5px; }
  .num { font-family: ui-monospace, "SF Mono", Menlo, monospace; font-variant-numeric: tabular-nums; }
  header { display: flex; flex-direction: column; gap: 6px; border-bottom: 1px solid var(--line); padding-bottom: 18px; }
  .panel { background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius); }
  section { display: flex; flex-direction: column; gap: 12px; }

  /* stato */
  .counts { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px,1fr)); gap: 10px; }
  .c { padding: 12px 14px; display: flex; flex-direction: column; gap: 2px; }
  .c .v { font-size: 21px; font-weight: 600; }
  .c .k { font-size: 10.5px; letter-spacing: .05em; text-transform: uppercase; color: var(--ink-3); }
  .c.bad .v { color: var(--crit); }

  /* controlli */
  .runbar { padding: 14px; display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
  button {
    padding: 7px 13px; border-radius: var(--radius); border: 1px solid var(--line);
    background: var(--panel); cursor: pointer; font-size: 13.5px;
  }
  button:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
  button:disabled { opacity: .45; cursor: not-allowed; }
  button.primary { background: var(--accent); border-color: var(--accent); color: var(--accent-ink); font-weight: 600; }
  button.primary:hover:not(:disabled) { color: var(--accent-ink); filter: brightness(1.1); }
  button.ok { color: var(--ok); border-color: var(--ok); }
  button.no { color: var(--crit); border-color: var(--crit); }
  button:focus-visible, input:focus-visible, select:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
  select, input[type=text] {
    padding: 6px 9px; border: 1px solid var(--line); border-radius: var(--radius);
    background: var(--panel); font-size: 13.5px;
  }

  .running {
    display: flex; align-items: center; gap: 9px; padding: 10px 14px;
    background: var(--accent-sr); border-top: 1px solid var(--line);
    font-size: 13.5px; color: var(--accent); font-weight: 600;
  }
  .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--accent); animation: p 1s infinite; }
  @keyframes p { 50% { opacity: .25; } }
  @media (prefers-reduced-motion: reduce) { .dot { animation: none; } }

  /* tabelle */
  .scroller { overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th { text-align: left; padding: 9px 12px; font-size: 10.5px; letter-spacing: .07em;
       text-transform: uppercase; color: var(--ink-3); font-weight: 600; border-bottom: 1px solid var(--line); white-space: nowrap; }
  td { padding: 9px 12px; border-bottom: 1px solid var(--line-soft); vertical-align: top; }
  th.r, td.r { text-align: right; }
  tbody tr:hover { background: var(--accent-sr); }

  .chip { display: inline-block; font-size: 10px; font-weight: 700; letter-spacing: .06em;
          text-transform: uppercase; padding: 2px 6px; border-radius: 3px; border: 1px solid currentColor; }
  .chip.web { color: var(--accent); } .chip.leadform { color: var(--ink-2); }
  .chip.ok { color: var(--ok); } .chip.no { color: var(--crit); } .chip.wait { color: var(--warn); }

  /* config */
  .cfg { display: flex; flex-direction: column; }
  .row { display: grid; grid-template-columns: 1fr auto; gap: 16px; align-items: center;
         padding: 12px 14px; border-bottom: 1px solid var(--line-soft); }
  .row:last-child { border-bottom: 0; }
  .row .desc { font-size: 12.5px; color: var(--ink-2); }
  .row .key { font-weight: 600; font-size: 13.5px; }
  .row .ctl { display: flex; gap: 6px; align-items: center; }
  .row.over { background: var(--accent-sr); }
  .badge { font-size: 10px; color: var(--accent); font-weight: 700; letter-spacing: .05em; }

  /* varianti */
  .v-card { padding: 14px; border-bottom: 1px solid var(--line-soft); display: grid;
            grid-template-columns: 132px 1fr; gap: 14px; align-items: start; }
  .v-card.noimg { grid-template-columns: 1fr; }
  .v-card:last-child { border-bottom: 0; }
  .v-txt { display: flex; flex-direction: column; gap: 7px; min-width: 0; }
  .v-img {
    width: 132px; aspect-ratio: 1; object-fit: cover; border-radius: var(--radius);
    border: 1px solid var(--line); background: var(--ground); cursor: zoom-in; display: block;
  }
  .v-noimg {
    width: 132px; aspect-ratio: 1; border: 1px dashed var(--line); border-radius: var(--radius);
    display: flex; align-items: center; justify-content: center; text-align: center;
    font-size: 11px; color: var(--ink-3); padding: 8px;
  }
  @media (max-width: 560px) { .v-card { grid-template-columns: 1fr; } }
  dialog { border: 0; padding: 0; background: transparent; max-width: 92vw; }
  dialog::backdrop { background: #000C; }
  dialog img { max-width: 92vw; max-height: 88vh; border-radius: 6px; display: block; }
  .v-head { display: flex; gap: 9px; align-items: center; flex-wrap: wrap; }
  .v-hl { font-weight: 600; font-size: 15px; }
  .v-body { color: var(--ink-2); font-size: 13.5px; }
  .v-meta { font-size: 12px; color: var(--ink-3); }
  .v-act { display: flex; gap: 6px; margin-top: 3px; }

  .empty { padding: 22px 14px; color: var(--ink-3); font-size: 13.5px; text-align: center; }
  .note { padding: 12px 14px; font-size: 13px; color: var(--ink-2); border-left: 2px solid var(--warn); background: var(--panel); }
  #toast {
    position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%);
    background: var(--ink); color: var(--ground); padding: 9px 16px; border-radius: var(--radius);
    font-size: 13.5px; opacity: 0; pointer-events: none; transition: opacity .2s; z-index: 9;
  }
  #toast.show { opacity: 1; }
  #toast.err { background: var(--crit); color: #fff; }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="eyebrow">Mailift · Pipeline creative</div>
    <h1>Configurazione e controllo</h1>
    <div class="sub" id="hdr">…</div>
  </header>

  <section>
    <h2>Stato</h2>
    <div class="counts" id="counts"></div>
  </section>

  <section>
    <h2>Esecuzione</h2>
    <p class="sub">Uno stage alla volta. <span class="num">generate</span> chiama Manus e consuma crediti:
       gira solo su richiesta e solo su un angolo che supera il gate.</p>
    <div class="panel">
      <div class="runbar" id="runbar"></div>
      <div class="runbar" style="border-top:1px solid var(--line-soft)">
        <span class="sub">Genera varianti per:</span>
        <select id="angle-sel"></select>
        <button id="btn-gen">generate</button>
        <span class="sub" id="gen-hint"></span>
      </div>
      <div class="running" id="running" hidden><span class="dot"></span><span id="running-txt"></span></div>
    </div>
  </section>

  <section>
    <h2>Angoli</h2>
    <p class="sub" id="angles-sub"></p>
    <div class="panel scroller">
      <table>
        <thead><tr><th>Angolo</th><th>Classe</th><th class="r">Creative</th><th class="r">Spesa</th>
                   <th class="r">Lead</th><th class="r">CPL</th><th>Generabile</th></tr></thead>
        <tbody id="angles"></tbody>
      </table>
      <div class="empty" id="angles-empty" hidden>Nessun angolo classificato in una classe con lead veri.</div>
    </div>
  </section>

  <section>
    <h2>Varianti proposte</h2>
    <p class="sub">Nessuna variante va su Meta senza la tua approvazione.</p>
    <div class="panel" id="variants"></div>
  </section>

  <section>
    <h2>Configurazione</h2>
    <p class="sub">Le righe evidenziate sono modificate rispetto al default.</p>
    <div class="panel cfg" id="cfg"></div>
  </section>

  <section>
    <h2>Ultimi run</h2>
    <div class="panel scroller">
      <table>
        <thead><tr><th>Stage</th><th>Esito</th><th class="r">Durata</th><th>Quando</th><th>Riepilogo</th></tr></thead>
        <tbody id="runs"></tbody>
      </table>
    </div>
  </section>
</div>
<dialog id="zoom"><img alt="Anteprima variante a schermo intero"></dialog>
<div id="toast"></div>

<script>
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const grp = i => i.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
const eur = n => "€" + grp(Math.round(n || 0).toString());
const eur2 = n => { const [i,d] = Math.abs(n).toFixed(2).split("."); return "€" + grp(i) + "," + d; };

let S = null, timer = null;

function toast(msg, err) {
  const t = $("#toast");
  t.textContent = msg;
  t.className = "show" + (err ? " err" : "");
  setTimeout(() => t.className = "", 3200);
}

async function api(path, method, body) {
  const r = await fetch(path, {
    method: method || "GET",
    headers: {"Content-Type": "application/json"},
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
  return data;
}

async function load() {
  try { S = await api("/api/state"); render(); }
  catch (e) { toast("Stato non caricato: " + e.message, true); }
}

function render() {
  const c = S.counts;
  $("#hdr").textContent = `soglia ${S.threshold} lead · aggiornato ${S.now}`;

  $("#counts").innerHTML = [
    ["creative", c.creatives], ["asset", `${c.assets}/${c.creatives}`],
    ["classificati", `${c.classified}/${c.creatives}`],
    ["errori classify", c.classify_errors, c.classify_errors > 0],
    ["varianti proposte", c.proposed], ["approvate", c.approved],
  ].map(([k, v, bad]) => `<div class="panel c ${bad ? "bad" : ""}">
      <div class="v num">${esc(v)}</div><div class="k">${esc(k)}</div></div>`).join("");

  // stage
  const busy = !!S.current;
  $("#runbar").innerHTML = `<button class="primary" data-stage="all" ${busy ? "disabled" : ""}>run all</button>` +
    S.auto_stages.map(s => `<button data-stage="${s}" ${busy ? "disabled" : ""}>${s}</button>`).join("") +
    `<span class="sub">run all = ${S.auto_stages.join(" → ")}</span>`;

  const ok = S.angles.filter(a => a.enough);
  $("#angle-sel").innerHTML = ok.length
    ? ok.map(a => `<option value="${esc(a.angle)}">${esc(a.angle)} (${a.leads} lead)</option>`).join("")
    : `<option value="">nessun angolo eleggibile</option>`;
  $("#angle-sel").disabled = !ok.length || busy;
  $("#btn-gen").disabled = !ok.length || busy;
  $("#gen-hint").textContent = ok.length ? "" : "nessun angolo supera il gate: serve più volume, non più varianti";

  $("#running").hidden = !busy;
  if (busy) $("#running-txt").textContent = `${S.current.stage} in corso…`;

  // angoli
  $("#angles-empty").hidden = S.angles.length > 0;
  $("#angles").innerHTML = S.angles.map(a => `<tr>
      <td><b>${esc(a.angle)}</b></td>
      <td><span class="chip ${esc(a.klass)}">${esc(a.klass)}</span></td>
      <td class="r num">${a.n}</td>
      <td class="r num">${eur(a.spend)}</td>
      <td class="r num">${a.leads}</td>
      <td class="r num">${a.cpl ? eur2(a.cpl) : "—"}</td>
      <td>${a.enough ? '<span class="chip ok">sì</span>'
                     : `<span class="chip wait">${a.leads}/${S.threshold}</span>`}</td>
    </tr>`).join("");
  $("#angles-sub").textContent = S.angles.length
    ? `${S.angles.length} angoli in classi con lead veri · ${S.angles.filter(a => a.enough).length} sopra soglia`
    : "Classifica i creative per popolare questa tabella.";

  // varianti
  const V = S.variants;
  $("#variants").innerHTML = V.length ? V.map(v => {
    const st = {proposed: "wait", approved: "ok", rejected: "no", published: "web"}[v.status] || "wait";
    const hasImg = !!v.asset_path;
    // cache-buster su rendered_at: rigenerando, l'URL è lo stesso ma il file cambia.
    const img = hasImg
      ? `<img class="v-img" loading="lazy" src="/api/variants/${v.id}/image?v=${encodeURIComponent(v.rendered_at || "")}"
              alt="Anteprima variante ${v.id}" data-zoom="${v.id}">`
      : `<div class="v-noimg">${v.da_produrre ? "va girata / registrata:<br>non si genera con l'AI"
                                : v.render_error ? "render fallito" : "nessuna immagine"}</div>`;
    return `<div class="v-card">
      ${img}
      <div class="v-txt">
        <div class="v-head">
          <span class="chip ${st}">${esc(v.status)}</span>
          ${v.format_family ? `<span class="chip web">${esc(v.format_family)}</span>` : ""}
          ${v.da_produrre ? `<span class="chip wait">da girare</span>` : ""}
          <span class="v-hl">${esc(v.headline || "(senza headline)")}</span>
        </div>
        <div class="v-body">${esc(v.body || "")}</div>
        <div class="v-meta">angolo ${esc(v.angle)} · voce ${esc(v.voice || "—")} ·
          hook ${esc(v.hook_type || "—")} · ${esc(v.awareness_stage || "—")} ·
          CTA ${esc(v.cta || "—")}${v.image_model ? ` · immagine ${esc(v.image_model)}` : ""}</div>
        ${v.extra?.visual_brief ? `<div class="v-meta">Visual: ${esc(v.extra.visual_brief)}</div>` : ""}
        ${v.extra?.rationale ? `<div class="v-meta">Perché: ${esc(v.extra.rationale)}</div>` : ""}
        ${v.render_error ? `<div class="v-meta" style="color:var(--crit)">Render: ${esc(v.render_error)}</div>` : ""}
        <div class="v-act">
          ${v.status === "proposed" ? `
            <button class="ok" data-dec="approved" data-id="${v.id}">approva</button>
            <button class="no" data-dec="rejected" data-id="${v.id}">rifiuta</button>` : ""}
          ${v.status !== "rejected" && !v.da_produrre ? `
            <button data-render="${v.id}" ${busy ? "disabled" : ""}>${hasImg ? "rigenera immagine" : "genera immagine"}</button>` : ""}
        </div>
      </div>
    </div>`;
  }).join("") : `<div class="empty">Nessuna variante generata finora.</div>`;

  // config
  $("#cfg").innerHTML = S.config.map(k => {
    let ctl;
    if (k.type === "bool") {
      ctl = `<select data-key="${esc(k.key)}">
        <option value="true" ${k.value ? "selected" : ""}>attivo</option>
        <option value="false" ${!k.value ? "selected" : ""}>disattivo</option></select>`;
    } else {
      const val = k.type === "list" ? JSON.stringify(k.value) : k.value;
      ctl = `<input type="text" data-key="${esc(k.key)}" value="${esc(val)}" size="18">`;
    }
    return `<div class="row ${k.overridden ? "over" : ""}">
      <div>
        <div class="key">${esc(k.key)} ${k.overridden ? '<span class="badge">MODIFICATO</span>' : ""}</div>
        <div class="desc">${esc(k.desc)}</div>
      </div>
      <div class="ctl">${ctl}
        <button data-save="${esc(k.key)}">salva</button>
        ${k.overridden ? `<button data-reset="${esc(k.key)}">default</button>` : ""}
      </div>
    </div>`;
  }).join("");

  // run
  $("#runs").innerHTML = S.runs.length ? S.runs.map(r => {
    const st = {ok: "ok", error: "no", running: "wait"}[r.status] || "wait";
    return `<tr>
      <td><b>${esc(r.stage)}</b></td>
      <td><span class="chip ${st}">${esc(r.status)}</span></td>
      <td class="r num">${r.duration_s != null ? r.duration_s.toFixed(1) + "s" : "—"}</td>
      <td class="num" style="font-size:12px">${esc(r.started_at)}</td>
      <td>${esc(r.summary || r.error || "")}</td>
    </tr>`;
  }).join("") : `<tr><td colspan="5" class="empty">Nessun run.</td></tr>`;

  // poll solo mentre qualcosa gira
  clearInterval(timer);
  if (busy) timer = setInterval(load, 2500);
}

document.addEventListener("click", async e => {
  const b = e.target.closest("button");
  if (!b) return;
  try {
    if (b.dataset.stage) {
      await api("/api/run", "POST", {stage: b.dataset.stage});
      toast(`avviato: ${b.dataset.stage}`);
      await load();
    } else if (b.id === "btn-gen") {
      const angle = $("#angle-sel").value;
      if (!angle) return;
      await api("/api/run", "POST", {stage: "generate", angle});
      toast(`generate avviato su ${angle}`);
      await load();
    } else if (b.dataset.save) {
      const el = document.querySelector(`[data-key="${CSS.escape(b.dataset.save)}"]`);
      const r = await api("/api/config", "POST", {key: b.dataset.save, value: el.value});
      toast(`${r.key} = ${r.value}`);
      await load();
    } else if (b.dataset.reset) {
      const r = await api("/api/config/reset", "POST", {key: b.dataset.reset, value: ""});
      toast(`${r.key} → default (${r.value})`);
      await load();
    } else if (b.dataset.dec) {
      await api(`/api/variants/${b.dataset.id}/decide`, "POST", {status: b.dataset.dec});
      toast(`variante ${b.dataset.id}: ${b.dataset.dec}`);
      await load();
    } else if (b.dataset.render) {
      await api(`/api/variants/${b.dataset.render}/render`, "POST", {});
      toast(`immagine variante ${b.dataset.render}: avviata (circa 2-3 minuti)`);
      await load();
    }
  } catch (err) {
    toast(err.message, true);
  }
});

// zoom sull'anteprima
document.addEventListener("click", e => {
  const img = e.target.closest("[data-zoom]");
  if (!img) return;
  const d = document.getElementById("zoom");
  d.querySelector("img").src = img.src;
  d.showModal();
});
document.getElementById("zoom").addEventListener("click", e => e.currentTarget.close());

load();
</script>
</body>
</html>
