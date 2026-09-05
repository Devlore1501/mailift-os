/**
 * sheet-webhook.gs — Google Apps Script da incollare nel foglio "Lead Fotovoltaico".
 *
 * Perché Apps Script e non l'API Sheets: il Worker gira su Cloudflare e firmare
 * un JWT di service account a ogni lead è complessità inutile. Qui basta un URL.
 *
 * Setup (5 minuti):
 *  1. Crea un Google Sheet nuovo → Estensioni → Apps Script
 *  2. Incolla questo file, salva
 *  3. Distribuisci → Nuova distribuzione → tipo "App web"
 *       Esegui come: me   |   Accesso: chiunque
 *  4. Copia l'URL /exec e mettilo nel secret SHEET_WEBHOOK_URL del Worker
 *
 * L'URL è pubblico ma non prevedibile e accetta solo append: il rischio è
 * qualcuno che inserisce righe spazzatura, non che legga i lead.
 */

const COLONNE = [
  'ts', 'nome', 'email', 'telefono', 'cap', 'fascia', 'score', 'esito',
  'immobile', 'proprieta', 'tetto', 'bolletta', 'consumo', 'batteria', 'quando',
  'kwp', 'risparmio_anno', 'costo_netto', 'payback_anni',
  'utm_source', 'utm_campaign', 'utm_content', 'landing_url', 'contatto_ok',
];

function doPost(e) {
  try {
    const d = JSON.parse(e.postData.contents);
    const sh = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
    if (sh.getLastRow() === 0) sh.appendRow(COLONNE);
    sh.appendRow(COLONNE.map(function (c) { return d[c] !== undefined ? d[c] : ''; }));
    return ContentService.createTextOutput(JSON.stringify({ ok: true }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ ok: false, error: String(err) }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
