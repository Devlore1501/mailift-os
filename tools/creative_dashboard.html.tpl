<title>Creative DB — Mailift</title>
<style>
  :root {
    --ground:    #F2F5F5;
    --panel:     #FFFFFF;
    --line:      #D8E0E0;
    --line-soft: #E8EDED;
    --ink:       #0E1A1C;
    --ink-2:     #46585A;
    --ink-3:     #7A8C8D;
    --accent:    #0F5257;
    --accent-sr: #0F525714;
    --ok:        #2E6F52;
    --warn:      #A25E14;
    --crit:      #9C3227;
    --noise:     #94A4A5;
    --radius:    4px;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --ground:    #0B1315;
      --panel:     #111E20;
      --line:      #24393B;
      --line-soft: #1A2B2D;
      --ink:       #E3EDEC;
      --ink-2:     #9DB2B2;
      --ink-3:     #6D8283;
      --accent:    #4FB3AE;
      --accent-sr: #4FB3AE1F;
      --ok:        #5FBF8E;
      --warn:      #D99A4E;
      --crit:      #E0705F;
      --noise:     #5A6E6F;
    }
  }
  :root[data-theme="dark"] {
    --ground:    #0B1315;
    --panel:     #111E20;
    --line:      #24393B;
    --line-soft: #1A2B2D;
    --ink:       #E3EDEC;
    --ink-2:     #9DB2B2;
    --ink-3:     #6D8283;
    --accent:    #4FB3AE;
    --accent-sr: #4FB3AE1F;
    --ok:        #5FBF8E;
    --warn:      #D99A4E;
    --crit:      #E0705F;
    --noise:     #5A6E6F;
  }
  :root[data-theme="light"] {
    --ground:    #F2F5F5;
    --panel:     #FFFFFF;
    --line:      #D8E0E0;
    --line-soft: #E8EDED;
    --ink:       #0E1A1C;
    --ink-2:     #46585A;
    --ink-3:     #7A8C8D;
    --accent:    #0F5257;
    --accent-sr: #0F525714;
    --ok:        #2E6F52;
    --warn:      #A25E14;
    --crit:      #9C3227;
    --noise:     #94A4A5;
  }

  body {
    background: var(--ground);
    color: var(--ink);
    font: 15px/1.55 system-ui, -apple-system, "Segoe UI", sans-serif;
    padding: 40px 24px 80px;
  }
  .wrap { max-width: 1140px; margin: 0 auto; display: flex; flex-direction: column; gap: 28px; }

  h1, h2 { font-family: Georgia, "Iowan Old Style", serif; font-weight: 600; text-wrap: balance; }
  h1 { font-size: 30px; letter-spacing: -0.01em; }
  h2 { font-size: 19px; margin-bottom: 2px; }
  .eyebrow {
    font-size: 11px; letter-spacing: 0.11em; text-transform: uppercase;
    color: var(--ink-3); font-weight: 600;
  }
  .sub { color: var(--ink-2); font-size: 13.5px; }
  .num { font-family: ui-monospace, "SF Mono", Menlo, monospace; font-variant-numeric: tabular-nums; }

  header { display: flex; flex-direction: column; gap: 6px; border-bottom: 1px solid var(--line); padding-bottom: 20px; }
  header .meta { display: flex; flex-wrap: wrap; gap: 16px; color: var(--ink-3); font-size: 12.5px; }

  .panel { background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius); }

  /* KPI */
  .kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }
  .kpi { padding: 16px 18px; display: flex; flex-direction: column; gap: 3px; }
  .kpi .v { font-size: 26px; font-weight: 600; letter-spacing: -0.02em; }
  .kpi .k { font-size: 11.5px; color: var(--ink-3); letter-spacing: 0.04em; text-transform: uppercase; }
  .kpi .note { font-size: 12px; color: var(--ink-2); }
  .kpi.flag .v { color: var(--crit); }

  /* classi */
  .classes { display: flex; flex-direction: column; }
  .cls {
    display: grid; grid-template-columns: 1fr auto auto auto; gap: 20px; align-items: baseline;
    padding: 14px 18px; border-bottom: 1px solid var(--line-soft);
  }
  .cls:last-child { border-bottom: 0; }
  .cls .who { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
  .cls .ev { font-weight: 600; font-size: 14px; }
  .cls .why { font-size: 12.5px; color: var(--ink-2); }
  .cls .fig { text-align: right; }
  .cls .fig .n { font-size: 16px; font-weight: 600; }
  .cls .fig .l { font-size: 10.5px; color: var(--ink-3); text-transform: uppercase; letter-spacing: 0.06em; }

  .chip {
    display: inline-block; font-size: 10.5px; font-weight: 700; letter-spacing: 0.06em;
    text-transform: uppercase; padding: 2px 7px; border-radius: 3px; border: 1px solid currentColor;
  }
  .chip.web      { color: var(--accent); }
  .chip.leadform { color: var(--ink-2); }
  .chip.junk     { color: var(--crit); }
  .chip.none     { color: var(--noise); }
  .chip.unknown  { color: var(--warn); }

  .cls.junk { background: color-mix(in srgb, var(--crit) 6%, transparent); }

  /* spesa giornaliera */
  .chart { padding: 18px; display: flex; flex-direction: column; gap: 10px; }
  .bars { display: flex; align-items: flex-end; gap: 2px; height: 96px; border-bottom: 1px solid var(--line); }
  .bar { flex: 1; min-width: 2px; background: var(--accent-sr); position: relative; border-radius: 1px 1px 0 0; }
  .bar i { position: absolute; inset: auto 0 0 0; background: var(--accent); border-radius: 1px 1px 0 0; display: block; }
  .bar.has-lead i { background: var(--ok); }
  .bar:hover { outline: 1px solid var(--ink-3); }
  .axis { display: flex; justify-content: space-between; font-size: 11px; color: var(--ink-3); }

  /* tabella */
  .toolbar { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
  .toolbar input {
    flex: 1; min-width: 180px; padding: 7px 10px; font: inherit; font-size: 13px;
    background: var(--panel); color: var(--ink);
    border: 1px solid var(--line); border-radius: var(--radius);
  }
  .toolbar input:focus-visible, .fbtn:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
  .fbtn {
    font: inherit; font-size: 12.5px; padding: 6px 11px; cursor: pointer;
    background: var(--panel); color: var(--ink-2);
    border: 1px solid var(--line); border-radius: var(--radius);
  }
  .fbtn[aria-pressed="true"] { background: var(--accent); border-color: var(--accent); color: var(--panel); font-weight: 600; }

  .scroller { overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th {
    text-align: left; padding: 9px 12px; font-size: 10.5px; letter-spacing: 0.07em;
    text-transform: uppercase; color: var(--ink-3); font-weight: 600;
    border-bottom: 1px solid var(--line); white-space: nowrap;
    position: sticky; top: 0; background: var(--panel);
  }
  th.r, td.r { text-align: right; }
  td { padding: 10px 12px; border-bottom: 1px solid var(--line-soft); vertical-align: top; }
  tbody tr:hover { background: var(--accent-sr); }
  .ad { font-weight: 600; }
  .hl { color: var(--ink-2); font-size: 12px; max-width: 340px; }
  .muted { color: var(--ink-3); }

  /* sufficienza dati: il punto della pagina */
  .suff { display: flex; align-items: center; gap: 7px; min-width: 108px; }
  .track { flex: 1; height: 5px; background: var(--line); border-radius: 3px; overflow: hidden; }
  .fill { height: 100%; background: var(--noise); border-radius: 3px; }
  .fill.ok { background: var(--ok); }
  .suff .lab { font-size: 11px; color: var(--ink-3); white-space: nowrap; }
  tr.enough .cpl { font-weight: 700; }
  tr:not(.enough) .cpl { color: var(--ink-3); }
  tr.junk-row td { opacity: 0.62; }

  .empty { padding: 28px; text-align: center; color: var(--ink-3); }
  footer { color: var(--ink-3); font-size: 12px; border-top: 1px solid var(--line); padding-top: 16px; }
  @media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
</style>

<div class="wrap">
  <header>
    <div class="eyebrow">Mailift · Creative DB</div>
    <h1>Registro test creativi</h1>
    <div class="meta">
      <span id="m-range"></span>
      <span id="m-accounts"></span>
      <span id="m-gen"></span>
    </div>
  </header>

  <section class="kpis" id="kpis"></section>

  <section>
    <h2>Classi di lead</h2>
    <p class="sub">Meta riporta tutto come <span class="num">lead</span>, ma sono eventi diversi.
       I CPL si confrontano dentro una classe, mai fra classi.</p>
    <div class="panel classes" id="classes" style="margin-top:12px"></div>
  </section>

  <section>
    <h2>Spesa giornaliera</h2>
    <p class="sub">Le barre verdi sono i giorni con almeno un lead.</p>
    <div class="panel chart" style="margin-top:12px">
      <div class="bars" id="bars"></div>
      <div class="axis"><span id="ax-from"></span><span id="ax-peak"></span><span id="ax-to"></span></div>
    </div>
  </section>

  <section>
    <h2>Creative</h2>
    <p class="sub" id="tbl-sub"></p>
    <div class="toolbar" style="margin:12px 0">
      <input id="q" type="search" placeholder="Cerca per ad, headline o campagna…" aria-label="Cerca creative">
      <span id="filters"></span>
    </div>
    <div class="panel scroller">
      <table>
        <thead>
          <tr>
            <th>Ad</th><th>Classe</th><th class="r">Spesa</th><th class="r">Lead</th>
            <th class="r">CPL</th><th>Dati sufficienti</th><th class="r">CTR</th><th>Attivo</th>
          </tr>
        </thead>
        <tbody id="rows"></tbody>
      </table>
      <div class="empty" id="empty" hidden>Nessun creative con questi filtri.</div>
    </div>
  </section>

  <footer id="foot"></footer>
</div>

<script>
const DATA = /*__DATA__*/null;

// Formattazione manuale: l'ICU it-IT non e' garantito ovunque e senza
// raggruppamento "€3046" si legge peggio di "€3.046".
function grp(intPart) { return intPart.replace(/\B(?=(\d{3})+(?!\d))/g, "."); }
const eur = n => "€" + grp(Math.round(n).toString());
const eur2 = n => {
  const [i, d] = Math.abs(n).toFixed(2).split(".");
  return "€" + grp(i) + "," + d;
};
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
// La classe finisce in un attributo class=: "?" non e' un selettore valido.
const slug = k => (k === "?" ? "unknown" : k);

const T = DATA.threshold;
const byClass = k => DATA.classes.filter(c => c.klass === k);
const sum = (arr, f) => arr.reduce((a, x) => a + f(x), 0);
// Classi che contengono lead veri: le uniche su cui una decisione ha senso.
const REAL = new Set(["web", "leadform"]);

// ── header
document.getElementById("m-range").textContent = `${DATA.range[0]} → ${DATA.range[1]}`;
document.getElementById("m-accounts").textContent = DATA.accounts.join(" · ");
document.getElementById("m-gen").textContent = `generata ${DATA.generated_at}`;

// ── KPI
const totSpend = sum(DATA.creatives, c => c.spend);
const web = byClass("web"), lf = byClass("leadform"), junk = byClass("junk");
const webLeads = sum(web, c => c.leads), lfLeads = sum(lf, c => c.leads), junkLeads = sum(junk, c => c.leads);
const allLeads = sum(DATA.classes, c => c.leads);
const junkShare = allLeads ? Math.round(junkLeads / allLeads * 100) : 0;
// Solo fra i creative con lead veri: contare i junk qui rifarebbe l'errore
// che la separazione per evento serve a evitare.
const real = DATA.creatives.filter(c => REAL.has(c.klass));
const enough = real.filter(c => c.leads >= T).length;

const kpis = [
  {k: "Spesa totale", v: eur(totSpend), note: `${DATA.creatives.length} creative`},
  {k: "Lead web", v: webLeads, note: webLeads ? `CPL ${eur2(sum(web, c => c.spend) / webLeads)}` : "—"},
  {k: "Lead form", v: lfLeads, note: lfLeads ? `CPL ${eur2(sum(lf, c => c.spend) / lfLeads)}` : "—"},
  {k: "Lead non validi", v: `${junkShare}%`, note: `${junkLeads} su ${allLeads} sono evento custom`, flag: junkShare > 0},
  {k: "Con dati sufficienti", v: `${enough}/${real.length}`, note: `soglia ${T} lead · esclusi i junk`, flag: enough === 0},
];
document.getElementById("kpis").innerHTML = kpis.map(x => `
  <div class="panel kpi ${x.flag ? "flag" : ""}">
    <div class="k">${esc(x.k)}</div>
    <div class="v num">${esc(x.v)}</div>
    <div class="note">${esc(x.note)}</div>
  </div>`).join("");

// ── classi
document.getElementById("classes").innerHTML = DATA.classes.map(c => {
  const cpl = c.leads ? eur2(c.spend / c.leads) : "—";
  return `<div class="cls ${c.klass === "junk" ? "junk" : ""}">
    <div class="who">
      <div class="ev">${esc(c.event)} <span class="chip ${slug(c.klass)}">${esc(c.klass)}</span></div>
      <div class="why">${esc(DATA.class_note[c.klass] || "")}</div>
    </div>
    <div class="fig"><div class="n num">${eur(c.spend)}</div><div class="l">spesa</div></div>
    <div class="fig"><div class="n num">${c.leads}</div><div class="l">lead</div></div>
    <div class="fig"><div class="n num">${cpl}</div><div class="l">cpl</div></div>
  </div>`;
}).join("");

// ── spesa giornaliera
const peak = Math.max(...DATA.daily.map(d => d.spend), 1);
document.getElementById("bars").innerHTML = DATA.daily.map(d => `
  <div class="bar ${d.leads ? "has-lead" : ""}" title="${d.day} · ${eur2(d.spend)} · ${d.leads} lead">
    <i style="height:${Math.max(d.spend / peak * 100, 1)}%"></i>
  </div>`).join("");
document.getElementById("ax-from").textContent = DATA.range[0];
document.getElementById("ax-peak").textContent = `picco ${eur2(peak)}/g`;
document.getElementById("ax-to").textContent = DATA.range[1];

// ── tabella
document.getElementById("tbl-sub").textContent =
  `${DATA.tagged} di ${DATA.creatives.length} classificate per angolo. ` +
  `La barra mostra quanto manca alla soglia di ${T} lead sotto cui un CPL non è un segnale.`;

const order = ["web", "leadform", "junk", "none", "?"];
const present = order.filter(k => DATA.creatives.some(c => c.klass === k));
let active = "tutte", query = "";

document.getElementById("filters").innerHTML =
  ["tutte", ...present].map(k =>
    `<button class="fbtn" data-k="${esc(k)}" aria-pressed="${k === "tutte"}">${esc(k === "?" ? "non classificati" : k)}</button>`).join("");

function render() {
  const rows = DATA.creatives.filter(c => {
    if (active !== "tutte" && c.klass !== active) return false;
    if (!query) return true;
    const hay = `${c.ad} ${c.headline} ${c.campaign} ${c.angle || ""}`.toLowerCase();
    return hay.includes(query);
  });

  document.getElementById("empty").hidden = rows.length > 0;
  document.getElementById("rows").innerHTML = rows.map(c => {
    const pct = Math.min(c.leads / T * 100, 100);
    const ok = c.leads >= T;
    return `<tr class="${ok ? "enough" : ""} ${c.klass === "junk" ? "junk-row" : ""}">
      <td>
        <div class="ad">${esc(c.ad)}</div>
        <div class="hl">${esc(c.headline || c.campaign)}</div>
      </td>
      <td><span class="chip ${slug(c.klass)}">${esc(c.klass)}</span></td>
      <td class="r num">${eur(c.spend)}</td>
      <td class="r num">${c.leads}</td>
      <td class="r num cpl">${c.cpl ? eur2(c.cpl) : "—"}</td>
      <td>
        <div class="suff">
          <div class="track"><div class="fill ${ok ? "ok" : ""}" style="width:${pct}%"></div></div>
          <span class="lab num">${ok ? "sì" : `${c.leads}/${T}`}</span>
        </div>
      </td>
      <td class="r num">${c.ctr != null ? c.ctr.toFixed(2) + "%" : "—"}</td>
      <td class="muted num" style="font-size:11.5px">${esc(c.first_seen)}<br>${esc(c.last_seen)}</td>
    </tr>`;
  }).join("");
}

document.getElementById("filters").addEventListener("click", e => {
  const b = e.target.closest(".fbtn");
  if (!b) return;
  active = b.dataset.k;
  document.querySelectorAll(".fbtn").forEach(x => x.setAttribute("aria-pressed", x === b));
  render();
});
document.getElementById("q").addEventListener("input", e => {
  query = e.target.value.trim().toLowerCase();
  render();
});

render();
document.getElementById("foot").textContent =
  `Rigenera con: python tools/creative_dashboard.py — fonte: data/creative_db.sqlite, ` +
  `${DATA.daily.length} giorni di risultati.`;
</script>
