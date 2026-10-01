/**
 * Questionario di onboarding cliente lead gen B2B, su Google Forms.
 * Specifica: clients/_mailift-team/ghl-questionario-onboarding-lead-gen.md
 *
 * Uso:
 *   1. script.google.com > Nuovo progetto > incolla questo file.
 *   2. Esegui creaQuestionario() e autorizza (Moduli, Drive, Gmail).
 *   3. Nel log trovi il link da inviare al cliente (pubblico) e il link di modifica.
 *   4. Esegui installaNotificaInvio() una volta sola per ricevere via email
 *      il riepilogo di ogni compilazione.
 *
 * Note di progetto:
 *   - Il modulo raccoglie l'email del compilatore e salva le risposte nel foglio
 *     collegato (Risposte > Collega a Fogli).
 *   - Google Forms non permette di creare da script la domanda "carica file":
 *     le foto, il logo e la contabile si chiedono come link Drive o via email.
 *   - Salti condizionali: le domande "se Altro" restano facoltative sulla stessa
 *     pagina, per non spezzare il modulo in rami.
 */

/* global FormApp, DriveApp, ScriptApp, GmailApp, Logger, PropertiesService */

var NOTIFICA_A_ = 'lorenzo.baretta997@gmail.com';
var PROP_FORM_ID_ = 'ONBOARDING_FORM_ID';

var CRITERIO_ = ['Obbligatorio', 'Desiderabile', 'Eliminatorio', 'Non rilevante'];

// tipo: t testo breve, p paragrafo, n numero, d data, r scelta singola, c caselle,
//       g griglia (righe = criteri, colonne = CRITERIO_), email, tel
// req: true se obbligatoria
var SEZIONI_ = [
  {
    titolo: 'Referenti',
    desc: 'Chi segue il progetto da parte vostra e a chi mandiamo gli avvisi.',
    domande: [
      { t: 't', q: 'Ragione sociale', req: true },
      { t: 't', q: 'Referente commerciale (nome e cognome)', req: true },
      { t: 'tel', q: 'Telefono del referente commerciale', req: true },
      { t: 't', q: 'Referente amministrativo (nome ed email)', req: true },
      { t: 't', q: 'Email che devono ricevere l\'avviso di ogni nuovo lead (anche più di una, separate da virgola)', req: true },
      { t: 't', q: 'Volete l\'avviso anche su WhatsApp? Se sì, indicate il numero', req: false },
      { t: 't', q: 'Chi decide in caso di dubbio sul messaggio degli annunci', req: true }
    ]
  },
  {
    titolo: 'Offerta',
    desc: 'Serve per scrivere annunci che promettono solo quello che il vostro commerciale poi mantiene.',
    domande: [
      { t: 'c', q: 'Con quale formula chiudete di solito?', req: true,
        o: ['Noleggio operativo', 'Acquisto diretto', 'Finanziamento', 'Bandi e incentivi'], altro: true },
      { t: 'p', q: 'Spiegate la formula principale in una frase, come la direste a un cliente', req: true },
      { t: 'p', q: 'Qual è il numero concreto che usate in trattativa (canone, coefficiente, risparmio tipo, durata)?', req: true },
      { t: 'p', q: 'Quali promesse o incentivi NON volete vedere negli annunci?', req: true },
      { t: 'r', q: 'Un lead che preferisce un\'altra formula, lo volete comunque?', req: true,
        o: ['Sì', 'No'], altro: true }
    ]
  },
  {
    titolo: 'Differenziatori e prove',
    desc: 'Cosa vi distingue e cosa possiamo mostrare nelle creatività.',
    domande: [
      { t: 'r', q: 'Siete installatori/produttori diretti o intermediari?', req: true,
        o: ['Diretti', 'Intermediari', 'Entrambi'] },
      { t: 'p', q: 'Numeri verificabili che aumentano la fiducia (anni di attività, impianti realizzati, squadre, certificazioni)', req: true },
      { t: 'p', q: 'Link a recensioni, casi o pagine con foto di lavori reali', req: false },
      { t: 'p', q: 'Link a una cartella Drive con 5–10 foto di lavori reali e il logo in alta risoluzione (condividetela con ' + NOTIFICA_A_ + ')', req: false },
      { t: 'p', q: 'Cosa hanno promesso e non mantenuto agenzie o concorrenti con cui avete lavorato?', req: false }
    ]
  },
  {
    titolo: 'Target',
    desc: 'Chi vogliamo raggiungere e dove.',
    domande: [
      { t: 'p', q: 'Chi è il vostro cliente ideale (tipo di azienda, settore)?', req: true },
      { t: 't', q: 'Soglia minima di consumo o spesa per considerarlo idoneo (esempio: bolletta mensile in euro)', req: true },
      { t: 'p', q: 'Regioni o province prioritarie', req: true },
      { t: 'p', q: 'Zone limitrofe accettabili e fino a dove', req: false },
      { t: 't', q: 'Zone da escludere', req: false },
      { t: 'p', q: 'Chi NON volete (privati, condomini, aziende sotto soglia, settori)', req: true },
      { t: 'c', q: 'Chi decide di solito in azienda?', req: true,
        o: ['Amministratore', 'Titolare', 'Energy manager', 'Responsabile acquisti', 'Varia'] },
      { t: 'n', q: 'Quanti appuntamenti nella stessa zona servono perché valga la trasferta?', req: true }
    ]
  },
  {
    titolo: 'Criteri di qualifica',
    desc: 'Per ogni criterio indicate quanto pesa nel decidere se un lead è buono.',
    domande: [
      { t: 'g', q: 'Importanza di ogni criterio', req: true,
        righe: ['Soglia di spesa o consumo', 'Condizione fisica del sito (esempio: tetto)',
                'Elemento che esclude il lead (esempio: amianto)', 'Solvibilità',
                'Decisore presente o coinvolto', 'Copia di un documento (esempio: bolletta)',
                'Disponibilità dichiarata all\'appuntamento'] },
      { t: 'p', q: 'Altri criteri che per voi sono eliminatori', req: false },
      { t: 'r', q: 'Chi verifica la solvibilità?', req: true, o: ['Voi', 'Noi', 'Entrambi'] },
      { t: 'p', q: 'Quali lead non volete ricevere mai (esempio: chi chiede solo il prezzo al telefono)?', req: true },
      { t: 'p', q: 'Descrivete un lead perfetto che avete avuto: che azienda era, cosa ha chiesto, perché è andato bene', req: true },
      { t: 'p', q: 'Descrivete un lead che vi ha fatto perdere tempo: che azienda era, cosa è successo', req: true }
    ]
  },
  {
    titolo: 'Obiezioni e freni',
    desc: 'Alimenta lo script di qualifica e gli angoli degli annunci. Più siete concreti, meglio è.',
    domande: [
      { t: 'p', q: 'Le 3–5 obiezioni che sentite più spesso', req: true },
      { t: 'p', q: 'Perché chi non ha ancora comprato non l\'ha fatto?', req: true },
      { t: 'p', q: 'Cosa spinge all\'acquisto?', req: true },
      { t: 'p', q: 'L\'argomento con cui chiudete più spesso', req: false }
    ]
  },
  {
    titolo: 'Consegna dei lead',
    desc: 'Come ricevete i contatti qualificati.',
    domande: [
      { t: 'r', q: 'Dove volete ricevere i lead?', req: true,
        o: ['Foglio Excel/Google Sheets condiviso', 'CRM', 'Solo email'], altro: true },
      { t: 't', q: 'Se CRM o altro: quale e come lo integriamo', req: false },
      { t: 'email', q: 'Email Google a cui dare accesso al foglio condiviso', req: false },
      { t: 'p', q: 'Campi extra che volete oltre a nome, azienda, telefono, email e risposte di qualifica', req: false },
      { t: 'r', q: 'Entro quanto ricontattate un lead consegnato?', req: true,
        o: ['Entro 1 ora', 'Entro 4 ore', 'Entro 24 ore', 'Non c\'è una regola'] },
      { t: 'r', q: 'Chi fissa l\'appuntamento?', req: true,
        o: ['Il vostro commerciale', 'Noi per conto vostro'] },
      { t: 'p', q: 'Come vi avvisiamo se un lead non è valido e come lo contestate?', req: false }
    ]
  },
  {
    titolo: 'Volumi e amministrativo',
    desc: 'Ultimo passo.',
    domande: [
      { t: 'n', q: 'Quanti lead qualificati al mese potete gestire senza perderli?', req: true },
      { t: 'n', q: 'Quanti ne vorreste nel primo mese?', req: true },
      { t: 'd', q: 'Da che data potete iniziare a ricevere lead?', req: true },
      { t: 'p', q: 'Dati per la fattura (ragione sociale, P.IVA, codice SDI o PEC)', req: true },
      { t: 'r', q: 'Avete già effettuato il pagamento?', req: true, o: ['Sì', 'No', 'In corso'] },
      { t: 'p', q: 'Altro che dovremmo sapere', req: false },
      { t: 'c', q: 'Conferma', req: true,
        o: ['Confermo che i criteri indicati sono quelli con cui valuterete i lead che riceverò'] }
    ]
  }
];

function creaQuestionario() {
  var form = FormApp.create('Onboarding lead generation, questionario');
  form.setDescription(
    'Questo questionario serve a scrivere gli annunci e lo script di qualifica con le vostre regole, ' +
    'senza una call. Servono circa 10 minuti. Rispondete come rispondereste a un vostro commerciale nuovo: ' +
    'più siete precisi su cosa NON volete, meno lead sprecati riceverete.');
  form.setCollectEmail(true);
  form.setProgressBar(true);
  form.setAllowResponseEdits(true);
  form.setConfirmationMessage('Abbiamo ricevuto tutto. Vi scriviamo quando le campagne sono pronte per la vostra revisione.');

  SEZIONI_.forEach(function (sez, i) {
    if (i > 0) {
      form.addPageBreakItem().setTitle((i + 1) + '. ' + sez.titolo).setHelpText(sez.desc);
    } else {
      form.addSectionHeaderItem().setTitle('1. ' + sez.titolo).setHelpText(sez.desc);
    }
    sez.domande.forEach(function (d) { aggiungiDomanda_(form, d); });
  });

  PropertiesService.getScriptProperties().setProperty(PROP_FORM_ID_, form.getId());
  Logger.log('Link per il cliente: ' + form.getPublishedUrl());
  Logger.log('Link di modifica:    ' + form.getEditUrl());
  return form.getPublishedUrl();
}

function aggiungiDomanda_(form, d) {
  var item;
  switch (d.t) {
    case 't':
      item = form.addTextItem();
      break;
    case 'tel':
      item = form.addTextItem();
      item.setValidation(FormApp.createTextValidation()
        .setHelpText('Inserite un numero di telefono (cifre, spazi, + e trattini).')
        .requireTextMatchesPattern('^[+0-9 ()\\-]{6,20}$').build());
      break;
    case 'email':
      item = form.addTextItem();
      item.setValidation(FormApp.createTextValidation()
        .setHelpText('Inserite un indirizzo email valido.')
        .requireTextIsEmail().build());
      break;
    case 'p':
      item = form.addParagraphTextItem();
      break;
    case 'n':
      item = form.addTextItem();
      item.setValidation(FormApp.createTextValidation()
        .setHelpText('Inserite un numero.')
        .requireNumber().build());
      break;
    case 'd':
      item = form.addDateItem();
      break;
    case 'r':
      item = form.addMultipleChoiceItem();
      item.setChoices(d.o.map(function (x) { return item.createChoice(x); }));
      if (d.altro) item.showOtherOption(true);
      break;
    case 'c':
      item = form.addCheckboxItem();
      item.setChoices(d.o.map(function (x) { return item.createChoice(x); }));
      if (d.altro) item.showOtherOption(true);
      break;
    case 'g':
      item = form.addGridItem();
      item.setRows(d.righe).setColumns(CRITERIO_);
      break;
    default:
      throw new Error('Tipo domanda sconosciuto: ' + d.t);
  }
  item.setTitle(d.q).setRequired(!!d.req);
  return item;
}

/** Da eseguire una volta: manda a Lorenzo un riepilogo a ogni compilazione. */
function installaNotificaInvio() {
  var id = PropertiesService.getScriptProperties().getProperty(PROP_FORM_ID_);
  if (!id) throw new Error('Esegui prima creaQuestionario()');
  var form = FormApp.openById(id);
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'alInvio_') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('alInvio_').forForm(form).onFormSubmit().create();
  Logger.log('Notifica attivata su ' + NOTIFICA_A_);
}

function alInvio_(e) {
  var r = e.response;
  var righe = r.getItemResponses().map(function (ir) {
    var v = ir.getResponse();
    if (Array.isArray(v)) v = v.join(' | ');
    return ir.getItem().getTitle() + '\n' + v + '\n';
  });
  var email = r.getRespondentEmail();
  var azienda = '';
  r.getItemResponses().some(function (ir) {
    if (ir.getItem().getTitle() === 'Ragione sociale') { azienda = ir.getResponse(); return true; }
    return false;
  });
  GmailApp.sendEmail(
    NOTIFICA_A_,
    'Onboarding compilato: ' + (azienda || email),
    'Compilato da ' + email + '\n\n' + righe.join('\n'));
}
