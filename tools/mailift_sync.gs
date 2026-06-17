/**
 * Mailift Ads Dashboard — Sync manuale da Google Sheets
 *
 * Tab:
 *   1. Daily Metrics   — metriche giornaliere FB + GHL
 *   2. Orders Log      — ogni ordine (FE/BUMP/OTO)
 *   3. Prodotti        — aggregato per prodotto
 *   4. Creatività Test — performance per annuncio FB (ultime 2 settimane)
 *   5. Campagne        — performance per campagna FB (ultime 2 settimane)
 *
 * Setup: Estensioni → Apps Script → ⚙️ Impostazioni progetto → Proprietà script
 * Chiavi: GHL_API_KEY, GHL_LOCATION_ID, FB_ACCESS_TOKEN, FB_AD_ACCOUNT_ID
 */

/* global PropertiesService, SpreadsheetApp, UrlFetchApp, Utilities, HtmlService, Logger */

'use strict';

var TEST_EMAILS_ = ['lorenzo.baretta997@gmail.com'];
var GHL_BASE_    = 'https://services.leadconnectorhq.com';
var GHL_VER_     = '2021-07-28';
var FB_BASE_     = 'https://graph.facebook.com/v21.0';

// ── Colori palette ────────────────────────────────────────────────────────────
var C_ = {
  headerBg:    '#1a1a2e',  // blu notte
  headerFg:    '#ffffff',
  accent:      '#e94560',  // rosso Mailift
  rowAlt:      '#f8f9fa',
  rowWhite:    '#ffffff',
  greenLight:  '#d9f7e8',
  redLight:    '#fde8e8',
  borderGray:  '#dee2e6',
  subHeaderBg: '#16213e',
  subHeaderFg: '#ffffff',
};

// ── Headers ───────────────────────────────────────────────────────────────────
var DAILY_HEADERS_ = [
  'Data',
  'FB Spend (€)', 'Impressioni', 'Reach', 'Click', 'CTR (%)', 'CPM (€)', 'CPC (€)',
  'FB Acquisti', 'FB Revenue (€)', 'ROAS',
  'FE Ordini', 'FE Revenue (€)', 'BUMP Ordini', 'BUMP Revenue (€)',
  'OTO Ordini', 'OTO Revenue (€)', 'TOT Ordini', 'TOT Revenue (€)', 'Profitto (€)',
];
var ORDERS_HEADERS_ = [
  'Data', 'Order ID', 'Funnel', 'Tipo', 'Prodotto',
  'Importo (€)', 'Status', 'Payment', 'Contatto', 'Email',
];
var PRODUCTS_HEADERS_ = [
  'Prodotto', 'Tipo', 'N° Vendite', 'Revenue (€)', '% Revenue',
];
var CREATIVES_HEADERS_ = [
  'Annuncio', 'AdSet', 'Campagna', 'Status',
  'Spend (€)', 'Impression', 'Click', 'CTR (%)', 'CPC (€)', 'CPM (€)',
  'Acquisti', 'Revenue (€)', 'ROAS',
];
var CAMPAIGNS_HEADERS_ = [
  'Campagna', 'Status',
  'Spend (€)', 'Impressioni', 'Click', 'CTR (%)', 'CPC (€)', 'CPM (€)',
  'Acquisti', 'Revenue (€)', 'ROAS',
  'Budget/gg (€)',
];

// ── Menu ──────────────────────────────────────────────────────────────────────

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('🔄 Mailift Sync')
    .addItem('Sync oggi',            'syncToday')
    .addItem('Sync ultimi 7 giorni', 'syncLast7')
    .addItem('Sync ultimi 30 giorni','syncLast30')
    .addSeparator()
    .addItem('🔍 Test connessione FB',   'testFbConnection')
    .addItem('⚙️ Configura credenziali', 'showConfigHelp')
    .addToUi();
}

function testFbConnection() {
  var ui = SpreadsheetApp.getUi();
  var p  = _props();
  if (!p.fbTok) { ui.alert('❌ FB_ACCESS_TOKEN non configurato nelle proprietà script.'); return; }
  if (!p.fbAcct) { ui.alert('❌ FB_AD_ACCOUNT_ID non configurato nelle proprietà script.'); return; }

  var acct = _fbAcct(p);
  var url  = FB_BASE_ + '/' + acct + '?fields=id,name,currency&access_token=' + p.fbTok;
  var r    = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
  var body = r.getContentText();
  var code = r.getResponseCode();

  if (code === 200) {
    var d = JSON.parse(body);
    ui.alert('✅ FB connesso!\n\nAccount: ' + (d.name || '—') + '\nID: ' + (d.id || '—') + '\nValuta: ' + (d.currency || '—'));
  } else {
    var err = '';
    try { err = JSON.parse(body).error.message; } catch(e) { err = body.slice(0, 200); }
    ui.alert('❌ Errore FB (HTTP ' + code + '):\n\n' + err + '\n\nAccount usato: ' + acct);
  }
}

function syncToday()   { var t = _today(); runSync(t, t); }
function syncLast7()   { runSync(_daysAgo(6),  _today()); }
function syncLast30()  { runSync(_daysAgo(29), _today()); }

function showConfigHelp() {
  var html = HtmlService.createHtmlOutput(
    '<style>body{font-family:sans-serif;font-size:13px;padding:16px;color:#1a1a2e}' +
    'code{background:#f0f0f0;padding:2px 6px;border-radius:3px;font-size:12px}' +
    'h3{color:#e94560;margin-top:0}li{margin-bottom:6px}</style>' +
    '<h3>⚙️ Configurazione credenziali</h3>' +
    '<ol>' +
    '<li>Vai su <b>Estensioni → Apps Script</b></li>' +
    '<li>Clicca <b>⚙️ Impostazioni progetto</b></li>' +
    '<li><b>Proprietà script → Aggiungi proprietà</b></li>' +
    '</ol>' +
    '<p><b>Chiavi richieste:</b></p>' +
    '<ul>' +
    '<li><code>GHL_API_KEY</code></li>' +
    '<li><code>GHL_LOCATION_ID</code></li>' +
    '<li><code>FB_ACCESS_TOKEN</code></li>' +
    '<li><code>FB_AD_ACCOUNT_ID</code> — solo numero, es. <code>1495124847595184</code></li>' +
    '</ul>' +
    '<p style="color:#888;font-size:11px">I valori si trovano nel file .env del progetto.</p>'
  ).setWidth(440).setHeight(320);
  SpreadsheetApp.getUi().showModalDialog(html, 'Configurazione credenziali');
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function _today()      { return _fmt(new Date()); }
function _daysAgo(n)   { var d = new Date(); d.setDate(d.getDate() - n); return _fmt(d); }
function _fmt(d)       { return Utilities.formatDate(d, 'UTC', 'yyyy-MM-dd'); }
function _r2(n)        { return Math.round(n * 100) / 100; }

function _props() {
  var p = PropertiesService.getScriptProperties();
  return {
    ghlKey: p.getProperty('GHL_API_KEY')      || '',
    ghlLoc: p.getProperty('GHL_LOCATION_ID')  || '',
    fbTok:  p.getProperty('FB_ACCESS_TOKEN')  || '',
    fbAcct: p.getProperty('FB_AD_ACCOUNT_ID') || '',
  };
}

function _ghlH(key) {
  return { 'Authorization': 'Bearer ' + key, 'Version': GHL_VER_, 'Accept': 'application/json' };
}

// ── Formatting helpers ────────────────────────────────────────────────────────

function _styleHeader(ws, numCols) {
  var hdr = ws.getRange(1, 1, 1, numCols);
  hdr.setBackground(C_.headerBg)
     .setFontColor(C_.headerFg)
     .setFontWeight('bold')
     .setFontSize(10)
     .setHorizontalAlignment('center')
     .setVerticalAlignment('middle')
     .setWrap(false);
  ws.setFrozenRows(1);
  ws.setRowHeight(1, 32);
}

function _styleRows(ws, startRow, numRows, numCols) {
  if (numRows <= 0) return;
  for (var i = 0; i < numRows; i++) {
    var row = startRow + i;
    var bg  = (i % 2 === 0) ? C_.rowWhite : C_.rowAlt;
    ws.getRange(row, 1, 1, numCols).setBackground(bg).setFontSize(10);
  }
}

function _formatCurrency(ws, startRow, numRows, cols) {
  if (numRows <= 0) return;
  for (var c = 0; c < cols.length; c++) {
    ws.getRange(startRow, cols[c], numRows, 1).setNumberFormat('€#,##0.00');
  }
}

function _formatPct(ws, startRow, numRows, cols) {
  if (numRows <= 0) return;
  for (var c = 0; c < cols.length; c++) {
    ws.getRange(startRow, cols[c], numRows, 1).setNumberFormat('0.000%');
  }
}

function _addBorder(ws, numCols) {
  var lastRow = ws.getLastRow();
  if (lastRow < 1) return;
  ws.getRange(1, 1, lastRow, numCols)
    .setBorder(true, true, true, true, true, true,
               C_.borderGray, SpreadsheetApp.BorderStyle.SOLID);
}

function _colorROAS(ws, startRow, numRows, roasCol) {
  if (numRows <= 0) return;
  for (var i = 0; i < numRows; i++) {
    var cell = ws.getRange(startRow + i, roasCol);
    var val  = cell.getValue();
    if (typeof val === 'number') {
      cell.setBackground(val >= 2 ? C_.greenLight : val > 0 ? '#fff3cd' : C_.redLight);
    }
  }
}

function _colorProfit(ws, startRow, numRows, profitCol) {
  if (numRows <= 0) return;
  for (var i = 0; i < numRows; i++) {
    var cell = ws.getRange(startRow + i, profitCol);
    var val  = cell.getValue();
    if (typeof val === 'number') {
      cell.setBackground(val >= 0 ? C_.greenLight : C_.redLight);
    }
  }
}

function _autoResize(ws, numCols) {
  ws.autoResizeColumns(1, numCols);
}

function _ensureSheet(ss, name, headers) {
  var ws = ss.getSheetByName(name);
  if (!ws) {
    ws = ss.insertSheet(name);
    ws.getRange(1, 1, 1, headers.length).setValues([headers]);
    _styleHeader(ws, headers.length);
    _autoResize(ws, headers.length);
  } else {
    var first = ws.getRange(1, 1, 1, headers.length).getValues()[0];
    var empty = first.every(function(v){ return v === '' || v === null; });
    if (empty) {
      ws.getRange(1, 1, 1, headers.length).setValues([headers]);
      _styleHeader(ws, headers.length);
    }
  }
  return ws;
}

// ── GHL Orders ────────────────────────────────────────────────────────────────

function _fetchGhlOrders(p, startDate, endDate) {
  var all = [], offset = 0, limit = 100;
  while (true) {
    var url = GHL_BASE_ + '/payments/orders?altId=' + p.ghlLoc +
              '&altType=location&limit=' + limit + '&offset=' + offset;
    var r = UrlFetchApp.fetch(url, { headers: _ghlH(p.ghlKey), muteHttpExceptions: true });
    if (r.getResponseCode() !== 200) break;
    var d = JSON.parse(r.getContentText());
    var batch = d.data || [];
    all = all.concat(batch);
    offset += limit;
    if (offset >= (d.totalCount || 0) || batch.length === 0) break;
    Utilities.sleep(150);
  }
  all = all.filter(function(o) {
    var day = (o.createdAt || '').slice(0, 10);
    return day >= startDate && day <= endDate;
  });
  return _parseOrders(p, all);
}

function _parseOrders(p, rawOrders) {
  var rows = [];
  for (var i = 0; i < rawOrders.length; i++) {
    var o = rawOrders[i];
    if (o.paymentStatus !== 'paid') continue;
    if (TEST_EMAILS_.indexOf((o.contactEmail || '').toLowerCase()) >= 0) continue;
    var detUrl = GHL_BASE_ + '/payments/orders/' + o._id +
                 '?altId=' + p.ghlLoc + '&altType=location';
    var dr = UrlFetchApp.fetch(detUrl, { headers: _ghlH(p.ghlKey), muteHttpExceptions: true });
    if (dr.getResponseCode() !== 200) continue;
    var det = JSON.parse(dr.getContentText()), items = det.items || [];
    var day = (o.createdAt || '').slice(0, 10);
    for (var j = 0; j < items.length; j++) {
      var item = items[j], sub = o.sourceSubType || '';
      var ptype = sub === 'upsell'              ? 'OTO'
                : sub === 'one_step_order_form' ? (item.bumpProduct ? 'BUMP' : 'FE')
                : (sub ? sub.toUpperCase()      : 'FE');
      rows.push({
        order_id: o._id, date: day, funnel_name: o.sourceName || '',
        product_type: ptype, product_name: item.name || '',
        amount: (item.price && item.price.amount) ? parseFloat(item.price.amount) : 0,
        status: o.status || '', payment_status: o.paymentStatus || '',
        contact_name: o.contactName || '', contact_email: o.contactEmail || '',
      });
    }
    Utilities.sleep(100);
  }
  return rows;
}

// ── Facebook Ads ──────────────────────────────────────────────────────────────

function _fbAcct(p) {
  var a = p.fbAcct.trim();
  return a.indexOf('act_') === 0 ? a : 'act_' + a;
}

function _actVal(lst, type) {
  for (var i = 0; i < (lst || []).length; i++) {
    if (lst[i].action_type === type) return parseFloat(lst[i].value || 0);
  }
  return 0;
}

function _normFb(raw) {
  var spend = parseFloat(raw.spend || 0);
  var pVal  = _actVal(raw.action_values, 'purchase');
  var rList = raw.purchase_roas || [];
  var roas  = rList.length ? parseFloat(rList[0].value) : (spend > 0 ? pVal / spend : 0);
  return {
    date:              raw.date_start || '',
    spend:             _r2(spend),
    impressions:       parseInt(raw.impressions || 0),
    reach:             parseInt(raw.reach       || 0),
    clicks:            parseInt(raw.clicks      || 0),
    ctr:               _r2(parseFloat(raw.ctr   || 0)),
    cpm:               _r2(parseFloat(raw.cpm   || 0)),
    cpc:               _r2(parseFloat(raw.cpc   || 0)),
    fb_purchases:      Math.round(_actVal(raw.actions, 'purchase')),
    fb_purchase_value: _r2(pVal),
    roas:              _r2(roas),
  };
}

function _fetchFbInsights(p, startDate, endDate) {
  if (!p.fbTok || !p.fbAcct) return {};
  var acct   = _fbAcct(p);
  var fields = 'date_start,spend,impressions,reach,clicks,ctr,cpm,cpc,actions,action_values,purchase_roas';
  var tr     = JSON.stringify({ since: startDate, until: endDate });
  var url    = FB_BASE_ + '/' + acct + '/insights?access_token=' + p.fbTok +
               '&fields=' + fields + '&time_range=' + encodeURIComponent(tr) +
               '&time_increment=1&level=account&limit=100';
  var rows = [];
  while (url) {
    var r = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
    if (r.getResponseCode() !== 200) break;
    var d = JSON.parse(r.getContentText());
    (d.data || []).forEach(function(row){ rows.push(_normFb(row)); });
    url = (d.paging && d.paging.next) ? d.paging.next : null;
  }
  var byDate = {};
  rows.forEach(function(r){ byDate[r.date] = r; });
  return byDate;
}

// ── Facebook: ad-level (Creatività) ──────────────────────────────────────────

function _fetchFbAds(p) {
  if (!p.fbTok || !p.fbAcct) return [];
  var acct   = _fbAcct(p);
  var since  = _daysAgo(13);   // ultimi 14 giorni
  var until  = _today();
  var tr     = JSON.stringify({ since: since, until: until });
  var fields = 'ad_name,adset_name,campaign_name,spend,impressions,clicks,ctr,cpm,cpc,actions,action_values,purchase_roas';
  var url    = FB_BASE_ + '/' + acct + '/insights?access_token=' + p.fbTok +
               '&fields=' + fields +
               '&time_range=' + encodeURIComponent(tr) +
               '&level=ad&sort=spend_descending&limit=100';
  var rows = [];
  while (url) {
    var r = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
    if (r.getResponseCode() !== 200) break;
    var d = JSON.parse(r.getContentText());
    (d.data || []).forEach(function(row){
      var spend = parseFloat(row.spend || 0);
      var pVal  = _actVal(row.action_values, 'purchase');
      var rList = row.purchase_roas || [];
      var roas  = rList.length ? parseFloat(rList[0].value) : (spend > 0 ? _r2(pVal / spend) : 0);
      rows.push([
        row.ad_name       || '',
        row.adset_name    || '',
        row.campaign_name || '',
        '',   // status — non disponibile da insights, lasciamo vuoto
        _r2(spend),
        parseInt(row.impressions || 0),
        parseInt(row.clicks      || 0),
        _r2(parseFloat(row.ctr   || 0)),
        _r2(parseFloat(row.cpc   || 0)),
        _r2(parseFloat(row.cpm   || 0)),
        Math.round(_actVal(row.actions, 'purchase')),
        _r2(pVal),
        _r2(roas),
      ]);
    });
    url = (d.paging && d.paging.next) ? d.paging.next : null;
  }
  return rows;
}

// ── Facebook: campaign-level ──────────────────────────────────────────────────

function _fetchFbCampaigns(p) {
  if (!p.fbTok || !p.fbAcct) return [];
  var acct  = _fbAcct(p);
  var since = _daysAgo(13);
  var until = _today();
  var tr    = JSON.stringify({ since: since, until: until });

  // 1. Insights per campagna (metriche aggregate periodo)
  var insFields = 'campaign_name,campaign_id,spend,impressions,clicks,ctr,cpm,cpc,actions,action_values,purchase_roas';
  var insUrl    = FB_BASE_ + '/' + acct + '/insights?access_token=' + p.fbTok +
                  '&fields=' + insFields +
                  '&time_range=' + encodeURIComponent(tr) +
                  '&level=campaign&sort=spend_descending&limit=50';

  var insights = {};
  while (insUrl) {
    var ir = UrlFetchApp.fetch(insUrl, { muteHttpExceptions: true });
    if (ir.getResponseCode() !== 200) break;
    var id = JSON.parse(ir.getContentText());
    (id.data || []).forEach(function(row){ insights[row.campaign_id] = row; });
    insUrl = (id.paging && id.paging.next) ? id.paging.next : null;
  }

  // 2. Campagne attive (per status + daily budget)
  var campFields = 'id,name,status,daily_budget';
  var campUrl    = FB_BASE_ + '/' + acct + '/campaigns?access_token=' + p.fbTok +
                   '&fields=' + campFields + '&limit=50';
  var campaigns  = {};
  while (campUrl) {
    var cr = UrlFetchApp.fetch(campUrl, { muteHttpExceptions: true });
    if (cr.getResponseCode() !== 200) break;
    var cd = JSON.parse(cr.getContentText());
    (cd.data || []).forEach(function(c){ campaigns[c.id] = c; });
    campUrl = (cd.paging && cd.paging.next) ? cd.paging.next : null;
  }

  var rows = [];
  var cids = Object.keys(insights);
  for (var i = 0; i < cids.length; i++) {
    var cid  = cids[i];
    var ins  = insights[cid];
    var camp = campaigns[cid] || {};
    var spend = parseFloat(ins.spend || 0);
    var pVal  = _actVal(ins.action_values, 'purchase');
    var rList = ins.purchase_roas || [];
    var roas  = rList.length ? parseFloat(rList[0].value) : (spend > 0 ? _r2(pVal / spend) : 0);
    var budget = camp.daily_budget ? _r2(parseFloat(camp.daily_budget) / 100) : '';
    rows.push([
      ins.campaign_name || camp.name || '',
      camp.status       || '',
      _r2(spend),
      parseInt(ins.impressions || 0),
      parseInt(ins.clicks      || 0),
      _r2(parseFloat(ins.ctr   || 0)),
      _r2(parseFloat(ins.cpc   || 0)),
      _r2(parseFloat(ins.cpm   || 0)),
      Math.round(_actVal(ins.actions, 'purchase')),
      _r2(pVal),
      _r2(roas),
      budget,
    ]);
  }
  // ordina per spend desc
  rows.sort(function(a, b){ return b[2] - a[2]; });
  return rows;
}

// ── Scrittura Google Sheets ───────────────────────────────────────────────────

function _sumByDate(rows) {
  var s = {};
  for (var i = 0; i < rows.length; i++) {
    var r = rows[i];
    if (!s[r.date]) s[r.date] = { fc:0, fr:0, bc:0, br:0, oc:0, or:0 };
    var amt = parseFloat(r.amount || 0), d = s[r.date];
    if (r.product_type === 'FE')   { d.fc++; d.fr += amt; }
    if (r.product_type === 'BUMP') { d.bc++; d.br += amt; }
    if (r.product_type === 'OTO')  { d.oc++; d.or += amt; }
  }
  return s;
}

function _writeDaily(ws, ghlRows, fbByDate, startDate, endDate) {
  var existDates = {};
  var all = ws.getDataRange().getValues();
  for (var i = 1; i < all.length; i++) { if (all[i][0]) existDates[String(all[i][0])] = true; }

  var dates = [], cur = new Date(startDate + 'T00:00:00Z'), end = new Date(endDate + 'T00:00:00Z');
  while (cur <= end) { dates.push(_fmt(cur)); cur.setUTCDate(cur.getUTCDate() + 1); }

  var ghlSum = _sumByDate(ghlRows), newRows = [];
  for (var i = 0; i < dates.length; i++) {
    var d = dates[i];
    if (existDates[d]) continue;
    var fb = fbByDate[d] || {}, g = ghlSum[d] || {};
    var feR = g.fr||0, buR = g.br||0, otR = g.or||0, totR = feR+buR+otR;
    var sp  = parseFloat(fb.spend||0);
    newRows.push([
      d, sp,
      fb.impressions||'', fb.reach||'', fb.clicks||'',
      fb.ctr||'', fb.cpm||'', fb.cpc||'',
      fb.fb_purchases||'', fb.fb_purchase_value||'', fb.roas||'',
      g.fc||0, _r2(feR), g.bc||0, _r2(buR), g.oc||0, _r2(otR),
      (g.fc||0)+(g.bc||0)+(g.oc||0), _r2(totR), _r2(totR - sp),
    ]);
  }
  if (newRows.length) {
    var startRow = ws.getLastRow() + 1;
    ws.getRange(startRow, 1, newRows.length, newRows[0].length).setValues(newRows);
    _styleRows(ws, startRow, newRows.length, DAILY_HEADERS_.length);
    // Formati: Data col1, € col2,8,10,13,15,17,19,20, % col6
    _formatCurrency(ws, startRow, newRows.length, [2,8,10,13,15,17,19,20]);
    ws.getRange(startRow, 6, newRows.length, 1).setNumberFormat('0.00"%"');
    ws.getRange(startRow, 1, newRows.length, 1).setNumberFormat('yyyy-mm-dd');
    _colorROAS(ws, startRow, newRows.length, 11);
    _colorProfit(ws, startRow, newRows.length, 20);
    _autoResize(ws, DAILY_HEADERS_.length);
  }
  return newRows.length;
}

function _writeOrders(ws, ghlRows) {
  var existKeys = {};
  var all = ws.getDataRange().getValues();
  for (var i = 1; i < all.length; i++) {
    if (all[i][1]) existKeys[all[i][1]+'|'+all[i][3]+'|'+all[i][4]] = true;
  }
  var newRows = [];
  for (var i = 0; i < ghlRows.length; i++) {
    var r = ghlRows[i], k = r.order_id+'|'+r.product_type+'|'+r.product_name;
    if (existKeys[k]) continue;
    newRows.push([
      r.date, r.order_id, r.funnel_name, r.product_type,
      r.product_name, _r2(parseFloat(r.amount||0)),
      r.status, r.payment_status, r.contact_name, r.contact_email,
    ]);
    existKeys[k] = true;
  }
  if (newRows.length) {
    var startRow = ws.getLastRow() + 1;
    ws.getRange(startRow, 1, newRows.length, newRows[0].length).setValues(newRows);
    _styleRows(ws, startRow, newRows.length, ORDERS_HEADERS_.length);
    _formatCurrency(ws, startRow, newRows.length, [6]);
    ws.getRange(startRow, 1, newRows.length, 1).setNumberFormat('yyyy-mm-dd');
    // Colora per tipo
    for (var i = 0; i < newRows.length; i++) {
      var tipo = newRows[i][3];
      var bg   = tipo === 'FE'   ? '#e8f4fd'
               : tipo === 'BUMP' ? '#fff3cd'
               : tipo === 'OTO'  ? '#d9f7e8'
               : null;
      if (bg) ws.getRange(startRow + i, 4, 1, 1).setBackground(bg);
    }
    _autoResize(ws, ORDERS_HEADERS_.length);
  }
  return newRows.length;
}

function _writeProducts(ws, ghlRows) {
  var stats = {};
  for (var i = 0; i < ghlRows.length; i++) {
    var r = ghlRows[i];
    if (!stats[r.product_name]) stats[r.product_name] = { t: r.product_type, c: 0, rev: 0 };
    stats[r.product_name].c++;
    stats[r.product_name].rev += parseFloat(r.amount||0);
  }
  var keys    = Object.keys(stats).sort(function(a,b){ return stats[b].rev - stats[a].rev; });
  var totRev  = keys.reduce(function(s,k){ return s + stats[k].rev; }, 0) || 1;
  var pRows   = [PRODUCTS_HEADERS_];
  for (var i = 0; i < keys.length; i++) {
    var k = keys[i], s = stats[k];
    pRows.push([k, s.t, s.c, _r2(s.rev), _r2(s.rev / totRev * 100)]);
  }
  ws.clearContents();
  ws.getRange(1, 1, pRows.length, pRows[0].length).setValues(pRows);
  _styleHeader(ws, PRODUCTS_HEADERS_.length);
  if (pRows.length > 1) {
    _styleRows(ws, 2, pRows.length - 1, PRODUCTS_HEADERS_.length);
    _formatCurrency(ws, 2, pRows.length - 1, [4]);
    ws.getRange(2, 5, pRows.length - 1, 1).setNumberFormat('0.0"%"');
    // Barra % visiva con color scale
    var pctRange = ws.getRange(2, 5, pRows.length - 1, 1);
    var rule = SpreadsheetApp.newConditionalFormatRule()
      .setGradientMinpoint('#ffffff')
      .setGradientMaxpoint('#e94560')
      .setRanges([pctRange])
      .build();
    ws.setConditionalFormatRules([rule]);
  }
  _autoResize(ws, PRODUCTS_HEADERS_.length);
  return keys.length;
}

function _writeCreatives(ws, adRows) {
  ws.clearContents();
  if (adRows.length === 0) {
    ws.getRange(1, 1, 1, CREATIVES_HEADERS_.length).setValues([CREATIVES_HEADERS_]);
    _styleHeader(ws, CREATIVES_HEADERS_.length);
    return 0;
  }
  var allRows = [CREATIVES_HEADERS_].concat(adRows);
  ws.getRange(1, 1, allRows.length, allRows[0].length).setValues(allRows);
  _styleHeader(ws, CREATIVES_HEADERS_.length);
  _styleRows(ws, 2, adRows.length, CREATIVES_HEADERS_.length);
  _formatCurrency(ws, 2, adRows.length, [5, 9, 10, 12]);  // Spend, CPC, CPM, Revenue
  ws.getRange(2, 8, adRows.length, 1).setNumberFormat('0.00"%"');  // CTR
  _colorROAS(ws, 2, adRows.length, 13);
  // Colora spend per calore
  var spendRange = ws.getRange(2, 5, adRows.length, 1);
  var rule = SpreadsheetApp.newConditionalFormatRule()
    .setGradientMinpoint('#ffffff')
    .setGradientMaxpoint('#e94560')
    .setRanges([spendRange])
    .build();
  ws.setConditionalFormatRules([rule]);
  _autoResize(ws, CREATIVES_HEADERS_.length);
  return adRows.length;
}

function _writeCampaigns(ws, campRows) {
  ws.clearContents();
  if (campRows.length === 0) {
    ws.getRange(1, 1, 1, CAMPAIGNS_HEADERS_.length).setValues([CAMPAIGNS_HEADERS_]);
    _styleHeader(ws, CAMPAIGNS_HEADERS_.length);
    return 0;
  }
  var allRows = [CAMPAIGNS_HEADERS_].concat(campRows);
  ws.getRange(1, 1, allRows.length, allRows[0].length).setValues(allRows);
  _styleHeader(ws, CAMPAIGNS_HEADERS_.length);
  _styleRows(ws, 2, campRows.length, CAMPAIGNS_HEADERS_.length);
  _formatCurrency(ws, 2, campRows.length, [3, 7, 8, 10, 12]);  // Spend, CPC, CPM, Revenue, Budget
  ws.getRange(2, 6, campRows.length, 1).setNumberFormat('0.00"%"');  // CTR
  _colorROAS(ws, 2, campRows.length, 11);
  // Status badge
  for (var i = 0; i < campRows.length; i++) {
    var status = campRows[i][1];
    var bg = status === 'ACTIVE'   ? C_.greenLight
           : status === 'PAUSED'   ? '#fff3cd'
           : status === 'ARCHIVED' ? '#e9ecef'
           : null;
    if (bg) ws.getRange(2 + i, 2, 1, 1).setBackground(bg).setFontWeight('bold');
  }
  _autoResize(ws, CAMPAIGNS_HEADERS_.length);
  return campRows.length;
}

// ── Main ──────────────────────────────────────────────────────────────────────

function runSync(startDate, endDate) {
  var ui = SpreadsheetApp.getUi();
  var p  = _props();

  if (!p.ghlKey || !p.ghlLoc) {
    ui.alert('❌ Credenziali GHL mancanti.\n\nUsa il menu → ⚙️ Configura credenziali.');
    return;
  }

  var ss = SpreadsheetApp.getActiveSpreadsheet();
  try {
    // Recupero dati
    var ghlRows  = _fetchGhlOrders(p, startDate, endDate);
    var fbByDate = _fetchFbInsights(p, startDate, endDate);
    var adRows   = _fetchFbAds(p);
    var campRows = _fetchFbCampaigns(p);

    // Scrittura tab
    var dailyWs    = _ensureSheet(ss, 'Daily Metrics',   DAILY_HEADERS_);
    var ordersWs   = _ensureSheet(ss, 'Orders Log',      ORDERS_HEADERS_);
    var productsWs = _ensureSheet(ss, 'Prodotti',        PRODUCTS_HEADERS_);
    var creativiWs = _ensureSheet(ss, 'Creatività Test', CREATIVES_HEADERS_);
    var campWs     = _ensureSheet(ss, 'Campagne',        CAMPAIGNS_HEADERS_);

    var dAdded = _writeDaily(dailyWs, ghlRows, fbByDate, startDate, endDate);
    var oAdded = _writeOrders(ordersWs, ghlRows);
    var nProd  = _writeProducts(productsWs, ghlRows);
    var nAds   = _writeCreatives(creativiWs, adRows);
    var nCamp  = _writeCampaigns(campWs, campRows);

    ui.alert(
      '✅ Sync completato!\n\n' +
      '📅 ' + startDate + ' → ' + endDate + '\n\n' +
      '📊 Daily Metrics:   +' + dAdded + ' righe\n' +
      '📦 Orders Log:      +' + oAdded + ' righe\n' +
      '🛒 Prodotti:         ' + nProd  + ' prodotti\n' +
      '🎨 Creatività Test:  ' + nAds   + ' annunci (ultime 2 sett.)\n' +
      '📣 Campagne:         ' + nCamp  + ' campagne (ultime 2 sett.)'
    );
  } catch (e) {
    Logger.log('SYNC ERROR: ' + e.toString() + '\n' + (e.stack || ''));
    ui.alert('❌ Errore:\n\n' + e.message);
  }
}
