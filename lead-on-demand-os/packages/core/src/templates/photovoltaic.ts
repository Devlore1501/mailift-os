import type { Criterion, QualificationTemplate, ScoreConfig } from "../qualification.js";

// Template iniziale del verticale fotovoltaico residenziale (PRD sez. 8, 15, 16).
// Vive come dato (JSON in tabella qualification_templates), qui c'è solo il seed di default.
export const PV_RESIDENTIAL_TEMPLATE: QualificationTemplate = {
  start: "interested",
  questions: [
    {
      key: "interested",
      text: "Mi conferma che sta valutando l'installazione di un impianto fotovoltaico?",
      type: "boolean",
      options: [
        { value: "true", label: "Sì", next: "owner" },
        { value: "false", label: "No", next: null },
      ],
    },
    {
      key: "owner",
      text: "L'immobile è di sua proprietà?",
      type: "boolean",
      options: [
        { value: "true", label: "Sì", next: "property_type" },
        { value: "false", label: "No", next: "decision_maker" },
      ],
    },
    {
      key: "property_type",
      text: "Che tipo di abitazione è?",
      type: "single",
      options: [
        { value: "villa", label: "Villetta / casa indipendente" },
        { value: "semi", label: "Bifamiliare / schiera" },
        { value: "condo", label: "Appartamento in condominio" },
      ],
      next: "roof_available",
    },
    {
      key: "roof_available",
      text: "Ha un tetto disponibile e di sua proprietà per l'installazione?",
      type: "boolean",
      options: [
        { value: "true", label: "Sì" },
        { value: "false", label: "No" },
      ],
      next: "monthly_bill",
    },
    { key: "monthly_bill", text: "Quanto paga di bolletta al mese, in media?", type: "number", next: "annual_kwh" },
    { key: "annual_kwh", text: "Conosce il consumo annuo in kWh? (opzionale)", type: "number", next: "household_size", required: false },
    { key: "household_size", text: "Quante persone vivono in casa?", type: "number", next: "heat_pump" },
    {
      key: "heat_pump",
      text: "Ha o sta valutando una pompa di calore?",
      type: "boolean",
      options: [
        { value: "true", label: "Sì" },
        { value: "false", label: "No" },
      ],
      next: "electric_car",
    },
    {
      key: "electric_car",
      text: "Ha un'auto elettrica o ibrida plug-in?",
      type: "boolean",
      options: [
        { value: "true", label: "Sì" },
        { value: "false", label: "No" },
      ],
      next: "storage",
    },
    {
      key: "storage",
      text: "È interessato anche all'accumulo (batteria)?",
      type: "boolean",
      options: [
        { value: "true", label: "Sì" },
        { value: "false", label: "No" },
      ],
      next: "motivation",
    },
    {
      key: "motivation",
      text: "Qual è la motivazione principale?",
      type: "single",
      options: [
        { value: "bill", label: "Ridurre la bolletta" },
        { value: "independence", label: "Indipendenza energetica" },
        { value: "incentives", label: "Incentivi / detrazioni" },
        { value: "other", label: "Altro" },
      ],
      next: "timeline",
    },
    {
      key: "timeline",
      text: "In che tempi vorrebbe installare?",
      type: "single",
      options: [
        { value: "lt3m", label: "Entro 3 mesi" },
        { value: "3to6m", label: "Tra 3 e 6 mesi" },
        { value: "gt6m", label: "Oltre 6 mesi" },
        { value: "unknown", label: "Non sa" },
      ],
      next: "decision_maker",
    },
    {
      key: "decision_maker",
      text: "La decisione la prende lei, anche insieme ad altri?",
      type: "boolean",
      options: [
        { value: "true", label: "Sì" },
        { value: "false", label: "No" },
      ],
      next: "quotes_requested",
    },
    {
      key: "quotes_requested",
      text: "Ha già richiesto altri preventivi?",
      type: "single",
      options: [
        { value: "none", label: "Nessuno" },
        { value: "one", label: "Uno" },
        { value: "many", label: "Più di uno" },
      ],
      next: "phone_verified",
    },
    {
      key: "phone_verified",
      text: "Confermo che il numero di telefono è raggiungibile e corretto",
      type: "boolean",
      options: [
        { value: "true", label: "Sì" },
        { value: "false", label: "No" },
      ],
      next: null,
    },
  ],
};

export const PV_RESIDENTIAL_CRITERIA: Criterion[] = [
  { field: "interested", op: "truthy", kind: "MANDATORY", label: "Interessato al fotovoltaico" },
  { field: "owner", op: "truthy", kind: "MANDATORY", label: "Proprietario dell'immobile" },
  { field: "roof_available", op: "truthy", kind: "MANDATORY", label: "Tetto disponibile" },
  { field: "property_type", op: "eq", value: "condo", kind: "EXCLUSION", label: "Appartamento in condominio" },
  { field: "monthly_bill", op: "gte", value: 80, kind: "PREFERRED", label: "Bolletta almeno 80 euro/mese" },
  { field: "timeline", op: "in", value: ["lt3m", "3to6m"], kind: "PREFERRED", label: "Installazione entro 6 mesi" },
];

export const PV_RESIDENTIAL_SCORE: ScoreConfig = {
  rules: [
    { field: "owner", op: "truthy", points: 20, label: "Proprietario" },
    { field: "monthly_bill", op: "gte", value: 100, points: 20, label: "Consumo adeguato" },
    { field: "timeline", op: "eq", value: "lt3m", points: 20, label: "Installazione entro 3 mesi" },
    { field: "decision_maker", op: "truthy", points: 15, label: "Decision maker disponibile" },
    { field: "roof_available", op: "truthy", points: 15, label: "Tetto compatibile" },
    { field: "storage", op: "truthy", points: 5, label: "Interesse accumulo" },
    { field: "phone_verified", op: "truthy", points: 5, label: "Telefono verificato" },
  ],
  thresholds: { hot: 80, qualified: 60, review: 40 },
};

export const PV_BUSINESS_TEMPLATE: QualificationTemplate = {
  start: "company_name",
  questions: [
    { key: "company_name", text: "Ragione sociale dell'azienda?", type: "text", next: "building_owner" },
    {
      key: "building_owner",
      text: "Il capannone / immobile è di proprietà dell'azienda?",
      type: "boolean",
      options: [
        { value: "true", label: "Sì" },
        { value: "false", label: "No" },
      ],
      next: "annual_kwh",
    },
    { key: "annual_kwh", text: "Consumo annuo stimato in kWh?", type: "number", next: "roof_sqm" },
    { key: "roof_sqm", text: "Superficie del tetto in metri quadri?", type: "number", next: "activity_type" },
    { key: "activity_type", text: "Tipologia di attività?", type: "text", next: "sites_count" },
    { key: "sites_count", text: "Numero di sedi?", type: "number", next: "storage" },
    {
      key: "storage",
      text: "Interesse per l'accumulo?",
      type: "boolean",
      options: [
        { value: "true", label: "Sì" },
        { value: "false", label: "No" },
      ],
      next: "timeline",
    },
    {
      key: "timeline",
      text: "Tempistica prevista?",
      type: "single",
      options: [
        { value: "lt3m", label: "Entro 3 mesi" },
        { value: "3to6m", label: "Tra 3 e 6 mesi" },
        { value: "gt6m", label: "Oltre 6 mesi" },
      ],
      next: "decision_maker",
    },
    {
      key: "decision_maker",
      text: "Il referente ha potere decisionale?",
      type: "boolean",
      options: [
        { value: "true", label: "Sì" },
        { value: "false", label: "No" },
      ],
      next: null,
    },
  ],
};

export const PV_BUSINESS_CRITERIA: Criterion[] = [
  { field: "building_owner", op: "truthy", kind: "MANDATORY", label: "Immobile di proprietà" },
  { field: "annual_kwh", op: "gte", value: 20000, kind: "PREFERRED", label: "Consumo almeno 20.000 kWh/anno" },
  { field: "decision_maker", op: "truthy", kind: "PREFERRED", label: "Referente decisionale" },
];

export const PV_BUSINESS_SCORE: ScoreConfig = {
  rules: [
    { field: "building_owner", op: "truthy", points: 25, label: "Immobile di proprietà" },
    { field: "annual_kwh", op: "gte", value: 20000, points: 25, label: "Consumo adeguato" },
    { field: "roof_sqm", op: "gte", value: 200, points: 15, label: "Tetto ampio" },
    { field: "timeline", op: "eq", value: "lt3m", points: 20, label: "Tempistica breve" },
    { field: "decision_maker", op: "truthy", points: 15, label: "Decision maker" },
  ],
  thresholds: { hot: 80, qualified: 60, review: 40 },
};
